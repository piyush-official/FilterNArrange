// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.platform.auth.JwtService;
import io.filternarrange.gateway.platform.plugin.PluginRegistryService;
import io.filternarrange.gateway.platform.tier.TierResolver;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(HealthController.class)
@WithMockUser
class HealthControllerTest {

    @MockBean JwtService jwtService;
    // Plan F tier-filter dependencies. @WebMvcTest only loads the controller
    // slice but Spring Security still constructs the filter chain, which
    // requires these beans.
    @MockBean StringRedisTemplate redis;
    @MockBean TierResolver tierResolver;
    @MockBean PluginRegistryService plugins;

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
            .andExpect(status().isOk())
            .andExpect(content().contentTypeCompatibleWith("application/json"))
            .andExpect(jsonPath("$.status").value("UP"));
    }
}
