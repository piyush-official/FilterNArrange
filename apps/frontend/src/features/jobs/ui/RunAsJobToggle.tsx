import * as React from 'react';

export interface RunAsJobToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
}

export function RunAsJobToggle({ value, onChange }: RunAsJobToggleProps) {
  return (
    <label className="run-as-job">
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
      />
      Run as job (async)
    </label>
  );
}
