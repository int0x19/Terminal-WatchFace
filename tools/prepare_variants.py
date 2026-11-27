#!/usr/bin/env python3
"""Generate minimal flavor overlays; never modify archived versions or shared fonts."""
import xml.etree.ElementTree as ET

from variant_config import ROOT, variants


def string_bytes(items):
    root = ET.Element("resources")
    for name, value in items.items():
        attributes = {"name": name}
        if name == "watch_face_name":
            attributes["translatable"] = "false"
        ET.SubElement(root, "string", attributes).text = value
    ET.indent(root, space="  ")
    return b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8") + b"\n"


def generated_files():
    files = {}
    for variant in variants():
        res = ROOT / f"watchface/src/{variant.name}/res"
        strings = {"watch_face_name": variant.display_name}
        if variant.name == "compact":
            strings.update({"field_2_name": "Left row 2 — data source", "field_3_name": "Left row 3 — data source",
                            "field_6_name": "Right row 2 — data source", "field_7_name": "Right row 3 — data source"})
            files[res / "raw/watchface.xml"] = (variant.base / "watchface.xml").read_bytes()
            files[res / "drawable/preview.png"] = (variant.base / "preview.png").read_bytes()
            files[res / "values-ru/variant.xml"] = string_bytes({
                "field_2_name": "Слева 2 — источник данных", "field_3_name": "Слева 3 — источник данных",
                "field_6_name": "Справа 2 — источник данных", "field_7_name": "Справа 3 — источник данных"})
        files[res / "values/variant.xml"] = string_bytes(strings)
    return files


if __name__ == "__main__":
    for path, data in generated_files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"Generated {path.relative_to(ROOT)}")
