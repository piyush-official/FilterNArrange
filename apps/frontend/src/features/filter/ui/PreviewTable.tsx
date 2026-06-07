interface Props {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

export function PreviewTable({ columns, rows }: Props) {
  return (
    <table aria-label="filter preview">
      <thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>{columns.map(c => <td key={c}>{String(r[c] ?? '')}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}
