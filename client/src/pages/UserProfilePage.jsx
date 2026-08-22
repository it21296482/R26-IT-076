import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";

const formatDate = (value) => {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
};

function UserProfilePage() {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadReports = async () => {
      try {
        const { data } = await api.get("/reports");
        setReports(data.reports || []);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load profile activity.");
      } finally {
        setLoadingReports(false);
      }
    };

    loadReports();
  }, []);

  const initials = useMemo(() => {
    const names = user?.name?.trim().split(/\s+/).filter(Boolean) || [];
    return names
      .slice(0, 2)
      .map((name) => name[0])
      .join("")
      .toUpperCase();
  }, [user?.name]);

  const uniqueCompanies = new Set(reports.map((report) => report.stockSymbol).filter(Boolean)).size;
  const latestReport = reports[0];

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-8">
        <section className="surface-panel fade-rise">
          <div className="grid gap-8 lg:grid-cols-[0.82fr_1.18fr] lg:items-center">
            <div className="flex flex-col items-center rounded-[26px] border border-[#dbe7fb] bg-[#f8fbff] p-8 text-center">
              <div className="flex h-28 w-28 items-center justify-center rounded-full bg-[linear-gradient(135deg,#1d4aa8_0%,#3ecf8e_100%)] text-4xl font-semibold text-white shadow-[0_18px_34px_rgba(29,74,168,0.24)]">
                {initials || "U"}
              </div>
              <h1 className="mt-6 text-3xl font-semibold tracking-tight text-slate-950">{user?.name}</h1>
              <p className="mt-2 text-sm text-slate-500">{user?.email}</p>
              <span className="mt-5 rounded-full border border-[#dbe7fb] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[#1d4aa8]">
                {user?.role || "user"} profile
              </span>
            </div>

            <div className="space-y-6">
              <p className="eyebrow">User profile</p>
              <h2 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-5xl">
                Manage your investor workspace identity.
              </h2>
              <p className="max-w-2xl text-base leading-8 text-slate-600">
                Review the account connected to your CSE analysis workspace and keep track of recent report activity.
              </p>

              <div className="flex flex-wrap gap-3">
                <Link className="primary-cta" to="/dashboard">
                  Back to Workspace
                </Link>
                <Link className="secondary-cta" to="/dashboard/insight-preview">
                  Open Insight Preview
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="surface-panel fade-rise-delay-1">
            <p className="eyebrow !text-slate-500">Account details</p>
            <div className="mt-6 grid gap-4">
              <div className="rounded-[22px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
                <p className="text-sm text-slate-500">Full name</p>
                <p className="mt-2 text-lg font-semibold text-slate-950">{user?.name || "Not available"}</p>
              </div>
              <div className="rounded-[22px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
                <p className="text-sm text-slate-500">Email address</p>
                <p className="mt-2 break-words text-lg font-semibold text-slate-950">{user?.email || "Not available"}</p>
              </div>
              <div className="rounded-[22px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
                <p className="text-sm text-slate-500">Member since</p>
                <p className="mt-2 text-lg font-semibold text-slate-950">{formatDate(user?.createdAt)}</p>
              </div>
            </div>
          </div>

          <aside className="surface-panel fade-rise-delay-2">
            <p className="eyebrow !text-slate-500">Workspace activity</p>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <div className="metric-card p-5">
                <p className="text-sm text-slate-500">Reports</p>
                <p className="mt-3 text-3xl font-semibold text-slate-950">{loadingReports ? "..." : reports.length}</p>
              </div>
              <div className="metric-card p-5">
                <p className="text-sm text-slate-500">Companies</p>
                <p className="mt-3 text-3xl font-semibold text-slate-950">{loadingReports ? "..." : uniqueCompanies}</p>
              </div>
              <div className="metric-card p-5">
                <p className="text-sm text-slate-500">Status</p>
                <p className="mt-3 text-3xl font-semibold text-emerald-600">Active</p>
              </div>
            </div>

            <div className="mt-6 rounded-[24px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
              <p className="text-sm font-semibold text-slate-950">Latest report</p>
              {error && <p className="mt-3 text-sm leading-6 text-rose-600">{error}</p>}
              {!error && loadingReports && <p className="mt-3 text-sm leading-6 text-slate-500">Loading latest activity...</p>}
              {!error && !loadingReports && latestReport && (
                <div className="mt-4 space-y-2 text-sm leading-6 text-slate-600">
                  <p>
                    <span className="font-semibold text-slate-900">{latestReport.companyName}</span> ({latestReport.stockSymbol})
                  </p>
                  <p>{latestReport.originalFilename}</p>
                  <p>Uploaded {formatDate(latestReport.createdAt)}</p>
                </div>
              )}
              {!error && !loadingReports && !latestReport && (
                <p className="mt-3 text-sm leading-6 text-slate-500">No reports uploaded yet.</p>
              )}
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}

export default UserProfilePage;
