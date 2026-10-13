#!/bin/sh
set -eu
task_project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_project_dir"
mkdir -p .tools

# Official Google release built 2026-09-08. Verify before running downloaded JARs.
curl -fL --retry 2 https://github.com/google/watchface/releases/download/release/wff-validator.jar -o .tools/wff-validator.jar
curl -fL --retry 2 https://github.com/google/watchface/releases/download/release/memory-footprint.jar -o .tools/memory-footprint.jar
printf '%s\n' \
    '28b244289ab748bb2b07017e9f3c06bb76bdf165d6fa55652a5dc64b852c3121  .tools/wff-validator.jar' \
    '6a5aa266821562d264859d09be6b771a509c478370fbc0c2336d4ed4c0ca5890  .tools/memory-footprint.jar' \
    | sha256sum --check
