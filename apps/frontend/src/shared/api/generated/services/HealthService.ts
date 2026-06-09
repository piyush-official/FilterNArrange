/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * @deprecated
     * Liveness probe — kept as a deprecated stub during the Plan A → Plan B
     * transition. Use the gateway actuator (`/actuator/health`) and the
     * data-engine probe (`/healthz`) instead. Scheduled for removal in
     * Plan G.
     *
     * @returns any ok
     * @throws ApiError
     */
    public static health(): CancelablePromise<{
        status: string;
    }> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
}
