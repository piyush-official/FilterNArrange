// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.plugin;

import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Optional;

/**
 * Plan F §6 — required-tier lookup for the gating filter. Backed by the
 * ``plugin_registry`` table seeded in V9; Redis-cached for 5 minutes.
 *
 * Cache sentinel: ``__none__`` stores "this plugin id is not in the registry"
 * so we don't re-hit the DB for unknown ids on the hot path.
 */
@Service
public class PluginRegistryService {

    private static final Duration CACHE_TTL = Duration.ofMinutes(5);
    private static final String NONE = "__none__";

    private final JdbcTemplate jdbc;
    private final StringRedisTemplate redis;

    public PluginRegistryService(JdbcTemplate jdbc, StringRedisTemplate redis) {
        this.jdbc = jdbc;
        this.redis = redis;
    }

    public Optional<Tier> requiredTier(String pluginId) {
        String key = "gw:plugin-tier:" + pluginId;
        String cached = redis.opsForValue().get(key);
        if (NONE.equals(cached)) {
            return Optional.empty();
        }
        if (cached != null) {
            return Optional.of(Tier.fromString(cached));
        }
        Optional<String> dbVal = jdbc.query(
            "SELECT required_tier FROM plugin_registry "
                + "WHERE plugin_id = ? AND status = 'enabled' "
                + "ORDER BY version DESC LIMIT 1",
            rs -> rs.next() ? Optional.ofNullable(rs.getString(1)) : Optional.<String>empty(),
            pluginId
        );
        if (dbVal == null || dbVal.isEmpty()) {
            redis.opsForValue().set(key, NONE, CACHE_TTL);
            return Optional.empty();
        }
        Tier t = Tier.fromString(dbVal.get());
        redis.opsForValue().set(key, t.wireValue(), CACHE_TTL);
        return Optional.of(t);
    }

    public void invalidateAll() {
        var keys = redis.keys("gw:plugin-tier:*");
        if (keys != null) {
            keys.forEach(redis::delete);
        }
    }
}
