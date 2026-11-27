#!/usr/bin/env python3
"""Read-only publication preflight; report paths, never print possible secrets."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    rb"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}",
    rb"\bAKIA[0-9A-Z]{16}\b",
    rb"\bxox[baprs]-[0-9A-Za-z-]{20,}",
)
PRIVATE_PATH = re.compile(r"(^|/)(\.env(?:\..*)?|local\.properties|keystore\.properties|signing\.properties)$|\.(jks|keystore|p12|pfx|pem|key)$", re.I)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def check():
    findings = set()
    tracked = git("ls-files", "-z").decode().split("\0")
    for name in filter(None, tracked):
        if PRIVATE_PATH.search(name):
            findings.add(f"Private file tracked: {name}")
    current = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    for name in filter(None, current):
        path = ROOT / name
        if path.is_file() and any(re.search(p, path.read_bytes()) for p in SECRET_PATTERNS):
            findings.add(f"Potential secret in current file: {name}")
    blobs = 0
    for line in git("rev-list", "--objects", "--all").decode().splitlines():
        object_id, _, name = line.partition(" ")
        if git("cat-file", "-t", object_id).strip() != b"blob":
            continue
        blobs += 1
        if PRIVATE_PATH.search(name):
            findings.add(f"Private file in history: {name}")
        data = git("cat-file", "-p", object_id)
        if any(re.search(p, data) for p in SECRET_PATTERNS):
            findings.add(f"Potential secret in history: {name or object_id}")
    for name in ("LICENSE", "NOTICE", ".gitignore", ".github/workflows/build.yml",
                 "tools/assets/LICENSE-DejaVu.txt", "watchface/src/main/res/raw/dejavu_license.txt"):
        if not (ROOT / name).is_file():
            findings.add(f"Missing publication file: {name}")
    workflow = (ROOT / ".github/workflows/build.yml").read_text()
    for action in re.findall(r"uses:\s+([^\s#]+)", workflow):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}", action):
            findings.add(f"Action not pinned to a full commit: {action.split('@')[0]}")
    if "pull_request_target" in workflow or "contents: write" in workflow:
        findings.add("Unexpected privileged workflow trigger or write permission")
    if "distributionSha256Sum=" not in (ROOT / "gradle/wrapper/gradle-wrapper.properties").read_text():
        findings.add("Missing Gradle distribution checksum")
    # Test actual ignore behavior, not merely the presence of strings in .gitignore.
    for name in ("local.properties", ".env", "release.jks", "release.keystore", "signing.properties"):
        result = subprocess.run(["git", "check-ignore", "--no-index", "-q", name], cwd=ROOT)
        if result.returncode != 0:
            findings.add(f"Private path not ignored: {name}")
    if findings:
        for finding in sorted(findings):
            print(finding)
        raise SystemExit("Publication preflight failed. Review findings; do not publish secrets.")
    print(f"Publication preflight PASS: {blobs} historical blobs, current files, secret-path exclusions, licenses and CI pins.")
    print("Pattern scanning is not proof that no secrets or private content exist; review before publishing.")


if __name__ == "__main__":
    check()
