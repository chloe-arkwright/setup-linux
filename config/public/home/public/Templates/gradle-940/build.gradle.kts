import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    idea
    `java-library`
    kotlin("jvm") version "2.3.10"
}

val projectVersion: String by project
val projectMavenGroup: String by project
val projectId: String by project

version = projectVersion
group = projectMavenGroup

tasks.wrapper {
    gradleVersion = "9.4.0"
    distributionSha256Sum = "b21468753cb43c167738ee04f10c706c46459cf8f8ae6ea132dc9ce589a261f2"
    distributionType = Wrapper.DistributionType.ALL
}

base.archivesName = projectId

kotlin {
    compilerOptions.jvmTarget = JvmTarget.JVM_25
}

java {
    withSourcesJar()

    sourceCompatibility = JavaVersion.VERSION_25
    targetCompatibility = JavaVersion.VERSION_25
}

tasks {
    withType<JavaCompile> {
        options.release = 25
    }

    jar {
        inputs.property("archivesName", project.base.archivesName)
    }
}

idea {
    module {
        isDownloadSources = true
        isDownloadJavadoc = true
    }
}
