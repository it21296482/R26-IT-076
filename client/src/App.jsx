import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import HomePage from "./pages/HomePage";
import InsightPreviewPage from "./pages/InsightPreviewPage";
import RegisterPage from "./pages/RegisterPage";
import UserDashboardPage from "./pages/UserDashboardPage";
import UserLoginPage from "./pages/UserLoginPage";
import { ADMIN_DASHBOARD_PATH, ADMIN_ENTRY_PATH } from "./lib/routes";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<UserLoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path={ADMIN_ENTRY_PATH} element={<AdminLoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute role="user">
            <UserDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/insight-preview"
        element={
          <ProtectedRoute role="user">
            <InsightPreviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path={ADMIN_DASHBOARD_PATH}
        element={
          <ProtectedRoute role="admin">
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
