/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AnalysisSpec = {
    kind: AnalysisSpec.kind;
    options?: Record<string, any>;
};
export namespace AnalysisSpec {
    export enum kind {
        SUMMARY_STATS = 'summary_stats',
        GROUP_BY = 'group_by',
        CHART_SUGGEST = 'chart_suggest',
        SCHEMA_INFER = 'schema_infer',
    }
}

