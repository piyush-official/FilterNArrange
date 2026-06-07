// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.dataengine;

public interface DataEngineClient {
    EngineDtos.DetectResult detect(EngineDtos.RefRequest req);
    EngineDtos.FilterResult filter(EngineDtos.FilterRequest req);
    EngineDtos.ConvertResult convert(EngineDtos.ConvertRequest req);
}
