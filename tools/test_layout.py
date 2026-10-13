#!/usr/bin/env python3
"""Regression checks for three test layouts and preserved complication choices."""
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from fontTools.ttLib import TTFont
from PIL import Image, ImageFont
from labels import LABELS, manual_label_expression
from build_layout_variants import LAYOUTS, cell_geometry, build

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "watchface/src/main/res"


class LayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(RES / "raw/watchface.xml").getroot()
        cls.baseline = ET.parse(ROOT / "versions/0.3.0/watchface.xml").getroot()

    def header(self, layout):
        return self.root.find(f"Scene/Condition/Compare[@expression='layout_{layout}']/Group")

    def cell(self, n, layout, complication_type):
        return self.root.find(f"Scene/ComplicationSlot[@slotId='{n}']/Complication[@type='{complication_type}']/Condition/Compare[@expression='layout_{layout}']/Group")

    def test_three_selectable_layouts(self):
        config = self.root.find("UserConfigurations/ListConfiguration[@id='layout']")
        self.assertEqual(config.attrib["defaultValue"], "a")
        self.assertEqual([o.attrib["id"] for o in config], list(LAYOUTS))
        for locale in ("values", "values-ru"):
            strings = ET.parse(RES / locale / "strings.xml").getroot()
            for option in config:
                self.assertIsNotNone(strings.find(f"string[@name='{option.attrib['displayName']}']"))

    def test_live_header_sources_and_date_modes(self):
        for layout in LAYOUTS:
            header = self.header(layout)
            utc = header.find(f"PartText[@name='{layout}_utc_time']")
            self.assertEqual(utc.find("Localization").attrib["timeZone"], "UTC")
            self.assertEqual([p.attrib["expression"] for p in utc.findall(".//Parameter")],
                             ["[HOUR_0_23]", "[MINUTE]"])
            zone = header.find(f"PartText[@name='{layout}_timezone']")
            self.assertEqual(zone.find(".//Parameter").attrib["expression"], "[TIMEZONE_OFFSET_DST]")
            battery = header.find(f"PartText[@name='{layout}_battery_value']")
            self.assertEqual(battery.find(".//Parameter").attrib["expression"], "[BATTERY_PERCENT]")
            time = header.find(f"PartText[@name='{layout}_time']")
            self.assertIn("IS_24_HOUR_MODE", time.find(".//Parameter").attrib["expression"])
            for style in ("full", "short", "iso"):
                date = header.find(f"Condition/Compare[@expression='date_{style}']/PartText")
                self.assertLess(int(date.attrib["y"]), int(time.attrib["y"]))
            self.assertIsNotNone(header.find(f"PartText[@name='{layout}_ambient_time']"))

    def test_eight_slots_and_existing_provider_policies(self):
        slots = self.root.findall("Scene/ComplicationSlot")
        self.assertEqual([int(s.attrib["slotId"]) for s in slots], list(range(1, 9)))
        boxes = []
        for slot in slots:
            n = int(slot.attrib["slotId"])
            original = self.baseline.find(f"Scene/ComplicationSlot[@slotId='{n}']")
            self.assertEqual(slot.attrib["isCustomizable"], "TRUE")
            self.assertEqual(slot.attrib["supportedTypes"], original.attrib["supportedTypes"])
            self.assertEqual(slot.find("DefaultProviderPolicy").attrib, original.find("DefaultProviderPolicy").attrib)
            self.assertEqual([c.attrib["type"] for c in slot.findall("Complication")],
                             [c.attrib["type"] for c in original.findall("Complication")])
            box = slot.find("BoundingBox")
            boxes.append(tuple(int(box.attrib[k]) for k in ("x", "y", "width", "height")))
            for layout in LAYOUTS:
                for complication in slot.findall("Complication"):
                    self.assertIsNotNone(self.cell(n, layout, complication.attrib["type"]))
        for index, (x, y, w, h) in enumerate(boxes):
            for xx, yy, ww, hh in boxes[index + 1:]:
                self.assertFalse(x < xx + ww and xx < x + w and y < yy + hh and yy < y + h)

    def test_short_labels_and_legacy_option_ids(self):
        ids = ["TITLE", *(item["id"] for item in LABELS), "NONE"]
        font = ImageFont.truetype(str(RES / "font/terminal_mono.ttf"), 30)
        for item in LABELS:
            self.assertLessEqual(len(item["text"]), 4)
            self.assertLessEqual(font.getlength(item["text"]), 62)
        for n in range(1, 9):
            config = self.root.find(f"UserConfigurations/ListConfiguration[@id='label{n}']")
            self.assertEqual([o.attrib["id"] for o in config], ids)
            for layout in LAYOUTS:
                for complication_type in ("SHORT_TEXT", "LONG_TEXT", "RANGED_VALUE", "GOAL_PROGRESS", "EMPTY"):
                    group = self.cell(n, layout, complication_type)
                    manual = group.find("Condition/Default/PartText/.//Parameter")
                    self.assertEqual(manual.attrib["expression"], manual_label_expression(n))
                    label = group.find(f"Condition/Compare[@expression='label_title_{n}']/PartText")
                    self.assertEqual(label.find(".//Parameter").attrib["expression"], "[COMPLICATION.TITLE]")
                    if complication_type == "EMPTY":
                        self.assertEqual(group.find("PartText/Text/Font").text, "--")

    def test_clickable_centers_in_all_layouts(self):
        for n in range(1, 9):
            box = self.root.find(f"Scene/ComplicationSlot[@slotId='{n}']/BoundingBox").attrib
            for layout in LAYOUTS:
                g = cell_geometry(layout, n)
                centers = [(g["x"] + g["label_width"] / 2, g["y"] + g["label_height"] / 2),
                           (g["x"] + g["value_x"] + g["value_width"] / 2,
                            g["y"] + g["value_y"] + g["value_height"] / 2)]
                for x, y in centers:
                    self.assertGreaterEqual(x, int(box["x"]))
                    self.assertLessEqual(x, int(box["x"]) + int(box["width"]))
                    self.assertGreaterEqual(y, int(box["y"]))
                    self.assertLessEqual(y, int(box["y"]) + int(box["height"]))

    def test_real_font_and_no_blank_editor_options(self):
        font = TTFont(RES / "font/terminal_mono.ttf")
        cmap = font.getBestCmap()
        self.assertEqual(len({font["hmtx"][cmap[ord(c)]][0] for c in "123ABCАБВ%"}), 1)
        for char in "°—…ёЯ":
            self.assertIn(ord(char), cmap)
        for option in self.root.findall("UserConfigurations/ListConfiguration/ListOption"):
            with Image.open(RES / "drawable" / (option.attrib["icon"] + ".png")) as icon:
                self.assertEqual(icon.size, (192, 192))
                pixels = list(icon.convert("RGB").getdata())
                self.assertGreater(sum(1 for r, g, b in pixels if r > 180 and g > 180), 100)

    def test_prior_archive_unchanged(self):
        manifest = json.loads((ROOT / "versions/0.3.0/manifest.json").read_text())
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((ROOT / "versions/0.3.0" / name).read_bytes()).hexdigest(), digest)

    def test_battery_asset_and_empty_values_present(self):
        with Image.open(RES / "drawable/battery_status.png") as icon:
            self.assertEqual(icon.mode, "RGBA")
            self.assertEqual(icon.size, (108, 78))
        for n in range(1, 9):
            for layout in LAYOUTS:
                self.assertEqual(self.cell(n, layout, "EMPTY").find("PartText/Text/Font").text, "--")

    def test_layout_generator_is_reproducible(self):
        expected = ET.fromstring(build())
        self.assertEqual(ET.tostring(expected), ET.tostring(self.root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
