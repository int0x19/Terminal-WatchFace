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

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_archive(target, files, version, version_code, application_id):
    hashes = {name: sha256(source) for name, source in files.items()}
    if target.exists():
        manifest = json.loads((target / "manifest.json").read_text())
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
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Must match the version in watchface/build.gradle.kts")
    args = parser.parse_args()
    build = (ROOT / "watchface/build.gradle.kts").read_text()
    version = re.search(r'versionName\s*=\s*"([^"]+)"', build).group(1)
    code = int(re.search(r"versionCode\s*=\s*(\d+)", build).group(1))
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version):
        raise SystemExit("Invalid version directory name.")
    if args.version is not None and args.version != version:
        raise SystemExit("Requested version does not match the current sources.")
    metadata = json.loads((ROOT / "watchface/build/outputs/apk/debug/output-metadata.json").read_text())
    artifact = metadata["elements"][0]
    if artifact["versionName"] != version or artifact["versionCode"] != code:
        raise SystemExit("APK is stale; run sh tools/check.sh first.")
    apk = ROOT / "watchface/build/outputs/apk/debug" / artifact["outputFile"]
    aab = ROOT / "watchface/build/outputs/bundle/release/watchface-release.aab"
    wff = ROOT / "watchface/src/main/res/raw/watchface.xml"
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
             "preview.png": ROOT / "docs/design-preview.png",
             "ambient-preview.png": ROOT / "docs/ambient-preview.png"}
    for source in files.values():
        if not source.is_file():
            raise SystemExit(f"Missing artifact: {source}")
    versions = ROOT / "versions"
    if not versions.resolve().is_relative_to(ROOT):
        raise SystemExit("Refusing to archive outside the project.")
    created = save_archive(versions / version, files, version, code, metadata["applicationId"])
    print(f"{'Archived' if created else 'Already archived, unchanged'}: versions/{version}")
    print(f"Source tag: v{version}; commit and tag this version after verification.")


if __name__ == "__main__":
    main()
