export type FilterMode = "column" | "row" | "expression" | "regex";

const TABS: { id: FilterMode; label: string }[] = [
  { id: "column",     label: "Columns" },
  { id: "row",        label: "Rows" },
  { id: "expression", label: "Expression" },
  { id: "regex",      label: "Regex" },
];

interface Props {
  mode: FilterMode;
  onChange: (m: FilterMode) => void;
}

export function FilterModePicker({ mode, onChange }: Props) {
  return (
    <div role="tablist" aria-label="Filter mode" className="filter-mode-picker">
      {TABS.map(t => (
        <button
          key={t.id}
          role="tab"
          aria-selected={mode === t.id}
          className={mode === t.id ? "tab tab-active" : "tab"}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
