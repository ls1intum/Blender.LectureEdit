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
import pathlib

__all__ = ("Path", "Paths")


class Path:
    def __init__(self, relative_path, base_path):
        os_path = pathlib.Path(base_path).resolve() / relative_path.lstrip(os.sep)
        # resolve, if the file is a .link file
        if os_path.suffix == ".link":
            with open(os_path) as f:
                path = pathlib.Path(f.read().strip())
            if path.is_absolute():
                os_path = path.resolve()
            else:
                os_path = (os_path.parent / path).resolve()
        self.blender = "//" + os.path.relpath(os_path, start=base_path)
        self.os = os_path
        self.standard = relative_path
        self.__base_path = base_path

    def __hash__(self):
        return hash((self.blender, self.os))

    def __eq__(self, other):
        return isinstance(other, Path) and other.blender == self.blender and other.os == self.os

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.standard < other.standard

    def __gt__(self, other):
        return self.standard > other.standard

    def __truediv__(self, other):
        return Path(os.path.join(self.standard, other), self.__base_path)

    def __str__(self):
        return f"{self.blender}"

    def __repr__(self):
        return f"<{self.blender}>"

    def mtime(self):
        return os.path.getmtime(self.os)


class Paths:
    def __init__(self, project_file):
        self.base_name = os.path.splitext(os.path.basename(project_file))[0]
        self.__base_path = os.path.abspath(os.path.expanduser(os.path.dirname(project_file)))
        self.refresh()

    def refresh(self):
        # directories
        self.raw_path = Path("Raw", self.__base_path)
        self.source_path = Path("Source", self.__base_path)
        self.intermediate_path = Path("Intermediate", self.__base_path)
        self.final_path = Path("Final", self.__base_path)
        self.common_path = self.__one_of("../../Common", "../Common")
        # source data
        self.presentation = self.__file(self.source_path, f"{self.base_name}.pptx")
        self.raw_slides_videos = self.__find_files(self.raw_path, f"{self.base_name} - Slides")
        self.slides_videos = self.__find_files(self.source_path, f"{self.base_name} - Slides")
        self.greenscreen_videos = self.__find_files(self.source_path, f"{self.base_name} - Greenscreen")
        self.speaker_videos = (
            self.greenscreen_videos
            if self.greenscreen_videos
            else self.__find_files(self.source_path, f"{self.base_name} - Speaker")
        )
        self.speaker_audio = self.__find_file(self.source_path, f"{self.base_name} - Audio")
        # extracted data
        self.sync_config = self.__file(self.intermediate_path, "sync.json")
        self.cut_config = self.__file(self.intermediate_path, "cut.json")
        self.greenscreen_config = self.__file(self.intermediate_path, "greenscreen.json")
        self.merge_config = self.__file(self.intermediate_path, "merge.json")
        self.slide_transitions = self.__file(self.intermediate_path, "slide_transitions.json")
        self.speaker_visibility = self.__file(self.intermediate_path, "speaker_visibility.json")
        self.audio_config = self.__file(self.intermediate_path, "audio.json")
        self.rough_audio = self.__file(self.intermediate_path, "rough_audio.wav")
        # processed data
        self.lecture_presentation = self.__file(self.intermediate_path, "lecture_presentation.pptx")
        self.presentation_video = self.__file(self.intermediate_path, "lecture_presentation.mp4")
        self.lecture_audio = self.__file(self.intermediate_path, "lecture_audio.wav")
        # final data
        self.lecture_video = self.__file(self.final_path, f"{self.base_name}.mp4")
        self.lecture_handout = self.__file(self.final_path, f"{self.base_name}.pdf")
        # other
        self.speaker_placement = self.__file(self.common_path, "speaker_placement.png")
        self.audio_reference = self.__file(self.common_path, "audio.json")

    def from_blender(self, path):
        for name in dir(self):
            if not name.startswith("_"):
                obj = getattr(self, name)
                if isinstance(obj, Path):
                    if obj.blender == path:
                        return obj
                elif isinstance(obj, list):
                    for p in obj:
                        if p.blender == path:
                            return p
        raise ValueError(f"Path object of blender path {path} could not be found")

    def from_standard(self, path):
        for name in dir(self):
            if not name.startswith("_"):
                obj = getattr(self, name)
                if isinstance(obj, Path):
                    if obj.standard == path:
                        return obj
                elif isinstance(obj, list):
                    for p in obj:
                        if p.standard == path:
                            return p
        raise ValueError(f"Path object of standard path {path} could not be found")

    def from_strip(self, strip):
        if hasattr(strip, "filepath"):
            return self.from_blender(strip.filepath)
        elif hasattr(strip, "sound"):
            return self.from_blender(strip.sound.filepath)
        elif hasattr(strip, "scene"):
            return self.from_blender(strip.scene.node_tree.nodes["Movie Clip"].clip.filepath)
        elif hasattr(strip, "input_1"):
            return self.from_strip(strip.input_1)
        else:
            raise ValueError(f"Cannot find file path for strip {strip}")

    def __file(self, path, filename):
        return Path(os.path.join(path.standard, filename), base_path=self.__base_path)

    def __find_file(self, path, base_name):
        if os.path.isdir(path.os):
            for filename in os.listdir(path.os):
                if os.path.splitext(filename)[0] == base_name:
                    return Path(os.path.join(path.standard, filename), self.__base_path)
        return None

    def __find_files(self, path, base_name):
        if os.path.isdir(path.os):
            return sorted(
                [
                    self.__file(path, filename)
                    for filename in os.listdir(path.os)
                    if os.path.splitext(filename)[0].rstrip(" 0123456789") == base_name
                ],
                key=lambda p: p.standard,
            )
        else:
            return []

    def __one_of(self, *paths):
        for p in paths:
            path = Path(p, self.__base_path)
            if os.path.exists(path.os):
                return path
        return None
