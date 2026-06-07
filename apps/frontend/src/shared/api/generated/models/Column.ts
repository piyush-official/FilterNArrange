/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type Column = {
    name: string;
    type: Column.type;
    nullable: boolean;
};
export namespace Column {
    export enum type {
        STRING = 'string',
        NUMBER = 'number',
        INTEGER = 'integer',
        BOOLEAN = 'boolean',
        DATETIME = 'datetime',
        NULL = 'null',
    }
}

