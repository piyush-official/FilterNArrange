interface Props {
  disabled: boolean;
  onClick: () => void;
  busy: boolean;
}

export function DownloadButton({ disabled, onClick, busy }: Props) {
  return (
    <button type="button" onClick={onClick} disabled={disabled || busy}>
      {busy ? 'Preparing…' : 'Download'}
    </button>
  );
}
