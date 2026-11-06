#!/usr/bin/env python3
"""Verify five-field proposals separately from the unchanged 0.8.1 application."""
from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import json
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw

from build_large_type_sketches import BASE, DATE, DEMO, FONTS, OUT, PROFILES, ROOT, SLOTS, build_sketch, xml_bytes
from rebuild_assets import render_preview


def structure(element):
    element = deepcopy(element)
    for node in element.iter():
        node.tail = None
        if not (node.text or "").strip():
            node.text = None
    return ET.tostring(element)


class FragmentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class LargeTypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(BASE).getroot()
        cls.mask = Image.new("L", (450, 450))
        ImageDraw.Draw(cls.mask).ellipse((0, 0, 449, 449), fill=255)

    def test_active_application_and_old_archives_unchanged(self):
        self.assertEqual((ROOT / "watchface/src/main/res/raw/watchface.xml").read_bytes(), BASE.read_bytes())
        build = (ROOT / "watchface/build.gradle.kts").read_text()
        self.assertIn('versionName = "0.8.1-test"', build)
        self.assertIn('versionCode = 11', build)
        for path in (ROOT / "versions").glob("*/manifest.json"):
            for name, digest in json.loads(path.read_text())["files"].items():
                self.assertEqual(hashlib.sha256((path.parent / name).read_bytes()).hexdigest(), digest)

    def test_exactly_five_existing_customizable_slots_and_no_overlap(self):
        for choice in PROFILES:
            root = build_sketch(choice)
            slots = root.findall("Scene/ComplicationSlot")
            self.assertEqual(tuple(int(slot.attrib["slotId"]) for slot in slots), SLOTS)
            boxes = []
            for slot in slots:
                baseline = self.baseline.find(f"Scene/ComplicationSlot[@slotId='{slot.attrib['slotId']}']")
                self.assertEqual(slot.attrib, baseline.attrib)
                self.assertEqual(slot.attrib["isCustomizable"], "TRUE")
                self.assertEqual(structure(slot.find("DefaultProviderPolicy")),
                                 structure(baseline.find("DefaultProviderPolicy")))
                self.assertEqual([c.attrib["type"] for c in slot.findall("Complication")],
                                 [c.attrib["type"] for c in baseline.findall("Complication")])
                boxes.append(tuple(int(slot.find("BoundingBox").attrib[k]) for k in ("x", "y", "width", "height")))
            for index, (x, y, w, h) in enumerate(boxes):
                for xx, yy, ww, hh in boxes[index + 1:]:
                    self.assertFalse(x < xx + ww and xx < x + w and y < yy + hh and yy < y + h)

    def test_settings_and_auto_labels_preserved_except_short_date_default(self):
        for choice, profile in PROFILES.items():
            root = build_sketch(choice)
            expected = deepcopy(self.baseline.find("UserConfigurations"))
            if profile["short_date"]:
                expected.find("ListConfiguration[@id='dateStyle']").set("defaultValue", "short")
            self.assertEqual(structure(root.find("UserConfigurations")), structure(expected))
            self.assertNotIn("CONFIGURATION.label", xml_bytes(root).decode())
            self.assertNotIn("CAVOK", xml_bytes(root).decode())
            for slot_id in SLOTS:
                for complication in root.findall(f"Scene/ComplicationSlot[@slotId='{slot_id}']/Complication"):
                    condition = complication.find("Group/Condition")
                    old = self.baseline.find(f"Scene/ComplicationSlot[@slotId='{slot_id}']/Complication[@type='{complication.attrib['type']}']/Group/Condition")
                    self.assertEqual(structure(condition.find("Expressions")), structure(old.find("Expressions")))
                    self.assertEqual([c.attrib for c in condition.findall("Compare")],
                                     [c.attrib for c in old.findall("Compare")])

    def test_increased_fonts_and_centered_clocks(self):
        for choice, profile in PROFILES.items():
            root = build_sketch(choice)
            self.assertGreaterEqual(profile["label_size"], 36)
            self.assertGreaterEqual(profile["value_size"], 40)
            for family in FONTS:
                part = root.find(f"Scene/Group/Condition/Compare[@expression='clock_font_{family}']/PartText")
                self.assertEqual(int(part.attrib["x"]) + int(part.attrib["width"]) / 2, 225)
                self.assertEqual(int(part.find("Text/Font").attrib["size"]), profile["clock_size"])
            footer = root.find("Scene/ComplicationSlot[@slotId='4']/BoundingBox")
            self.assertEqual(int(footer.attrib["x"]) + int(footer.attrib["width"]) / 2, 225)
            for slot_id in SLOTS:
                self.assertEqual(root.find(f"Scene/ComplicationSlot[@slotId='{slot_id}']/Variant").attrib["value"], "0")

    def test_saved_xml_previews_and_unclipped_round_screen(self):
        stress = {2: ("HI/LO", "34° / 21°"), 3: ("DIST", "0.79 KM"),
                  4: ("ALRM", "06:45"), 6: ("GOAL", "8000"), 7: ("HR", "84 BPM")}
        for choice in PROFILES:
            root = build_sketch(choice)
            self.assertEqual((OUT / f"{choice}.xml").read_bytes(), xml_bytes(root))
            for clock in FONTS:
                with self.subTest(choice=choice, font=clock):
                    image = render_preview(watchface=root, clock_font=clock, complication_data=DEMO, source_values=DATE)
                    with Image.open(OUT / f"{choice}-{clock}.png") as saved:
                        self.assertEqual(saved.size, (450, 450))
                        self.assertEqual(image.tobytes(), saved.tobytes())
                    for fixture in (DEMO, stress):
                        full = render_preview(watchface=root, clock_font=clock, complication_data=fixture,
                                              source_values=DATE, clip_circle=False, background_mode="amoled")
                        outside = ImageChops.multiply(full.convert("L"), ImageChops.invert(self.mask))
                        # Ignore only near-black antialiasing, not clipped strokes.
                        self.assertIsNone(outside.point(lambda value: 255 if value > 8 else 0).getbbox())
            with Image.open(OUT / f"{choice}-ambient.png") as saved:
                ambient = render_preview(watchface=root, ambient=True, complication_data=DEMO, source_values=DATE)
                self.assertEqual(saved.tobytes(), ambient.tobytes())

    def test_snapshot_manifest_and_self_contained_preview(self):
        manifest = json.loads((OUT / "manifest.json").read_text())
        self.assertEqual(manifest["kind"], "design-sketches-not-apk")
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((OUT / name).read_bytes()).hexdigest(), digest)
        fragment = (OUT / "large-type-preview.html").read_text()
        self.assertLess(len(fragment.encode()), 1_000_000)
        self.assertNotIn("__PREVIEW_IMAGES__", fragment)
        parser = FragmentParser()
        parser.feed(fragment)
        variants = [attrs for tag, attrs in parser.elements if "data-variant" in attrs]
        self.assertEqual([a["data-variant"] for a in variants], [p["name"] for p in PROFILES.values()])
        self.assertEqual(["hidden" in a for a in variants], [False, True, True])
        images = [attrs for tag, attrs in parser.elements if tag == "img"]
        self.assertEqual([image["data-sketch"] for image in images], list(PROFILES))
        # Exercise initial render and the real font-change callback without a network/browser.
        script = re.search(r"<script>(.*?)</script>", fragment, re.S).group(1)
        harness = """
const vm = require('node:vm');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const images = ['familiar', 'stacked', 'maximum'].map(sketch => ({ dataset: { sketch } }));
let registered;
const root = { querySelectorAll: selector => {
  assert.equal(selector, 'img[data-sketch]'); return images;
}};
class Tweak {
  constructor(options) { this.options = options; }
  addSelect(state, key, options) { registered = { state, key, options, onChange: this.options.onChange }; }
}
const sandbox = { document: { getElementById: id => {
  assert.equal(id, 'terminal-large-type-sketches'); return root;
}}, Tweak };
vm.runInNewContext(fs.readFileSync(0, 'utf8'), sandbox);
assert.ok(registered);
const initial = images.map(image => image.src);
for (const image of images) assert.ok(image.src.startsWith('data:image/png;base64,'));
registered.state[registered.key] = 'mono'; registered.onChange();
for (let i = 0; i < images.length; i++) assert.notEqual(images[i].src, initial[i]);
registered.state[registered.key] = 'block'; registered.onChange();
assert.deepEqual(images.map(image => image.src), initial);
"""
        subprocess.run(["node", "-e", harness], input=script, text=True, check=True,
                       capture_output=True, timeout=15)
        fallback = harness[:harness.index("vm.runInNewContext(")] + "delete sandbox.Tweak; vm.runInNewContext(fs.readFileSync(0, 'utf8'), sandbox);"
        subprocess.run(["node", "-e", fallback], input=script, text=True, check=True,
                       capture_output=True, timeout=15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
