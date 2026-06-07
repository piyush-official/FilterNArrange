import { useNavigate } from 'react-router-dom';
import { LoginForm, useAuth } from '../features/auth';

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  return (
    <main>
      <h1>Log in</h1>
      <LoginForm onSubmit={async ({ email, password }) => {
        await login(email, password); nav('/');
      }} />
    </main>
  );
}
