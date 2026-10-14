plugins {
    id("com.android.application")
}

android {
    enableKotlin = false
    namespace = "dev.int0x19.watchface.terminal"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "dev.int0x19.watchface.terminal"
        minSdk = 34
        targetSdk = 37
        versionCode = 10
        versionName = "0.8.0-test"
    }

    // WFF bundles must contain resources only, including development builds.
    buildTypes {
        getByName("debug") {
            isDebuggable = false
            isMinifyEnabled = true
            isShrinkResources = false
        }
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = false
        }
    }
}
