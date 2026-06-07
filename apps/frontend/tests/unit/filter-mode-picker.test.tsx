import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { FilterModePicker } from '../../src/features/filter/ui/FilterModePicker';


describe('FilterModePicker', () => {
  it('renders all four tabs', () => {
    render(<FilterModePicker mode="column" onChange={() => {}} />);
    expect(screen.getByRole('tab', { name: /columns/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /rows/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /expression/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /regex/i })).toBeInTheDocument();
  });

  it('switches active mode on tab click', () => {
    const onChange = vi.fn();
    render(<FilterModePicker mode="column" onChange={onChange} />);
    fireEvent.click(screen.getByRole('tab', { name: /rows/i }));
    expect(onChange).toHaveBeenCalledWith('row');
  });

  it('marks the active tab via aria-selected', () => {
    render(<FilterModePicker mode="expression" onChange={() => {}} />);
    expect(screen.getByRole('tab', { name: /expression/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: /columns/i })).toHaveAttribute('aria-selected', 'false');
  });
});
