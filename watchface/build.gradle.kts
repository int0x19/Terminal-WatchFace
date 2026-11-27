import java.util.Properties

plugins {
    id("com.android.application")
}

val faceVersions = Properties().apply {
    project.file("variants.properties").inputStream().use { load(it) }
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
        versionCode = faceVersions.getProperty("versionCode").toInt()
    }

    flavorDimensions += "layout"
    productFlavors {
        for (face in listOf("compact", "large")) {
            create(face) {
                dimension = "layout"
                applicationId = faceVersions.getProperty("$face.applicationId")
                versionName = faceVersions.getProperty("$face.versionName")
            }
        }
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
