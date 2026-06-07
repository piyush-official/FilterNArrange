// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.auth.dto;

public record AuthResponse(String token, UserDto user) {}
