/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ColumnFilterSpec } from './ColumnFilterSpec';
import type { ExpressionFilterSpec } from './ExpressionFilterSpec';
import type { RegexFilterSpec } from './RegexFilterSpec';
import type { RowFilterSpec } from './RowFilterSpec';
/**
 * Added in 1.1.0 — discriminated union of the four filter kinds.
 */
export type FilterSpec = (ColumnFilterSpec | RowFilterSpec | ExpressionFilterSpec | RegexFilterSpec);

