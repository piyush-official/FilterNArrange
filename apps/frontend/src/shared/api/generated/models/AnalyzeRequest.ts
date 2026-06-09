/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AnalysisSpec } from './AnalysisSpec';
import type { FilterSpec } from './FilterSpec';
export type AnalyzeRequest = {
    uploadId: string;
    analysis: AnalysisSpec;
    /**
     * optional filter applied before analysis
     */
    filter?: FilterSpec | null;
};

