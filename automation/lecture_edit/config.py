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

import json
import logging
import os
import time
from . import pptx
import default_settings

__all__ = ("Config", )


class Config:
    def __init__(self, paths):
        self.__paths = paths
        self.__config_cache = {}
        self.__config_load_times = {}

    def save(self, path, config):
        directory = os.path.dirname(path.os)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(path.os, "w") as f:
            json.dump(config, f, indent=4)
        self.__config_load_times[path] = time.time()
        self.__config_cache[path] = config

    def defaults(self):
        try:
            import bpy
        except ImportError:
            pass
        else:
            if "default_settings.py" in bpy.data.texts:
                return bpy.data.texts["default_settings.py"].as_module()
        return default_settings

    def use_greenscreen(self):
        return bool(self.__paths.greenscreen_videos)

    def cuts(self, name):
        # fmt:off
        config_mapping = {  # maps to configs, that store the cut configuration
            "sync.speaker_audio": (self.__paths.sync_config, "speaker_audio", [self.__paths.speaker_audio], None),
            "sync.speaker_video": (self.__paths.sync_config, "speaker_video", self.__paths.speaker_videos, None),
            "sync.slides_video": (self.__paths.sync_config, "slides_video", self.__paths.slides_videos, None),
            "cut.speaker_audio": (self.__paths.cut_config, "speaker_audio", [self.__paths.speaker_audio], "sync.speaker_audio"),
            "cut.speaker_video": (self.__paths.cut_config, "speaker_video", self.__paths.speaker_videos, "sync.speaker_video"),
        }
        sync_mapping = {  # maps to cut configurations in the sync scene, by which the respective offsets can be determined
            "slides.slides_video": "sync.slides_video",
            "greenscreen.speaker_video": "sync.speaker_video",
            "merge.speaker_video": "sync.speaker_video",
        }
        scene_mapping = {  # maps to cut configurations for the videos, that are the basis of the respective scene
            "merge.greenscreen_scene": "merge.speaker_video",
        }
        # fmt: on
        if name in config_mapping:
            config_path, key, files, fallback = config_mapping[name]
            cut = self.__config_get(config_path, key)
            if cut is None:
                if fallback is not None:
                    return self.cuts(fallback)
                cut = {}
            if files:
                configured = {self.__paths.from_standard(k): v for k, v in cut.items()}
                result = {files[0]: configured.get(files[0], [(0, 1, None)])}
                for p in files[1:]:
                    result[p] = configured.get(p, [(None, None, None)])
                return result
            else:
                return {}
        elif name in sync_mapping:
            # create a data set with one tuple for each file in the respective track in the sync scene
            synced = {}
            for path, cuts in self.cuts(sync_mapping[name]).items():
                first = min(cuts, key=lambda c: c[1])
                last = max(cuts, key=lambda c: c[2])
                offset = first[0]
                drift = (last[0] - first[0]) / (last[2] - first[1])
                start = first[1]
                end = last[2]
                synced[path] = (offset, drift, start, end)
            # compute the cuts
            if self.__paths.speaker_audio is None:
                cut_reference = self.cuts("cut.speaker_video")
                sync_reference = self.cuts("sync.speaker_video")
            else:
                cut_reference = self.cuts("cut.speaker_audio")
                sync_reference = self.cuts("sync.speaker_audio")
            result = {}
            for cut_path, cut_cuts in cut_reference.items():
                cut_cuts = cut_cuts.copy()
                while cut_cuts:
                    cut_offset, cut_start, cut_end = cut_cuts.pop(0)
                    # find the coresponding part of the reference in the sync scene
                    ref_offset = sync_reference[cut_path][0][0]
                    ref_start = cut_start - cut_offset + ref_offset
                    ref_end = cut_end - cut_offset + ref_offset
                    # map the part according to the data in the synced dictionary
                    for synced_path, (
                        synced_offset,
                        synced_drift,
                        synced_start,
                        synced_end,
                    ) in synced.items():
                        if synced_start <= ref_start < synced_end:
                            if ref_end > synced_end:
                                cut_cuts.insert(
                                    0, [cut_offset, synced_end - ref_offset + cut_offset, cut_end]
                                )
                                ref_end = synced_end
                            drift = synced_drift * (ref_start + ref_end - synced_start - synced_end) / 2
                            offset = cut_offset - ref_offset + synced_offset + int(round(drift))
                            start = ref_start - ref_offset + cut_offset
                            end = ref_end - ref_offset + cut_offset
                            result.setdefault(synced_path, []).append([offset, start, end])
            return result
        elif name in scene_mapping:
            return self.cuts(scene_mapping[name])
        else:
            raise ValueError(f"Unknown name: {name}")

    def audio_config(self):
        config = self.__config_get(self.__paths.audio_config, default={})
        # compatibility with older config files from a time, when there was only one high pass frequency
        if "highpass_frequency" in config:
            highpass = config["highpass_frequency"]
            config["highpass_frequencies"] = [highpass] if highpass else []
            del config["highpass_frequency"]
        # get the default values for all values, that are not specified in the config file
        defaults = self.defaults()
        config.setdefault("channel", defaults.audio_channel)
        config.setdefault("highpass_frequencies", defaults.highpass_frequencies)
        config.setdefault("notch_filter_frequencies", defaults.notch_filter_frequencies)
        config.setdefault("notch_filter_q_factor", defaults.notch_filter_q_factor)
        config.setdefault("target_level", defaults.target_level)
        config.setdefault("headroom", defaults.headroom)
        config.setdefault("resolution", defaults.audio_resolution)
        config.setdefault("level_smoothing", defaults.level_smoothing)
        config.setdefault("level_threshold", defaults.level_threshold)
        config.setdefault("limiter_lookahead", defaults.limiter_lookahead)
        return config

    def slide_transitions(self):
        return sorted(self.__config_get(self.__paths.slide_transitions, None, default=[]))

    def slide_titles(self):
        if os.path.isfile(self.__paths.presentation.os):
            for slide_xml in pptx.slide_xmls(self.__paths.presentation):
                body = pptx.xml_find(slide_xml, ["p:cSld", "p:spTree", "p:sp", "p:txBody"])
                if body:
                    node = pptx.xml_find(body, ["a:p"])
                    yield "".join(n.text for n in pptx.xml_walk(node) if n.text is not None)
                else:
                    yield "<picture slide>"
                for i, _ in enumerate(pptx.slide_animations(slide_xml), start=1):
                    yield f"Animation {i}"

    def slide_durations(self, scene, powerpoint=False):
        """yields tuples (total slide duration, [list of animation duration])
        """
        if not powerpoint:
            fps = scene.render.fps
            last_frame = scene.frame_end
            frame = 0
            transitions = iter(self.slide_transitions())
            for slide_xml in pptx.slide_xmls(self.__paths.presentation):
                start = frame
                animations = []
                for _ in pptx.slide_animations(slide_xml):
                    try:
                        t = next(transitions)
                    except StopIteration:
                        break
                    else:
                        animations.append((t - frame) / fps)
                        frame = t
                try:
                    t = next(transitions)
                except StopIteration:
                    t = last_frame
                yield (t - start) / fps, animations
                frame = t
        else:
            correction = self.defaults().fps_correction
            durations = self.slide_durations(scene)
            slide_duration, animation_durations = next(durations)
            for next_ in durations:
                yield int(round(slide_duration / correction * 1000)), [
                    int(round(d / correction * 1000)) for d in animation_durations
                ]
                slide_duration, animation_durations = next_
            yield int(round(slide_duration / correction * 1000)) + 1000, [
                int(round(d / correction * 1000)) for d in animation_durations
            ]

    def optimize_greenscreen_processing(self):
        return self.__config_get(self.__paths.greenscreen_config, "optimize", default=False)

    def greenscreen_perspective(self, path):
        result = self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("perspective distortion", {})
        defaults = self.defaults()
        result.setdefault("Upper Left", tuple(defaults.upper_left))
        result.setdefault("Upper Right", tuple(defaults.upper_right))
        result.setdefault("Lower Left", tuple(defaults.lower_left))
        result.setdefault("Lower Right", tuple(defaults.lower_right))
        return result

    def greenscreen_lens(self, path):
        result = self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("lens distortion", {})
        defaults = self.defaults()
        result.setdefault("Fit", defaults.fit_equalized)
        result.setdefault("Jitter", defaults.jitter_distortion_compensation)
        result.setdefault("Projector", defaults.projector_distortion)
        result.setdefault("Distortion", defaults.distortion_compensation)
        result.setdefault("Dispersion", defaults.dispersion)
        return result

    def greenscreen_keying(self, path):
        result = self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("keying", {})
        defaults = self.defaults()
        result.setdefault("Pre Blur", defaults.pre_blur)
        result.setdefault("Screen Balance", defaults.screen_balance)
        result.setdefault("Despill Factor", defaults.despill_factor)
        result.setdefault("Despill Balance", defaults.despill_balance)
        result.setdefault("Edge Kernel Radius", defaults.edge_kernel_radius)
        result.setdefault("Edge Kernel Tolerance", defaults.edge_kernel_tolerance)
        result.setdefault("Clip Black", defaults.clip_black)
        result.setdefault("Clip White", defaults.clip_white)
        result.setdefault("Dilate/Erode", defaults.dilate_erode)
        result.setdefault("Feather Falloff", defaults.feather_falloff)
        result.setdefault("Feather Distance", defaults.feather_distance)
        result.setdefault("Post Blur", defaults.post_blur)
        result.setdefault("Key Color", tuple(defaults.key_color) + (1.0,) * max(0, 4 - len(defaults.key_color)))
        return result

    def hue_saturation_value(self, path):
        result = self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("color", {})
        defaults = self.defaults()
        result.setdefault("Hue", defaults.speaker_hue)
        result.setdefault("Saturation", defaults.speaker_saturation)
        result.setdefault("Value", defaults.speaker_value)
        return result

    def color_correction(self, path):
        result = self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("color correction", {})
        defaults = self.defaults()
        result.setdefault("Red", defaults.enable_color_correction)
        result.setdefault("Green", defaults.enable_color_correction)
        result.setdefault("Blue", defaults.enable_color_correction)
        result.setdefault("Master Saturation", 1.0)
        result.setdefault("Master Contrast", 1.0)
        result.setdefault("Master Gamma", 1.0)
        result.setdefault("Master Gain", 1.0)
        result.setdefault("Master Lift", 0.0)
        result.setdefault("Highlights Saturation", 1.0)
        result.setdefault("Highlights Contrast", 1.0)
        result.setdefault("Highlights Gamma", 1.0)
        result.setdefault("Highlights Gain", 1.0)
        result.setdefault("Highlights Lift", 0.0)
        result.setdefault("Midtones Saturation", 1.0)
        result.setdefault("Midtones Contrast", 1.0)
        result.setdefault("Midtones Gamma", 1.0)
        result.setdefault("Midtones Gain", 1.0)
        result.setdefault("Midtones Lift", 0.0)
        result.setdefault("Shadows Saturation", 1.0)
        result.setdefault("Shadows Contrast", 1.0)
        result.setdefault("Shadows Gamma", 1.0)
        result.setdefault("Shadows Gain", 1.0)
        result.setdefault("Shadows Lift", 0.0)
        result.setdefault("Midtones Start", 0.2)
        result.setdefault("Midtones End", 0.7)
        return result

    def speaker_placement(self, path):
        result = self.__config_get(self.__paths.merge_config, path.standard, default={})
        defaults = self.defaults()
        result.setdefault("scale", defaults.speaker_scale)
        result.setdefault("shift_x", defaults.speaker_shift_x)
        result.setdefault("shift_y", defaults.speaker_shift_y)
        result.setdefault("crop_left", defaults.speaker_crop_left)
        result.setdefault("crop_right", defaults.speaker_crop_right)
        result.setdefault("crop_top", defaults.speaker_crop_top)
        result.setdefault("crop_bottom", defaults.speaker_crop_bottom)
        return result

    def speaker_visibility_fades(self, fps=25):
        fade = int(round(self.defaults().speaker_fade_time * fps / 2))  # the number of frames at the beginning or end of the slide, that shall be affected by the fade (half the frames for the full fade)
        visibility = self.__config_get(self.__paths.speaker_visibility, default={})
        numbers = sorted(visibility.keys(), key=int)
        if visibility:
            show = visibility[numbers[0]][-1]
            if not show:
                yield (0, 0, show)
            for number, frame in zip(numbers[1:], self.slide_transitions()):
                if visibility[number][-1] != show:
                    show = visibility[number][-1]
                    yield (frame - fade, frame + fade, show)

    def __config_get(self, path, key=None, default=None):
        if os.path.isfile(path.os):
            if path not in self.__config_cache or self.__config_load_times[path] <= path.mtime():
                self.__config_load_times[path] = time.time()
                with open(path.os) as f:
                    self.__config_cache[path] = json.load(f)
            if key is None:
                return self.__config_cache[path]
            else:
                return self.__config_cache[path].get(key, default)
        else:
            return default

    def __get_path(self, blender, paths):
        for path in paths:
            if path.blender == blender:
                return path
        logging.warning(f"did not find path for {blender}")
