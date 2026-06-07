// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.tier;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.UUID;

/**
 * Resolves the current effective tier for a user (Plan F §6).
 *
 * <p>Cache: Redis ``gw:tier:{user_id}`` with 60s TTL. The default is
 * {@link Tier#FREE} when no active subscription exists.
 */
@Service
public class TierResolver {

    private static final Duration CACHE_TTL = Duration.ofSeconds(60);
    private static final String KEY_PREFIX = "gw:tier:";

    private final StringRedisTemplate redis;
    private final SubscriptionRepository subs;

    public TierResolver(StringRedisTemplate redis, SubscriptionRepository subs) {
        this.redis = redis;
        this.subs = subs;
    }

    public Tier resolve(UUID userId) {
        String key = KEY_PREFIX + userId;
        String cached = redis.opsForValue().get(key);
        if (cached != null) {
            return Tier.fromString(cached);
        }
        Tier tier = subs.findActiveByUserId(userId)
            .filter(Subscription::isActiveNow)
            .map(Subscription::tier)
            .orElse(Tier.FREE);
        redis.opsForValue().set(key, tier.wireValue(), CACHE_TTL);
        return tier;
    }

    public void invalidate(UUID userId) {
        redis.delete(KEY_PREFIX + userId);
    }
}
