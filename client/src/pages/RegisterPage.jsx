import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell";
import { useAuth } from "../hooks/useAuth";

function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await register({
        name: form.name,
        email: form.email,
        password: form.password,
      });
      setSuccess("Account created successfully. Redirecting...");
      setTimeout(() => navigate("/login"), 900);
    } catch (err) {
      setError(err.response?.data?.message || "Unable to create your account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Create your account and start understanding the market"
      subtitle="Join a simpler stock insight experience built to reduce noise, improve trust, and support clear investor decisions."
      footer={
        <p>
          Already have an account?{" "}
          <Link className="font-semibold text-orange-500" to="/login">
            Sign in
          </Link>
          .
        </p>
      }
    >
      <div className="space-y-8">
        <div className="space-y-3">
          <p className="eyebrow !text-slate-500">Create account</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Get started in minutes</h2>
          <p className="text-sm leading-7 text-slate-500">Set up your account and move directly into guided stock analysis.</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Full name</span>
            <input
              className="input-surface"
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Enter your full name"
              type="text"
              value={form.name}
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Email address</span>
            <input
              className="input-surface"
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="you@example.com"
              type="email"
              value={form.email}
            />
          </label>

          <div className="grid gap-5 sm:grid-cols-2">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Password</span>
              <input
                className="input-surface"
                minLength={8}
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="At least 8 characters"
                type="password"
                value={form.password}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Confirm password</span>
              <input
                className="input-surface"
                minLength={8}
                onChange={(event) => setForm((current) => ({ ...current, confirmPassword: event.target.value }))}
                placeholder="Repeat your password"
                type="password"
                value={form.confirmPassword}
              />
            </label>
          </div>

          {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
          {success && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}

          <button className="primary-cta w-full" disabled={loading} type="submit">
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>
      </div>
    </AuthShell>
  );
}

export default RegisterPage;
