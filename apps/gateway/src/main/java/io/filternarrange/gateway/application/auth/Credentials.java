// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.auth;

public record Credentials(String email, String password, String displayName) {}
