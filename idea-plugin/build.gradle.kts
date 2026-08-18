plugins {
    kotlin("jvm") version "2.0.21"
    // 2.1 crashes parsing a 2025.x product-info.json (resolveIdeHomeVariable).
    id("org.jetbrains.intellij.platform") version "2.5.0"
}

group = "org.openunderstand"
version = "0.2.0"  // Marketplace rejects a re-upload under the version it verified

kotlin { jvmToolchain(21) }

repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}

// Build against an IDE already on this machine when `ideaHome` points at one --
// downloading a platform is a 1.2 GB fetch that times out on a slow link.
//
// Blank counts as unset, which is what lets CI say `-PideaHome=` to override the
// developer path committed in gradle.properties. That path does not exist on a
// runner, and `local()` on it fails the build before anything else runs.
val ideaHome = providers.gradleProperty("ideaHome").orNull?.takeIf { it.isNotBlank() }

dependencies {
    intellijPlatform {
        if (ideaHome != null) local(ideaHome) else intellijIdeaCommunity("2025.1")
    }
}

// The analyser is Python. Ship the dumper as a plugin resource rather than
// keeping a second copy here -- one script, two consumers (this and the
// External Tool setup in the README).
tasks.processResources {
    from("../scripts/idea_metrics.py")
    // Bundle the analyser itself when a wheel has been built, so the plugin
    // installs the source tree it was built from rather than whatever version
    // PyPI happens to serve. Optional on purpose: without it the bootstrap
    // falls back to `pip install openunderstand`, and building the plugin does
    // not require a Python toolchain.
    //
    //     OPENUNDERSTAND_BUILD_ACCELERATOR=0 python -m build --wheel
    //
    // Only the py3-none-any wheel. `dist/` may also hold the ~20 compiled
    // wheels a release builds, and those are specific to one platform and one
    // Python minor -- bundling one would ship a jar that works on the machine
    // that built it. It would also make this rename collide, since every match
    // becomes the same filename. The plugin upgrades to a compiled wheel from
    // PyPI at first run instead.
    from("../dist") { include("*-py3-none-any.whl"); rename { "openunderstand.whl" } }
}

// Nothing here registers searchable settings, and the task starts a headless
// IDE that fails while the sandbox one holds its lock.
tasks.buildSearchableOptions { enabled = false }
// ... and the task that packs its output, which otherwise fails on a clean
// build looking for a directory the disabled task never created.
tasks.named("prepareJarSearchableOptions") { enabled = false }

// `gradle runIde -PrunProject=/some/java/project` opens it in the sandbox IDE
// instead of the empty welcome screen.
tasks.runIde {
    args = listOfNotNull(providers.gradleProperty("runProject").orNull)
}

intellijPlatform {
    pluginConfiguration {
        ideaVersion {
            // Must not be lower than the platform this is compiled against --
            // the Marketplace verifier runs the plugin against every IDE in the
            // range, and bytecode compiled on 251 references signatures 242 does
            // not have (FileSaverDescriptor's 3-String constructor is a vararg
            // there). `verifyPluginConfiguration` reports the mismatch.
            sinceBuild = "251"  // 2025.1; to support older IDEs, build against them
            untilBuild = provider { null }
        }
    }

    // `gradle verifyPlugin` is what the Marketplace runs on upload. Point it at
    // the local IDE so it costs no download; off the machine, one IDE at the
    // floor of the supported range -- `recommended()` fetches several gigabytes,
    // and the Marketplace verifies the whole range itself on upload anyway.
    pluginVerification {
        ides { if (ideaHome != null) local(ideaHome) else ide("IC", "2025.1") }
    }

    // `gradle publishPlugin` uploads to the Marketplace. The token is a
    // permanent one from plugins.jetbrains.com -> your profile -> My Tokens; it
    // is read from the environment so it never lands in the repository. The
    // plugin must already exist there: the first version of a plugin has to be
    // uploaded through the web form, later ones can go through the API.
    publishing {
        token = providers.environmentVariable("PUBLISH_TOKEN")
    }
}