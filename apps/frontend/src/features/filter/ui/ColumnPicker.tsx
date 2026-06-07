interface Props {
  columns: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}

export function ColumnPicker({ columns, selected, onChange }: Props) {
  function toggle(c: string) {
    const set = new Set(selected);
    set.has(c) ? set.delete(c) : set.add(c);
    onChange(columns.filter(col => set.has(col)));
  }
  return (
    <fieldset>
      <legend>Columns to keep</legend>
      <button type="button" onClick={() => onChange([...columns])}>Select all</button>
      <button type="button" onClick={() => onChange([])}>Select none</button>
      <ul>
        {columns.map(c => (
          <li key={c}>
            <label>
              <input type="checkbox" aria-label={c}
                     checked={selected.includes(c)}
                     onChange={() => toggle(c)} />
              {c}
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}
