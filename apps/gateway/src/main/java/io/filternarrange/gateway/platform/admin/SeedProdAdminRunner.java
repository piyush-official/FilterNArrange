// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.admin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Plan H §T5 — bootstrap the first admin user on a freshly-deployed VM.
 *
 * <p>Run via:
 * <pre>
 *   docker exec fna-gateway java -jar /app/app.jar \
 *     --seed-prod-admin --email=you@example.com --password=$(openssl rand -base64 24)
 * </pre>
 *
 * Exits the application cleanly after seeding so the container can be a
 * one-shot. Idempotent: re-running with the same email updates the row
 * to admin=true instead of inserting a duplicate.
 */
@Component
public class SeedProdAdminRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(SeedProdAdminRunner.class);

    private final JdbcTemplate jdbc;
    private final PasswordEncoder encoder;
    private final ConfigurableApplicationContext ctx;

    public SeedProdAdminRunner(
        JdbcTemplate jdbc,
        PasswordEncoder encoder,
        ConfigurableApplicationContext ctx
    ) {
        this.jdbc = jdbc;
        this.encoder = encoder;
        this.ctx = ctx;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (!args.containsOption("seed-prod-admin")) {
            return;
        }
        String email = required(args, "email");
        String password = required(args, "password");

        UUID existing = jdbc.query(
            "SELECT id FROM users WHERE email = ? LIMIT 1",
            ps -> ps.setString(1, email),
            rs -> rs.next() ? UUID.fromString(rs.getString("id")) : null
        );

        String hash = encoder.encode(password);
        UUID userId = existing != null ? existing : UUID.randomUUID();

        if (existing == null) {
            jdbc.update(
                "INSERT INTO users (id, email, password_hash, created_at) "
                    + "VALUES (?, ?, ?, ?)",
                userId, email, hash, java.sql.Timestamp.from(Instant.now())
            );
            log.info("seed-prod-admin: created user {}", userId);
        } else {
            jdbc.update(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                hash, userId
            );
            log.info("seed-prod-admin: updated existing user {}", userId);
        }

        // The admin column lives behind a future migration (Plan H follow-up).
        // Try the update; swallow if the column doesn't exist yet.
        try {
            jdbc.update("UPDATE users SET admin = TRUE WHERE id = ?", userId);
            log.info("seed-prod-admin: promoted {} to admin", userId);
        } catch (Exception e) {
            log.warn(
                "seed-prod-admin: users.admin column not present; user created "
                    + "but admin flag must be set manually. Error: {}",
                e.toString()
            );
        }

        // Mirror to a 'paid' subscription so the seeded admin has no quota
        // friction during go-live.
        jdbc.update(
            "INSERT INTO subscriptions(id, user_id, tier, status, started_at) "
                + "SELECT ?, ?, 'paid', 'active', now() "
                + "WHERE NOT EXISTS ("
                + "  SELECT 1 FROM subscriptions WHERE user_id = ? AND status = 'active'"
                + ")",
            UUID.randomUUID(), userId, userId
        );

        log.info("seed-prod-admin: done. exiting.");
        // Exit so the one-shot container terminates instead of serving HTTP.
        ctx.close();
        Runtime.getRuntime().exit(0);
    }

    private static String required(ApplicationArguments args, String name) {
        List<String> vals = args.getOptionValues(name);
        if (vals == null || vals.isEmpty() || vals.get(0).isBlank()) {
            throw new IllegalArgumentException(
                "--seed-prod-admin requires --" + name + "=<value>"
            );
        }
        return vals.get(0);
    }
}
