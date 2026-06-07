import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RowFilterForm, type RowPredicate } from '../../src/features/filter/ui/RowFilterForm';


const SCHEMA = [
  { name: 'name', type: 'string' },
  { name: 'age',  type: 'integer' },
];

describe('RowFilterForm', () => {
  it('reports column change', () => {
    const onChange = vi.fn();
    const value: RowPredicate = { col: 'name', op: 'eq', value: '' };
    render(<RowFilterForm schema={SCHEMA} value={value} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('row-filter-column'), { target: { value: 'age' } });
    expect(onChange).toHaveBeenCalledWith({ col: 'age', op: 'eq', value: '' });
  });

  it('hides the value input for is_null / is_not_null', () => {
    const value: RowPredicate = { col: 'age', op: 'is_null' };
    render(<RowFilterForm schema={SCHEMA} value={value} onChange={() => {}} />);
    expect(screen.queryByLabelText('row-filter-value')).not.toBeInTheDocument();
  });

  it('updates the value input', async () => {
    const onChange = vi.fn();
    const value: RowPredicate = { col: 'age', op: 'gt', value: '' };
    render(<RowFilterForm schema={SCHEMA} value={value} onChange={onChange} />);
    await userEvent.type(screen.getByLabelText('row-filter-value'), '5');
    expect(onChange).toHaveBeenCalledWith({ col: 'age', op: 'gt', value: '5' });
  });
});
