import { useEffect, useMemo, useState } from "react";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";

const initialUploadForm = {
  symbol: "",
  companyName: "",
  notes: "",
};

const initialUserForm = {
  name: "",
  email: "",
  password: "",
  role: "user",
};

const initialRecordForm = {
  _id: "",
  symbol: "",
  companyName: "",
  tradeDate: "",
  open: "",
  high: "",
  low: "",
  close: "",
  adjustedClose: "",
  volume: "",
  notes: "",
};

const USERS_PER_PAGE = 5;
const RECORDS_PER_PAGE = 6;

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
  const { user: currentUser } = useAuth();
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [stockRecords, setStockRecords] = useState([]);
  const [uploadForm, setUploadForm] = useState(initialUploadForm);
  const [userForm, setUserForm] = useState(initialUserForm);
  const [recordForm, setRecordForm] = useState(initialRecordForm);
  const [csvFile, setCsvFile] = useState(null);
  const [resetDrafts, setResetDrafts] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [resettingUserId, setResettingUserId] = useState("");
  const [editingUserId, setEditingUserId] = useState("");
  const [savingUser, setSavingUser] = useState(false);
  const [deletingUserId, setDeletingUserId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [recordSearchTerm, setRecordSearchTerm] = useState("");
  const [recordPage, setRecordPage] = useState(1);
  const [savingRecord, setSavingRecord] = useState(false);
  const [deletingRecordId, setDeletingRecordId] = useState("");

  const loadAdminData = async () => {
    try {
      const [{ data: overviewData }, { data: usersData }] = await Promise.all([
        api.get("/admin/overview"),
        api.get("/admin/users"),
      ]);
      setOverview(overviewData);
      setUsers(usersData.users);
      const { data: stockData } = await api.get("/stocks");
      setStockRecords(stockData.stocks || []);
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

  const filteredUsers = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    if (!query) {
      return userRows;
    }

    return userRows.filter((user) =>
      [user.name, user.email, user.role].some((value) => value?.toLowerCase().includes(query))
    );
  }, [searchTerm, userRows]);

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / USERS_PER_PAGE));
  const paginatedUsers = filteredUsers.slice((currentPage - 1) * USERS_PER_PAGE, currentPage * USERS_PER_PAGE);

  const filteredRecords = useMemo(() => {
    const query = recordSearchTerm.trim().toLowerCase();

    if (!query) {
      return stockRecords;
    }

    return stockRecords.filter((record) =>
      [record.companyName, record.symbol, record.notes].some((value) => String(value || "").toLowerCase().includes(query))
    );
  }, [recordSearchTerm, stockRecords]);

  const totalRecordPages = Math.max(1, Math.ceil(filteredRecords.length / RECORDS_PER_PAGE));
  const paginatedRecords = filteredRecords.slice((recordPage - 1) * RECORDS_PER_PAGE, recordPage * RECORDS_PER_PAGE);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    setRecordPage(1);
  }, [recordSearchTerm]);

  useEffect(() => {
    if (recordPage > totalRecordPages) {
      setRecordPage(totalRecordPages);
    }
  }, [recordPage, totalRecordPages]);

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

  const handleSaveUser = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSavingUser(true);

    try {
      if (editingUserId) {
        const { data } = await api.put(`/admin/users/${editingUserId}`, {
          name: userForm.name,
          email: userForm.email,
          role: userForm.role,
        });
        setSuccess(data.message);
      } else {
        const { data } = await api.post("/admin/users", userForm);
        setSuccess(data.message);
      }

      setUserForm(initialUserForm);
      setEditingUserId("");
      await loadAdminData();
    } catch (err) {
      setError(err.response?.data?.message || "Unable to save the user.");
    } finally {
      setSavingUser(false);
    }
  };

  const handleEditUser = (user) => {
    setEditingUserId(user._id);
    setUserForm({
      name: user.name,
      email: user.email,
      password: "",
      role: user.role,
    });
    setError("");
    setSuccess("");
  };

  const handleCancelEdit = () => {
    setEditingUserId("");
    setUserForm(initialUserForm);
  };

  const handleDeleteUser = async (userId) => {
    setError("");
    setSuccess("");
    setDeletingUserId(userId);

    try {
      const { data } = await api.delete(`/admin/users/${userId}`);
      setSuccess(data.message);
      await loadAdminData();
    } catch (err) {
      setError(err.response?.data?.message || "Unable to delete the user.");
    } finally {
      setDeletingUserId("");
    }
  };

  const handleExportUsers = () => {
    const rows = filteredUsers
      .map(
        (user, index) => `
          <tr>
            <td>${index + 1}</td>
            <td>${user.name}</td>
            <td>${user.email}</td>
            <td>${user.role}</td>
            <td>${user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : "Not recorded"}</td>
          </tr>
        `
      )
      .join("");

    const popup = window.open("", "_blank", "width=980,height=720");

    if (!popup) {
      setError("Allow pop-ups to download the users PDF.");
      return;
    }

    popup.document.write(`
      <html>
        <head>
          <title>Users Export</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 32px; color: #0f172a; }
            h1 { margin: 0 0 8px; font-size: 24px; }
            p { margin: 0 0 24px; color: #475569; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: left; font-size: 12px; }
            th { background: #eff6ff; }
          </style>
        </head>
        <body>
          <h1>CSE Insight Generator Users</h1>
          <p>Generated on ${new Date().toLocaleString()}</p>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Last Login</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  };

  const handleEditRecord = (record) => {
    setRecordForm({
      _id: record._id,
      symbol: record.symbol,
      companyName: record.companyName,
      tradeDate: new Date(record.tradeDate).toISOString().slice(0, 10),
      open: record.open,
      high: record.high,
      low: record.low,
      close: record.close,
      adjustedClose: record.adjustedClose ?? "",
      volume: record.volume,
      notes: record.notes || "",
    });
    setError("");
    setSuccess("");
  };

  const handleCancelRecordEdit = () => {
    setRecordForm(initialRecordForm);
  };

  const handleSaveRecord = async (event) => {
    event.preventDefault();

    if (!recordForm._id) {
      setError("Select a stock record to edit.");
      return;
    }

    setError("");
    setSuccess("");
    setSavingRecord(true);

    try {
      const { data } = await api.put(`/admin/stocks/${recordForm._id}`, recordForm);
      setSuccess(data.message);
      setRecordForm(initialRecordForm);
      await loadAdminData();
    } catch (err) {
      setError(err.response?.data?.message || "Unable to update the stock record.");
    } finally {
      setSavingRecord(false);
    }
  };

  const handleDeleteRecord = async (stockId) => {
    setError("");
    setSuccess("");
    setDeletingRecordId(stockId);

    try {
      const { data } = await api.delete(`/admin/stocks/${stockId}`);
      setSuccess(data.message);
      if (recordForm._id === stockId) {
        setRecordForm(initialRecordForm);
      }
      await loadAdminData();
    } catch (err) {
      setError(err.response?.data?.message || "Unable to delete the stock record.");
    } finally {
      setDeletingRecordId("");
    }
  };

  const stats = [
    ["Registered users", overview?.metrics?.userCount ?? 0],
    ["Admin accounts", overview?.metrics?.adminCount ?? 0],
    ["Tracked companies", overview?.metrics?.companyCount ?? 0],
    ["Total price rows", overview?.metrics?.stockRecordCount ?? 0],
  ];

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-10">
        <section className="grid gap-8 lg:grid-cols-[1fr_360px]">
          <div className="space-y-5 fade-rise">
            <p className="eyebrow">Secure admin console</p>
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">Control access and keep market data ready.</h1>
            <p className="max-w-3xl text-lg leading-8 text-slate-600">
              Manage users, support account recovery, and import historical price data through CSV so the platform stays operational and trustworthy.
            </p>
          </div>

          <div className="market-hero relative overflow-hidden p-6 fade-rise-delay-1">
            <div className="market-orb absolute -right-16 top-4 h-40 w-40 opacity-70" />
            <div className="relative z-10 grid gap-4">
              {stats.map(([label, value]) => (
                <div className="rounded-2xl border border-white/10 bg-white/8 px-4 py-4" key={label}>
                  <p className="text-xs uppercase tracking-[0.22em] text-blue-100/75">{label}</p>
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

        <section className="grid gap-8 2xl:grid-cols-[0.86fr_1.14fr]">
          <article className="surface-panel fade-rise">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="eyebrow !text-slate-500">Historical price import</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Import CSV data</h2>
                <p className="mt-3 max-w-xl text-sm leading-7 text-slate-600">
                  Upload one company dataset at a time so the system can load the correct historical prices when users select a stock.
                </p>
              </div>

              <button className="secondary-cta self-start !border-[#d7e6ff] !bg-[#eff5ff] !text-[#1d4aa8] hover:!bg-[#e4efff] sm:self-auto" onClick={buildTemplateFile} type="button">
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

              <div className="metric-card px-4 py-4 text-sm leading-7 text-slate-600">
                Expected columns: <code>tradeDate</code>, <code>open</code>, <code>high</code>, <code>low</code>,{" "}
                <code>close</code>, <code>adjustedClose</code>, <code>volume</code>
              </div>

              {csvFile && <p className="text-sm text-slate-500">Selected file: {csvFile.name}</p>}

              <button className="primary-cta w-full" disabled={uploading} type="submit">
                {uploading ? "Importing CSV..." : "Import Historical Prices"}
              </button>
            </form>
          </article>

          <article className="surface-panel fade-rise-delay-1">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="eyebrow !text-slate-500">User directory</p>
              </div>
              <button className="secondary-cta self-start lg:self-auto" onClick={handleExportUsers} type="button">
                Download users PDF
              </button>
            </div>

            <form className="mt-8 grid gap-4 rounded-[24px] border border-[#dbe7fb] bg-[#f8fbff] p-5 xl:grid-cols-2" onSubmit={handleSaveUser}>
              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">Full name</span>
                <input
                  className="input-surface"
                  onChange={(event) => setUserForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Enter full name"
                  type="text"
                  value={userForm.name}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">Email</span>
                <input
                  className="input-surface"
                  onChange={(event) => setUserForm((current) => ({ ...current, email: event.target.value }))}
                  placeholder="you@example.com"
                  type="email"
                  value={userForm.email}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">Role</span>
                <select
                  className="input-surface"
                  onChange={(event) => setUserForm((current) => ({ ...current, role: event.target.value }))}
                  value={userForm.role}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">
                  {editingUserId ? "Password managed separately" : "Temporary password"}
                </span>
                <input
                  className="input-surface"
                  disabled={Boolean(editingUserId)}
                  onChange={(event) => setUserForm((current) => ({ ...current, password: event.target.value }))}
                  placeholder={editingUserId ? "Use reset password below for changes" : "At least 8 characters"}
                  type="password"
                  value={userForm.password}
                />
              </label>

              <div className="flex flex-wrap gap-3 md:col-span-2">
                <button className="primary-cta" disabled={savingUser} type="submit">
                  {savingUser ? "Saving..." : editingUserId ? "Update User" : "Create User"}
                </button>
                {editingUserId && (
                  <button className="secondary-cta" onClick={handleCancelEdit} type="button">
                    Cancel Edit
                  </button>
                )}
              </div>
            </form>

            <div className="mt-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <label className="block w-full max-w-md space-y-2">
                <span className="text-sm font-medium text-slate-700">Search users</span>
                <input
                  className="input-surface"
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Search by name, email, or role"
                  type="search"
                  value={searchTerm}
                />
              </label>
              <div className="rounded-2xl border border-[#dbe7fb] bg-[#f8fbff] px-4 py-3 text-sm text-slate-600">
                Showing {paginatedUsers.length} of {filteredUsers.length} users
              </div>
            </div>

            <div className="mt-6 overflow-hidden rounded-[24px] border border-[#dbe7fb]">
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white">
                  <thead className="bg-[#f8fbff]">
                    <tr className="text-left text-xs uppercase tracking-[0.22em] text-slate-500">
                      <th className="px-5 py-4">User</th>
                      <th className="px-5 py-4">Role</th>
                      <th className="px-5 py-4">Last login</th>
                      <th className="px-5 py-4">Reset password</th>
                      <th className="px-5 py-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedUsers.map((user) => (
                      <tr className="border-t border-slate-200 align-top" key={user._id}>
                        <td className="px-5 py-4">
                          <p className="font-semibold text-slate-900">{user.name}</p>
                          <p className="mt-1 text-sm text-slate-500">{user.email}</p>
                        </td>
                        <td className="px-5 py-4">
                          <span className="rounded-full bg-[#eff5ff] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#1d4aa8]">
                            {user.role}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-600">
                          {user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : "Not recorded"}
                        </td>
                        <td className="px-5 py-4">
                          <div className="space-y-3">
                            <input
                              className="input-surface"
                              onChange={(event) =>
                                setResetDrafts((current) => ({ ...current, [user._id]: event.target.value }))
                              }
                              placeholder="Temporary new password"
                              type="password"
                              value={resetDrafts[user._id] || ""}
                            />
                            <button
                              className="secondary-cta !w-full !justify-center"
                              onClick={() => handleResetPassword(user._id)}
                              type="button"
                            >
                              {resettingUserId === user._id ? "Resetting..." : "Reset Password"}
                            </button>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex flex-col gap-3">
                            <button className="secondary-cta !justify-center" onClick={() => handleEditUser(user)} type="button">
                              Edit
                            </button>
                            <button
                              className="rounded-full border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
                              disabled={deletingUserId === user._id || currentUser?._id === user._id}
                              onClick={() => handleDeleteUser(user._id)}
                              type="button"
                            >
                              {deletingUserId === user._id ? "Deleting..." : currentUser?._id === user._id ? "Current Admin" : "Delete"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {!loading && !paginatedUsers.length && (
                <div className="px-5 py-8 text-center text-sm text-slate-500">No users match your search.</div>
              )}
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-slate-500">
                Page {currentPage} of {totalPages}
              </p>
              <div className="flex gap-3">
                <button
                  className="secondary-cta"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                  type="button"
                >
                  Previous
                </button>
                <button
                  className="secondary-cta"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                  type="button"
                >
                  Next
                </button>
              </div>
            </div>
          </article>
        </section>

        <section className="surface-panel fade-rise">
          <div className="overflow-hidden rounded-[24px] border border-[#dbe7fb]">
            <div className="overflow-x-auto">
              <table className="min-w-full bg-white">
                <thead className="bg-[#f8fbff]">
                  <tr className="text-left text-xs uppercase tracking-[0.22em] text-slate-500">
                    <th className="px-5 py-4">Company</th>
                    <th className="px-5 py-4">Date</th>
                    <th className="px-5 py-4">Prices</th>
                    <th className="px-5 py-4">Volume</th>
                    <th className="px-5 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedRecords.map((stock) => (
                    <tr className="border-t border-slate-200 align-top" key={stock._id}>
                      <td className="px-5 py-4">
                        <p className="font-semibold text-slate-900">{stock.companyName}</p>
                        <p className="mt-1 text-sm text-slate-500">{stock.symbol}</p>
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-600">{new Date(stock.tradeDate).toLocaleDateString()}</td>
                      <td className="px-5 py-4 text-sm text-slate-600">
                        O: {stock.open} | H: {stock.high} | L: {stock.low} | C: {stock.close}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-600">{stock.volume}</td>
                      <td className="px-5 py-4">
                        <div className="flex flex-col gap-3">
                          <button className="secondary-cta !justify-center" onClick={() => handleEditRecord(stock)} type="button">
                            Edit
                          </button>
                          <button
                            className="rounded-full border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
                            disabled={deletingRecordId === stock._id}
                            onClick={() => handleDeleteRecord(stock._id)}
                            type="button"
                          >
                            {deletingRecordId === stock._id ? "Deleting..." : "Delete"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {!loading && !paginatedRecords.length && (
              <div className="px-5 py-8 text-center text-sm text-slate-500">No stock records match your search.</div>
            )}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-500">
              Page {recordPage} of {totalRecordPages}
            </p>
            <div className="flex gap-3">
              <button
                className="secondary-cta"
                disabled={recordPage === 1}
                onClick={() => setRecordPage((page) => Math.max(1, page - 1))}
                type="button"
              >
                Previous
              </button>
              <button
                className="secondary-cta"
                disabled={recordPage === totalRecordPages}
                onClick={() => setRecordPage((page) => Math.min(totalRecordPages, page + 1))}
                type="button"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default AdminDashboardPage;
