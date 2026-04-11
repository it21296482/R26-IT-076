import SiteHeader from "./SiteHeader";

function AuthShell({ title, subtitle, children, mode = "user", footer }) {
  const isAdmin = mode === "admin";
  const visualImage = isAdmin
    ? "/assets/rTh56Sw5YjFvpW8SF5pJvV.jpg"
    : "/assets/360_F_754695855_hkDMu3QQ8Yu1kQZbyHHwgokSpmkXqqff.jpg";

  return (
    <div className="min-h-screen pb-10">
      <SiteHeader compact />

      <main className="shell grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section
          className="dark-card chart-grid relative overflow-hidden p-8 fade-rise"
          style={{
            backgroundImage: `linear-gradient(180deg, rgba(7,19,31,0.26), rgba(7,19,31,0.92)), url(${visualImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        >
          <div className="trend-path absolute left-6 right-6 top-28 h-36 bg-gradient-to-r from-emerald-300/80 via-sky-300/90 to-amber-300/80 blur-[1px]" />
          <div className="relative z-10 flex min-h-[620px] flex-col justify-end">
            <div className="max-w-xl space-y-5">
              <p className="eyebrow">{isAdmin ? "Restricted Access" : "Secure Account Access"}</p>
              <h1 className="text-5xl font-semibold tracking-tight text-white md:text-6xl">{title}</h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-200">{subtitle}</p>
              <div className="grid gap-4 pt-4 sm:grid-cols-2">
                <div className="glass-card rounded-[24px] p-5">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-200">Market-aware flow</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-200">
                    Built around stock selection, report upload, and clear investor understanding.
                  </p>
                </div>
                <div className="glass-card rounded-[24px] p-5">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-200">Clear guidance</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-200">
                    Designed to simplify financial complexity instead of increasing cognitive load.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="light-card fade-rise-delay-1 p-8 md:p-10">
          <div className="mx-auto flex min-h-[620px] max-w-md flex-col justify-center">
            {children}
            {footer && <div className="mt-6 text-sm text-slate-500">{footer}</div>}
          </div>
        </section>
      </main>
    </div>
  );
}

export default AuthShell;
