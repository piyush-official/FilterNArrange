import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { LoginForm } from '../../src/features/auth/ui/LoginForm';

describe('LoginForm', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('calls onSubmit with email and password', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<LoginForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.co');
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
    expect(onSubmit).toHaveBeenCalledWith({ email: 'a@b.co', password: 'hunter2hunter2' });
  });

  it('validates required fields', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
