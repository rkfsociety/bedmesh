import java.util.Properties

plugins {
    id("com.android.application") version "8.5.2"
    // Kotlin 1.9.x + Compose compiler extension is the most stable combo across Android Studio installs.
    id("org.jetbrains.kotlin.android") version "1.9.24"
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.24"
}

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties()
val releaseSigningEnabled = keystorePropertiesFile.exists()
if (releaseSigningEnabled) {
    keystorePropertiesFile.inputStream().use { keystoreProperties.load(it) }
}

android {
    namespace = "com.rkfsociety.bedmesh"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.rkfsociety.bedmesh"
        minSdk = 24
        targetSdk = 35
        versionCode = 165
        versionName = "0.165-android"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (releaseSigningEnabled) {
            create("release") {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storeFile = rootProject.file(keystoreProperties.getProperty("storeFile")!!)
                storePassword = keystoreProperties.getProperty("storePassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            // Если нет keystore.properties — подписываем debug-ключом (стабильный, не меняется между сборками)
            signingConfig = if (releaseSigningEnabled)
                signingConfigs.getByName("release")
            else
                signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }

    packaging {
        resources {
            excludes += setOf(
                "META-INF/AL2.0",
                "META-INF/LGPL2.1",
                "META-INF/versions/9/OSGI-INF/MANIFEST.MF",
            )
        }
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    // SSH/SFTP (явный BC: на Android встроенный провайдер "BC" без X25519 — см. BedMeshApp)
    implementation("com.hierynomus:sshj:0.40.0")
    implementation("org.bouncycastle:bcprov-jdk18on:1.78.1")
    implementation("org.bouncycastle:bcpkix-jdk18on:1.78.1")

    // HTTP (GitHub update check)
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.12.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

