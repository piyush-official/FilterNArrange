import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Dropzone } from '../../src/features/upload/ui/Dropzone';

describe('Dropzone', () => {
  it('invokes onSelect when a file is chosen', async () => {
    const onSelect = vi.fn();
    render(<Dropzone onSelect={onSelect} />);
    const input = screen.getByLabelText(/upload csv or json/i) as HTMLInputElement;
    const file = new File(['name,age\nA,1'], 'x.csv', { type: 'text/csv' });
    await userEvent.upload(input, file);
    expect(onSelect).toHaveBeenCalledWith(file);
  });
});
