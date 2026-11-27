#!/usr/bin/env python3
"""Archive a built version without overwriting an existing version directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from variant_config import variants

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_archive(target, files, version, version_code, application_id, *, flavor=None, base_version=None):
    hashes = {name: sha256(source) for name, source in files.items()}
    if target.exists():
        manifest = json.loads((target / "manifest.json").read_text())
        if (manifest["version"], manifest["versionCode"], manifest["applicationId"]) != (version, version_code, application_id):
            raise ValueError(f"{target} has different package metadata; do not overwrite it.")
        if manifest["files"] != hashes or any(sha256(target / name) != digest
                                               for name, digest in hashes.items()):
            raise ValueError(f"{target} is already archived; increment the version, do not overwrite it.")
        return False
    target.mkdir(parents=True, exist_ok=False)
    for name, source in files.items():
        shutil.copyfile(source, target / name)
    manifest = {"version": version, "versionCode": version_code,
                "applicationId": application_id, "sourceGitTag": f"v{version}",
                "createdUtc": datetime.now(timezone.utc).isoformat(),
                "apkSigning": "development key", "aabSigning": "unsigned",
                "files": hashes}
    if flavor is not None:
        manifest.update(flavor=flavor, baseVersion=base_version)
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return True


def archive_variant(variant):
    version, code = variant.version, variant.version_code
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version):
        raise SystemExit("Invalid version directory name.")
    metadata = json.loads(variant.metadata.read_text())
    artifact = metadata["elements"][0]
    if artifact["versionName"] != version or artifact["versionCode"] != code:
        raise SystemExit("APK is stale; run sh tools/check.sh first.")
    if metadata["applicationId"] != variant.application_id:
        raise SystemExit("APK has a different applicationId; rebuild first.")
    apk = variant.metadata.parent / artifact["outputFile"]
    aab, wff = variant.aab, variant.wff
    # AGP can rename resource paths. Compare raw XML contents, not resource filenames.
    for artifact_file in (apk, aab):
        with zipfile.ZipFile(artifact_file) as bundle:
            if any(name.endswith(".dex") for name in bundle.namelist()):
                raise SystemExit(f"Unexpected code in resource-only package: {artifact_file}")
            if not any(bundle.read(name) == wff.read_bytes() for name in bundle.namelist()
                       if name.endswith(".xml")):
                raise SystemExit(f"Package contains a different WFF; rebuild first: {artifact_file}")
    files = {f"terminal-face-{version}.apk": apk,
             f"terminal-face-{version}.aab": aab,
             "watchface.xml": wff,
             "preview.png": variant.previews / ("preview.png" if variant.name == "compact" else "design-preview.png"),
             "ambient-preview.png": variant.previews / "ambient-preview.png"}
    layout_config = ET.parse(wff).getroot().find("UserConfigurations/ListConfiguration[@id='layout']")
    if layout_config is not None:
        for option in layout_config:
            layout = option.attrib["id"]
            for suffix in ("", "-ambient"):
                name = f"layout-{layout}{suffix}.png"
                files[name] = variant.previews / name
        files["layout-comparison.png"] = variant.previews / "layout-comparison.png"
    font_config = ET.parse(wff).getroot().find("UserConfigurations/ListConfiguration[@id='clockFont']")
    if font_config is not None:
        for option in font_config:
            for suffix in ("", "-ambient"):
                name = f"font-{option.attrib['id']}{suffix}.png"
                files[name] = variant.previews / name
        files["font-comparison.png"] = variant.previews / "font-comparison.png"
    palette_config = ET.parse(wff).getroot().find("UserConfigurations/ColorConfiguration[@id='palette']")
    background_config = ET.parse(wff).getroot().find("UserConfigurations/ListConfiguration[@id='backgroundMode']")
    if palette_config is not None and len(palette_config) > 3:
        for option in palette_config:
            suffixes = ("", "-ambient", "-amoled") if background_config is not None else ("", "-ambient")
            for suffix in suffixes:
                name = f"palette-{option.attrib['id']}{suffix}.png"
                files[name] = variant.previews / name
        files["palette-comparison.png"] = variant.previews / "palette-comparison.png"
        if background_config is not None:
            files["palette-amoled-comparison.png"] = variant.previews / "palette-amoled-comparison.png"
    for source in files.values():
        if not source.is_file():
            raise SystemExit(f"Missing artifact: {source}")
    versions = ROOT / "versions"
    if not versions.resolve().is_relative_to(ROOT):
        raise SystemExit("Refusing to archive outside the project.")
    created = save_archive(versions / version, files, version, code, metadata["applicationId"],
                           flavor=variant.name, base_version=variant.base_version)
    print(f"{'Archived' if created else 'Already archived, unchanged'}: versions/{version}")
    print(f"Source tag: v{version}; commit and tag this version after verification.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flavor", choices=("all", "compact", "large"), default="all")
    parser.add_argument("--version", help="Optional check; only with a single --flavor")
    args = parser.parse_args()
    selected = [v for v in variants() if args.flavor == "all" or v.name == args.flavor]
    if args.version is not None and (len(selected) != 1 or selected[0].version != args.version):
        raise SystemExit("--version must match one explicitly selected --flavor.")
    for variant in selected:
        archive_variant(variant)


if __name__ == "__main__":
    main()
