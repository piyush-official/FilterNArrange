import { Navigate, Route, Routes } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { SignupPage } from '../pages/SignupPage';
import { WorkbenchPage } from '../pages/WorkbenchPage';
import { JobsListPage, BatchTab } from '../features/jobs';
import { useAuth } from '../features/auth';

function Private({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

export function Router() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/" element={<Private><WorkbenchPage /></Private>} />
      <Route path="/jobs" element={<Private><JobsListPage /></Private>} />
      <Route path="/batch" element={<Private><BatchTab /></Private>} />
    </Routes>
  );
}
