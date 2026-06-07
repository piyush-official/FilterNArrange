interface Props {
  value: 'csv' | 'json';
  onChange: (v: 'csv' | 'json') => void;
}

export function FormatChooser({ value, onChange }: Props) {
  return (
    <fieldset>
      <legend>Output format</legend>
      <label><input type="radio" name="fmt" checked={value === 'csv'} onChange={() => onChange('csv')} />CSV</label>
      <label><input type="radio" name="fmt" checked={value === 'json'} onChange={() => onChange('json')} />JSON</label>
    </fieldset>
  );
}
