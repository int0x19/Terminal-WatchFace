#!/usr/bin/env python3
"""Regression checks for the combined layout, clock fonts and preserved choices."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET

from fontTools.ttLib import TTFont
from PIL import Image, ImageFont
from labels import LABELS, manual_label_expression
from build_layout import CLOCK_FONTS, ROWS, SLOTS, DATE_SIZE, cell_geometry, build

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "watchface/src/main/res"


class LayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(RES / "raw/watchface.xml").getroot()
        cls.baseline = ET.parse(ROOT / "versions/0.3.0/watchface.xml").getroot()
        cls.header = cls.root.find("Scene/Group[@name='header']")

    def cell(self, n, complication_type):
        return self.root.find(f"Scene/ComplicationSlot[@slotId='{n}']/Complication[@type='{complication_type}']/Group")

    def clock(self, choice):
        return self.header.find(f"Condition/Compare[@expression='clock_font_{choice}']/PartText")

    def test_three_selectable_clock_fonts(self):
        config = self.root.find("UserConfigurations/ListConfiguration[@id='clockFont']")
        self.assertEqual(config.attrib["defaultValue"], "block")
        self.assertEqual([o.attrib["id"] for o in config], list(CLOCK_FONTS))
        self.assertIsNone(self.root.find("UserConfigurations/ListConfiguration[@id='layout']"))
        for locale in ("values", "values-ru"):
            strings = ET.parse(RES / locale / "strings.xml").getroot()
            for name in [config.attrib["displayName"], *(o.attrib["displayName"] for o in config)]:
                self.assertIsNotNone(strings.find(f"string[@name='{name}']"))
        for choice, family in CLOCK_FONTS.items():
            time = self.clock(choice)
            self.assertEqual(time.find("Text/Font").attrib["family"], family)
            self.assertEqual(time.find("Variant").attrib["value"], "0")

    def test_live_header_sources_and_date_modes(self):
        utc = self.header.find("PartText[@name='utc_time']")
        self.assertEqual(utc.find("Localization").attrib["timeZone"], "UTC")
        self.assertEqual(utc.find(".//Template").text, "%02d:%02d")
        self.assertEqual([p.attrib["expression"] for p in utc.findall(".//Parameter")],
                         ["[HOUR_0_23]", "[MINUTE]"])
        zone = self.header.find("PartText[@name='timezone']")
        self.assertEqual(zone.find(".//Parameter").attrib["expression"], "[TIMEZONE_OFFSET_DST]")
        self.assertEqual(zone.find(".//Template").text, "UTC%s")
        self.assertEqual(zone.find("Localization").attrib["timeZone"], "SYNC_TO_DEVICE")
        self.assertEqual(self.header.find("PartText[@name='battery_label']/Text/Font").text, "BATT")
        battery = self.header.find("PartText[@name='battery_value']")
        self.assertEqual(battery.find(".//Parameter").attrib["expression"], "[BATTERY_PERCENT]")
        for choice in CLOCK_FONTS:
            time = self.clock(choice)
            self.assertIn("IS_24_HOUR_MODE", time.find(".//Parameter").attrib["expression"])
            for style in ("full", "short", "iso"):
                date = self.header.find(f"Condition/Compare[@expression='date_{style}']/PartText")
                self.assertLess(int(date.attrib["y"]) + int(date.attrib["height"]), int(time.attrib["y"]))

    def test_centered_columns_clock_and_compact_rows(self):
        centers = []
        for top, bottom in (("utc_time", "timezone"), ("battery_label", "battery_value")):
            parts = [self.header.find(f"PartText[@name='{name}']") for name in (top, bottom)]
            x_centers = [int(p.attrib["x"]) + int(p.attrib["width"]) / 2 for p in parts]
            self.assertEqual(x_centers[0], x_centers[1])
            self.assertTrue(all(p.find("Text").attrib["align"] == "CENTER" for p in parts))
            centers.append(x_centers[0])
        self.assertEqual(sum(centers) / 2, 225)
        for choice in CLOCK_FONTS:
            time = self.clock(choice)
            self.assertEqual(int(time.attrib["x"]) + int(time.attrib["width"]) / 2, 225)
            self.assertEqual(time.find("Text").attrib["align"], "CENTER")
        self.assertEqual([b - a for a, b in zip(ROWS, ROWS[1:])], [36, 36, 36])

    def test_clock_outlines_centered_in_equal_width_cells(self):
        for family in CLOCK_FONTS.values():
            font = TTFont(RES / "font" / (family + ".ttf"))
            self.assertEqual(font["post"].isFixedPitch, 1)
            cmap, advances = font.getBestCmap(), set()
            for char in "0123456789:":
                name = cmap[ord(char)]
                glyph = font["glyf"][name]
                advance, bearing = font["hmtx"][name]
                advances.add(advance)
                self.assertEqual(bearing, glyph.xMin)
                self.assertLessEqual(abs((glyph.xMin + glyph.xMax) / 2 - advance / 2), 0.5)
                self.assertAlmostEqual(advance / font["head"].unitsPerEm, 0.6, places=3)
            self.assertEqual(len(advances), 1)
            for value in ("00:00", "11:11", "23:59", "12:59"):
                f = ImageFont.truetype(str(RES / "font" / (family + ".ttf")), 100)
                self.assertLessEqual(f.getlength(value), 302)

    def test_ambient_hides_table_and_seconds(self):
        ambient = self.header.find("PartText[@name='ambient_time']")
        self.assertEqual(ambient.attrib["alpha"], "0")
        self.assertEqual(ambient.find("Variant").attrib["value"], "255")
        self.assertEqual(ambient.find("Text/Font").attrib["family"], "terminal_dot")
        seconds = self.header.find("Condition/Compare[@expression='show_seconds']/PartText")
        self.assertEqual(seconds.find("Variant").attrib["value"], "0")
        for slot in self.root.findall("Scene/ComplicationSlot"):
            self.assertEqual(slot.find("Variant").attrib["value"], "0")

    def test_seven_slots_and_existing_provider_policies(self):
        slots = self.root.findall("Scene/ComplicationSlot")
        self.assertEqual([int(s.attrib["slotId"]) for s in slots], list(SLOTS))
        self.assertIsNone(self.root.find("Scene/ComplicationSlot[@slotId='8']"))
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
            for complication in slot.findall("Complication"):
                self.assertIsNotNone(self.cell(n, complication.attrib["type"]))
        for index, (x, y, w, h) in enumerate(boxes):
            for xx, yy, ww, hh in boxes[index + 1:]:
                self.assertFalse(x < xx + ww and xx < x + w and y < yy + hh and yy < y + h)

    def test_existing_configuration_ids_preserved(self):
        expected_ids = {item.attrib["id"] for item in self.baseline.find("UserConfigurations")}
        expected_ids.remove("label8")
        expected_ids.add("clockFont")
        self.assertEqual({item.attrib["id"] for item in self.root.find("UserConfigurations")}, expected_ids)
        for old in self.baseline.find("UserConfigurations"):
            if old.attrib["id"] == "label8":
                self.assertIsNone(self.root.find("UserConfigurations/ListConfiguration[@id='label8']"))
                continue
            current = self.root.find(f"UserConfigurations/{old.tag}[@id='{old.attrib['id']}']")
            old_copy, current_copy = deepcopy(old), deepcopy(current)
            old_copy.tail = current_copy.tail = None
            self.assertEqual(ET.tostring(current_copy), ET.tostring(old_copy))

    def test_short_labels_and_legacy_option_ids(self):
        ids = ["TITLE", *(item["id"] for item in LABELS), "NONE"]
        font = ImageFont.truetype(str(RES / "font/terminal_mono.ttf"), 30)
        for item in LABELS:
            self.assertLessEqual(len(item["text"]), 4)
            self.assertLessEqual(font.getlength(item["text"]), 62)
        for n in SLOTS:
            config = self.root.find(f"UserConfigurations/ListConfiguration[@id='label{n}']")
            self.assertEqual([o.attrib["id"] for o in config], ids)
            for complication_type in ("SHORT_TEXT", "LONG_TEXT", "RANGED_VALUE", "GOAL_PROGRESS", "EMPTY"):
                group = self.cell(n, complication_type)
                manual = group.find("Condition/Default/.//Parameter")
                self.assertEqual(manual.attrib["expression"], manual_label_expression(n))
                label = group.find(f"Condition/Compare[@expression='label_title_{n}']")
                self.assertEqual(label.find(".//Parameter").attrib["expression"], "[COMPLICATION.TITLE]")
                if complication_type == "EMPTY":
                    if n == 4:
                        for part in group.findall(".//PartText"):
                            self.assertEqual(part.findall("Text/Font")[-1].text, "--")
                    else:
                        self.assertEqual(group.find("PartText/Text/Font").text, "--")

    def test_clickable_centers(self):
        for n in SLOTS:
            box = self.root.find(f"Scene/ComplicationSlot[@slotId='{n}']/BoundingBox").attrib
            g = cell_geometry(n)
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

    def test_prior_archives_unchanged(self):
        for version in ("0.3.0", "0.4.0-test", "0.5.0-test", "0.6.0-test", "0.7.0-test"):
            archive = ROOT / "versions" / version
            manifest = json.loads((archive / "manifest.json").read_text())
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((archive / name).read_bytes()).hexdigest(), digest)

    def test_rollback_resources_match_saved_060(self):
        build_config = (ROOT / "watchface/build.gradle.kts").read_text()
        if 'versionName = "0.6.1-rollback"' not in build_config:
            self.skipTest("Exact-resource comparison applies to the rollback build only")
        self.assertIn("versionCode = 8", build_config)
        archive = ROOT / "versions/0.6.0-test"
        self.assertEqual((RES / "raw/watchface.xml").read_bytes(), (archive / "watchface.xml").read_bytes())
        for name in ("preview.png", "ambient-preview.png", "font-comparison.png",
                     *(f"font-{choice}{suffix}.png" for choice in CLOCK_FONTS for suffix in ("", "-ambient"))):
            current = ROOT / "docs" / ("design-preview.png" if name == "preview.png" else name)
            self.assertEqual(current.read_bytes(), (archive / name).read_bytes(), name)
        self.assertEqual((RES / "drawable/preview.png").read_bytes(), (archive / "preview.png").read_bytes())
        with zipfile.ZipFile(archive / "terminal-face-0.6.0-test.apk") as apk:
            saved_fonts = {hashlib.sha256(apk.read(name)).hexdigest()
                           for name in apk.namelist() if name.endswith(".ttf")}
        current_fonts = {hashlib.sha256(path.read_bytes()).hexdigest() for path in (RES / "font").glob("*.ttf")}
        self.assertEqual(len(current_fonts), 4)
        self.assertEqual(current_fonts, saved_fonts)

    def test_larger_date_fits_all_english_months(self):
        font = ImageFont.truetype(str(RES / "font/terminal_mono.ttf"), DATE_SIZE)
        self.assertGreaterEqual(DATE_SIZE / 28, 1.2)
        self.assertLessEqual(DATE_SIZE / 28, 1.4)
        for style in ("full", "short", "iso"):
            part = self.header.find(f"Condition/Compare[@expression='date_{style}']/PartText")
            self.assertEqual(int(part.find("Text/Font").attrib["size"]), DATE_SIZE)
            self.assertEqual(int(part.attrib["x"]) + int(part.attrib["width"]) / 2, 225)
        for month in ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
                      "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"):
            for weekday in ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"):
                self.assertLessEqual(font.getlength(f"{weekday} 31 {month} 2026"), 390)

    def test_wide_bottom_line_centers_label_and_value_together(self):
        slot = self.root.find("Scene/ComplicationSlot[@slotId='4']")
        self.assertEqual(slot.attrib["displayName"], "field_4_name")
        box = slot.find("BoundingBox").attrib
        self.assertEqual(int(box["x"]) + int(box["width"]) / 2, 225)
        self.assertEqual(box["width"], "286")
        for complication_type in ("SHORT_TEXT", "LONG_TEXT", "RANGED_VALUE", "GOAL_PROGRESS", "EMPTY"):
            group = self.cell(4, complication_type)
            for part in group.findall(".//PartText"):
                self.assertEqual(part.attrib["width"], "286")
                self.assertEqual(part.find("Text").attrib["align"], "CENTER")
                self.assertEqual(part.find("Text").attrib["maxLines"], "1")
                self.assertEqual(part.findall("Text/Font")[-1].attrib["color"], "[CONFIGURATION.palette.1]")
            hidden = group.find("Condition/Compare[@expression='label_hidden_4']")
            self.assertTrue(all(len(p.findall("Text/Font")) == 1 for p in hidden.findall(".//PartText")))
            title = group.find("Condition/Compare[@expression='label_title_4']")
            for part in title.findall(".//PartText"):
                self.assertEqual(part.find("Text/Font").attrib["color"], "[CONFIGURATION.palette.0]")
            if complication_type != "EMPTY":
                image = group.find("Condition/Compare[@expression='label_icon_4']/.//InlineImage")
                self.assertEqual(image.attrib["resource"], "[COMPLICATION.MONOCHROMATIC_IMAGE]")
                self.assertEqual(image.attrib["source"], "[COMPLICATION.MONOCHROMATIC_IMAGE]")
            if complication_type in ("RANGED_VALUE", "GOAL_PROGRESS"):
                numeric = "[COMPLICATION.RANGED_VALUE_VALUE]" if complication_type == "RANGED_VALUE" else "[COMPLICATION.GOAL_PROGRESS_VALUE]"
                self.assertTrue(any(p.attrib["expression"] == numeric for p in group.findall(".//Parameter")))

    def test_layout_generator_is_reproducible(self):
        expected = ET.fromstring(build())
        self.assertEqual(ET.tostring(expected), ET.tostring(self.root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
