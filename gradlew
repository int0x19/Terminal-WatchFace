#!/bin/sh

# Minimal Gradle Wrapper launcher. The wrapper JAR and distribution URL are
# managed by Gradle; this script deliberately adds no project-specific logic.
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec java -classpath "$project_dir/gradle/wrapper/gradle-wrapper.jar" \
    org.gradle.wrapper.GradleWrapperMain "$@"
