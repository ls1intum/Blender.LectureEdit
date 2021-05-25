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


# automation = bpy.data.texts["automation.py"].as_module()

import logging
import os
import sys
import bpy

if os.path.dirname(bpy.data.texts["automation.py"].filepath) not in sys.path:
    sys.path.append(os.path.dirname(bpy.data.texts["automation.py"].filepath))
import lecture_edit
lecture_edit.reload()

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def setup():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    # create and initialize the scenes
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.setup_sync_scene(sync_scene, paths, config)
    lecture_edit.setup_cut_scene(cut_scene, paths, config)
    if os.path.isfile(paths.sync_config.os) and os.path.isfile(paths.cut_config.os):
        lecture_edit.setup_slides_scene(slides_scene, paths, config)
    if greenscreen_scenes:
        lecture_edit.setup_greenscreen_scenes(greenscreen_scenes, paths, config)
    if os.path.isfile(paths.sync_config.os) and os.path.isfile(paths.cut_config.os):
        lecture_edit.setup_merge_scene(merge_scene, greenscreen_scenes, paths, config)
    # create missing config files
    if not os.path.isfile(paths.audio_config.os):
        config.save(paths.audio_config, config.audio_config())
    if not os.path.isfile(paths.speaker_visibility.os) and os.path.isfile(paths.slide_transitions.os):
        lecture_edit.initialize_speaker_visibility(merge_scene, paths, config)


def convert_slides_videos():
    paths = lecture_edit.Paths(bpy.data.filepath)
    lecture_edit.convert_slides_videos(paths)


def save_sync_scene():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.save_sync_scene(sync_scene, paths, config)
    lecture_edit.setup_sync_scene(sync_scene, paths, config)


def save_cut_scene():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.save_cut_scene(cut_scene, paths, config)
    lecture_edit.setup_cut_scene(cut_scene, paths, config)
    if not os.path.isfile(paths.audio_config.os):
        config.save(paths.audio_config, config.audio_config())


def normalize_audio():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    lecture_edit.normalize_audio(paths, config)


def save_slides_scene():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.save_slides_scene(slides_scene, paths, config)
    lecture_edit.setup_slides_scene(slides_scene, paths, config)


def create_presentation():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.create_presentation(merge_scene, paths, config)


def save_greenscreen_scenes():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.save_greenscreen_scenes(greenscreen_scenes, paths, config)
    lecture_edit.setup_greenscreen_scenes(greenscreen_scenes, paths, config)


def initialize_speaker_visibility():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.initialize_speaker_visibility(merge_scene, paths, config)


def save_merge_scene():
    paths = lecture_edit.Paths(bpy.data.filepath)
    config = lecture_edit.Config(paths)
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.save_merge_scene(merge_scene, paths, config)
    lecture_edit.setup_merge_scene(merge_scene, greenscreen_scenes, paths, config)
    if not os.path.isfile(paths.speaker_visibility.os) and os.path.isfile(paths.slide_transitions.os):
        lecture_edit.initialize_speaker_visibility(merge_scene, paths, config)
