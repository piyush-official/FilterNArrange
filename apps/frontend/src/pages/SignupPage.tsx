import { useNavigate } from 'react-router-dom';
import { SignupForm, useAuth } from '../features/auth';

export function SignupPage() {
  const { signup } = useAuth();
  const nav = useNavigate();
  return (
    <main>
      <h1>Sign up</h1>
      <SignupForm onSubmit={async ({ email, password, displayName }) => {
        await signup(email, password, displayName); nav('/');
      }} />
    </main>
  );
}
