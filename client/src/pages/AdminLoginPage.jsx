import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_DASHBOARD_PATH } from "../lib/routes";

function AdminLoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login("admin", form);
      navigate(ADMIN_DASHBOARD_PATH);
    } catch (err) {
      setError(err.response?.data?.message || "Unable to sign in right now.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      mode="admin"
      subtitle="Secure administration for access control, user support, and historical price imports."
      title="Restricted console entry"
    >
      <div className="space-y-8">
        <div className="space-y-3">
          <p className="eyebrow !text-slate-500">Secure console</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Administrator sign in</h2>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Admin email</span>
            <input
              className="input-surface"
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="admin@cseinsight.lk"
              type="email"
              value={form.email}
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Password</span>
            <input
              className="input-surface"
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="Enter admin password"
              type="password"
              value={form.password}
            />
          </label>

          {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

          <button className="primary-cta w-full" disabled={loading} type="submit">
            {loading ? "Checking access..." : "Enter Console"}
          </button>
        </form>
      </div>
    </AuthShell>
  );
}

export default AdminLoginPage;
