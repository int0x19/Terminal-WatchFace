# Wear OS watch face (API 34–37)

Resource-only starter project for a Wear OS watch face. It uses Watch Face
Format (WFF) 2, so the same package supports Wear OS devices from API 34 through
API 37. `compileSdk` and `targetSdk` are 37.

## Layout

- `watchface/src/main/res/raw/watchface.xml` — the actual WFF definition.
- `watchface/src/main/res/xml/watch_face_info.xml` — picker metadata.
- `watchface/src/main/res/drawable/preview.xml` — temporary picker preview; replace it with the final artwork before release.

The package intentionally contains no Kotlin/Java sources: WFF packages are
declarative and must have `android:hasCode="false"`.

## Build

```sh
./gradlew :watchface:assembleDebug
./gradlew :watchface:bundleRelease
```

The debug APK will be placed under
`watchface/build/outputs/apk/debug/`; the release AAB under
`watchface/build/outputs/bundle/release/`.

## Required local SDK components

The project needs Android SDK Platform 37 and Android SDK Build-Tools 37.x.
They are not installed yet on this machine. Android Studio Canary is recommended
because it provides WFF-aware XML completion, linting, and a watch-face run
configuration. A Wear OS emulator or physical watch is needed for deployment.

For API-34 compatibility this starter stays on WFF 2. WFF 3/4 features require
raising `minSdk` to 35/36 respectively, so they should be published as separate
artifacts rather than silently breaking older watches.
