#!/usr/bin/env python3
"""Check requested 34/40 roles, UTC swap and unchanged released APK/source."""
import hashlib
import json
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw, ImageFont

from build_large_type_sketches import FONTS, ROOT, xml_bytes
from preview_typography_hierarchy import BASE, DEMO, OUT, PROFILE, SOURCES, build_hierarchy, preview
from test_large_type_sketches import structure


class TypographyHierarchyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = build_hierarchy()
        cls.previous = ET.parse(BASE).getroot()
        cls.header = cls.root.find("Scene/Group[@name='header']")

    def test_existing_release_and_all_archives_unchanged(self):
        self.assertEqual((ROOT / "watchface/src/main/res/raw/watchface.xml").read_bytes(), BASE.read_bytes())
        for path in [*(ROOT / "versions").glob("*/manifest.json"),
                     *(ROOT / "docs/large-type-sketches").glob("*/manifest.json")]:
            for name, digest in json.loads(path.read_text())["files"].items():
                self.assertEqual(hashlib.sha256((path.parent / name).read_bytes()).hexdigest(), digest)

    def test_live_utc_and_timezone_swapped_with_correct_sizes_and_colors(self):
        roles = {"timezone": (38, 34, "0"), "battery_label": (38, 34, "0"),
                 "utc_time": (72, 40, "2"), "battery_value": (72, 40, "2")}
        parts = {}
        for name, (y, size, color) in roles.items():
            part = self.header.find(f".//PartText[@name='{name}']")
            parts[name] = part
            self.assertEqual(int(part.attrib["y"]), y)
            self.assertEqual(int(part.find("Text/Font").attrib["size"]), size)
            self.assertEqual(part.attrib["tintColor"], f"[CONFIGURATION.palette.{color}]")
            self.assertEqual(part.find("Text").attrib["align"], "CENTER")
        self.assertEqual(parts["utc_time"].find("Localization").attrib["timeZone"], "UTC")
        self.assertEqual(parts["timezone"].find("Localization").attrib["timeZone"], "SYNC_TO_DEVICE")
        self.assertEqual(parts["timezone"].find(".//Parameter").attrib["expression"], "[TIMEZONE_OFFSET_DST]")
        self.assertEqual(parts["utc_time"].find(".//Template").text, "%02d:%02d")
        self.assertEqual(parts["battery_value"].find(".//Parameter").attrib["expression"], "[BATTERY_PERCENT]")
        for top, bottom in (("timezone", "utc_time"), ("battery_label", "battery_value")):
            self.assertEqual(int(parts[top].attrib["x"]) + int(parts[top].attrib["width"]) / 2,
                             int(parts[bottom].attrib["x"]) + int(parts[bottom].attrib["width"]) / 2)

    def test_all_complication_captions_34_values_40_or_38_including_footer(self):
        for slot in self.root.findall("Scene/ComplicationSlot"):
            for complication in slot.findall("Complication"):
                group = complication.find("Group")
                if slot.attrib["slotId"] == "4":
                    for font in group.findall(".//Font"):
                        expected = "34" if font.attrib.get("color") == "[CONFIGURATION.palette.0]" else "40"
                        self.assertEqual(font.attrib["size"], expected)
                else:
                    for font in group[0].findall(".//Font"):
                        self.assertEqual(font.attrib["size"], "34")
                    for node in list(group)[1:]:
                        for font in node.findall(".//Font"):
                            self.assertIn(font.attrib["size"], ("38", "40"))
                            if complication.attrib["type"] == "LONG_TEXT":
                                self.assertEqual(font.attrib["size"], "38")

    def test_full_date_40_fits_all_months_and_ordinary_values_fit_at_40(self):
        font_path = ROOT / "watchface/src/main/res/font/terminal_mono.ttf"
        font = ImageFont.truetype(str(font_path), 40)
        for style in ("full", "short", "iso"):
            part = self.header.find(f"Condition/Compare[@expression='date_{style}']/PartText")
            self.assertEqual(part.find("Text/Font").attrib["size"], "40")
            self.assertEqual(part.find("Text/Font").attrib["letterSpacing"], "-0.02")
        for month in ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
                      "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"):
            text = f"WED 30 {month} 2026"
            self.assertLessEqual(font.getlength(text) - (len(text) - 1) * .02 * 40, 390)
        for value in ("VFR", "CLOUDS", "+19/+6", "10KM+"):
            self.assertLessEqual(font.getlength(value) + 2, PROFILE["value_width"])

    def test_clock_settings_and_provider_identities_unchanged(self):
        self.assertEqual(structure(self.root.find("UserConfigurations")), structure(self.previous.find("UserConfigurations")))
        self.assertEqual([s.attrib for s in self.root.findall("Scene/ComplicationSlot")],
                         [s.attrib for s in self.previous.findall("Scene/ComplicationSlot")])
        for slot in self.root.findall("Scene/ComplicationSlot"):
            old = self.previous.find(f"Scene/ComplicationSlot[@slotId='{slot.attrib['slotId']}']")
            self.assertEqual(structure(slot.find("DefaultProviderPolicy")), structure(old.find("DefaultProviderPolicy")))
            self.assertEqual(structure(slot.find("BoundingBox")), structure(old.find("BoundingBox")))
        for clock in FONTS:
            path = f"Scene/Group/Condition/Compare[@expression='clock_font_{clock}']/PartText"
            self.assertEqual(structure(self.root.find(path)), structure(self.previous.find(path)))
        self.assertNotIn("CLOUDS", xml_bytes(self.root).decode())

    def test_saved_xml_and_previews_are_reproducible(self):
        self.assertEqual(xml_bytes(self.root), (OUT / "hierarchy.xml").read_bytes())
        for clock in FONTS:
            for revision, root in (("current", self.root), ("previous", self.previous)):
                with Image.open(OUT / f"{revision}-{clock}.png") as saved:
                    self.assertEqual(saved.tobytes(), preview(root, clock).tobytes())
        with Image.open(OUT / "ambient.png") as saved:
            self.assertEqual(saved.tobytes(), preview(self.root, ambient=True).tobytes())

    def test_no_clipping_with_fractional_offsets_and_long_date(self):
        mask = Image.new("L", (450, 450))
        ImageDraw.Draw(mask).ellipse((0, 0, 449, 449), fill=255)
        for clock in FONTS:
            for offset in ("+5", "+14", "-12", "+5:45", "+13:45", "-3:30"):
                with self.subTest(clock=clock, offset=offset):
                    sources = {**SOURCES, "TIMEZONE_OFFSET_DST": offset,
                               "DAY_OF_WEEK_S": "WED", "DAY": 30, "MONTH_F": "SEPTEMBER"}
                    image = preview(self.root, clock, source_values=sources, clip_circle=False)
                    outside = ImageChops.multiply(image.convert("L"), ImageChops.invert(mask))
                    self.assertIsNone(outside.point(lambda value: 255 if value > 8 else 0).getbbox())

    def test_self_contained_interactive_preview(self):
        fragment = (OUT / "typography-hierarchy.html").read_text()
        self.assertLess(len(fragment.encode()), 1_000_000)
        self.assertNotIn("__PREVIEW_IMAGES__", fragment)
        script = re.search(r"<script>(.*?)</script>", fragment, re.S).group(1)
        harness = """
const vm = require('node:vm'), fs = require('node:fs'), assert = require('node:assert/strict');
const script = fs.readFileSync(0, 'utf8');
for (const withTweak of [true, false]) {
  const image = {}, spec = {}, controls = {};
  const root = { querySelector: selector => selector === 'img' ? image : spec };
  const sandbox = { document: { getElementById: id => {
    assert.equal(id, 'terminal-typography-hierarchy'); return root;
  }}};
  if (withTweak) sandbox.Tweak = class {
    constructor(options) { this.options = options; }
    addSelect(state, key) { controls[key] = { state, render: this.options.onChange }; }
  };
  vm.runInNewContext(script, sandbox);
  assert.ok(image.src.startsWith('data:image/png;base64,'));
  assert.ok(spec.textContent.includes('34'));
  const initial = image.src;
  if (!withTweak) continue;
  controls.revision.state.revision = 'previous'; controls.revision.render();
  assert.notEqual(image.src, initial); assert.ok(spec.textContent.includes('42'));
  controls.clockFont.state.clockFont = 'mono'; controls.clockFont.render();
  assert.notEqual(image.src, initial);
  controls.revision.state.revision = 'current'; controls.revision.render();
  controls.clockFont.state.clockFont = 'block'; controls.clockFont.render();
  assert.equal(image.src, initial);
}
"""
        subprocess.run(["node", "-e", harness], input=script, text=True, capture_output=True,
                       check=True, timeout=15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
