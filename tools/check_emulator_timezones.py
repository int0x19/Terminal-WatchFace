#!/usr/bin/env python3
"""Capture a running Terminal Face in several zones; always restore the zone.

Only an Android emulator is accepted. No app data, providers or labels are reset.
Install/activate the current APK before running this optional integration check.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sdk = Path(os.environ.get("ANDROID_HOME", Path.home() / "android-sdk"))
    parser.add_argument("--adb", default=str(sdk / "platform-tools/adb"))
    parser.add_argument("--serial", default="emulator-5556")
    args = parser.parse_args()

    def adb(*command):
        return subprocess.check_output([args.adb, "-s", args.serial, *command], text=True).strip()

    if not args.serial.startswith("emulator-") or adb("shell", "getprop", "ro.kernel.qemu") != "1":
        raise SystemExit("Refusing to change time zone on a non-emulator device.")
    if "dev.int0x19.watchface.terminal" not in adb("shell", "pm", "list", "packages",
                                                  "dev.int0x19.watchface.terminal"):
        raise SystemExit("Install and activate Terminal Face first.")
    original_zone = adb("shell", "getprop", "persist.sys.timezone")
    if not original_zone:
        raise SystemExit("Could not determine the original time zone; refusing to change it.")
    results = []

    def capture(name):
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        time.sleep(2)
        device_file = "/sdcard/terminal-face-timezone.png"
        adb("shell", "screencap", "-p", device_file)
        adb("pull", device_file, str(ROOT / f"docs/api34-v2-{name}.png"))
        result = {"timezone": adb("shell", "getprop", "persist.sys.timezone"),
                  "local": adb("shell", "date", "+%H:%M%z"),
                  "utc": adb("shell", "date", "-u", "+%H:%M"),
                  "screenshot": f"api34-v2-{name}.png"}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    try:
        capture("active")
        for zone, name in [("Europe/London", "london"), ("Asia/Kathmandu", "kathmandu"),
                           ("America/St_Johns", "st-johns")]:
            adb("shell", "cmd", "alarm", "set-timezone", zone)
            if adb("shell", "getprop", "persist.sys.timezone") != zone:
                raise RuntimeError(f"Time zone was not changed to {zone}")
            capture(name)
    finally:
        adb("shell", "cmd", "alarm", "set-timezone", original_zone)
        restored = adb("shell", "getprop", "persist.sys.timezone")
        if restored != original_zone:
            raise RuntimeError(f"Failed to restore original time zone {original_zone}")
        print(f"Restored time zone: {restored}", flush=True)
    capture("active")
    # Generated diagnostic artifact, not input to the watch face.
    (ROOT / "docs/emulator-timezones.json").write_text(
        json.dumps({"serial": args.serial, "sdk": adb("shell", "getprop", "ro.build.version.sdk"),
                    "restored_zone": original_zone, "captures": results}, indent=2) + "\n")


if __name__ == "__main__":
    main()
