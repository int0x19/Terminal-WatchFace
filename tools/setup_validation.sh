#!/bin/sh
set -eu
task_project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_project_dir"
mkdir -p .tools

# Official Google release 2026-11-26, API asset digests verified 2026-11-27.
# Stage downloads so an upstream replacement cannot overwrite verified tools.
task_download_dir=$(mktemp -d .tools/validation-download.XXXXXX)
trap 'rm -f -- "$task_download_dir/wff-validator.jar" "$task_download_dir/memory-footprint.jar"; rmdir -- "$task_download_dir"' EXIT
curl -fL --retry 2 https://github.com/google/watchface/releases/download/release/wff-validator.jar -o "$task_download_dir/wff-validator.jar"
curl -fL --retry 2 https://github.com/google/watchface/releases/download/release/memory-footprint.jar -o "$task_download_dir/memory-footprint.jar"
printf '%s\n' \
    "0e2204137fca618264e82f9a053c6c9ec6d4fad08d2b56aa8a57d75c0508a804  $task_download_dir/wff-validator.jar" \
    "503c5f7bc9209ec4d4d4974f973cf66ad6fbb435e8422c310aac5b820f1f991a  $task_download_dir/memory-footprint.jar" \
    | sha256sum --check
cp -- "$task_download_dir/wff-validator.jar" .tools/wff-validator.jar
cp -- "$task_download_dir/memory-footprint.jar" .tools/memory-footprint.jar
