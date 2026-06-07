// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.billing;

import io.filternarrange.gateway.platform.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.platform.tier.TierConfig;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Plan F §T24 — exposes the caller's current tier + today's quota usage so
 * the frontend can render the billing/usage panel.
 */
@RestController
@RequestMapping("/api/v1/billing")
public class BillingController {

    private final TierResolver tierResolver;
    private final TierConfig cfg;
    private final StringRedisTemplate redis;

    public BillingController(
        TierResolver tierResolver, TierConfig cfg, StringRedisTemplate redis
    ) {
        this.tierResolver = tierResolver;
        this.cfg = cfg;
        this.redis = redis;
    }

    @GetMapping("/me")
    public Map<String, Object> me() {
        UUID userId = CurrentUser.id();
        Tier tier = tierResolver.resolve(userId);
        String today = LocalDate.now(ZoneOffset.UTC).toString();
        String key = "gw:rate:user:" + userId + ":ops:" + today;
        String raw = redis.opsForValue().get(key);
        long used = raw == null ? 0L : Long.parseLong(raw);

        var body = new LinkedHashMap<String, Object>();
        body.put("tier", tier.wireValue());
        body.put("ops_today", used);
        body.put("ops_limit", cfg.dailyOps(tier));
        body.put("ops_unlimited", cfg.isUnlimitedOps(tier));
        body.put("max_upload_mb", cfg.maxUploadMb(tier));
        body.put("upload_unlimited", cfg.isUnlimitedUpload(tier));
        body.put("upgrade_hint", tier == Tier.FREE ? "/account/billing" : null);
        return body;
    }
}
