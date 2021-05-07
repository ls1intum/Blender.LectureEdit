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

import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile

__all__ = ("create_presentation",)

_xml_namespaces = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
}


def xml_find(node, path, create=False):
    if not path:
        return node
    for child in node.findall(path[0], _xml_namespaces):
        result = xml_find(child, path[1:], create=create)
        if result is not None:
            return result
    if create:
        for p in path:
            new_node = ET.SubElement(node, p)
            node = new_node
        return node


def xml_walk(node):
    for child in node:
        yield child
        yield from xml_walk(child)


def node_source(node, source):
    tag = node.tag
    for ns, url in _xml_namespaces.items():
        if tag.startswith(f"{{{url}}}"):
            tag = tag.replace(f"{{{url}}}", f"{ns}:")
    regex = f"<{tag}\s+"
    for name, value in node.attrib.items():
        regex += f'{name}="{value}"\s*'
    regex += ">"
    match = re.search(regex, source)
    if match:
        return match.group(0)


def slide_sources(path):
    with zipfile.ZipFile(path.os) as archive:
        slides = [
            n
            for n in archive.namelist()
            if n.startswith("ppt/slides") and not n.startswith("ppt/slides/_rels")
        ]
        slides.sort(key=lambda n: int(os.path.basename(n).lstrip("slide").rstrip(".xml")))
        for slide in slides:
            with archive.open(slide) as f:
                yield f.read().decode()


def slide_animations(slide_xml, node_types=("clickEffect",)):
    seq = xml_find(slide_xml, ["p:timing", "p:tnLst", "p:par", "p:cTn", "p:childTnLst", "p:seq"])
    if seq:
        for node in xml_walk(seq):
            if (
                node.tag == f"{{{_xml_namespaces['p']}}}cTn"
                and "nodeType" in node.attrib
                and node.attrib["nodeType"] in node_types
            ):
                yield node


def dependent_animations(node, slide_xml):
    node_found = False
    for animation_node in slide_animations(slide_xml, node_types=("clickEffect", "afterEffect", "withEffect")):
        if node_found:
            if animation_node.attrib["nodeType"] == "clickEffect":
                break
            else:
                yield animation_node
        elif animation_node.attrib["id"] == node.attrib["id"]:
            node_found = True


def slide_xmls(path):
    for s in slide_sources(path):
        yield ET.fromstring(s)


def create_presentation(source_file, target_file, durations):
    with zipfile.ZipFile(source_file.os) as source:
        with zipfile.ZipFile(
            target_file.os,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as target:
            slides = []
            for path in source.namelist():
                if path.startswith("ppt/slides") and not path.startswith("ppt/slides/_rels"):
                    slides.append(path)
                else:
                    data = source.read(path)
                    target.writestr(path, data)
            slides.sort(key=lambda n: int(os.path.basename(n).lstrip("slide").rstrip(".xml")))
            for path, original, (slide_duration, animation_durations) in zip(
                slides, slide_sources(source_file), durations
            ):
                with target.open(path, "w") as target_file:
                    # add the timings for the animations
                    modified = original
                    slide_xml = ET.fromstring(original)
                    cumulative_duration = 0
                    for duration, node in zip(animation_durations, slide_animations(slide_xml)):
                        # change the node from click-triggered to automatically started
                        node_sourcecode = node_source(node, modified)
                        modified_node_source = node_sourcecode.replace(node.attrib["nodeType"], "afterEffect")
                        # add the timing
                        old = f'{node_sourcecode}<p:stCondLst><p:cond delay="0"/>'
                        new = f'{modified_node_source}<p:stCondLst><p:cond delay="{duration}"/>'
                        if old not in modified:
                            print(f"{old} not found in {path}")
                        modified = modified.replace(old, new)
                        # add the cumulative timing before the node
                        old = (
                            f'<p:cTn id="{int(node.attrib["id"]) - 1}" fill="hold">'
                            f"<p:stCondLst>"
                            f'<p:cond delay="\d+"/>'
                            f"</p:stCondLst>"
                        )
                        new = (
                            f'<p:cTn id="{int(node.attrib["id"]) - 1}" fill="hold">'
                            f"<p:stCondLst>"
                            f'<p:cond delay="{cumulative_duration}"/>'
                            f"</p:stCondLst>"
                        )
                        to_replace = re.findall(old, modified)
                        if not to_replace:
                            print(f"{len(to_replace)} cumulative timings in {path} before  node {node.attrib['id']}")
                        for match in to_replace:
                            modified = modified.replace(match, new)
                        if new not in modified:
                            print(path, node.attrib["id"], old in modified)
                            print(match)
                            print(new)
                        cumulative_duration += duration
                        # change the timings of the automatically started animations
                        for dependent_node in dependent_animations(node, slide_xml):
                            node_sourcecode = node_source(dependent_node, modified)
                            old = f'{node_sourcecode}<p:stCondLst><p:cond delay="0"/>'
                            new = f'{node_sourcecode}<p:stCondLst><p:cond delay="{duration}"/>'
                            modified = modified.replace(old, new)
                    # remove obsolete nodes the automatically started animations
                    for node in slide_animations(ET.fromstring(modified), node_types=("withEffect",)):
                        to_remove = (
                            f"</p:childTnLst>"
                            f"</p:cTn>"
                            f"</p:par>"
                            f"<p:par>"
                            f'<p:cTn id="{int(node.attrib["id"]) - 1}" fill="hold">'
                            f"<p:stCondLst>"
                            f'<p:cond delay="0"/>'
                            f"</p:stCondLst>"
                            f"<p:childTnLst>"
                        )
                        modified = modified.replace(to_remove, "")
                    # remove obsolete nodes inside the automatically started animations
                    regex = (
                        "</p:childTnLst>"
                        "</p:cTn>"
                        "</p:par>"
                        "<p:par>"
                        '<p:cTn id="\d+" fill="hold">'
                        "<p:stCondLst>"
                        '<p:cond delay="indefinite"/>'
                        "</p:stCondLst>"
                        "<p:childTnLst>"
                    )
                    to_remove = re.findall(regex, modified)
                    # if not to_remove:
                    #     print(f"no obsolete nodes in {path}")
                    for match in to_remove:
                        modified = modified.replace(match, "")
                    # add a node about the beginning of the animations
                    old = '<p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
                    new = (
                        "<p:stCondLst>"
                        '<p:cond delay="indefinite"/>'
                        '<p:cond evt="onBegin" delay="0">'
                        '<p:tn val="2"/>'
                        "</p:cond>"
                        "</p:stCondLst>"
                    )
                    modified = modified.replace(old, new)
                    # fix the numeration of the animation ids
                    for i, match in enumerate(re.findall(r'<p:cTn id="\d+"', modified), start=1):
                        new = f'<p:cTn id="{i}"'
                        if match != new:
                            modified = modified.replace(match, new)
                    # add the timing for the slide transition
                    if "<p:transition " in modified:
                        logging.info(f"slide transition is already defined in {path}")
                    addition = (
                        f'<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
                        f'<mc:Choice xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" Requires="p14">'
                        f'<p:transition spd="slow" p14:dur="2000" advTm="{slide_duration}" />'
                        f"</mc:Choice>"
                        f"<mc:Fallback>"
                        f'<p:transition spd="slow" advTm="{slide_duration}" />'
                        f"</mc:Fallback>"
                        f"</mc:AlternateContent>"
                    )
                    if animation_durations:
                        delimiter = "<p:timing>"
                    else:
                        delimiter = "</p:sld>"
                    split = modified.split(delimiter)
                    modified = delimiter.join(split[0:-1]) + addition + delimiter + delimiter.join(split[-1:])
                    target_file.write(modified.encode())
