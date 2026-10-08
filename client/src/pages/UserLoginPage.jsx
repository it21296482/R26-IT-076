import { useLanguage } from "../context/languageStore";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell";
import { useAuth } from "../hooks/useAuth";

function UserLoginPage() {
  const { t } = useLanguage();
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
      await login("user", form);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Unable to sign in right now.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title={t("Sign in and continue with confidence")}
      subtitle={t("Access one place for stock selection, required company report upload, and a clear investor-focused explanation.")}
      footer={
        <p>{t("Need an account?")}{" "}
          <Link className="font-semibold text-orange-500" to="/register">{t("Create one")}{" "}</Link>
          .
        </p>
      }
    >
      <div className="space-y-8">
        <div className="space-y-3">
          <p className="eyebrow !text-slate-500">{t("Welcome back")}</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">{t("Investor sign in")}</h2>
          <p className="text-sm leading-7 text-slate-500">{t("Understand what changed, why it changed, and what it means.")}</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">{t("Email address")}</span>
            <input
              className="input-surface"
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="you@example.com"
              type="email"
              value={form.email}
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">{t("Password")}</span>
            <input
              className="input-surface"
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              placeholder={t("Enter your password")}
              type="password"
              value={form.password}
            />
          </label>

          {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{t(error)}</div>}

          <button className="primary-cta w-full" disabled={loading} type="submit">
            {loading ? t("Signing in...") : t("Start Analysis")}
          </button>
        </form>
      </div>
    </AuthShell>
  );
}

export default UserLoginPage;
