plugins {
    kotlin("jvm") version "2.0.21"
    id("org.jetbrains.intellij.platform") version "2.1.0"
}

group = "org.openunderstand"
version = "0.1.0"

kotlin { jvmToolchain(17) }

repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}

dependencies {
    intellijPlatform {
        intellijIdeaCommunity("2024.2")
        instrumentationTools()
    }
}

// The analyser is Python. Ship the dumper as a plugin resource rather than
// keeping a second copy here -- one script, two consumers (this and the
// External Tool setup in the README).
tasks.processResources {
    from("../scripts/idea_metrics.py")
}

intellijPlatform {
    pluginConfiguration {
        ideaVersion {
            sinceBuild = "242"
            untilBuild = provider { null }
        }
    }
}