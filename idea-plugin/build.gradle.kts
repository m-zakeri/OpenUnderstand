plugins {
    kotlin("jvm") version "2.0.21"
    // 2.1 crashes parsing a 2025.x product-info.json (resolveIdeHomeVariable).
    id("org.jetbrains.intellij.platform") version "2.5.0"
}

group = "org.openunderstand"
version = "0.1.0"

kotlin { jvmToolchain(21) }

repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}

// Build against an IDE already on this machine when `ideaHome` points at one --
// downloading a platform is a 1.2 GB fetch that times out on a slow link.
val ideaHome = providers.gradleProperty("ideaHome").orNull

dependencies {
    intellijPlatform {
        if (ideaHome != null) local(ideaHome) else intellijIdeaCommunity("2024.2")
    }
}

// The analyser is Python. Ship the dumper as a plugin resource rather than
// keeping a second copy here -- one script, two consumers (this and the
// External Tool setup in the README).
tasks.processResources {
    from("../scripts/idea_metrics.py")
}

// Nothing here registers searchable settings, and the task starts a headless
// IDE that fails while the sandbox one holds its lock.
tasks.buildSearchableOptions { enabled = false }

// `gradle runIde -PrunProject=/some/java/project` opens it in the sandbox IDE
// instead of the empty welcome screen.
tasks.runIde {
    args = listOfNotNull(providers.gradleProperty("runProject").orNull)
}

intellijPlatform {
    pluginConfiguration {
        ideaVersion {
            sinceBuild = "242"  // 2024.2; raise only if you use a newer API
            untilBuild = provider { null }
        }
    }
}