import os
import subprocess
import normalization
import pptx


def adjust_slides_videos(paths):
    for path in paths.raw_slides_videos:
        filename = os.path.splitext(os.path.basename(path.os))[0]
        command = [
            "/usr/local/bin/ffmpeg",
            "-i",
            str(path.os),
            "-vf",
            "scale=1920x1080,fps=25",
            str((paths.source_path / f"{filename}.mp4").os),
        ]
        print(" ".join(command))
        output = subprocess.check_output(command)


def normalize_audio(paths):
    normalization.normalize(
        source=paths.rough_audio.os,
        target=paths.lecture_audio.os,
        channel=1,
        highpass_frequency=100.0,
        target_level=-20.0,
        headroom=-0.1,
        resolution=16,
        level_smoothing=10.0,
        level_threshold=-10.0,
        limiter_lookahead=0.025
    )


def create_presentation(scene, paths, config):
    pptx.create_presentation(
        source_file=paths.presentation,
        target_file=paths.lecture_presentation,
        durations=config.slide_durations(scene, powerpoint=True),
    )


def initialize_speaker_visibility(scene, paths, config):
    titles = config.slide_titles()
    durations = config.slide_durations(scene)
    i = 1
    visibility = {}
    t = 0
    for d, a in durations:
        t += d
        visibility[i] = [next(titles), t, True]
        i += 1
        for n in a:
            visibility[i] = [next(titles), n, True]
            i += 1
    config.save(paths.speaker_visibility, visibility)
