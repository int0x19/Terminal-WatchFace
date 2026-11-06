#!/usr/bin/env python3
"""Check equal visible spacing and larger fonts without altering prior sketches."""
import hashlib
import json
import re
import subprocess
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageFont

from build_large_type_sketches import DATE, DEMO, FONTS, OUT as PREVIOUS, PROFILES, ROOT, build_sketch, xml_bytes
from refine_familiar_sketch import OUT, PROFILE, build_refined, ink_bands
from rebuild_assets import render_preview
from test_large_type_sketches import structure


class RefinedFamiliarTest(unittest.TestCase):
    def test_originals_preserved_and_rejected_variants_not_used(self):
        manifest = json.loads((PREVIOUS / "manifest.json").read_text())
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((PREVIOUS / name).read_bytes()).hexdigest(), digest)
        for choice in PROFILES:
            self.assertEqual(xml_bytes(build_sketch(choice)), (PREVIOUS / f"{choice}.xml").read_bytes())
        for archive in (ROOT / "versions").glob("*/manifest.json"):
            for name, digest in json.loads(archive.read_text())["files"].items():
                self.assertEqual(hashlib.sha256((archive.parent / name).read_bytes()).hexdigest(), digest)
        manifest = json.loads((OUT / "manifest.json").read_text())
        self.assertEqual(manifest["selectedLayout"], "familiar")
        self.assertEqual(manifest["rejectedLayouts"], ["stacked", "maximum"])

    def test_same_settings_providers_and_five_nonoverlapping_fields(self):
        old, root = build_sketch("familiar"), build_refined()
        self.assertEqual(structure(root.find("UserConfigurations")), structure(old.find("UserConfigurations")))
        self.assertEqual(root.find("UserConfigurations/ListConfiguration[@id='dateStyle']").attrib["defaultValue"], "full")
        boxes = []
        for slot in root.findall("Scene/ComplicationSlot"):
            original = old.find(f"Scene/ComplicationSlot[@slotId='{slot.attrib['slotId']}']")
            self.assertEqual(slot.attrib, original.attrib)
            self.assertEqual(structure(slot.find("DefaultProviderPolicy")), structure(original.find("DefaultProviderPolicy")))
            boxes.append(tuple(int(slot.find("BoundingBox").attrib[key]) for key in ("x", "y", "width", "height")))
        self.assertEqual(len(boxes), 5)
        for index, (x, y, w, h) in enumerate(boxes):
            for xx, yy, ww, hh in boxes[index + 1:]:
                self.assertFalse(x < xx + ww and xx < x + w and y < yy + hh and yy < y + h)
        self.assertEqual(PROFILE["rows"][1] - PROFILE["rows"][0], PROFILE["footer_y"] - PROFILE["rows"][1])

    def test_every_requested_font_is_larger_and_date_still_fits(self):
        for key in ("header_size", "date_size", "clock_size", "label_size", "value_size",
                    "fallback_size", "long_size", "footer_size"):
            self.assertGreater(PROFILE[key], PROFILES["familiar"][key], key)
        font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), PROFILE["date_size"])
        for month in ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
                      "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"):
            self.assertLessEqual(font.getlength(f"WED 31 {month} 2026"), 390)
        for profile in (PROFILES["familiar"], PROFILE):
            font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), profile["fallback_size"])
            self.assertLessEqual(font.getlength("+25/+8"), profile["value_width"])
        font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), PROFILE["long_size"])
        long_width = font.getlength("0.79 KM") - 6 * 0.04 * PROFILE["long_size"]
        self.assertLessEqual(long_width, PROFILE["value_width"])

    def test_visible_gaps_are_nearly_equal_not_only_the_line_boxes(self):
        old = ink_bands(build_sketch("familiar"))["visibleVerticalGaps"]
        new = ink_bands(build_refined())["visibleVerticalGaps"]
        self.assertGreater(max(old) - min(old), 15)
        self.assertLessEqual(max(new) - min(new), 2)
        self.assertLess(new[0], old[0])
        self.assertTrue(all(14 <= gap <= 18 for gap in new))
        for clock in FONTS:
            self.assertTrue(all(gap >= 10 for gap in ink_bands(build_refined(), clock)["visibleVerticalGaps"]))

    def test_saved_previews_no_clipped_strokes_and_unchanged_ambient_policy(self):
        root = build_refined()
        self.assertEqual(xml_bytes(root), (OUT / "familiar-refined.xml").read_bytes())
        stress = {2: ("HI/LO", "34° / 21°"), 3: ("DIST", "0.79 KM"),
                  4: ("ALRM", "06:45"), 6: ("GOAL", "8000"), 7: ("HR", "84 BPM")}
        mask = Image.new("L", (450, 450))
        ImageDraw.Draw(mask).ellipse((0, 0, 449, 449), fill=255)
        for clock in FONTS:
            with Image.open(OUT / f"familiar-{clock}.png") as saved:
                actual = render_preview(watchface=root, clock_font=clock, complication_data=DEMO, source_values=DATE)
                self.assertEqual(saved.tobytes(), actual.tobytes())
            for data in (DEMO, stress):
                full = render_preview(watchface=root, clock_font=clock, complication_data=data,
                                      source_values=DATE, background_mode="amoled", clip_circle=False)
                outside = ImageChops.multiply(full.convert("L"), ImageChops.invert(mask))
                self.assertIsNone(outside.point(lambda value: 255 if value > 8 else 0).getbbox())
        for slot in root.findall("Scene/ComplicationSlot"):
            self.assertEqual(slot.find("Variant").attrib["value"], "0")
        with Image.open(OUT / "ambient.png") as saved:
            self.assertEqual(saved.tobytes(), render_preview(watchface=root, ambient=True,
                                                            complication_data=DEMO, source_values=DATE).tobytes())

    def test_manifest_and_preview_interactions_with_and_without_tweak(self):
        manifest = json.loads((OUT / "manifest.json").read_text())
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((OUT / name).read_bytes()).hexdigest(), digest)
        fragment = (OUT / "familiar-refinement.html").read_text()
        self.assertLess(len(fragment.encode()), 1_000_000)
        self.assertNotIn("__PREVIEW_IMAGES__", fragment)
        self.assertNotIn("data-variant", fragment)
        script = re.search(r"<script>(.*?)</script>", fragment, re.S).group(1)
        harness = """
const vm = require('node:vm'), assert = require('node:assert/strict'), fs = require('node:fs');
const script = fs.readFileSync(0, 'utf8');
function run(withTweak) {
  const image = {}, spec = {}, controls = {};
  const root = { querySelector: selector => selector === 'img' ? image : spec };
  const sandbox = { document: { getElementById: id => {
    assert.equal(id, 'terminal-familiar-refinement'); return root;
  }}};
  if (withTweak) sandbox.Tweak = class {
    constructor(options) { this.options = options; }
    addSelect(state, key, options) { controls[key] = { state, options, render: this.options.onChange }; }
  };
  vm.runInNewContext(script, sandbox);
  assert.ok(image.src.startsWith('data:image/png;base64,'));
  assert.ok(spec.textContent.includes('38'));
  const initial = image.src;
  if (!withTweak) return;
  controls.revision.state.revision = 'previous'; controls.revision.render();
  assert.notEqual(image.src, initial); assert.ok(spec.textContent.includes('36'));
  controls.clockFont.state.clockFont = 'mono'; controls.clockFont.render();
  const previousMono = image.src;
  controls.revision.state.revision = 'refined'; controls.revision.render();
  assert.notEqual(image.src, previousMono); assert.ok(spec.textContent.includes('42'));
  controls.clockFont.state.clockFont = 'block'; controls.clockFont.render();
  assert.equal(image.src, initial);
}
run(true); run(false);
"""
        subprocess.run(["node", "-e", harness], input=script, text=True, capture_output=True,
                       check=True, timeout=15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
