#!/usr/bin/env python3
"""Save reversible, resource-native sketches; never change the installed WFF/APK."""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from rebuild_assets import render_preview

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/large-type-sketches/2026-11-06"
BASE = ROOT / "versions/0.8.1-test/watchface.xml"
FONTS = ("block", "dot", "mono")
SLOTS = (2, 3, 4, 6, 7)
DEMO = {2: ("T/TD", "+25/+8"), 3: ("COND", "CAVOK"),
        4: ("ALRM", "06:45"), 6: ("HR", "84"), 7: ("NTFY", "3")}
DATE = {"DAY_OF_WEEK_S": "FRI", "DAY": 6, "MONTH_S": "NOV", "MONTH_F": "NOVEMBER"}
PROFILES = {
    "familiar": dict(name="Привычные строки", header_size=32, header_shift=0,
                     date_size=36, date_y=113, date_height=42, short_date=False,
                     clock_size=100, clock_y=156, clock_height=96, seconds_x=385, seconds_y=192,
                     stacked=False, rows=(266, 314), cell_height=46, x=(40, 230), width=180,
                     label_size=36, label_width=72, label_height=46,
                     value_size=40, fallback_size=34, long_size=30,
                     value_x=78, value_y=0, value_width=102, value_height=46,
                     footer_y=367, footer_size=38, footer_height=46),
    "stacked": dict(name="Подписи сверху", header_size=32, header_shift=-8,
                    date_size=36, date_y=103, date_height=42, short_date=False,
                    clock_size=100, clock_y=144, clock_height=96, seconds_x=385, seconds_y=180,
                    stacked=True, rows=(240, 314), cell_height=74, x=(60, 230), width=160,
                    label_size=36, label_width=160, label_height=32,
                    value_size=44, fallback_size=38, long_size=36,
                    value_x=0, value_y=32, value_width=160, value_height=42,
                    footer_y=390, footer_size=38, footer_height=40),
    "maximum": dict(name="Крупные значения", header_size=34, header_shift=-10,
                    date_size=42, date_y=98, date_height=36, short_date=True,
                    clock_size=108, clock_y=136, clock_height=92, seconds_x=390, seconds_y=176,
                    stacked=True, rows=(232, 312), cell_height=80, x=(60, 230), width=160,
                    label_size=36, label_width=160, label_height=32,
                    value_size=48, fallback_size=42, long_size=36,
                    value_x=0, value_y=32, value_width=160, value_height=48,
                    footer_y=394, footer_size=38, footer_height=40),
}


def resize(part, *, x=None, y=None, width=None, height=None, size=None, align=None):
    for key, value in (("x", x), ("y", y), ("width", width), ("height", height)):
        if value is not None:
            part.set(key, str(value))
    if size is not None:
        for font in part.findall("Text/Font"):
            font.set("size", str(size))
    if align is not None:
        part.find("Text").set("align", align)


def resize_values(node, profile, complication_type):
    """Preserve native provider fallbacks; fit longer SHORT_TEXT with a second size."""
    size = profile["long_size"] if complication_type == "LONG_TEXT" else profile["value_size"]
    for part in node.iter("PartText"):
        resize(part, x=profile["value_x"], y=profile["value_y"],
               width=profile["value_width"], height=profile["value_height"],
               size=size, align="CENTER" if profile["stacked"] else "START")
    if node.tag != "Condition" or complication_type == "LONG_TEXT":
        return
    expression = node.find("Expressions/Expression")
    branch = node.find("Compare")
    if branch is None or expression is None:
        return
    large_name = f"value_large_{expression.attrib['name']}"
    # Terminal Mono is fixed-pitch. The conservative bound also leaves glyph bearings.
    cell = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), size).getlength("0")
    limit = int((profile["value_width"] - 2) / cell)
    ET.SubElement(node.find("Expressions"), "Expression", name=large_name).text = (
        f'({expression.text}) && textLength([COMPLICATION.TEXT]) <= {limit}')
    large = deepcopy(branch)
    large.set("expression", large_name)
    node.insert(1, large)
    for font in branch.findall(".//Font"):
        font.set("size", str(profile["fallback_size"]))


def build_sketch(choice):
    profile = PROFILES[choice]
    root = ET.parse(BASE).getroot()
    if profile["short_date"]:
        root.find("UserConfigurations/ListConfiguration[@id='dateStyle']").set("defaultValue", "short")
    scene = root.find("Scene")
    header = scene.find("Group[@name='header']")
    for name in ("utc_time", "timezone", "battery_label", "battery_value"):
        part = header.find(f"PartText[@name='{name}']")
        resize(part, y=int(part.attrib["y"]) + profile["header_shift"],
               height=34, size=profile["header_size"])
    for style in ("full", "short", "iso"):
        part = header.find(f"Condition/Compare[@expression='date_{style}']/PartText")
        # The long full-date alternative must still fit if selected later.
        size = 36 if profile["short_date"] and style == "full" else profile["date_size"]
        resize(part, y=profile["date_y"], height=profile["date_height"], size=size)
    for part in header.findall(".//PartText"):
        name = part.attrib.get("name", "")
        if name.startswith("time_") or name == "ambient_time":
            width = profile["clock_size"] * 3 + 2
            resize(part, x=(450 - width) // 2, y=profile["clock_y"], width=width,
                   height=profile["clock_height"], size=profile["clock_size"])
        elif name == "seconds":
            resize(part, x=profile["seconds_x"], y=profile["seconds_y"])
        elif name == "ampm":
            resize(part, x=profile["seconds_x"], y=profile["seconds_y"] - 22)
    for slot in list(scene.findall("ComplicationSlot")):
        slot_id = int(slot.attrib["slotId"])
        if slot_id in (1, 5):
            scene.remove(slot)
            continue
        if slot_id == 4:
            slot.find("BoundingBox").attrib.update(x="75", y=str(profile["footer_y"]),
                                                  width="300", height=str(profile["footer_height"]))
        else:
            row = 0 if slot_id in (2, 6) else 1
            x, y = profile["x"][int(slot_id > 4)], profile["rows"][row]
            slot.find("BoundingBox").attrib.update(x=str(x), y=str(y), width=str(profile["width"]),
                                                  height=str(profile["cell_height"]))
        for complication in slot.findall("Complication"):
            group = complication.find("Group")
            if slot_id == 4:
                group.attrib.update(x="75", y=str(profile["footer_y"]), width="300",
                                    height=str(profile["footer_height"]))
                for part in group.iter("PartText"):
                    resize(part, width=300, height=profile["footer_height"], size=profile["footer_size"])
                for icon in group.iter("InlineImage"):
                    icon.attrib.update(width="34", height="34")
                continue
            group.attrib.update(x=str(x), y=str(y), width=str(profile["width"]),
                                height=str(profile["cell_height"]))
            labels = group[0]
            for part in labels.iter("PartText"):
                resize(part, width=profile["label_width"], height=profile["label_height"],
                       size=profile["label_size"], align="CENTER" if profile["stacked"] else "START")
            for icon in labels.iter("PartImage"):
                icon.attrib.update(x=str((profile["label_width"] - 32) // 2 if profile["stacked"] else 0),
                                   y=str((profile["label_height"] - 32) // 2), width="32", height="32")
            for node in list(group)[1:]:
                resize_values(node, profile, complication.attrib["type"])
    ET.indent(root, space="  ")
    return root


def xml_bytes(root):
    return b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8") + b"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    comparison = Image.new("RGB", (1350, 540), "#101510")
    title_font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), 27)
    caption_font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), 22)
    preview_data = {}
    for index, (choice, profile) in enumerate(PROFILES.items()):
        root = build_sketch(choice)
        (args.output / f"{choice}.xml").write_bytes(xml_bytes(root))
        preview_data[choice] = {}
        for clock in FONTS:
            image = render_preview(watchface=root, clock_font=clock, complication_data=DEMO, source_values=DATE)
            image.save(args.output / f"{choice}-{clock}.png")
            preview_data[choice][clock] = "data:image/png;base64," + base64.b64encode(
                (args.output / f"{choice}-{clock}.png").read_bytes()).decode("ascii")
        render_preview(watchface=root, ambient=True, complication_data=DEMO, source_values=DATE).save(
            args.output / f"{choice}-ambient.png")
        image = Image.open(args.output / f"{choice}-block.png")
        comparison.paste(image, (index * 450, 45))
        draw = ImageDraw.Draw(comparison)
        draw.text((index * 450 + 225, 23), profile["name"], font=title_font, anchor="mm", fill="#F2FFF1")
        caption = f'ПОДПИСИ {profile["label_size"]} · ЗНАЧЕНИЯ {profile["value_size"]}'
        draw.text((index * 450 + 225, 518), caption, font=caption_font, anchor="mm", fill="#80F5BA")
    comparison.save(args.output / "comparison.png")
    template = (ROOT / "tools/assets/large-type-preview.html").read_text()
    assert template.count("__PREVIEW_IMAGES__") == 1
    (args.output / "large-type-preview.html").write_text(
        template.replace("__PREVIEW_IMAGES__", json.dumps(preview_data, separators=(",", ":"))))
    files = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(args.output.iterdir()) if path.name != "manifest.json"}
    manifest = {"kind": "design-sketches-not-apk", "baseTag": "v0.8.1-test",
                "baseCommit": "f93853422e60392268b41af37de8d418defaebf8",
                "removedSlotIds": [1, 5], "remainingSlotIds": list(SLOTS),
                "fixtureDataOnlyInPreviews": True, "profiles": PROFILES, "files": files}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved three five-field sketches and comparison: {args.output}")


if __name__ == "__main__":
    main()
