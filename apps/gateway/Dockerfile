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
USER gateway
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=10 \
    CMD curl -fsS http://localhost:8080/health || exit 1
ENTRYPOINT ["java", "-jar", "/app/gateway.jar"]
