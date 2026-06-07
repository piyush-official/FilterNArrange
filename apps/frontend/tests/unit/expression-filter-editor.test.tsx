import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ExpressionFilterEditor } from '../../src/features/filter/ui/ExpressionFilterEditor';

// Mock @monaco-editor/react so the test runs without bundling the monaco
// editor / loading WASM. Renders a plain textarea that forwards onChange.
vi.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea
      data-testid="monaco"
      aria-label="expression-monaco"
      value={value}
      onChange={e => onChange(e.target.value)}
    />
  ),
}));


describe('ExpressionFilterEditor', () => {
  it('renders the editor + hint', () => {
    render(<ExpressionFilterEditor
      schema={[{ name: 'age', type: 'integer' }]}
      value={{ expr: '' }}
      onChange={() => {}}
    />);
    expect(screen.getByTestId('monaco')).toBeInTheDocument();
    expect(screen.getByText(/AND country/i)).toBeInTheDocument();
  });

  it('reports edits through onChange', () => {
    const onChange = vi.fn();
    render(<ExpressionFilterEditor
      schema={[{ name: 'age', type: 'integer' }]}
      value={{ expr: '' }}
      onChange={onChange}
    />);
    fireEvent.change(screen.getByTestId('monaco'), { target: { value: "age > 18" } });
    expect(onChange).toHaveBeenCalledWith({ expr: 'age > 18' });
  });
});
