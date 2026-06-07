// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.idempotency;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Optional;
import java.util.UUID;

/**
 * Idempotency-key → job_id lookup backed by Redis with a 24h TTL.
 * Key prefix follows the gateway Redis keyspace convention (spec §5).
 */
@Component
public class IdempotencyStore {

    private static final Duration TTL = Duration.ofHours(24);
    private static final String PREFIX = "gw:idem:";

    private final StringRedisTemplate redis;

    public IdempotencyStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    /**
     * Stores key → job_id if absent. Returns the existing value if the key
     * was already there; empty if this caller "won" the slot.
     */
    public Optional<UUID> putIfAbsent(String key, UUID jobId) {
        String redisKey = PREFIX + key;
        Boolean ok = redis.opsForValue().setIfAbsent(redisKey, jobId.toString(), TTL);
        if (Boolean.TRUE.equals(ok)) {
            return Optional.empty();
        }
        String existing = redis.opsForValue().get(redisKey);
        if (existing == null) {
            // TTL expired between SETNX and GET; treat as a free slot.
            return Optional.empty();
        }
        return Optional.of(UUID.fromString(existing));
    }
}
