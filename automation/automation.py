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
    sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = lecture_edit.scenes(paths)
    lecture_edit.setup_sync_scene(sync_scene, paths, config)
    lecture_edit.setup_cut_scene(cut_scene, paths, config)
    lecture_edit.setup_slides_scene(slides_scene, paths, config)
    if greenscreen_scenes:
        lecture_edit.setup_greenscreen_scenes(greenscreen_scenes, paths, config)
    lecture_edit.setup_merge_scene(merge_scene, greenscreen_scenes, paths, config)


def adjust_slides_videos():
    paths = lecture_edit.Paths(bpy.data.filepath)
    lecture_edit.adjust_slides_videos(paths)


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


def normalize_audio():
    paths = lecture_edit.Paths(bpy.data.filepath)
    lecture_edit.normalize_audio(paths)


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
