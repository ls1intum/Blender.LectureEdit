import os
import shutil
import subprocess
import tempfile
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


def normalize_audio(paths, config):
    audio_file = paths.rough_audio
    factor = config.audio_normalization(audio_file)
    if factor > 1.0:
        with tempfile.TemporaryDirectory() as d:
            intermediate_file = os.path.join(d, "temp.flac")
            output = subprocess.check_output(
                [
                    "lv2file",
                    "-i",
                    audio_file.os,
                    "-o",
                    intermediate_file,
                    "--ignore-clipping",
                    "-c",
                    "1:in_1",
                    "-c",
                    "1:in_2",
                    "-p",
                    "ingain:17",
                    "http://plugin.org.uk/swh-plugins/fastLookaheadLimiter",
                ]
            )
            # print(output)
            output = subprocess.check_output(["sox", intermediate_file, paths.lecture_audio.os, "remix", "1"])
            # print(output)


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
