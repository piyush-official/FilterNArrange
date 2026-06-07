interface Props {
  format: string;
  confidence: number;
  schema: Array<{ name: string; type: string; nullable: boolean }>;
}

export function DetectionPanel({ format, confidence, schema }: Props) {
  return (
    <section aria-label="detection result">
      <h2>Detected: {format}</h2>
      <p>Confidence: {(confidence * 100).toFixed(0)}%</p>
      <table>
        <thead><tr><th>Column</th><th>Type</th><th>Nullable</th></tr></thead>
        <tbody>
          {schema.map(c => (
            <tr key={c.name}>
              <td>{c.name}</td><td>{c.type}</td><td>{c.nullable ? 'yes' : 'no'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
