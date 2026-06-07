import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface Props { onSelect: (file: File) => void; }

export function Dropzone({ onSelect }: Props) {
  const onDrop = useCallback((files: File[]) => {
    if (files.length > 0) onSelect(files[0]);
  }, [onSelect]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: false, accept: { 'text/csv': ['.csv'], 'application/json': ['.json'] },
  });
  return (
    <div {...getRootProps()} role="button">
      <input {...getInputProps({ id: 'upload-input' })} aria-label="Upload CSV or JSON" />
      <p>{isDragActive ? 'Drop the file here' : 'Drop a CSV or JSON file, or click to choose'}</p>
    </div>
  );
}
