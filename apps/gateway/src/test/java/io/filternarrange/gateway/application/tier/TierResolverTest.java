// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.tier;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class TierResolverTest {

    @SuppressWarnings("unchecked")
    private static ValueOperations<String, String> mockOps() {
        return (ValueOperations<String, String>) mock(ValueOperations.class);
    }

    @Test
    void cacheHitSkipsDb() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mockOps();
        when(redis.opsForValue()).thenReturn(ops);
        UUID userId = UUID.randomUUID();
        when(ops.get("gw:tier:" + userId)).thenReturn("paid");
        SubscriptionRepository repo = mock(SubscriptionRepository.class);

        TierResolver r = new TierResolver(redis, repo);
        assertThat(r.resolve(userId)).isEqualTo(Tier.PAID);
        verifyNoInteractions(repo);
    }

    @Test
    void cacheMissReadsDbAndPopulates() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mockOps();
        when(redis.opsForValue()).thenReturn(ops);
        UUID userId = UUID.randomUUID();
        when(ops.get("gw:tier:" + userId)).thenReturn(null);
        SubscriptionRepository repo = mock(SubscriptionRepository.class);
        when(repo.findActiveByUserId(userId)).thenReturn(Optional.of(
            new Subscription(UUID.randomUUID(), userId, Tier.PAID,
                Subscription.Status.ACTIVE, Instant.now(), null, null)));

        TierResolver r = new TierResolver(redis, repo);
        assertThat(r.resolve(userId)).isEqualTo(Tier.PAID);
        verify(ops).set(eq("gw:tier:" + userId), eq("paid"), any(Duration.class));
    }

    @Test
    void noSubscriptionDefaultsToFree() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mockOps();
        when(redis.opsForValue()).thenReturn(ops);
        UUID userId = UUID.randomUUID();
        when(ops.get(anyString())).thenReturn(null);
        SubscriptionRepository repo = mock(SubscriptionRepository.class);
        when(repo.findActiveByUserId(userId)).thenReturn(Optional.empty());

        TierResolver r = new TierResolver(redis, repo);
        assertThat(r.resolve(userId)).isEqualTo(Tier.FREE);
    }

    @Test
    void invalidateClearsCacheEntry() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        UUID userId = UUID.randomUUID();
        TierResolver r = new TierResolver(redis, mock(SubscriptionRepository.class));
        r.invalidate(userId);
        verify(redis).delete("gw:tier:" + userId);
    }
}
