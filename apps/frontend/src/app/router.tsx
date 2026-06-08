import { Navigate, Route, Routes } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { SignupPage } from '../pages/SignupPage';
import { WorkbenchPage } from '../pages/WorkbenchPage';
import { JobsListPage, BatchTab } from '../features/jobs';
import { BillingPanel } from '../features/billing';
import { RecipesPage } from '../features/recipes';
import { AdminFormatRequestsPage } from '../features/formatRequests';
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
      <Route path="/account/billing" element={<Private><BillingPanel /></Private>} />
      <Route path="/recipes" element={<Private><RecipesPage /></Private>} />
      <Route
        path="/admin/format-requests"
        element={<Private><AdminFormatRequestsPage /></Private>}
      />
    </Routes>
  );
}
