#!/usr/bin/env python3
"""Generate three selectable test layouts from the immutable 0.3.0 WFF snapshot."""
import argparse
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "watchface/src/main/res"
LAYOUTS = ("a", "b", "c")
ROWS = (204, 252, 300, 348)


def text_part(name, x, y, width, height, size, text=None, template=None,
              parameters=(), color=0, family="terminal_mono", align="START", zone=None):
    part = ET.Element("PartText", x=str(x), y=str(y), width=str(width), height=str(height),
                      name=name, tintColor=f"[CONFIGURATION.palette.{color}]")
    if zone:
        ET.SubElement(part, "Localization", locales="en_US", timeZone=zone)
    content = ET.SubElement(part, "Text", align=align, ellipsis="TRUE")
    font = ET.SubElement(content, "Font", family=family, size=str(size))
    if template:
        value = ET.SubElement(font, "Template")
        value.text = template
        for expression in parameters:
            ET.SubElement(value, "Parameter", expression=expression)
    else:
        font.text = text
    return part


def condition(expressions):
    node = ET.Element("Condition")
    values = ET.SubElement(node, "Expressions")
    for name, expression in expressions:
        ET.SubElement(values, "Expression", name=name).text = expression
    return node


def header(layout):
    group = ET.Element("Group", name=f"header_{layout}", x="0", y="0", width="450", height="450")
    if layout == "b":
        group.append(text_part("b_utc_time", 100, 39, 168, 34, 30, template="%02d:%02d UTC",
                               parameters=("[HOUR_0_23]", "[MINUTE]"), zone="UTC"))
        group.append(text_part("b_timezone", 100, 73, 168, 30, 28, template="UTC%s",
                               parameters=("[TIMEZONE_OFFSET_DST]",), color=2, zone="SYNC_TO_DEVICE"))
        group.append(text_part("b_battery_label", 280, 39, 92, 34, 30, text="BATT"))
        group.append(text_part("b_battery_value", 280, 73, 92, 30, 30, template="%d%%",
                               parameters=("[BATTERY_PERCENT]",), color=2))
        date_y, time_x, time_y, time_size = 108, 56, 128, 96
        seconds_x, seconds_y = 355, 164
    else:
        # A single status row: UTC clock, current local offset, battery icon + percentage.
        group.append(text_part(f"{layout}_utc_time", 80, 49, 124, 34, 26, template="%02d:%02d UTC",
                               parameters=("[HOUR_0_23]", "[MINUTE]"), zone="UTC"))
        group.append(text_part(f"{layout}_timezone", 204, 49, 81, 34, 26, template="%s",
                               parameters=("[TIMEZONE_OFFSET_DST]",), color=0, zone="SYNC_TO_DEVICE"))
        icon = ET.SubElement(group, "PartImage", x="287", y="60", width="18", height="13",
                             name=f"{layout}_battery_icon", tintColor="[CONFIGURATION.palette.0]")
        ET.SubElement(icon, "Image", resource="battery_status")
        group.append(text_part(f"{layout}_battery_value", 310, 49, 65, 34, 28, template="%d%%",
                               parameters=("[BATTERY_PERCENT]",), color=2))
        date_y = 88
        time_x, time_y, time_size = (41, 119, 104) if layout == "a" else (61, 111, 94)
        seconds_x, seconds_y = (363, 158) if layout == "a" else (354, 151)
    dates = condition([(f"date_{style}", f'[CONFIGURATION.dateStyle] == "{style}"')
                       for style in ("full", "short", "iso")])
    formats = {"full": ("%s %02d %s %04d", ("[DAY_OF_WEEK_S]", "[DAY]", "[MONTH_F]", "[YEAR]")),
               "short": ("%s %02d %s", ("[DAY_OF_WEEK_S]", "[DAY]", "[MONTH_S]")),
               "iso": ("%04d-%02d-%02d", ("[YEAR]", "[MONTH]", "[DAY]"))}
    for style, (template, parameters) in formats.items():
        compare = ET.SubElement(dates, "Compare", expression=f"date_{style}")
        part = text_part(f"{layout}_date_{style}", 50, date_y, 350, 30, 28, template=template,
                         parameters=parameters, align="CENTER", zone="SYNC_TO_DEVICE")
        font = part.find("Text/Font")
        upper = ET.Element("Upper")
        upper.append(font[0])
        font.remove(font[0])
        font.append(upper)
        compare.append(part)
    group.append(dates)
    time_width = round(time_size * 3) + 2
    time = text_part(f"{layout}_time", time_x, time_y, time_width, 96, time_size,
                     template="%02d:%02d", parameters=("[IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12]", "[MINUTE]"),
                     color=2, family="terminal_block")
    ET.SubElement(time, "Variant", mode="AMBIENT", target="alpha", value="0")
    group.append(time)
    ambient = deepcopy(time)
    ambient.set("name", f"{layout}_ambient_time")
    ambient.set("alpha", "0")
    ambient.find("Variant").set("value", "255")
    ambient.find("Text/Font").set("family", "terminal_dot")
    group.append(ambient)
    ampm = condition([("show_ampm", "[IS_24_HOUR_MODE] == false")])
    ET.SubElement(ampm, "Compare", expression="show_ampm").append(
        text_part(f"{layout}_ampm", seconds_x, seconds_y - 22, 66, 22, 20,
                  template="%s", parameters=("[AMPM_STRING]",)))
    group.append(ampm)
    seconds = condition([("show_seconds", '[CONFIGURATION.seconds] == "TRUE"')])
    part = text_part(f"{layout}_seconds", seconds_x, seconds_y, 65, 49, 46,
                     template="%02d", parameters=("[SECOND]",), family="terminal_dot")
    ET.SubElement(part, "Variant", mode="AMBIENT", target="alpha", value="0")
    ET.SubElement(seconds, "Compare", expression="show_seconds").append(part)
    group.append(seconds)
    return group


def cell_geometry(layout, slot):
    row = (slot - 1) % 4
    right = slot > 4
    if layout == "c":
        x = (239 if right else 80) if row == 3 else (240 if right else 74)
        return dict(x=x, y=196 + row * 50, width=140, label_width=140, label_height=22,
                    value_x=0, value_y=22, value_width=140, value_height=28,
                    label_font=26, value_font=36, long_font=28, align="CENTER")
    x = (226 if right else 72) if row == 3 else (232 if right else 48)
    label_width, value_x = (62, 67) if layout == "a" else (52, 60)
    width = ((158 if layout == "a" else 160) if right else 150) if row == 3 else 184
    return dict(x=x, y=ROWS[row] + 6, width=width, label_width=label_width,
                label_height=36, value_x=value_x, value_y=0, value_width=width - value_x,
                value_height=36, label_font=30 if layout == "a" else 26,
                value_font=32 if layout == "a" else 36,
                long_font=(20 if row == 3 else 24) if layout == "a" else (22 if row == 3 else 26),
                align="START")


def cell(original, layout, slot, complication_type):
    geometry = cell_geometry(layout, slot)
    group = ET.Element("Group", name=f"cell_{slot}_{layout}_{complication_type}",
                       x=str(geometry["x"]), y=str(geometry["y"]),
                       width=str(geometry["width"]), height="50" if layout == "c" else "48")
    label = deepcopy(original.find("Condition"))
    for element in label.iter():
        if "name" in element.attrib and element.tag not in {"Expression"}:
            element.set("name", f"{layout}_{complication_type}_{element.attrib['name']}")
    for part in label.findall(".//PartText"):
        part.set("width", str(geometry["label_width"]))
        part.set("height", str(geometry["label_height"]))
        part.find("Text").set("align", geometry["align"])
        part.find("Text/Font").set("size", str(geometry["label_font"]))
    for part in label.findall(".//PartImage"):
        part.set("x", "58" if layout == "c" else "0")
        part.set("y", "0" if layout == "c" else "3")
        part.set("width", "22" if layout == "c" else "30")
        part.set("height", "22" if layout == "c" else "30")
    group.append(label)
    parts = list(original)[1:]
    for value in parts:
        value = deepcopy(value)
        for part in ([value] if value.tag == "PartText" else value.findall(".//PartText")):
            part.set("x", str(geometry["value_x"]))
            part.set("y", str(geometry["value_y"]))
            part.set("width", str(geometry["value_width"]))
            part.set("height", str(geometry["value_height"]))
            part.find("Text").set("align", geometry["align"])
            font = part.find("Text/Font")
            font.set("size", str(geometry["long_font"] if complication_type == "LONG_TEXT" else geometry["value_font"]))
            if complication_type == "LONG_TEXT":
                font.set("letterSpacing", "-0.04")
        # Keep 6–7 character SHORT_TEXT values legible in the narrower bottom row.
        if value.tag == "Condition" and (slot - 1) % 4 == 3 and complication_type != "LONG_TEXT":
            compare = value.find("Compare")
            if compare is not None:
                existing = value.find("Expressions/Expression").text
                large_name = f"value_large_{slot}_{layout}_{complication_type}"
                limit = 8 if layout == "c" else 5
                ET.SubElement(value.find("Expressions"), "Expression", name=large_name).text = (
                    f"({existing}) && textLength([COMPLICATION.TEXT]) <= {limit}")
                large = deepcopy(compare)
                large.set("expression", large_name)
                value.insert(1, large)
                for font in compare.findall(".//Font"):
                    font.set("size", "28" if layout == "c" else "24")
                    font.set("letterSpacing", "-0.04")
        group.append(value)
    return group


def build():
    root = ET.parse(ROOT / "versions/0.3.0/watchface.xml").getroot()
    configurations = root.find("UserConfigurations")
    config = ET.Element("ListConfiguration", id="layout", displayName="layout_name", defaultValue="a")
    for layout in LAYOUTS:
        ET.SubElement(config, "ListOption", id=layout, displayName=f"layout_{layout}_name", icon=f"layout_{layout}_icon")
    configurations.insert(0, config)
    previous_scene = root.find("Scene")
    scene = ET.Element("Scene", backgroundColor="#FF000000")
    layouts = condition([(f"layout_{layout}", f'[CONFIGURATION.layout] == "{layout}"') for layout in LAYOUTS])
    for layout in LAYOUTS:
        ET.SubElement(layouts, "Compare", expression=f"layout_{layout}").append(header(layout))
    scene.append(layouts)
    for old_slot in previous_scene.findall("ComplicationSlot"):
        slot = int(old_slot.attrib["slotId"])
        row, right = (slot - 1) % 4, slot > 4
        attributes = dict(old_slot.attrib, x="0", y="0", width="450", height="450")
        new_slot = ET.SubElement(scene, "ComplicationSlot", attributes)
        new_slot.append(deepcopy(old_slot.find("Variant")))
        ET.SubElement(new_slot, "BoundingBox", x=str((226 if right else 72) if row == 3 else (232 if right else 48)),
                      y=str(ROWS[row]), width=str((160 if right else 152) if row == 3 else 184), height="48")
        new_slot.append(deepcopy(old_slot.find("DefaultProviderPolicy")))
        for old_complication in old_slot.findall("Complication"):
            complication_type = old_complication.attrib["type"]
            complication = ET.SubElement(new_slot, "Complication", type=complication_type)
            choices = condition([(f"layout_{layout}", f'[CONFIGURATION.layout] == "{layout}"') for layout in LAYOUTS])
            for layout in LAYOUTS:
                ET.SubElement(choices, "Compare", expression=f"layout_{layout}").append(
                    cell(old_complication, layout, slot, complication_type))
            complication.append(choices)
    root.remove(previous_scene)
    root.append(scene)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(build())
    print(f"Generated A/B/C layouts: {args.output}")
