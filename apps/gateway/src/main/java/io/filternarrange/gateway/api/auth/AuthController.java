// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.auth;

import io.filternarrange.gateway.api.auth.dto.*;
import io.filternarrange.gateway.application.auth.AuthService;
import io.filternarrange.gateway.application.auth.Credentials;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService auth;
    public AuthController(AuthService auth) { this.auth = auth; }

    @PostMapping("/signup")
    public AuthResponse signup(@Valid @RequestBody SignupRequest r) {
        var a = auth.signup(new Credentials(r.email(), r.password(), r.displayName()));
        return new AuthResponse(a.token(), UserDto.of(a.user()));
    }

    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest r) {
        var a = auth.login(new Credentials(r.email(), r.password(), null));
        return new AuthResponse(a.token(), UserDto.of(a.user()));
    }

    @GetMapping("/me")
    public UserDto me() {
        return UserDto.of(auth.requireUser(CurrentUser.id()));
    }
}
