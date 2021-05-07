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
import subprocess
from . import normalization
from . import pptx

__all__ = ("adjust_slides_videos", "normalize_audio", "create_presentation", "initialize_speaker_visibility")


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
    settings = config.audio_config()
    normalization.normalize(
        source=paths.rough_audio.os,
        target=paths.lecture_audio.os,
        channel=settings["channel"],
        highpass_frequency=settings["highpass_frequency"],
        target_level=settings["target_level"],
        headroom=settings["headroom"],
        resolution=settings["resolution"],
        level_smoothing=settings["level_smoothing"],
        level_threshold=settings["level_threshold"],
        limiter_lookahead=settings["limiter_lookahead"],
        show_progress=False
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
