import logging

__all__ = ("ensure_audio_strips", "ensure_video_strips", "ensure_scene_strips", "cut_config")


def ensure_audio_strips(sequence_editor, cuts, channel, base_name):
    for strip in __ensure_strips(
        sequence_editor,
        cuts,
        channel,
        base_name,
        path_function=lambda s: s.sound.filepath,
        create_function=lambda n, p, c, s: sequence_editor.sequences.new_sound(
            name=n, filepath=p.blender, channel=c, frame_start=s
        ),
    ):
        strip.show_waveform = True
        yield strip


def _video_helper(sequence_editor, name, path, channel, start):
    strip = sequence_editor.sequences.new_movie(
        name=name, filepath=path.blender, channel=channel, frame_start=start
    )
    strip.filepath = path.blender
    return strip


def ensure_video_strips(sequence_editor, cuts, channel, base_name):
    for strip in __ensure_strips(
        sequence_editor,
        cuts,
        channel,
        base_name,
        path_function=lambda s: s.filepath,
        create_function=lambda n, p, c, s: _video_helper(sequence_editor, n, p, c, s),
    ):
        yield strip


def ensure_scene_strips(sequence_editor, scenes, cuts, channel, base_name):
    for strip in [s for s in sequence_editor.sequences if s.channel == channel]:
        sequence_editor.sequences.remove(strip)
    i = 1
    for scene, path in zip(scenes, cuts):
        cut = cuts[path]
        for offset, start, end in cut:
            strip = sequence_editor.sequences.new_scene(f"{base_name} {i:02}", scene, channel, frame_start=0)
            strip.frame_start = offset
            strip.frame_final_start = start
            strip.frame_final_end = end
            strip.name = f"{base_name} {i:02}"
            strip.channel = channel
            yield strip
            i += 1


def cut_config(paths, sequence_editor, channel):
    result = {}
    for strip in sequence_editor.sequences:
        if strip.channel == channel:
            try:
                path = strip.filepath
            except AttributeError:
                path = strip.sound.filepath
            result.setdefault(paths.from_blender(path).standard, []).append(
                (strip.frame_start, strip.frame_final_start, strip.frame_final_end)
            )
    return {p: sorted(c, key=lambda x: x[1]) for p, c in result.items()}


def __ensure_strips(sequence_editor, cuts, channel, base_name, path_function, create_function):
    strips = list(sequence_editor.sequences)
    frame = 0
    i = 0
    paths = sorted(cuts.keys())
    for path in paths:
        cut = cuts[path]
        candidates = [c for c in strips if c.channel == channel and path_function(c) == path.blender]
        candidates.sort(key=lambda c: c.frame_final_start)
        icandidates = iter(candidates)
        icut = iter(cut)
        for i, (candidate, (offset, start, end)) in enumerate(zip(icandidates, icut), start=i + 1):
            logging.debug(f"found {type(candidate).__name__} strip for {base_name} {i:02}")
            if start is None:
                start = frame
            if end is None:
                end = start + candidate.frame_duration
            candidate.frame_start = offset
            candidate.frame_final_start = start
            candidate.frame_final_end = end
            candidate.name = f"{base_name} {i:02}"
            candidate.channel = channel
            yield candidate
            frame = end
        for candidate in icandidates:
            logging.info(f"deleting unused {type(candidate).__name__} strip {candidate.name}")
            sequence_editor.sequences.remove(candidate)
        for i, (offset, start, end) in enumerate(icut, start=i + 1):
            if start is None:
                start = frame
            strip = create_function(f"{base_name} {i:02}", path, 16, 0)
            if end is None:
                end = start + strip.frame_duration
            if offset is None:
                offset = start
            logging.info(f"created {type(strip).__name__} strip from {path.blender} for {strip.name}")
            strip.frame_start = offset
            strip.frame_final_start = start
            strip.frame_final_end = end
            strip.channel = channel
            yield strip
            frame = end
        for c in candidates:
            strips.remove(c)
