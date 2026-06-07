/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConvertRequest } from '../models/ConvertRequest';
import type { ConvertResponse } from '../models/ConvertResponse';
import type { DetectRequest } from '../models/DetectRequest';
import type { DetectResponse } from '../models/DetectResponse';
import type { FilterPreviewRequest } from '../models/FilterPreviewRequest';
import type { FilterPreviewResponse } from '../models/FilterPreviewResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PipelineService {
    /**
     * @returns DetectResponse detected
     * @throws ApiError
     */
    public static detect({
        requestBody,
    }: {
        requestBody: DetectRequest,
    }): CancelablePromise<DetectResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/detect',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `structured error`,
                404: `structured error`,
            },
        });
    }
    /**
     * @returns FilterPreviewResponse preview
     * @throws ApiError
     */
    public static filterPreview({
        requestBody,
    }: {
        requestBody: FilterPreviewRequest,
    }): CancelablePromise<FilterPreviewResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/filter/preview',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `structured error`,
            },
        });
    }
    /**
     * @returns ConvertResponse result-ready
     * @throws ApiError
     */
    public static convert({
        requestBody,
    }: {
        requestBody: ConvertRequest,
    }): CancelablePromise<ConvertResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/convert',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `structured error`,
            },
        });
    }
}
