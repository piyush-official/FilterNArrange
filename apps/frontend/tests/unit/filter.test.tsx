import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ColumnPicker } from '../../src/features/filter/ui/ColumnPicker';

describe('ColumnPicker', () => {
  it('toggles columns and reports selection', async () => {
    const onChange = vi.fn();
    render(<ColumnPicker columns={['a', 'b', 'c']} selected={['a']} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText('b'));
    expect(onChange).toHaveBeenCalledWith(['a', 'b']);
  });

  it('select all and none', async () => {
    const onChange = vi.fn();
    render(<ColumnPicker columns={['a', 'b']} selected={[]} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: /select all/i }));
    expect(onChange).toHaveBeenCalledWith(['a', 'b']);
    await userEvent.click(screen.getByRole('button', { name: /select none/i }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});
