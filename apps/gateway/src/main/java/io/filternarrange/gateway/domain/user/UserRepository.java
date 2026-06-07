// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.user;

import java.util.Optional;
import java.util.UUID;

public interface UserRepository {
    User save(User user);
    Optional<User> findByEmail(String email);
    Optional<User> findById(UUID id);
}
