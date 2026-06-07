// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.persistence;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
class MigrationTest {

    @Container
    static PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Container
    static MinIOContainer MINIO =
        new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
    }

    @Autowired JdbcTemplate jdbc;

    @Test
    void usersTableExists() {
        Integer count = jdbc.queryForObject(
            "select count(*) from information_schema.tables where table_name = 'users'",
            Integer.class);
        assertThat(count).isEqualTo(1);
    }

    @Test
    void sessionsTableExists() {
        Integer count = jdbc.queryForObject(
            "select count(*) from information_schema.tables where table_name = 'sessions'",
            Integer.class);
        assertThat(count).isEqualTo(1);
    }

    @Test
    void jobsTableExists() {
        Integer count = jdbc.queryForObject(
            "select count(*) from information_schema.tables where table_name = 'jobs'",
            Integer.class);
        assertThat(count).isEqualTo(1);
    }

    @Test
    void jobsIndexesExist() {
        java.util.List<String> idx = jdbc.queryForList(
            "select indexname from pg_indexes where tablename = 'jobs'",
            String.class);
        assertThat(idx).contains("jobs_user_recent", "jobs_status_open");
    }

    @Test
    void auditLogIsPartitioned() {
        Integer partitioned = jdbc.queryForObject(
            "select count(*) from pg_partitioned_table where partrelid = 'audit_log'::regclass",
            Integer.class);
        assertThat(partitioned).isEqualTo(1);

        Integer parts = jdbc.queryForObject(
            "select count(*) from pg_inherits where inhparent = 'audit_log'::regclass",
            Integer.class);
        assertThat(parts).isGreaterThanOrEqualTo(2);
    }

    @Test
    void subscriptionsTableExistsWithActiveUniquenessConstraint() {
        Integer count = jdbc.queryForObject(
            "select count(*) from information_schema.tables where table_name = 'subscriptions'",
            Integer.class);
        assertThat(count).isEqualTo(1);
        java.util.List<String> idx = jdbc.queryForList(
            "select indexname from pg_indexes where tablename = 'subscriptions'",
            String.class);
        assertThat(idx).contains("one_active_sub_per_user");
    }

    @Test
    void formatRequestsRecipesPluginRegistryTablesExist() {
        java.util.List<String> tables = jdbc.queryForList(
            "select table_name from information_schema.tables "
                + "where table_name in ('format_requests', 'recipes', 'plugin_registry')",
            String.class);
        assertThat(tables)
            .contains("format_requests", "recipes", "plugin_registry");
    }

    @Test
    void pluginRegistrySeededWithPaidEntries() {
        java.util.List<String> paidIds = jdbc.queryForList(
            "select plugin_id from plugin_registry where required_tier = 'paid' order by plugin_id",
            String.class);
        assertThat(paidIds).contains(
            "ai-anomaly-detect",
            "ai-auto-summary",
            "ai-chart-suggest",
            "ai-nl-to-filter",
            "format-request-submit",
            "job-batch-filter",
            "recipe-crud"
        );
    }
}
