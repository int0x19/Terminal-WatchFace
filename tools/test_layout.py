#!/usr/bin/env python3
"""Regression checks for WFF resources; does not substitute for device tests."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from fontTools.ttLib import TTFont
from PIL import Image, ImageFont
from labels import LABELS, manual_label_expression

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "watchface/src/main/res"


class LayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(RES / "raw/watchface.xml").getroot()

    def test_header_positions_and_live_sources(self):
        scene = self.root.find("Scene")
        expected = {"utc_time": (110, 48), "timezone": (110, 73),
                    "battery_label": (272, 48), "battery_value": (272, 73)}
        for name, coordinates in expected.items():
            part = scene.find(f"PartText[@name='{name}']")
            self.assertEqual(tuple(int(part.attrib[k]) for k in ("x", "y")), coordinates)
        utc = scene.find("PartText[@name='utc_time']")
        self.assertEqual(utc.find("Localization").attrib["timeZone"], "UTC")
        self.assertEqual([p.attrib["expression"] for p in utc.findall(".//Parameter")],
                         ["[HOUR_0_23]", "[MINUTE]"])
        timezone = scene.find("PartText[@name='timezone']")
        self.assertEqual(timezone.find("Localization").attrib["timeZone"], "SYNC_TO_DEVICE")
        self.assertEqual(timezone.find(".//Parameter").attrib["expression"], "[TIMEZONE_OFFSET_DST]")
        battery = scene.find("PartText[@name='battery_value']")
        self.assertEqual(battery.find(".//Parameter").attrib["expression"], "[BATTERY_PERCENT]")
        self.assertEqual(scene.find("PartText[@name='battery_label']/Text/Font").text, "BATT")
        self.assertIsNone(self.root.find("UserConfigurations/ListConfiguration[@id='city']"))

    def test_date_above_clock_in_every_style(self):
        for style in ("full", "short", "iso"):
            part = self.root.find(f"Scene/Condition/Compare[@expression='date_{style}']/PartText")
            self.assertEqual((int(part.attrib["x"]), int(part.attrib["y"])), (55, 108))
            self.assertLessEqual(int(part.attrib["y"]) + int(part.attrib["height"]), 138)
            self.assertEqual(part.find("Text/Font").attrib["size"], "26")
        self.assertIsNone(self.root.find(".//PartText[@y='224']"))

    def test_short_manual_labels_and_legacy_ids(self):
        expected_ids = ["TITLE", *(item["id"] for item in LABELS), "NONE"]
        self.assertEqual(len(expected_ids), len(set(expected_ids)))
        self.assertEqual(len({item["text"] for item in LABELS}), len(LABELS))
        self.assertTrue({"HR", "BPM", "NTFY", "STEPS", "ALRM", "SPO2"}.issubset(expected_ids))
        captions = {item["id"]: item["text"] for item in LABELS}
        self.assertEqual({k: captions[k] for k in ("HI/LO", "STEPS", "EVENT")},
                         {"HI/LO": "H/L", "STEPS": "STEP", "EVENT": "EVNT"})
        font = ImageFont.truetype(str(RES / "font/terminal_mono.ttf"), 26)
        for item in LABELS:
            self.assertLessEqual(len(item["text"]), 4)
            self.assertLessEqual(font.getlength(item["text"]), 62)
        locales = [ET.parse(RES / d / "strings.xml").getroot() for d in ("values", "values-ru")]
        for n in range(1, 9):
            config = self.root.find(f"UserConfigurations/ListConfiguration[@id='label{n}']")
            self.assertEqual([option.attrib["id"] for option in config], expected_ids)
            for item in LABELS:
                option = config.find(f"ListOption[@id='{item['id']}']")
                key = f"label_{item['key']}"
                self.assertEqual(option.attrib["displayName"], key)
                self.assertEqual(option.attrib["icon"], f"{key}_icon")
                for locale in locales:
                    value = locale.find(f"string[@name='{key}']").text
                    self.assertTrue(value.startswith(item["text"] + " — "))
            parameters = self.root.findall(f"Scene/ComplicationSlot[@slotId='{n}']/Complication/Condition/Default/PartText/Text/Font/Template/Parameter")
            manual_parameters = [p for p in parameters if "CONFIGURATION.label" in p.attrib["expression"]]
            self.assertEqual(len(manual_parameters), 5)
            for parameter in manual_parameters:
                self.assertEqual(parameter.attrib["expression"], manual_label_expression(n))

    def test_icon_sheet_covers_all_options(self):
        resources = {option.attrib["icon"] for option in self.root.findall("UserConfigurations/ListConfiguration/ListOption")}
        with Image.open(ROOT / "docs/label-options.png") as sheet:
            self.assertEqual(sheet.size, (960, ((len(resources) + 4) // 5) * 192))

    def test_long_value_keeps_units_after_font_increase(self):
        font = ImageFont.truetype(str(RES / "font/terminal_mono.ttf"), 22)
        for slot in self.root.findall("Scene/ComplicationSlot"):
            part = slot.find("Complication[@type='LONG_TEXT']/Condition/Compare/PartText[@x='65']")
            f = part.find("Text/Font")
            self.assertEqual(f.attrib["size"], "22")
            spacing = float(f.attrib["letterSpacing"]) * 22
            value = "NE 3.1 M/S"
            width = font.getlength(value) + (len(value) - 1) * spacing
            self.assertLessEqual(width, int(part.attrib["width"]))

    def test_eight_independent_slots_and_auto_labels(self):
        slots = self.root.findall("Scene/ComplicationSlot")
        self.assertEqual([int(s.attrib["slotId"]) for s in slots], list(range(1, 9)))
        for slot in slots:
            n = slot.attrib["slotId"]
            self.assertEqual(slot.attrib["isCustomizable"], "TRUE")
            config = self.root.find(f"UserConfigurations/ListConfiguration[@id='label{n}']")
            self.assertEqual(config.attrib["defaultValue"], "TITLE")
            self.assertEqual(config[0].attrib["id"], "TITLE")
            for complication in slot.findall("Complication"):
                condition = complication.find("Condition")
                expressions = condition.findall("Expressions/Expression")
                self.assertIn(f"label_title_{n}", [e.attrib["name"] for e in expressions])
                if complication.attrib["type"] != "EMPTY":
                    icon = condition.find(f"Compare[@expression='label_icon_{n}']/PartImage/Image")
                    self.assertEqual(icon.attrib["resource"], "[COMPLICATION.MONOCHROMATIC_IMAGE]")
                fallback = condition.find(f"Compare[@expression='label_auto_empty_{n}']/.//Font")
                self.assertEqual(fallback.text, "—")

    def test_no_blank_editor_options(self):
        for option in self.root.findall("UserConfigurations/ListConfiguration/ListOption"):
            resource = option.attrib["icon"]
            image = Image.open(RES / "drawable" / f"{resource}.png").convert("RGBA")
            self.assertEqual(image.size, (192, 192))
            # The title area must contain actual high-contrast lettering.
            pixels = list(image.crop((35, 48, 157, 100)).getdata())
            self.assertGreater(sum(1 for r, g, b, a in pixels if r > 200 and g > 200 and a), 100)

    def test_real_monospace_font_and_text_fit(self):
        font = TTFont(RES / "font/terminal_mono.ttf")
        cmap = font.getBestCmap()
        widths = {font["hmtx"][cmap[ord(c)]][0] for c in "0123456789ABCDEFАБВГДЕЁ%"}
        self.assertEqual(len(widths), 1)
        for char in "°—…ёЯ":
            self.assertIn(ord(char), cmap)
        self.assertEqual(font["post"].isFixedPitch, 1)
        pil_font = ImageFont.truetype(str(RES / "font/terminal_mono.ttf"), 26)
        self.assertLessEqual(pil_font.getlength("H/L"), 62)
        self.assertLessEqual(pil_font.getlength("STEP"), 62)
        self.assertLessEqual(pil_font.getlength("TUE 08 SEPTEMBER 2026"), 340)
        self.assertLessEqual(pil_font.getlength("23:59 UTC"), 156)
        for part in self.root.findall(".//PartText"):
            f = part.find("Text/Font")
            if part.attrib.get("name") not in {"time", "seconds", "ambient_time"}:
                self.assertEqual(f.attrib["family"], "terminal_mono")
                self.assertGreaterEqual(float(f.attrib["size"]), 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
