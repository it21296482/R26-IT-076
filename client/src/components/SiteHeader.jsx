import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_DASHBOARD_PATH } from "../lib/routes";
import BrandLogo from "./BrandLogo";

function SiteHeader({ compact = false }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const navLinkClass = ({ isActive }) =>
    `rounded-full px-4 py-2 text-sm font-medium transition ${
      isActive ? "bg-[#1d4aa8] text-white shadow-[0_12px_24px_rgba(29,74,168,0.24)]" : "text-slate-600 hover:bg-[#eff5ff] hover:text-slate-900"
    }`;

  return (
    <header className="shell sticky top-4 z-30 mb-6">
      <div className={`glass-nav flex flex-wrap items-center justify-between gap-4 rounded-[26px] px-5 py-4 ${compact ? "" : ""}`}>
        <BrandLogo compact={compact} />

        <nav className="flex flex-wrap items-center gap-2">
          <NavLink className={navLinkClass} to="/">
            Home
          </NavLink>
          {!user && (
            <>
              <NavLink className={navLinkClass} to="/login">
                Sign In
              </NavLink>
              <NavLink className={navLinkClass} to="/register">
                Sign Up
              </NavLink>
            </>
          )}
          {user?.role === "user" && (
            <NavLink className={navLinkClass} to="/dashboard">
              Workspace
            </NavLink>
          )}
          {user?.role === "admin" && (
            <NavLink className={navLinkClass} to={ADMIN_DASHBOARD_PATH}>
              Console
            </NavLink>
          )}
          {user && (
            <button
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
              onClick={handleLogout}
              type="button"
            >
              Logout
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}

export default SiteHeader;
