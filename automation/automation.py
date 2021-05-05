# automation = bpy.data.texts["automation.py"].as_module()

import os
import sys
import bpy
import logging

if os.path.dirname(bpy.data.texts["automation.py"].filepath) not in sys.path:
    sys.path.append(os.path.dirname(bpy.data.texts["automation.py"].filepath))

# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
logging.debug = print
logging.info = print

import paths
import config
import pptx
import normalization
import external
import sequences
import scenes

import importlib

importlib.reload(paths)
importlib.reload(config)
importlib.reload(pptx)
importlib.reload(external)
importlib.reload(normalization)
importlib.reload(sequences)
importlib.reload(scenes)

paths = paths.Paths(bpy.data.filepath)
config = config.Config(paths)

sync_scene, cut_scene, slides_scene, greenscreen_scenes, merge_scene = scenes.scenes(paths)

#external.adjust_slides_videos(paths)
#scenes.setup_sync_scene(sync_scene, paths, config)
#scenes.save_sync_scene(sync_scene, paths, config)
#scenes.setup_cut_scene(cut_scene, paths, config)
#scenes.save_cut_scene(cut_scene, paths, config)
#external.normalize_audio(paths)
#scenes.setup_slides_scene(slides_scene, paths, config)
#scenes.save_slides_scene(slides_scene, paths, config)
#external.create_presentation(merge_scene, paths, config)
#scenes.setup_greenscreen_scenes(greenscreen_scenes, paths, config)
#scenes.save_greenscreen_scenes(greenscreen_scenes, paths, config)
#external.initialize_speaker_visibility(merge_scene, paths, config)
#scenes.setup_merge_scene(merge_scene, greenscreen_scenes, paths, config)
#scenes.save_merge_scene(merge_scene, paths, config)
