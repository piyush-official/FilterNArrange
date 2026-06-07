// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.persistence;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
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

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
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
}
