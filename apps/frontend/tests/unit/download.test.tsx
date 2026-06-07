import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { FormatChooser } from '../../src/features/download/ui/FormatChooser';

describe('FormatChooser', () => {
  it('reports format change', async () => {
    const onChange = vi.fn();
    render(<FormatChooser value="csv" onChange={onChange} />);
    await userEvent.click(screen.getByLabelText('JSON'));
    expect(onChange).toHaveBeenCalledWith('json');
  });
});
