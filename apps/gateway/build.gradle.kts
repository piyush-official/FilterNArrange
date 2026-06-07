plugins {
    java
    id("org.springframework.boot") version "3.3.4"
    id("io.spring.dependency-management") version "1.1.6"
    id("org.openapi.generator") version "7.7.0"
    id("org.flywaydb.flyway") version "10.17.0"
}

group = "io.filternarrange"
version = "0.1.0-SNAPSHOT"
java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }

repositories { mavenCentral() }

// Plan D §3 — Kafka schemas live at <repo>/contracts/kafka/*.schema.json. Adding
// <repo>/contracts as a resource srcDir copies them to the runtime classpath at
// /kafka/*.schema.json. The gateway is its own Gradle root (settings.gradle.kts
// here sets rootProject.name="gateway"), so rootProject.file(..) would resolve
// to apps/gateway/contracts — we hop up two levels with a relative path instead.
sourceSets {
    named("main") {
        resources.srcDir(layout.projectDirectory.dir("../../contracts"))
    }
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-websocket")
    implementation("org.springframework.kafka:spring-kafka:3.2.4")
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
    runtimeOnly("org.postgresql:postgresql")
    implementation("io.minio:minio:8.5.12")
    implementation("io.jsonwebtoken:jjwt-api:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.12.6")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.6.0")
    implementation("io.github.resilience4j:resilience4j-spring-boot3:2.2.0")
    // Plan G §T3 — Keycloak OIDC support. JwtDecoder bean is gated on
    // AUTH_PROVIDER=keycloak at runtime via AuthConfig.
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
    implementation("org.springframework.security:spring-security-oauth2-jose")
    // Plan G §T9 — Micrometer Prometheus registry exposes /actuator/prometheus.
    implementation("io.micrometer:micrometer-registry-prometheus")
    // Plan G §T11 — JSON layout for logback (loaded only when SPRING_PROFILES_ACTIVE=prod).
    runtimeOnly("ch.qos.logback.contrib:logback-json-classic:0.1.5")
    runtimeOnly("ch.qos.logback.contrib:logback-jackson:0.1.5")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("com.fasterxml.jackson.module:jackson-module-parameter-names")
    // networknt/json-schema-validator supports draft-2019-09 + 2020-12 natively;
    // everit-json-schema stops at draft-07 and silently fails on our schemas.
    implementation("com.networknt:json-schema-validator:1.5.2")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
    testImplementation("org.springframework.kafka:spring-kafka-test:3.2.4")
    testImplementation("org.testcontainers:junit-jupiter:1.20.1")
    testImplementation("org.testcontainers:postgresql:1.20.1")
    testImplementation("org.testcontainers:minio:1.20.1")
    testImplementation("com.tngtech.archunit:archunit-junit5:1.3.0")
    testImplementation("org.wiremock:wiremock-standalone:3.9.1")
    testImplementation("org.awaitility:awaitility:4.2.2")
}

tasks.test { useJUnitPlatform() }
