/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ColumnFilterSpec } from './ColumnFilterSpec';
export type ConvertRequest = {
    uploadId: string;
    filter: ColumnFilterSpec;
    outputFormat: ConvertRequest.outputFormat;
};
export namespace ConvertRequest {
    export enum outputFormat {
        CSV = 'csv',
        JSON = 'json',
    }
}

