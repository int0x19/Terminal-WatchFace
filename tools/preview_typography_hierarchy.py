#!/usr/bin/env python3
"""Preview the requested 34/40 hierarchy separately from the released 0.9 APK."""
import base64
from copy import deepcopy
import hashlib
import json
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from build_large_type_sketches import FONTS, ROOT, build_sketch, resize, xml_bytes
from build_layout_variants import condition
from refine_familiar_sketch import PROFILE as BASE_PROFILE, ink_bands
from rebuild_assets import render_preview

OUT = ROOT / "docs/large-type-sketches/2026-11-06-r3"
BASE = ROOT / "versions/0.9.0-large-type-test/watchface.xml"
PROFILE = {**BASE_PROFILE, "name": "Подписи 34 — значения 40",
           "header_size": 34, "date_size": 40,
           "label_size": 34, "label_width": 66,
           "value_size": 40, "fallback_size": 38, "long_size": 38,
           "value_x": 70, "value_width": 118, "footer_size": 40}
DEMO = {2: ("UZTT", "VFR"), 3: ("T/TD", "+19/+6"),
        4: ("QNH", "1021"), 6: ("COND", "CLOUDS"), 7: ("VIS", "10KM+")}
SOURCES = {"HOUR_0_23": 21, "UTC_HOUR_0_23": 16, "MINUTE": 42,
           "SECOND": 39, "BATTERY_PERCENT": 69, "TIMEZONE_OFFSET_DST": "+5",
           "DAY_OF_WEEK_S": "FRI", "DAY": 6, "MONTH_S": "NOV", "MONTH_F": "NOVEMBER"}
PALETTE = "tango"


def build_hierarchy():
    root = build_sketch("familiar", profile=PROFILE)
    header = root.find("Scene/Group[@name='header']")
    timezone = header.find("PartText[@name='timezone']")
    utc_time = header.find("PartText[@name='utc_time']")
    resize(timezone, y=38, size=34)
    timezone.set("tintColor", "[CONFIGURATION.palette.0]")
    # Keep requested 34 for ordinary offsets, with an automatic fit for rare
    # longer offsets such as UTC+5:45 / UTC+13:45 at the round screen's top edge.
    choice = condition([("timezone_regular", "textLength([TIMEZONE_OFFSET_DST]) <= 3"),
                        ("timezone_fractional", "textLength([TIMEZONE_OFFSET_DST]) > 3")])
    header.insert(list(header).index(timezone), choice)
    header.remove(timezone)
    ET.SubElement(choice, "Compare", expression="timezone_regular").append(timezone)
    fractional = deepcopy(timezone)
    fractional.set("name", "timezone_fractional")
    resize(fractional, size=28)
    ET.SubElement(choice, "Compare", expression="timezone_fractional").append(fractional)
    resize(utc_time, y=72, size=40)
    utc_time.set("tintColor", "[CONFIGURATION.palette.2]")
    resize(header.find("PartText[@name='battery_label']"), size=34)
    resize(header.find("PartText[@name='battery_value']"), size=40)
    # Full month names still fit the unchanged 390-unit box at size 40.
    for style in ("full", "short", "iso"):
        part = header.find(f"Condition/Compare[@expression='date_{style}']/PartText")
        part.find("Text/Font").set("letterSpacing", "-0.02")
    for slot in root.findall("Scene/ComplicationSlot"):
        for complication in slot.findall("Complication"):
            if slot.attrib["slotId"] == "4":
                for font in complication.findall(".//Font"):
                    caption = font.attrib.get("color") == "[CONFIGURATION.palette.0]"
                    font.set("size", "34" if caption else "40")
            elif complication.attrib["type"] == "LONG_TEXT":
                group = complication.find("Group")
                for node in list(group)[1:]:
                    for font in node.findall(".//Font"):
                        font.set("letterSpacing", "-0.045")
    ET.indent(root, space="  ")
    return root


def preview(root, clock="block", ambient=False, **overrides):
    options = dict(watchface=root, clock_font=clock, ambient=ambient,
                   complication_data=DEMO, source_values=SOURCES,
                   palette_id=PALETTE, background_mode="amoled")
    options.update(overrides)
    return render_preview(**options)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    current, previous = build_hierarchy(), ET.parse(BASE).getroot()
    (OUT / "hierarchy.xml").write_bytes(xml_bytes(current))
    images = {"current": {}, "previous": {}}
    for revision, root in (("current", current), ("previous", previous)):
        for clock in FONTS:
            path = OUT / f"{revision}-{clock}.png"
            preview(root, clock).save(path)
            images[revision][clock] = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    preview(current, ambient=True).save(OUT / "ambient.png")
    long_date = {**SOURCES, "DAY_OF_WEEK_S": "WED", "DAY": 30, "MONTH_F": "SEPTEMBER"}
    preview(current, source_values=long_date).save(OUT / "long-date.png")
    comparison = Image.new("RGB", (900, 530), "#101510")
    font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), 27)
    for index, (revision, title) in enumerate((("previous", "APK 0.9.0"), ("current", "Новая иерархия"))):
        with Image.open(OUT / f"{revision}-block.png") as image:
            comparison.paste(image, (index * 450, 45))
        ImageDraw.Draw(comparison).text((index * 450 + 225, 23), title,
                                       font=font, fill="#F2FFF1", anchor="mm")
    comparison.save(OUT / "comparison.png")
    template = (ROOT / "tools/assets/typography-hierarchy-preview.html").read_text()
    assert template.count("__PREVIEW_IMAGES__") == 1
    (OUT / "typography-hierarchy.html").write_text(
        template.replace("__PREVIEW_IMAGES__", json.dumps(images, separators=(",", ":"))))
    manifest = {"kind": "design-sketch-not-apk", "baseTag": "v0.9.0-large-type-test",
                "profile": PROFILE, "fixtureDataOnlyInPreviews": True,
                "previewPalette": PALETTE, "previewBackground": "amoled",
                "inkMeasurements": {clock: ink_bands(current, clock, DEMO, source_values=SOURCES) for clock in FONTS},
                "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(OUT.iterdir()) if p.name != "manifest.json"}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved 34/40 hierarchy preview; current APK unchanged: {OUT}")


if __name__ == "__main__":
    main()
