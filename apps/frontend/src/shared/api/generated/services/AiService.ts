/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AiService {
    /**
     * Translate a natural-language query to a FilterSpec
     * @returns any OK
     * @throws ApiError
     */
    public static aiNlToFilter({
        requestBody,
    }: {
        requestBody: {
            ref: string;
            query: string;
            schema?: Array<Record<string, any>>;
        },
    }): CancelablePromise<{
        filter_spec: Record<string, any>;
        confidence: number;
    }> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/ai/nl-to-filter',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                404: `structured error`,
                502: `structured error`,
                504: `structured error`,
            },
        });
    }
    /**
     * Generate a plain-English auto-summary of a dataset
     * @returns any OK
     * @throws ApiError
     */
    public static aiSummary({
        requestBody,
    }: {
        requestBody: {
            ref: string;
            schema: Array<Record<string, any>>;
            sample_rows: Array<Record<string, any>>;
            total_rows: number;
            total_size_bytes: number;
        },
    }): CancelablePromise<{
        summary: string;
        key_observations: Array<string>;
    }> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/ai/summary',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                404: `structured error`,
                502: `structured error`,
                504: `structured error`,
            },
        });
    }
    /**
     * Suggest a chart for the dataset
     * @returns any OK
     * @throws ApiError
     */
    public static aiChartSuggest({
        requestBody,
    }: {
        requestBody: {
            ref: string;
            schema: Array<Record<string, any>>;
            cardinality_per_column: Record<string, number>;
        },
    }): CancelablePromise<{
        recommended_chart: {
            kind: 'line' | 'bar' | 'pie' | 'histogram' | 'scatter' | 'heatmap';
            'x'?: string | null;
            'y'?: string | null;
            color?: string | null;
            justification: string;
        };
    }> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/ai/chart-suggest',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                404: `structured error`,
                502: `structured error`,
                504: `structured error`,
            },
        });
    }
    /**
     * Detect anomalies and data-quality issues
     * @returns any OK
     * @throws ApiError
     */
    public static aiAnomaly({
        requestBody,
    }: {
        requestBody: {
            ref: string;
            schema: Array<Record<string, any>>;
            sample_rows: Array<Record<string, any>>;
            summary_stats: Record<string, any>;
        },
    }): CancelablePromise<{
        findings: Array<{
            kind: 'outlier' | 'missing_values' | 'format_inconsistency' | 'possible_duplicate' | 'type_drift';
            column?: string | null;
            severity: 'low' | 'medium' | 'high';
            description: string;
            suggested_action?: string | null;
        }>;
    }> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/ai/anomaly',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                404: `structured error`,
                502: `structured error`,
                504: `structured error`,
            },
        });
    }
}
