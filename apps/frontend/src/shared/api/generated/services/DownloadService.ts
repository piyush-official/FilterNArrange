/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DownloadService {
    /**
     * @returns void
     * @throws ApiError
     */
    public static download({
        resultId,
    }: {
        resultId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/download/{resultId}',
            path: {
                'resultId': resultId,
            },
            errors: {
                302: `redirect to pre-signed MinIO URL`,
                404: `structured error`,
            },
        });
    }
}
