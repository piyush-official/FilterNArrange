interface SchemaColumn {
  name: string;
  type: string;
}

export const ROW_OPS = [
  "eq", "ne", "gt", "gte", "lt", "lte",
  "contains", "starts_with", "ends_with",
  "regex", "in", "not_in", "is_null", "is_not_null",
] as const;

export type RowOp = (typeof ROW_OPS)[number];

export interface RowPredicate {
  col: string;
  op: RowOp;
  value?: unknown;
}

interface Props {
  schema: SchemaColumn[];
  value: RowPredicate;
  onChange: (p: RowPredicate) => void;
}

export function RowFilterForm({ schema, value, onChange }: Props) {
  const needsValue = !value.op.startsWith("is_");
  return (
    <div className="row-filter">
      <label>
        Column:
        <select
          aria-label="row-filter-column"
          value={value.col}
          onChange={e => onChange({ ...value, col: e.target.value })}
        >
          {schema.map(c => (
            <option key={c.name} value={c.name}>{c.name} ({c.type})</option>
          ))}
        </select>
      </label>
      <label>
        Operator:
        <select
          aria-label="row-filter-op"
          value={value.op}
          onChange={e => onChange({ ...value, op: e.target.value as RowOp })}
        >
          {ROW_OPS.map(op => (
            <option key={op} value={op}>{op}</option>
          ))}
        </select>
      </label>
      {needsValue && (
        <label>
          Value:
          <input
            aria-label="row-filter-value"
            value={(value.value as string) ?? ""}
            onChange={e => onChange({ ...value, value: e.target.value })}
          />
        </label>
      )}
    </div>
  );
}
