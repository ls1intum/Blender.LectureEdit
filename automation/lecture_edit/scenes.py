import os
import bpy
from . import sequences

__all__ = ("scenes", "setup_sync_scene", "save_sync_scene", "setup_cut_scene", "save_cut_scene", "setup_slides_scene", "save_slides_scene", "setup_greenscreen_scenes", "save_greenscreen_scenes", "setup_merge_scene", "save_merge_scene")


def scenes(paths):
    result = (
        __ensure_scene("Sync"),
        __ensure_scene("Cut"),
        __ensure_scene("Slides"),
        [__ensure_scene(f"Greenscreen {i+1}") for i in range(len(paths.greenscreen_videos))],
        __ensure_scene("Merge"),
    )
    default_scene = bpy.data.scenes.get("Scene")
    if default_scene:
        bpy.data.scenes.remove(default_scene)
    return result


def __ensure_scene(name):
    scene = bpy.data.scenes.get(name)
    if scene is None:
        scene = bpy.data.scenes.new(name)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.fps = 25
    scene.view_settings.view_transform = "Standard"
    return scene


def setup_sync_scene(scene, paths, config):
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    length = 250
    channel = 1
    if paths.speaker_audio is not None:
        for strip in sequences.ensure_audio_strips(
            scene.sequence_editor,
            config.cuts("sync.speaker_audio"),
            channel=channel,
            base_name="Speaker Audio",
        ):
            length = max(length, strip.frame_final_end)
        channel += 1
    for strip in sequences.ensure_audio_strips(
        scene.sequence_editor, config.cuts("sync.speaker_video"), channel=channel, base_name="Speaker Video"
    ):
        length = max(length, strip.frame_final_end)
    channel += 1
    for strip in sequences.ensure_audio_strips(
        scene.sequence_editor, config.cuts("sync.slides_video"), channel=channel, base_name="Slides Video"
    ):
        length = max(length, strip.frame_final_end)
    scene.frame_end = length


def save_sync_scene(scene, paths, config):
    configuration = {}
    channel = 1
    if paths.speaker_audio is not None:
        configuration["speaker_audio"] = sequences.cut_config(paths, scene.sequence_editor, channel=channel)
        channel += 1
    if paths.speaker_videos or paths.greenscreen_video:
        configuration["speaker_video"] = sequences.cut_config(paths, scene.sequence_editor, channel=channel)
    channel += 1
    if paths.slides_videos:
        configuration["slides_video"] = sequences.cut_config(paths, scene.sequence_editor, channel=channel)
    config.save(paths.sync_config, configuration)


def setup_cut_scene(scene, paths, config):
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    length = 250
    if paths.speaker_audio is not None:
        for strip in sequences.ensure_audio_strips(
            scene.sequence_editor, config.cuts("cut.speaker_audio"), channel=1, base_name="Speaker Audio"
        ):
            length = max(length, strip.frame_final_end)
    else:
        for strip in sequences.ensure_audio_strips(
            scene.sequence_editor, config.cuts("cut.speaker_video"), channel=1, base_name="Speaker Video"
        ):
            length = max(length, strip.frame_final_end)
    scene.frame_end = length


def save_cut_scene(scene, paths, config):
    configuration = {}
    key = "speaker_audio" if paths.speaker_audio is not None else "speaker_video"
    configuration[key] = sequences.cut_config(paths, scene.sequence_editor, channel=1)
    config.save(paths.cut_config, configuration)


def setup_slides_scene(scene, paths, config):
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    length = 250
    if os.path.isfile(paths.lecture_audio.os):
        for strip in sequences.ensure_audio_strips(
            scene.sequence_editor, {paths.lecture_audio: [(0, 1, None)]}, channel=1, base_name="Lecture Audio"
        ):
            length = max(length, strip.frame_final_end)
    elif os.path.isfile(paths.rough_audio.os):
        for strip in sequences.ensure_audio_strips(
            scene.sequence_editor, {paths.rough_audio: [(0, 1, None)]}, channel=1, base_name="Rough Audio"
        ):
            length = max(length, strip.frame_final_end)
    if paths.slides_videos:
        for strip in sequences.ensure_video_strips(
            scene.sequence_editor, config.cuts("slides.slides_video"), channel=2, base_name="Slides Video"
        ):
            length = max(length, strip.frame_final_end)
    scene.frame_end = length
    setup_slide_markers(scene, config)


def setup_slide_markers(scene, config):
    if not scene.timeline_markers:
        for frame in config.slide_transitions():
            scene.timeline_markers.new(f"m{frame}", frame=frame)
    slide_titles = config.slide_titles()
    try:
        next(slide_titles)
    except StopIteration:
        pass
    else:
        markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
        for marker, title in zip(markers, slide_titles):
            marker.name = title


def save_slides_scene(scene, paths, config):
    if scene.timeline_markers:
        config.save(paths.slide_transitions, sorted([m.frame for m in scene.timeline_markers]))


def setup_greenscreen_scenes(scenes, paths, config):
    for scene, path in zip(scenes, sorted(paths.greenscreen_videos)):
        scene.use_nodes = True
        # create the nodes
        nodes = scene.node_tree.nodes
        node_types = [
            ("Movie Clip", "CompositorNodeMovieClip"),
            ("Keying", "CompositorNodeKeying"),
            ("Hue Saturation Value", "CompositorNodeHueSat"),
            ("Alpha Convert", "CompositorNodePremulKey"),
            ("Composite", "CompositorNodeComposite"),
            ("Split Viewer", "CompositorNodeSplitViewer"),
        ]
        clip, keying, color, converter, composite, viewer = (
            nodes[n] if n in nodes else nodes.new(t) for n, t in node_types
        )
        clip.location = (-700, 590)
        keying.location = (-330, 580)
        color.location = (-40, 605)
        converter.location = (250, 630)
        composite.location = (530, 630)
        viewer.location = (250, 340)
        # delete surplus nodes
        for node in [node for node in nodes if node.name not in dict(node_types)]:
            nodes.remove(node)
        # create the connections
        connections = [
            (clip.outputs["Image"], keying.inputs["Image"]),
            (keying.outputs["Matte"], viewer.inputs[1]),
            (keying.outputs["Image"], color.inputs["Image"]),
            (color.outputs["Image"], converter.inputs["Image"]),
            (converter.outputs["Image"], composite.inputs["Image"]),
            (color.outputs["Image"], viewer.inputs[0]),
        ]
        for fr, to in connections:
            for c in scene.node_tree.links:
                if (
                    c.from_node.name == fr.node.name
                    and c.from_socket.identifier == fr.identifier
                    and c.to_node.name == to.node.name
                    and c.to_socket.identifier == to.identifier
                ):
                    break
            else:
                scene.node_tree.links.new(fr, to)
        # restore the settings
        if clip.clip is None:
            clip.clip = bpy.data.movieclips.load(path.blender)
        kconfig = config.greenscreen_keying(path)
        keying.despill_balance = kconfig.get("Despill Balance", 0.8)
        keying.edge_kernel_radius = kconfig.get("Edge Kernel Radius", keying.edge_kernel_radius)
        keying.edge_kernel_tolerance = kconfig.get("Edge Kernel Tolerance", 0.3)
        keying.clip_black = kconfig.get("Clip Black", 0.2)
        keying.clip_white = kconfig.get("Clip White", 0.9)
        keying.dilate_distance = kconfig.get("Dilate/Erode", keying.dilate_distance)
        keying.inputs["Key Color"].default_value.foreach_set(
            kconfig.get("Key Color", keying.inputs["Key Color"].default_value)
        )
        cconfig = config.color_correction(path)
        color.inputs["Saturation"].default_value = cconfig.get(
            "Saturation", color.inputs["Saturation"].default_value
        )
        # set the start and the end of the scene
        scene.frame_start = 0
        scene.frame_end = clip.clip.frame_duration


def save_greenscreen_scenes(scenes, paths, config):
    gs_config = {}
    for scene, path in zip(scenes, paths.greenscreen_videos):
        s_config = {"keying": {}, "color": {}}
        if "Keying" in scene.node_tree.nodes:
            node = scene.node_tree.nodes["Keying"]
            s_config["keying"]["Despill Balance"] = node.despill_balance
            s_config["keying"]["Edge Kernel Radius"] = node.edge_kernel_radius
            s_config["keying"]["Edge Kernel Tolerance"] = node.edge_kernel_tolerance
            s_config["keying"]["Clip Black"] = node.clip_black
            s_config["keying"]["Clip White"] = node.clip_white
            s_config["keying"]["Dilate/Erode"] = node.dilate_distance
            s_config["keying"]["Key Color"] = tuple(node.inputs["Key Color"].default_value)
        if "Hue Saturation Value" in scene.node_tree.nodes:
            node = scene.node_tree.nodes["Hue Saturation Value"]
            s_config["color"]["Saturation"] = node.inputs["Saturation"].default_value
        gs_config[path.standard] = s_config
    config.save(paths.greenscreen_config, gs_config)


def setup_merge_scene(scene, greenscreen_scenes, paths, config):
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    length = 250
    # Audio
    if os.path.isfile(paths.lecture_audio.os):
        strips = sequences.ensure_audio_strips(
            scene.sequence_editor, {paths.lecture_audio: [(0, 1, None)]}, channel=1, base_name="Audio"
        )
    elif os.path.isfile(paths.rough_audio.os):
        strips = sequences.ensure_audio_strips(
            scene.sequence_editor, {paths.rough_audio: [(0, 1, None)]}, channel=1, base_name="Audio"
        )
    else:
        strips = sequences.ensure_audio_strips(
            scene.sequence_editor, config.cuts("cut.speaker_videp"), channel=1, base_name="Audio"
        )
    for strip in strips:
        length = max(length, strip.frame_final_end)
    # Slides
    for strip in sequences.ensure_video_strips(
        scene.sequence_editor, {paths.presentation_video: [(0, 1, length)]}, channel=2, base_name="Slides"
    ):
        length = max(length, strip.frame_final_end)
    # Speaker
    for strip in [s for s in scene.sequence_editor.sequences if s.channel == 4]:
        scene.sequence_editor.sequences.remove(strip)
    if paths.greenscreen_videos:
        strips = sequences.ensure_scene_strips(
            scene.sequence_editor,
            greenscreen_scenes,
            config.cuts("merge.greenscreen_scene"),
            channel=3,
            base_name="Speaker",
        )
    else:
        strips = sequences.ensure_video_strips(
            scene.sequence_editor, config.cuts("merge.speaker_video"), channel=3, base_name="Speaker"
        )
    for i, strip in enumerate(strips, start=1):
        # configure the movie/scene strip
        strip.mute = True
        length = max(length, strip.frame_final_end)
        # create the effect strip for tranlating and cropping
        speaker_placement = config.speaker_placement(paths.from_strip(strip))
        effect_strip = scene.sequence_editor.sequences.new_effect(
            name=f"SpeakerPIP {i:02}", type="TRANSFORM", channel=4, frame_start=strip.frame_start, seq1=strip
        )
        effect_strip.blend_type = "ALPHA_OVER"
        effect_strip.interpolation = "BICUBIC"
        effect_strip.use_uniform_scale = True
        effect_strip.scale_start_x = speaker_placement["scale"]
        effect_strip.scale_start_y = speaker_placement["scale"]
        effect_strip.crop.min_x = speaker_placement["crop_left"]
        effect_strip.crop.max_x = speaker_placement["crop_right"]
        effect_strip.crop.min_y = speaker_placement["crop_bottom"]
        effect_strip.crop.max_y = speaker_placement["crop_top"]
        effect_strip.transform.offset_x = speaker_placement["shift_x"]
        effect_strip.transform.offset_y = speaker_placement["shift_y"]
        # configure the fades for speaker visibility
        shown = True
        last_end = 0
        for start, end, show in config.speaker_visibility_fades(fps=scene.render.fps):
            if last_end <= effect_strip.frame_final_start < start:
                if not shown:
                    effect_strip.blend_alpha = 0.0
                    effect_strip.keyframe_insert(
                        data_path="blend_alpha",
                        frame=effect_strip.frame_final_start,
                        group=f"speaker_visibility {i}",
                    )
            if (
                start <= effect_strip.frame_final_start < end
                or effect_strip.frame_final_start < start < effect_strip.frame_final_end
            ):
                effect_strip.blend_alpha = 0.0 if show else 1.0
                effect_strip.keyframe_insert(
                    data_path="blend_alpha", frame=start, group=f"speaker_visibility {i}"
                )
                effect_strip.blend_alpha = 1.0 if show else 0.0
                effect_strip.keyframe_insert(
                    data_path="blend_alpha", frame=end, group=f"speaker_visibility {i}"
                )
            last_end = end
            shown = show
    # Speaker placement reference
    if 5 not in [s.channel for s in scene.sequence_editor.sequences]:
        strip = scene.sequence_editor.sequences.new_image(
            name="Speaker Placement", filepath=paths.speaker_placement.blender, channel=5, frame_start=1
        )
        strip.blend_type = "ALPHA_OVER"
        strip.blend_alpha = 0.5
        strip.frame_final_end = length
        if os.path.isfile(paths.merge_config.os):
            strip.mute = True
    # load the slide transitions and titles
    scene.timeline_markers.clear()
    setup_slide_markers(scene, config)
    # configure the render settings
    scene.frame_end = length
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "VORBIS"
    scene.render.ffmpeg.audio_bitrate = 128
    scene.render.ffmpeg.audio_channels = "MONO"
    scene.render.ffmpeg.audio_mixrate = 44100
    scene.render.filepath = paths.lecture_video.blender


def save_merge_scene(scene, paths, config):
    all_strips = {}
    for s in scene.sequence_editor.sequences:
        if s.channel == 4:
            all_strips.setdefault(paths.from_strip(s), []).append(s)
    result = {}
    for path, strips in all_strips.items():
        effect_strip = min([s for s in strips], key=lambda s: s.frame_final_start)
        result[path.standard] = {
            "scale": effect_strip.scale_start_x,
            "crop_left": effect_strip.crop.min_x,
            "crop_right": effect_strip.crop.max_x,
            "crop_bottom": effect_strip.crop.min_y,
            "crop_top": effect_strip.crop.max_y,
            "shift_x": effect_strip.transform.offset_x,
            "shift_y": effect_strip.transform.offset_y,
        }
    config.save(paths.merge_config, result)
