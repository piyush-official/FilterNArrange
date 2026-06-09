/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type RowFilterPredicate = {
    col: string;
    op: RowFilterPredicate.op;
    /**
     * present for ops other than is_null / is_not_null
     */
    value?: any;
};
export namespace RowFilterPredicate {
    export enum op {
        EQ = 'eq',
        NE = 'ne',
        GT = 'gt',
        GTE = 'gte',
        LT = 'lt',
        LTE = 'lte',
        CONTAINS = 'contains',
        STARTS_WITH = 'starts_with',
        ENDS_WITH = 'ends_with',
        REGEX = 'regex',
        IN = 'in',
        NOT_IN = 'not_in',
        IS_NULL = 'is_null',
        IS_NOT_NULL = 'is_not_null',
    }
}

