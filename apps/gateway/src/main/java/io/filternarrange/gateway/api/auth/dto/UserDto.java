// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.auth.dto;

import io.filternarrange.gateway.domain.user.User;
import java.util.UUID;

public record UserDto(UUID id, String email, String displayName) {
    public static UserDto of(User u) { return new UserDto(u.id(), u.email(), u.displayName()); }
}
