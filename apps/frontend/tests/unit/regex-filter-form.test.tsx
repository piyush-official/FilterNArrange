import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RegexFilterForm } from '../../src/features/filter/ui/RegexFilterForm';


describe('RegexFilterForm', () => {
  it('reports pattern changes', () => {
    const onChange = vi.fn();
    render(<RegexFilterForm value={{ pattern: '', flags: [] }} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('regex-filter-pattern'), { target: { value: '^foo' } });
    expect(onChange).toHaveBeenCalledWith({ pattern: '^foo', flags: [] });
  });

  it('toggles flags', () => {
    const onChange = vi.fn();
    render(<RegexFilterForm value={{ pattern: '^foo', flags: [] }} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText('regex-flag-i'));
    expect(onChange).toHaveBeenCalledWith({ pattern: '^foo', flags: ['i'] });
  });
});
