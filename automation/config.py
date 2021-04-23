import datetime
import json
import logging
import os
import time
import pptx


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

    def audio_normalization(self, audio_file=None):
        reference = max(
            self.__config_get(self.__paths.audio_reference, "analysis"),
            key=lambda r: datetime.datetime.fromisoformat(r["timestamp"]),
        )
        if audio_file is None:
            audio_file = self.__paths.rough_audio
        analyses = self.__config_get(self.__paths.audio_config, "analysis")
        analyses = filter(lambda r: r["file"] == os.path.basename(audio_file.blender), analyses)
        analysis = max(analyses, key=lambda r: datetime.datetime.fromisoformat(r["timestamp"]))
        quantity = "active speech level [A]"
        quantity = "level [A]"
        return reference[quantity] / analysis[quantity]

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
        """yields tuples (total slide duration, [list of animation duration])"""
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
            # compute a correction factor for the weird frame rate, at which Powerpoint exports their videos
            # fmt:off
            correction = 85918 / 70845  # the actual number of frames divided by the expected number of frames for Hugo's keynote (without any correction factor)
            correction *= 70832 / 70845 # the actual number of frames divided by the expected number of frames for Hugo's keynote (after applying the previous correction factor)
            # correction = 1
            # fmt:on
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

    def greenscreen_keying(self, path):
        return self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("keying", {})

    def color_correction(self, path):
        return self.__config_get(self.__paths.greenscreen_config, path.standard, default={}).get("color", {})

    def speaker_placement(self, path):
        result = self.__config_get(self.__paths.merge_config, path.standard, default={})
        result.setdefault("scale", 0.5)
        result.setdefault("crop_left", 0)
        result.setdefault("crop_right", 0)
        result.setdefault("crop_bottom", 0)
        result.setdefault("crop_top", 0)
        result.setdefault("shift_x", 650)
        result.setdefault("shift_y", -280)
        return result

    def speaker_visibility_fades(self, fps=25):
        fade = int(round(1.0 * fps / 2))
        visibility = self.__config_get(self.__paths.speaker_visibility)
        numbers = sorted(visibility.keys(), key=int)
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
