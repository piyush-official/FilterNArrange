// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.github;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * Plan F §T21 — thin GitHub REST adapter. Used by {@link
 * io.filternarrange.gateway.infrastructure.messaging.FormatRequestConsumer}
 * to mirror new format-requests into a tracker repo. The adapter is a no-op
 * when ``filternarrange.github.token`` is blank — keeps local dev quiet.
 */
@Component
public class GithubIssueClient {

    private static final Logger log = LoggerFactory.getLogger(GithubIssueClient.class);

    private final RestClient rest;
    private final String repo;
    private final boolean enabled;

    public GithubIssueClient(
        @Value("${filternarrange.github.api-base:https://api.github.com}") String apiBase,
        @Value("${filternarrange.github.repo:}") String repo,
        @Value("${filternarrange.github.token:}") String token
    ) {
        this.repo = repo;
        this.enabled = !token.isBlank() && !repo.isBlank();
        var builder = RestClient.builder().baseUrl(apiBase);
        if (this.enabled) {
            builder = builder.defaultHeader("Authorization", "Bearer " + token);
        }
        this.rest = builder
            .defaultHeader("Accept", "application/vnd.github+json")
            .defaultHeader("X-GitHub-Api-Version", "2022-11-28")
            .build();
    }

    public boolean isEnabled() {
        return enabled;
    }

    /** Returns the new issue's ``number`` (GitHub issue id within the repo). */
    public Integer createIssue(String title, String body, List<String> labels) {
        if (!enabled) {
            log.info("github mirror disabled — would have opened issue: {}", title);
            return null;
        }
        try {
            var resp = rest.post()
                .uri("/repos/{repo}/issues", repo)
                .body(Map.of("title", title, "body", body, "labels", labels))
                .retrieve()
                .onStatus(HttpStatusCode::isError, (req, res) -> {
                    throw new RuntimeException(
                        "github create-issue failed: " + res.getStatusCode()
                    );
                })
                .toEntity(JsonNode.class);
            JsonNode b = resp.getBody();
            return b == null ? null : b.path("number").asInt();
        } catch (Exception e) {
            log.warn("github create-issue raised: {}", e.toString());
            return null;
        }
    }

    public void closeIssue(int number, String comment) {
        if (!enabled) return;
        try {
            rest.post()
                .uri("/repos/{repo}/issues/{n}/comments", repo, number)
                .body(Map.of("body", comment))
                .retrieve()
                .toBodilessEntity();
            rest.patch()
                .uri("/repos/{repo}/issues/{n}", repo, number)
                .body(Map.of("state", "closed"))
                .retrieve()
                .toBodilessEntity();
        } catch (Exception e) {
            log.warn("github close-issue {} raised: {}", number, e.toString());
        }
    }
}
