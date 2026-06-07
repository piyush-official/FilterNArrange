export type RegexFlag = "i" | "m" | "s";

export interface RegexFilterSpec {
  pattern: string;
  flags: RegexFlag[];
}

interface Props {
  value: RegexFilterSpec;
  onChange: (s: RegexFilterSpec) => void;
}

const FLAGS: RegexFlag[] = ["i", "m", "s"];

export function RegexFilterForm({ value, onChange }: Props) {
  function toggle(f: RegexFlag) {
    onChange({
      ...value,
      flags: value.flags.includes(f) ? value.flags.filter(x => x !== f) : [...value.flags, f],
    });
  }
  return (
    <div className="regex-filter">
      <label>
        Pattern:
        <input
          aria-label="regex-filter-pattern"
          value={value.pattern}
          onChange={e => onChange({ ...value, pattern: e.target.value })}
        />
      </label>
      <fieldset className="flags">
        <legend>Flags</legend>
        {FLAGS.map(f => (
          <label key={f}>
            <input
              type="checkbox"
              aria-label={`regex-flag-${f}`}
              checked={value.flags.includes(f)}
              onChange={() => toggle(f)}
            />
            {f}
          </label>
        ))}
      </fieldset>
    </div>
  );
}
