#!/usr/bin/env python3
"""Refine only the chosen inline layout; retain the original three sketches."""
import base64
from copy import deepcopy
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont

from build_large_type_sketches import DATE, DEMO, FONTS, OUT as PREVIOUS, PROFILES, ROOT, build_sketch, xml_bytes
from rebuild_assets import render_preview

OUT = ROOT / "docs/large-type-sketches/2026-11-06-r2"
PROFILE = {
    **PROFILES["familiar"],
    "name": "Ровные интервалы",
    "header_size": 34,
    "date_size": 38,
    "clock_size": 106,
    "clock_height": 100,
    "rows": (250, 300),
    "cell_height": 50,
    "x": (32, 230),
    "width": 188,
    "label_size": 38,
    "label_width": 78,
    "label_height": 50,
    "value_size": 42,
    "fallback_size": 36,
    "long_size": 34,
    "value_x": 80,
    "value_width": 108,
    "value_height": 50,
    "footer_y": 350,
    "footer_size": 42,
    "footer_height": 50,
}


def build_refined():
    return build_sketch("familiar", profile=PROFILE)


def ink_bands(root, clock="block", data=None, *, source_values=None):
    """Measure actual antialiased strokes, not line boxes, at 450×450."""
    bands = {}
    selected = {"clock": None, "row1": (2, 6), "row2": (3, 7), "footer": (4,)}
    for name, slot_ids in selected.items():
        layer = deepcopy(root)
        scene = layer.find("Scene")
        for child in list(scene):
            if slot_ids is None:
                if child.tag != "Group":
                    scene.remove(child)
                    continue
                for part in list(child):
                    # The active clock selection is the only retained header element.
                    first = part.find("Expressions/Expression") if part.tag == "Condition" else None
                    if first is None or not first.attrib["name"].startswith("clock_font_"):
                        child.remove(part)
            elif child.tag != "ComplicationSlot" or int(child.attrib["slotId"]) not in slot_ids:
                scene.remove(child)
        image = render_preview(watchface=layer, clock_font=clock, complication_data=data or DEMO,
                               source_values=source_values or DATE, background_mode="amoled", clip_circle=False)
        box = image.convert("L").point(lambda value: 255 if value > 8 else 0).getbbox()
        bands[name] = list(box) if box else None
    gaps = [bands[lower][1] - bands[upper][3]
            for upper, lower in (("clock", "row1"), ("row1", "row2"), ("row2", "footer"))]
    return {"bands": bands, "visibleVerticalGaps": gaps}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    root = build_refined()
    (OUT / "familiar-refined.xml").write_bytes(xml_bytes(root))
    images = {"refined": {}, "previous": {}}
    for clock in FONTS:
        preview = render_preview(watchface=root, clock_font=clock, complication_data=DEMO, source_values=DATE)
        preview.save(OUT / f"familiar-{clock}.png")
        for revision, path in (("refined", OUT / f"familiar-{clock}.png"),
                               ("previous", PREVIOUS / f"familiar-{clock}.png")):
            images[revision][clock] = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    render_preview(watchface=root, ambient=True, complication_data=DEMO, source_values=DATE).save(OUT / "ambient.png")
    comparison = Image.new("RGB", (900, 530), "#101510")
    font = ImageFont.truetype(str(ROOT / "watchface/src/main/res/font/terminal_mono.ttf"), 28)
    for index, (directory, title) in enumerate(((PREVIOUS, "Первый эскиз"), (OUT, "Доработанный"))):
        with Image.open(directory / "familiar-block.png") as image:
            comparison.paste(image, (index * 450, 45))
        ImageDraw.Draw(comparison).text((index * 450 + 225, 23), title, font=font, fill="#F2FFF1", anchor="mm")
    comparison.save(OUT / "comparison.png")
    fragment = (ROOT / "tools/assets/familiar-refinement-preview.html").read_text()
    assert fragment.count("__PREVIEW_IMAGES__") == 1
    (OUT / "familiar-refinement.html").write_text(
        fragment.replace("__PREVIEW_IMAGES__", json.dumps(images, separators=(",", ":"))))
    measurement = {clock: ink_bands(root, clock) for clock in FONTS}
    manifest = {"kind": "design-sketch-not-apk", "baseSketchTag": "sketches/large-type-2026-11-06",
                "selectedLayout": "familiar", "rejectedLayouts": ["stacked", "maximum"],
                "profile": PROFILE, "inkMeasurements": measurement,
                "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(OUT.iterdir()) if path.name != "manifest.json"}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(measurement, ensure_ascii=False))
    print(f"Saved refined first sketch separately: {OUT}")


if __name__ == "__main__":
    main()
