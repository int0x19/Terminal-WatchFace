#!/usr/bin/env python3
"""Verify co-installable flavors and inspect the actual APK/AAB metadata."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET
import zipfile

from prepare_variants import generated_files
from variant_config import LEGACY_ID, ROOT, variants


def build_tool(name):
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk is None:
        local = ROOT / "local.properties"
        for line in local.read_text().splitlines() if local.exists() else ():
            if line.startswith("sdk.dir="):
                sdk = line.split("=", 1)[1].replace("\\:", ":").replace("\\\\", "\\")
    if not sdk:
        raise ValueError("Set ANDROID_HOME or sdk.dir in ignored local.properties")
    return Path(sdk) / "build-tools/36.0.0" / name


def verify_packages():
    certificates = set()
    font_hashes = {hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (ROOT / "watchface/src/main/res/font").glob("*.ttf")}
    license_bytes = (ROOT / "watchface/src/main/res/raw/dejavu_license.txt").read_bytes()
    identities = set()
    for variant in variants():
        metadata = json.loads(variant.metadata.read_text())
        element = metadata["elements"][0]
        assert metadata["applicationId"] == variant.application_id
        assert element["versionName"] == variant.version
        assert element["versionCode"] == variant.version_code
        apk = variant.metadata.parent / element["outputFile"]
        for artifact in (apk, variant.aab):
            with zipfile.ZipFile(artifact) as package:
                names = package.namelist()
                assert not any(n.endswith(".dex") for n in names), artifact
                assert any(package.read(n) == variant.wff.read_bytes() for n in names if n.endswith(".xml")), artifact
                assert {hashlib.sha256(package.read(n)).hexdigest() for n in names if n.endswith(".ttf")} == font_hashes
                assert any(package.read(n) == license_bytes for n in names if n.endswith(".txt")), artifact
        badging = subprocess.check_output([str(build_tool("aapt2")), "dump", "badging", str(apk)], text=True)
        assert f"name='{variant.application_id}'" in badging
        assert f"versionName='{variant.version}'" in badging
        assert f"versionCode='{variant.version_code}'" in badging
        assert f"application-label:'{variant.display_name}'" in badging
        assert "minSdkVersion:'34'" in badging or "sdkVersion:'34'" in badging
        assert "targetSdkVersion:'37'" in badging
        signature = subprocess.check_output([str(build_tool("apksigner")), "verify", "--print-certs", str(apk)], text=True)
        certificates.add(re.search(r"certificate SHA-256 digest: ([0-9a-f]+)", signature).group(1))
        identities.add(variant.application_id)
        print(f"{variant.name}: {variant.application_id}, {variant.display_name}, {variant.version}, code {variant.version_code}; package PASS")
    assert len(identities) == 2 and LEGACY_ID not in identities
    assert len(certificates) == 1
    print("Different application IDs, valid signatures, exact WFFs, original fonts/licenses, no DEX: PASS")


class VariantTest(unittest.TestCase):
    def test_ids_are_unique_and_both_differ_from_legacy(self):
        configs = variants()
        self.assertEqual([v.name for v in configs], ["compact", "large"])
        self.assertEqual(len({v.application_id for v in configs}), 2)
        self.assertEqual(len({v.display_name for v in configs}), 2)
        for variant in configs:
            self.assertNotEqual(variant.application_id, LEGACY_ID)
            self.assertEqual(variant.application_id, LEGACY_ID + "." + variant.name)

    def test_generated_overlays_are_reproducible(self):
        for path, data in generated_files().items():
            self.assertEqual(path.read_bytes(), data, path)

    def test_each_layout_matches_its_base_without_manual_labels(self):
        for variant in variants():
            self.assertEqual(variant.wff.read_bytes(), (variant.base / "watchface.xml").read_bytes())
            root = ET.parse(variant.wff).getroot()
            expected = 7 if variant.name == "compact" else 5
            self.assertEqual(len(root.findall("Scene/ComplicationSlot")), expected)
            self.assertEqual(len(root.find("UserConfigurations")), 5)
            self.assertEqual(len(root.findall("UserConfigurations/ListConfiguration/ListOption")), 9)
            self.assertEqual(len(root.findall("UserConfigurations/ColorConfiguration/ColorOption")), 10)
            self.assertNotIn("CONFIGURATION.label", variant.wff.read_text())

    def test_names_and_field_labels_use_flavor_overlays(self):
        for variant in variants():
            resources = ROOT / f"watchface/src/{variant.name}/res"
            for locale in ("values", "values-ru"):
                labels = {n.attrib["name"]: n.text for n in ET.parse(ROOT / f"watchface/src/main/res/{locale}/strings.xml").getroot()}
                overlay = resources / locale / "variant.xml"
                if overlay.exists():
                    labels.update({n.attrib["name"]: n.text for n in ET.parse(overlay).getroot()})
                self.assertEqual(labels.get("watch_face_name", variant.display_name), variant.display_name)
                slots = ET.parse(variant.wff).getroot().findall("Scene/ComplicationSlot")
                visible = [labels[s.attrib["displayName"]] for s in slots]
                self.assertEqual(len(visible), len(set(visible)))
                self.assertTrue(all("источник данных" in text if locale == "values-ru" else "data source" in text for text in visible))

    def test_compact_preview_and_shared_fonts_are_preserved(self):
        compact = variants()[0]
        self.assertEqual((ROOT / "watchface/src/compact/res/drawable/preview.png").read_bytes(),
                         (compact.base / "preview.png").read_bytes())
        for variant in variants():
            with zipfile.ZipFile(variant.base / f"terminal-face-{variant.base_version}.apk") as old:
                saved = {hashlib.sha256(old.read(n)).hexdigest() for n in old.namelist() if n.endswith(".ttf")}
            current = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "watchface/src/main/res/font").glob("*.ttf")}
            self.assertEqual(saved, current)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", action="store_true", help="Also inspect both already-built APK/AAB pairs")
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(VariantTest))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.packages:
        verify_packages()
