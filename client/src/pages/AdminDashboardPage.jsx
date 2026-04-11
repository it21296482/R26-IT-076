import { useEffect, useMemo, useState } from "react";
import SiteHeader from "../components/SiteHeader";
import api from "../lib/api";

const initialUploadForm = {
  symbol: "",
  companyName: "",
  notes: "",
};

const buildTemplateFile = () => {
  const template = [
    "tradeDate,open,high,low,close,adjustedClose,volume",
    "2026-01-02,182.50,185.00,181.25,184.40,184.40,1450000",
    "2026-01-03,184.40,186.00,183.90,185.55,185.55,1582300",
  ].join("\n");

  const blob = new Blob([template], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "historical-price-template.csv";
  anchor.click();
  URL.revokeObjectURL(url);
};

function AdminDashboardPage() {
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [uploadForm, setUploadForm] = useState(initialUploadForm);
  const [csvFile, setCsvFile] = useState(null);
  const [resetDrafts, setResetDrafts] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [resettingUserId, setResettingUserId] = useState("");

  const loadAdminData = async () => {
    try {
      const [{ data: overviewData }, { data: usersData }] = await Promise.all([
        api.get("/admin/overview"),
        api.get("/admin/users"),
      ]);
      setOverview(overviewData);
      setUsers(usersData.users);
    } catch (err) {
      setError(err.response?.data?.message || "Unable to load the administration console.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const userRows = useMemo(
    () =>
      users.map((user) => ({
        ...user,
        passwordStatus: "Protected",
      })),
    [users]
  );

  const handleCsvUpload = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!csvFile) {
      setError("Please choose a CSV file to import.");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("symbol", uploadForm.symbol);
      formData.append("companyName", uploadForm.companyName);
      formData.append("notes", uploadForm.notes);
      formData.append("file", csvFile);

      const { data } = await api.post("/admin/stocks/upload-csv", formData);
      setSuccess(data.message);
      setUploadForm(initialUploadForm);
      setCsvFile(null);
      await loadAdminData();
    } catch (err) {
      setError(err.response?.data?.message || "Unable to import the CSV file.");
    } finally {
      setUploading(false);
    }
  };

  const handleResetPassword = async (userId) => {
    const newPassword = resetDrafts[userId];

    if (!newPassword || newPassword.length < 8) {
      setError("Enter a temporary password with at least 8 characters.");
      return;
    }

    setError("");
    setSuccess("");
    setResettingUserId(userId);

    try {
      const { data } = await api.post(`/admin/users/${userId}/reset-password`, {
        newPassword,
      });

      setSuccess(data.message);
      setResetDrafts((current) => ({ ...current, [userId]: "" }));
      await loadAdminData();
    } catch (err) {
      setError(err.response?.data?.message || "Unable to reset the password.");
    } finally {
      setResettingUserId("");
    }
  };

  const stats = [
    ["Registered users", overview?.metrics?.userCount ?? 0],
    ["Admin accounts", overview?.metrics?.adminCount ?? 0],
    ["Tracked companies", overview?.metrics?.companyCount ?? 0],
    ["Total price rows", overview?.metrics?.stockRecordCount ?? 0],
  ];

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-10">
        <section className="grid gap-8 lg:grid-cols-[1fr_360px]">
          <div className="space-y-5 fade-rise">
            <p className="eyebrow">Secure admin console</p>
            <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">Control access and keep market data ready.</h1>
            <p className="max-w-3xl text-lg leading-8 text-slate-300">
              Manage users, support account recovery, and import historical price data through CSV so the platform stays operational and trustworthy.
            </p>
          </div>

          <div className="dark-card chart-grid relative overflow-hidden p-6 fade-rise-delay-1">
            <div className="trend-path absolute left-6 right-6 top-12 h-24 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
            <div className="relative z-10 grid gap-4">
              {stats.map(([label, value]) => (
                <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4" key={label}>
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{label}</p>
                  <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {(error || success) && (
          <section className="space-y-3">
            {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
            {success && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}
          </section>
        )}

        <section className="grid gap-8 xl:grid-cols-[0.92fr_1.08fr]">
          <article className="light-card p-8 fade-rise">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="eyebrow !text-slate-500">Historical price import</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Import CSV data</h2>
                <p className="mt-3 max-w-xl text-sm leading-7 text-slate-600">
                  Upload one company dataset at a time so the system can load the correct historical prices when users select a stock.
                </p>
              </div>

              <button className="rounded-full border border-slate-200 bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800" onClick={buildTemplateFile} type="button">
                Download template
              </button>
            </div>

            <form className="mt-8 space-y-5" onSubmit={handleCsvUpload}>
              <div className="grid gap-5 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Company name</span>
                  <input
                    className="input-surface"
                    onChange={(event) => setUploadForm((current) => ({ ...current, companyName: event.target.value }))}
                    placeholder="John Keells Holdings PLC"
                    type="text"
                    value={uploadForm.companyName}
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Ticker symbol</span>
                  <input
                    className="input-surface"
                    onChange={(event) => setUploadForm((current) => ({ ...current, symbol: event.target.value.toUpperCase() }))}
                    placeholder="JKH.N0000"
                    type="text"
                    value={uploadForm.symbol}
                  />
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">CSV file</span>
                <input
                  className="input-surface file:mr-4 file:rounded-full file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
                  onChange={(event) => setCsvFile(event.target.files?.[0] || null)}
                  type="file"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">Notes</span>
                <textarea
                  className="input-surface min-h-32 resize-none"
                  onChange={(event) => setUploadForm((current) => ({ ...current, notes: event.target.value }))}
                  placeholder="Optional import note"
                  value={uploadForm.notes}
                />
              </label>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm leading-7 text-slate-600">
                Expected columns: <code>tradeDate</code>, <code>open</code>, <code>high</code>, <code>low</code>,{" "}
                <code>close</code>, <code>adjustedClose</code>, <code>volume</code>
              </div>

              {csvFile && <p className="text-sm text-slate-500">Selected file: {csvFile.name}</p>}

              <button className="primary-cta w-full" disabled={uploading} type="submit">
                {uploading ? "Importing CSV..." : "Import Historical Prices"}
              </button>
            </form>
          </article>

          <article className="dark-card chart-grid relative overflow-hidden p-8 fade-rise-delay-1">
            <div className="trend-path absolute left-6 right-6 top-16 h-24 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
            <div className="relative z-10">
              <p className="eyebrow">User directory</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Support access without exposing passwords</h2>
              <div className="mt-6 space-y-4">
                {userRows.map((user) => (
                  <div className="rounded-[24px] border border-white/10 bg-white/6 p-5" key={user._id}>
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-2">
                        <p className="text-lg font-semibold text-white">{user.name}</p>
                        <p className="text-sm text-slate-300">{user.email}</p>
                        <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                          {user.role} • Last login: {user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : "Not recorded"}
                        </p>
                      </div>

                      <div className="w-full max-w-sm space-y-3">
                        <div className="rounded-2xl border border-white/10 bg-slate-950/35 px-4 py-3 text-sm text-slate-300">
                          Password status: <span className="font-semibold text-white">{user.passwordStatus}</span>
                        </div>
                        <input
                          className="w-full rounded-2xl border border-white/10 bg-slate-950/35 px-4 py-3 text-white outline-none transition focus:border-sky-300/40 focus:ring-4 focus:ring-sky-300/10"
                          onChange={(event) =>
                            setResetDrafts((current) => ({ ...current, [user._id]: event.target.value }))
                          }
                          placeholder="Temporary new password"
                          type="password"
                          value={resetDrafts[user._id] || ""}
                        />
                        <button
                          className="w-full rounded-full border border-white/10 bg-white/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/14"
                          onClick={() => handleResetPassword(user._id)}
                          type="button"
                        >
                          {resettingUserId === user._id ? "Resetting..." : "Reset Password"}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}

                {!loading && !userRows.length && <p className="text-sm text-slate-400">No user accounts available yet.</p>}
              </div>
            </div>
          </article>
        </section>

        <section className="light-card p-8 fade-rise">
          <p className="eyebrow !text-slate-500">Recent market rows</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Latest imported records</h2>
          <div className="mt-6 grid gap-4">
            {(overview?.latestStocks || []).map((stock) => (
              <div className="flex flex-col gap-3 rounded-[22px] border border-slate-200 bg-slate-50 px-5 py-4 md:flex-row md:items-center md:justify-between" key={stock._id}>
                <div>
                  <p className="text-base font-semibold text-slate-900">{stock.companyName}</p>
                  <p className="text-sm text-slate-500">{stock.symbol}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Trade date</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{new Date(stock.tradeDate).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Close</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{stock.close}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Volume</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{stock.volume}</p>
                  </div>
                </div>
              </div>
            ))}
            {!overview?.latestStocks?.length && <p className="text-sm text-slate-500">No historical price rows imported yet.</p>}
          </div>
        </section>
      </main>
    </div>
  );
}

export default AdminDashboardPage;
