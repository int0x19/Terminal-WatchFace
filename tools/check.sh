#!/bin/sh
set -eu
task_project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_project_dir"
python3 tools/test_layout.py
python3 tools/test_archive.py

if ! test -f .tools/wff-validator.jar || ! test -f .tools/memory-footprint.jar; then
    printf '%s\n' 'Run sh tools/setup_validation.sh first.' >&2
    exit 1
fi
printf '%s\n' \
    '28b244289ab748bb2b07017e9f3c06bb76bdf165d6fa55652a5dc64b852c3121  .tools/wff-validator.jar' \
    '6a5aa266821562d264859d09be6b771a509c478370fbc0c2336d4ed4c0ca5890  .tools/memory-footprint.jar' \
    | sha256sum --check
# This validator can return zero after a schema failure; require its PASS marker.
task_validation_output=$(java -jar .tools/wff-validator.jar 2 watchface/src/main/res/raw/watchface.xml 2>&1)
printf '%s\n' "$task_validation_output"
if ! printf '%s\n' "$task_validation_output" | rg -q 'PASSED :'; then
    exit 1
fi
./gradlew --no-daemon :watchface:assembleDebug :watchface:bundleRelease :watchface:lintDebug
if unzip -Z1 watchface/build/outputs/apk/debug/watchface-debug.apk | rg '\.dex$'; then
    printf '%s\n' 'WFF packages must not contain DEX files.' >&2
    exit 1
fi
if ! task_memory_output=$(java -jar .tools/memory-footprint.jar \
    --watch-face watchface/build/outputs/bundle/release/watchface-release.aab \
    --schema-version 2 --greedy-after-iterations 1000 2>&1); then
    printf '%s\n' "$task_memory_output" >&2
    exit 1
fi
printf '%s\n' "$task_memory_output"
printf '%s\n' "$task_memory_output" | rg -q 'has passed the memory footprint test'
