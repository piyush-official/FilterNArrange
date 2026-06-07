// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import org.springframework.security.core.context.SecurityContextHolder;
import java.util.UUID;

public final class CurrentUser {
    private CurrentUser() {}
    public static UUID id() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || auth.getPrincipal() == null) throw new IllegalStateException("no auth");
        return (UUID) auth.getPrincipal();
    }
}
