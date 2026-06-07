import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../src/features/auth', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

vi.mock('../../src/features/upload/api/sheets', () => ({
  listSheets: vi.fn().mockResolvedValue(['people', 'orders']),
}));

import { SheetPicker } from '../../src/features/upload/ui/SheetPicker';


describe('SheetPicker', () => {
  it('lists sheet names and emits selection', async () => {
    const onPick = vi.fn();
    render(<SheetPicker uploadId="u1" picked={null} onPick={onPick} />);
    await waitFor(() => screen.getByText('orders'));
    fireEvent.click(screen.getByText('orders'));
    expect(onPick).toHaveBeenCalledWith('orders');
  });

  it('marks the picked sheet via aria-pressed', async () => {
    render(<SheetPicker uploadId="u1" picked="people" onPick={() => {}} />);
    await waitFor(() => screen.getByText('people'));
    expect(screen.getByText('people')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('orders')).toHaveAttribute('aria-pressed', 'false');
  });
});
