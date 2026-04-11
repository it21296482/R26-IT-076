import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_DASHBOARD_PATH, ADMIN_ENTRY_PATH } from "../lib/routes";

function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="screen-center">Loading secure workspace...</div>;
  }

  if (!user) {
    return <Navigate to={role === "admin" ? ADMIN_ENTRY_PATH : "/login"} replace state={{ from: location }} />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "admin" ? ADMIN_DASHBOARD_PATH : "/dashboard"} replace />;
  }

  return children;
}

export default ProtectedRoute;
