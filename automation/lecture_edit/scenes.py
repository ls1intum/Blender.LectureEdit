# Copyright 2020-2021 Jonas Schulte-Coerne and the CYSTINET-Africa project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import bpy
from . import sequences

__all__ = ("scenes", "setup_sync_scene", "save_sync_scene", "setup_cut_scene", "save_cut_scene", "setup_slides_scene", "save_slides_scene", "setup_greenscreen_scenes", "save_greenscreen_scenes", "setup_merge_scene", "save_merge_scene")


def scenes(paths, config):
    defaults = config.defaults()
    result = (
        __ensure_scene("Sync", defaults.width, defaults.height, defaults.fps),
        __ensure_scene("Cut", defaults.width, defaults.height, defaults.fps),
        __ensure_scene("Slides", defaults.width, defaults.height, defaults.fps),
        [__ensure_scene(f"Greenscreen {i+1}", defaults.width, defaults.height, defaults.fps) for i in range(len(paths.greenscreen_videos))],
        __ensure_scene("Merge", defaults.width, defaults.height, defaults.fps),
    )
    default_scene = bpy.data.scenes.get("Scene")
    if default_scene:
        bpy.data.scenes.remove(default_scene)
    return result


def __ensure_scene(name, width, height, fps):
    scene = bpy.data.scenes.get(name)
    if scene is None:
        scene = bpy.data.scenes.new(name)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = fps
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
            ("Color Correction", "CompositorNodeColorCorrection"),
            ("Hue Saturation Value", "CompositorNodeHueSat"),
            ("Alpha Convert", "CompositorNodePremulKey"),
            ("Composite", "CompositorNodeComposite"),
            ("Switch", "CompositorNodeSwitch"),
            ("Split Viewer", "CompositorNodeSplitViewer"),
        ]
        clip, keying, color_correction, hsv, converter, composite, switch, viewer = (
            nodes[n] if n in nodes else nodes.new(t) for n, t in node_types
        )
        clip.location = (-800, 350)
        keying.location = (-530, 580)
        color_correction.location = (-240, 800)
        hsv.location = (300, 630)
        converter.location = (550, 630)
        composite.location = (800, 630)
        switch.location = (580, 250)
        viewer.location = (800, 140)
        # delete surplus nodes
        for node in [node for node in nodes if node.name not in dict(node_types)]:
            nodes.remove(node)
        # create the connections
        connections = [
            (clip.outputs["Image"], keying.inputs["Image"]),
            (clip.outputs["Image"], viewer.inputs[1]),
            (keying.outputs["Matte"], switch.inputs["On"]),
            (keying.outputs["Image"], color_correction.inputs["Image"]),
            (color_correction.outputs["Image"], hsv.inputs["Image"]),
            (hsv.outputs["Image"], converter.inputs["Image"]),
            (hsv.outputs["Image"], switch.inputs["Off"]),
            (converter.outputs["Image"], composite.inputs["Image"]),
            (switch.outputs["Image"], viewer.inputs[0]),
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
        keying.blur_pre = kconfig["Pre Blur"]
        keying.screen_balance = kconfig["Screen Balance"]
        keying.despill_factor = kconfig["Despill Factor"]
        keying.despill_balance = kconfig["Despill Balance"]
        keying.edge_kernel_radius = kconfig["Edge Kernel Radius"]
        keying.edge_kernel_tolerance = kconfig["Edge Kernel Tolerance"]
        keying.clip_black = kconfig["Clip Black"]
        keying.clip_white = kconfig["Clip White"]
        keying.dilate_distance = kconfig["Dilate/Erode"]
        keying.feather_falloff = kconfig["Feather Falloff"]
        keying.feather_distance = kconfig["Feather Distance"]
        keying.blur_post = kconfig["Post Blur"]
        keying.inputs["Key Color"].default_value.foreach_set(tuple(kconfig["Key Color"]) + (1.0,) * (4 - len(kconfig["Key Color"])))
        sconfig = config.hue_saturation_value(path)
        hsv.inputs["Hue"].default_value = sconfig["Hue"]
        hsv.inputs["Saturation"].default_value = sconfig["Saturation"]
        hsv.inputs["Value"].default_value = sconfig["Value"]
        cconfig = config.color_correction(path)
        color_correction.red = cconfig["Red"]
        color_correction.green = cconfig["Green"]
        color_correction.blue = cconfig["Blue"]
        color_correction.master_saturation = cconfig["Master Saturation"]
        color_correction.master_contrast = cconfig["Master Contrast"]
        color_correction.master_gamma = cconfig["Master Gamma"]
        color_correction.master_gain = cconfig["Master Gain"]
        color_correction.master_lift = cconfig["Master Lift"]
        color_correction.highlights_saturation = cconfig["Highlights Saturation"]
        color_correction.highlights_contrast = cconfig["Highlights Contrast"]
        color_correction.highlights_gamma = cconfig["Highlights Gamma"]
        color_correction.highlights_gain = cconfig["Highlights Gain"]
        color_correction.highlights_lift = cconfig["Highlights Lift"]
        color_correction.midtones_saturation = cconfig["Midtones Saturation"]
        color_correction.midtones_contrast = cconfig["Midtones Contrast"]
        color_correction.midtones_gamma = cconfig["Midtones Gamma"]
        color_correction.midtones_gain = cconfig["Midtones Gain"]
        color_correction.midtones_lift = cconfig["Midtones Lift"]
        color_correction.shadows_saturation = cconfig["Shadows Saturation"]
        color_correction.shadows_contrast = cconfig["Shadows Contrast"]
        color_correction.shadows_gamma = cconfig["Shadows Gamma"]
        color_correction.shadows_gain = cconfig["Shadows Gain"]
        color_correction.shadows_lift = cconfig["Shadows Lift"]
        color_correction.midtones_start = cconfig["Midtones Start"]
        color_correction.midtones_end = cconfig["Midtones End"]
        # set the start and the end of the scene
        scene.frame_start = 0
        scene.frame_end = clip.clip.frame_duration


def save_greenscreen_scenes(scenes, paths, config):
    gs_config = {}
    for scene, path in zip(scenes, paths.greenscreen_videos):
        s_config = {"keying": {}, "color": {}, "color correction": {}}
        if "Keying" in scene.node_tree.nodes:
            node = scene.node_tree.nodes["Keying"]
            s_config["keying"]["Pre Blur"] = node.blur_pre
            s_config["keying"]["Screen Balance"] = node.screen_balance
            s_config["keying"]["Despill Balance"] = node.despill_balance
            s_config["keying"]["Despill Factor"] = node.despill_factor
            s_config["keying"]["Edge Kernel Radius"] = node.edge_kernel_radius
            s_config["keying"]["Edge Kernel Tolerance"] = node.edge_kernel_tolerance
            s_config["keying"]["Clip Black"] = node.clip_black
            s_config["keying"]["Clip White"] = node.clip_white
            s_config["keying"]["Dilate/Erode"] = node.dilate_distance
            s_config["keying"]["Feather Falloff"] = node.feather_falloff
            s_config["keying"]["Feather Distance"] = node.feather_distance
            s_config["keying"]["Post Blur"] = node.blur_post
            s_config["keying"]["Key Color"] = tuple(node.inputs["Key Color"].default_value)[0:3]
        if "Hue Saturation Value" in scene.node_tree.nodes:
            node = scene.node_tree.nodes["Hue Saturation Value"]
            s_config["color"]["Hue"] = node.inputs["Hue"].default_value
            s_config["color"]["Saturation"] = node.inputs["Saturation"].default_value
            s_config["color"]["Value"] = node.inputs["Value"].default_value
        if "Color Correction" in scene.node_tree.nodes:
            node = scene.node_tree.nodes["Color Correction"]
            s_config["color correction"]["Red"] = node.red
            s_config["color correction"]["Green"] = node.green
            s_config["color correction"]["Blue"] = node.blue
            s_config["color correction"]["Master Saturation"] = node.master_saturation
            s_config["color correction"]["Master Contrast"] = node.master_contrast
            s_config["color correction"]["Master Gamma"] = node.master_gamma
            s_config["color correction"]["Master Gain"] = node.master_gain
            s_config["color correction"]["Master Lift"] = node.master_lift
            s_config["color correction"]["Highlights Saturation"] = node.highlights_saturation
            s_config["color correction"]["Highlights Contrast"] = node.highlights_contrast
            s_config["color correction"]["Highlights Gamma"] = node.highlights_gamma
            s_config["color correction"]["Highlights Gain"] = node.highlights_gain
            s_config["color correction"]["Highlights Lift"] = node.highlights_lift
            s_config["color correction"]["Midtones Saturation"] = node.midtones_saturation
            s_config["color correction"]["Midtones Contrast"] = node.midtones_contrast
            s_config["color correction"]["Midtones Gamma"] = node.midtones_gamma
            s_config["color correction"]["Midtones Gain"] = node.midtones_gain
            s_config["color correction"]["Midtones Lift"] = node.midtones_lift
            s_config["color correction"]["Shadows Saturation"] = node.shadows_saturation
            s_config["color correction"]["Shadows Contrast"] = node.shadows_contrast
            s_config["color correction"]["Shadows Gamma"] = node.shadows_gamma
            s_config["color correction"]["Shadows Gain"] = node.shadows_gain
            s_config["color correction"]["Shadows Lift"] = node.shadows_lift
            s_config["color correction"]["Midtones Start"] = node.midtones_start
            s_config["color correction"]["Midtones End"] = node.midtones_end
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
            scene.sequence_editor, config.cuts("cut.speaker_video"), channel=1, base_name="Audio"
        )
    for strip in strips:
        length = max(length, strip.frame_final_end)
    # Slides
    for strip in [s for s in scene.sequence_editor.sequences if s.channel == 2]:  # it is more reliable, if the slides video is purged before loading the current one
        scene.sequence_editor.sequences.remove(strip)
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
        effect_strip.transform.offset_x = speaker_placement["shift_x"]
        effect_strip.transform.offset_y = speaker_placement["shift_y"]
        effect_strip.crop.min_x = speaker_placement["crop_left"]
        effect_strip.crop.max_x = speaker_placement["crop_right"]
        effect_strip.crop.max_y = speaker_placement["crop_top"]
        effect_strip.crop.min_y = speaker_placement["crop_bottom"]
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
    defaults = config.defaults()
    scene.frame_end = length
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = defaults.container
    scene.render.ffmpeg.codec = defaults.video_codec
    scene.render.ffmpeg.constant_rate_factor = defaults.video_quality
    scene.render.ffmpeg.ffmpeg_preset = defaults.encoding_speed
    scene.render.ffmpeg.audio_codec = defaults.audio_codec
    scene.render.ffmpeg.audio_bitrate = defaults.audio_bitrate
    scene.render.ffmpeg.audio_channels = "MONO"
    scene.render.ffmpeg.audio_mixrate = defaults.sampling_rate
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
            "shift_x": effect_strip.transform.offset_x,
            "shift_y": effect_strip.transform.offset_y,
            "crop_left": effect_strip.crop.min_x,
            "crop_right": effect_strip.crop.max_x,
            "crop_top": effect_strip.crop.max_y,
            "crop_bottom": effect_strip.crop.min_y,
        }
    config.save(paths.merge_config, result)
