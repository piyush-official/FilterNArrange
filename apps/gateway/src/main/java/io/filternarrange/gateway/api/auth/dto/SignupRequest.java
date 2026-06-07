// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record SignupRequest(
    @Email @NotBlank String email,
    @NotBlank @Size(min = 8) String password,
    String displayName) {}
