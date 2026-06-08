# syntax=docker/dockerfile:1.7

# ---- build stage ----
# Build context is the repo root so the shared ``contracts/`` tree is reachable
# from ``apps/gateway/build.gradle.kts``'s ``../../contracts`` source-set entry.
# See ``infra/docker-compose/docker-compose.yml`` and the matrix entry in
# ``.github/workflows/release.yml`` for the matching context wiring.
FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /workspace
COPY apps/gateway/gradlew apps/gateway/gradlew
COPY apps/gateway/gradle apps/gateway/gradle
COPY apps/gateway/settings.gradle.kts apps/gateway/build.gradle.kts apps/gateway/gradle.properties apps/gateway/
COPY apps/gateway/src apps/gateway/src
COPY contracts /contracts
RUN cd apps/gateway && chmod +x gradlew && ./gradlew --no-daemon bootJar \
    && cp build/libs/gateway-*[!-plain].jar /workspace/app.jar

# ---- runtime stage ----
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
RUN useradd --system --uid 1001 --create-home --home-dir /home/gateway gateway
COPY --from=build /workspace/app.jar /app/gateway.jar

# Plan G §T12 — OpenTelemetry Java agent for auto-instrumentation. Activated
# via JAVA_TOOL_OPTIONS so it attaches before main(). Defaults below point at
# the otel-collector service from the dev compose stack; the prod overlay
# overrides them via prod.env. Setting OTEL_TRACES_EXPORTER=otlp at runtime
# (or leaving it unset to default to otlp) opts in; set to "none" to disable.
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v2.8.0/opentelemetry-javaagent.jar /opt/otel/otel.jar
RUN chmod 0644 /opt/otel/otel.jar
ENV JAVA_TOOL_OPTIONS="-javaagent:/opt/otel/otel.jar" \
    OTEL_SERVICE_NAME=fna-gateway \
    OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_LOGS_EXPORTER=none \
    OTEL_METRICS_EXPORTER=none \
    OTEL_PROPAGATORS=tracecontext,baggage

USER gateway
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=10 \
    CMD curl -fsS http://localhost:8080/health || exit 1
ENTRYPOINT ["java", "-jar", "/app/gateway.jar"]
