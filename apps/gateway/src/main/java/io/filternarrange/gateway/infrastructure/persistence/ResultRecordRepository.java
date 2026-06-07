// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface ResultRecordRepository extends JpaRepository<ResultRecordEntity, UUID> {}
