#!/usr/bin/env python3
"""Generate the approved combined header and compact table from the 0.3.0 snapshot."""
import argparse
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

from build_layout_variants import text_part, condition, cell as legacy_cell
from build_layout_variants import cell_geometry as legacy_geometry
from typography import LANGUAGES, DATE_PATTERNS, configurations as typography_configurations, style_variants, style_labels

ROOT = Path(__file__).resolve().parents[1]
CLOCK_FONTS = {"block": "terminal_block", "dot": "terminal_dot", "mono": "clock_mono"}
ROWS = (248, 284, 320, 356)
SLOTS = (1, 2, 3, 4, 5, 6, 7)
DATE_SIZE = 36


def header():
    group = ET.Element("Group", name="header", x="0", y="0", width="450", height="450")
    group.append(text_part("utc_time", 65, 38, 180, 34, 30,
                           template="%02d:%02d", parameters=("[HOUR_0_23]", "[MINUTE]"),
                           align="CENTER", zone="UTC"))
    group.append(text_part("timezone", 65, 72, 180, 32, 30,
                           template="UTC%s", parameters=("[TIMEZONE_OFFSET_DST]",),
                           align="CENTER", zone="SYNC_TO_DEVICE", color=2))
    group.append(text_part("battery_label", 235, 38, 120, 34, 30, text="BATT", align="CENTER"))
    group.append(text_part("battery_value", 235, 72, 120, 32, 30,
                           template="%d%%", parameters=("[BATTERY_PERCENT]",),
                           align="CENTER", color=2))
    dates = condition([(f"date_{style}", f'[CONFIGURATION.dateStyle] == "{style}"')
                       for style in ("full", "short", "iso")])
    for style, pattern in DATE_PATTERNS.items():
        languages = condition([(f"language_{language}", f'[CONFIGURATION.dateLanguage] == "{language}"')
                               for language in LANGUAGES])
        for language, locale in LANGUAGES.items():
            part = text_part(f"date_{style}_{language}", 30, 112, 390, 44, DATE_SIZE, template="%s",
                             parameters=(f'icuText("{pattern}")',), align="CENTER", zone="SYNC_TO_DEVICE")
            localization = part.find("Localization")
            localization.set("calendar", "GREGORIAN")
            # ISO stays ASCII/Gregorian in every language; no system calendar or digit changes.
            if style == "iso" or locale:
                localization.set("locales", "en_US" if style == "iso" else locale)
            else:
                localization.attrib.pop("locales", None)
            part.find("Text").set("maxLines", "1")
            ET.SubElement(languages, "Compare", expression=f"language_{language}").append(style_variants(part))
        ET.SubElement(dates, "Compare", expression=f"date_{style}").append(languages)
    group.append(dates)
    choices = condition([(f"clock_font_{choice}", f'[CONFIGURATION.clockFont] == "{choice}"')
                         for choice in CLOCK_FONTS])
    for choice, family in CLOCK_FONTS.items():
        time = text_part(f"time_{choice}", 74, 156, 302, 96, 100,
                         template="%02d:%02d", parameters=("[IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12]", "[MINUTE]"),
                         color=2, family=family, align="CENTER")
        ET.SubElement(time, "Variant", mode="AMBIENT", target="alpha", value="0")
        ET.SubElement(choices, "Compare", expression=f"clock_font_{choice}").append(time)
    group.append(choices)
    # One dotted ambient clock for all choices; font switching cannot light extra pixels in AOD.
    ambient = deepcopy(time)
    ambient.set("name", "ambient_time")
    ambient.set("alpha", "0")
    ambient.find("Variant").set("value", "255")
    ambient.find("Text/Font").set("family", "terminal_dot")
    group.append(ambient)
    ampm = condition([("show_ampm", "[IS_24_HOUR_MODE] == false")])
    ET.SubElement(ampm, "Compare", expression="show_ampm").append(
        text_part("ampm", 385, 170, 56, 22, 20, template="%s",
                  parameters=("[AMPM_STRING]",), align="CENTER"))
    group.append(ampm)
    seconds = condition([("show_seconds", '[CONFIGURATION.seconds] == "TRUE"')])
    part = text_part("seconds", 385, 192, 56, 45, 42, template="%02d",
                     parameters=("[SECOND]",), family="terminal_dot", align="CENTER")
    ET.SubElement(part, "Variant", mode="AMBIENT", target="alpha", value="0")
    ET.SubElement(seconds, "Compare", expression="show_seconds").append(part)
    group.append(seconds)
    return group


def cell_geometry(slot):
    if slot == 4:
        return dict(x=82, y=362, width=286, height=36, label_width=286, label_height=36,
                    value_x=0, value_y=0, value_width=286, value_height=36,
                    label_font=32, value_font=32, long_font=30, align="CENTER")
    geometry = legacy_geometry("a", slot)
    geometry.update(y=ROWS[(slot - 1) % 4] + 6, height=36)
    return geometry


def cell(original, slot, complication_type):
    if slot == 4:
        return wide_cell(original, complication_type)
    # Reuse the tested AUTO/icon/manual-label and SHORT_TEXT fallback logic from 0.4.0.
    group = legacy_cell(original, "a", slot, complication_type)
    geometry = cell_geometry(slot)
    group.set("name", f"cell_{slot}_{complication_type}")
    group.set("y", str(geometry["y"]))
    group.set("height", str(geometry["height"]))
    style_labels(group)
    return group


def wide_cell(original, complication_type):
    """One rich-text line: native CENTER applies to label + value as a whole."""
    geometry = cell_geometry(4)
    group = ET.Element("Group", name=f"cell_4_{complication_type}", x="82", y="362", width="286", height="36")
    labels = deepcopy(original.find("Condition"))
    for branch in list(labels):
        if branch.tag == "Expressions":
            continue
        label_part = branch.find("PartText")
        icon = branch.find("PartImage")
        prefix = None
        if label_part is not None:
            prefix = deepcopy(label_part.find("Text/Font"))
            prefix.set("size", "32")
            prefix.set("color", "[CONFIGURATION.palette.0]")
        elif icon is not None:
            prefix = ET.Element("Font", family="terminal_mono", size="32", color="[CONFIGURATION.palette.0]")
            ET.SubElement(prefix, "InlineImage", resource="[COMPLICATION.MONOCHROMATIC_IMAGE]",
                          source="[COMPLICATION.MONOCHROMATIC_IMAGE]",
                          width="30", height="30", color="[CONFIGURATION.palette.0]")
        for child in list(branch):
            branch.remove(child)
        # Clone the original per-type TEXT / numeric fallback, never invent sensor values.
        for value in list(original)[1:]:
            value = deepcopy(value)
            for part in ([value] if value.tag == "PartText" else value.findall(".//PartText")):
                part.attrib.update(x="0", y="0", width="286", height="36", tintColor="#FFFFFFFF")
                text = part.find("Text")
                text.set("align", "CENTER")
                text.set("maxLines", "1")
                font = text.find("Font")
                font.set("size", str(geometry["long_font"] if complication_type == "LONG_TEXT" else 32))
                font.set("color", "[CONFIGURATION.palette.1]")
                if prefix is not None:
                    text.insert(0, deepcopy(prefix))
                    space = ET.Element("Font", family="terminal_mono", size="32", color="[CONFIGURATION.palette.0]")
                    template = ET.SubElement(space, "Template")
                    template.text = "%s"
                    ET.SubElement(template, "Parameter", expression='" "')
                    text.insert(1, space)
            branch.append(value)
    group.append(labels)
    style_labels(group, rich=True)
    return group


def build():
    root = ET.parse(ROOT / "versions/0.3.0/watchface.xml").getroot()
    configurations = root.find("UserConfigurations")
    configurations.remove(configurations.find("ListConfiguration[@id='label8']"))
    fonts = ET.Element("ListConfiguration", id="clockFont", displayName="clock_font_name", defaultValue="block")
    for choice in CLOCK_FONTS:
        ET.SubElement(fonts, "ListOption", id=choice, displayName=f"clock_font_{choice}_name", icon=f"clock_font_{choice}_icon")
    configurations.insert(0, fonts)
    for index, config in enumerate(typography_configurations(), start=1):
        configurations.insert(index, config)
    previous_scene = root.find("Scene")
    scene = ET.Element("Scene", backgroundColor="#FF000000")
    scene.append(header())
    for old_slot in previous_scene.findall("ComplicationSlot"):
        slot = int(old_slot.attrib["slotId"])
        if slot not in SLOTS:
            continue
        row, right = (slot - 1) % 4, slot > 4
        attributes = dict(old_slot.attrib, x="0", y="0", width="450", height="450")
        new_slot = ET.SubElement(scene, "ComplicationSlot", attributes)
        new_slot.append(deepcopy(old_slot.find("Variant")))
        ET.SubElement(new_slot, "BoundingBox", x="82" if slot == 4 else str(232 if right else 48),
                      y=str(ROWS[row] + 6), width="286" if slot == 4 else "184", height="36")
        new_slot.append(deepcopy(old_slot.find("DefaultProviderPolicy")))
        for original in old_slot.findall("Complication"):
            complication_type = original.attrib["type"]
            ET.SubElement(new_slot, "Complication", type=complication_type).append(cell(original, slot, complication_type))
    root.remove(previous_scene)
    root.append(scene)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(build())
    print(f"Generated combined layout with three clock fonts: {args.output}")
