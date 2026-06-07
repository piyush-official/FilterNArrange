import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AiFilterMode } from '../ui/AiFilterMode';
import * as api from '../api';

describe('AiFilterMode', () => {
  it('submits the query and renders the returned spec', async () => {
    vi.spyOn(api.aiApi, 'nlToFilter').mockResolvedValue({
      filter_spec: {
        kind: 'row',
        predicate: { op: 'gt', column: 'age', value: 18 },
      },
      confidence: 0.9,
    });
    const onApply = vi.fn();
    render(<AiFilterMode ref_={'x'} schema={[]} onApply={onApply} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about your data/i), {
      target: { value: 'rows where age > 18' },
    });
    fireEvent.click(screen.getByText(/translate/i));
    await waitFor(() =>
      expect(screen.getByText(/confidence/i)).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText(/apply/i));
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'row' }),
    );
  });

  it('shows AI unavailable message when capability disabled', async () => {
    vi.spyOn(api.aiApi, 'nlToFilter').mockRejectedValue(
      new api.AiUnavailableError('AI_CAPABILITY_DISABLED', 'off'),
    );
    render(<AiFilterMode ref_={'x'} schema={[]} onApply={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about your data/i), {
      target: { value: 'x' },
    });
    fireEvent.click(screen.getByText(/translate/i));
    await waitFor(() =>
      expect(screen.getByText(/AI feature unavailable/i)).toBeInTheDocument(),
    );
  });
});
