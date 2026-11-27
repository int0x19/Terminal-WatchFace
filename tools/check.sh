#!/bin/sh
set -eu
task_project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_project_dir"
python3 tools/test_layout.py
python3 tools/test_archive.py
python3 tools/test_variants.py

if ! test -f .tools/wff-validator.jar || ! test -f .tools/memory-footprint.jar; then
    printf '%s\n' 'Run sh tools/setup_validation.sh first.' >&2
    exit 1
fi
printf '%s\n' \
    '0e2204137fca618264e82f9a053c6c9ec6d4fad08d2b56aa8a57d75c0508a804  .tools/wff-validator.jar' \
    '503c5f7bc9209ec4d4d4974f973cf66ad6fbb435e8422c310aac5b820f1f991a  .tools/memory-footprint.jar' \
    | sha256sum --check
# This validator can return zero after a schema failure; require its PASS marker.
for task_wff in watchface/src/main/res/raw/watchface.xml watchface/src/compact/res/raw/watchface.xml; do
    task_validation_output=$(java -jar .tools/wff-validator.jar 2 "$task_wff" 2>&1)
    printf '%s\n' "$task_validation_output"
    if ! printf '%s\n' "$task_validation_output" | grep -Fq 'PASSED :'; then
        exit 1
    fi
done
./gradlew --no-daemon \
    :watchface:assembleCompactDebug :watchface:assembleLargeDebug \
    :watchface:bundleCompactRelease :watchface:bundleLargeRelease \
    :watchface:lintCompactDebug :watchface:lintLargeDebug
python3 tools/test_variants.py --packages
for task_face in compact large; do
    if ! task_memory_output=$(java -jar .tools/memory-footprint.jar \
        --watch-face "watchface/build/outputs/bundle/${task_face}Release/watchface-${task_face}-release.aab" \
        --schema-version 2 --greedy-after-iterations 1000 2>&1); then
        printf '%s\n' "$task_memory_output" >&2
        exit 1
    fi
    printf '%s\n' "$task_memory_output" >&2
    printf '%s\n' "$task_memory_output" | grep -Fq 'has passed the memory footprint test'
done
