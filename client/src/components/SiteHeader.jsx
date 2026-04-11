import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_DASHBOARD_PATH } from "../lib/routes";

function SiteHeader({ compact = false }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const navLinkClass = ({ isActive }) =>
    `rounded-full px-4 py-2 text-sm font-medium transition ${
      isActive ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/6 hover:text-white"
    }`;

  return (
    <header className="shell sticky top-4 z-30 mb-6">
      <div className={`glass-nav flex items-center justify-between gap-6 rounded-[26px] px-5 py-4 ${compact ? "" : ""}`}>
        <Link className="min-w-0" to="/">
          <p className="eyebrow !mb-1">AI Powered Market Intelligence</p>
          <p className="truncate text-base font-semibold text-white md:text-lg">CSE Insight Generator</p>
        </Link>

        <nav className="flex items-center gap-2">
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
              className="rounded-full border border-white/10 bg-white/6 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
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
