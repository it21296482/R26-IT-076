import SiteHeader from "./SiteHeader";

function AuthShell({ title, subtitle, children, mode = "user", footer }) {
  const isAdmin = mode === "admin";
  const visualImage = isAdmin
    ? "/assets/cse-trading-floor.jpg"
    : "/assets/1772533178-Colombo-Stock-Exchange-CSE-Sri-Lanka-6.jpg";

  return (
    <div className="page-with-sticky-header min-h-screen pb-10">
      <SiteHeader compact />

      <main className="shell grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section
          className="market-hero relative overflow-hidden p-8 fade-rise"
          style={{
            backgroundImage: `linear-gradient(180deg, rgba(7,26,69,0.30), rgba(7,26,69,0.92)), url(${visualImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        >
          <div className="market-orb absolute -right-20 top-10 h-56 w-56 opacity-70" />
          <div className="market-orb absolute -left-12 bottom-12 h-32 w-32 opacity-40" />
          <div className="relative z-10 flex min-h-[620px] flex-col justify-end">
            <div className="max-w-xl space-y-5">
              <p className="eyebrow !text-blue-100">{isAdmin ? "Restricted Access" : "Secure Account Access"}</p>
              <h1 className="text-5xl font-semibold tracking-tight text-white md:text-6xl">{title}</h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-200">{subtitle}</p>
              <div className="grid gap-4 pt-4 sm:grid-cols-2">
                <div className="glass-card rounded-[24px] p-5">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-blue-100">Market-aware flow</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-200">
                    Built around stock selection, report upload, and clear investor understanding.
                  </p>
                </div>
                <div className="glass-card rounded-[24px] p-5">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-blue-100">Clear guidance</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-200">
                    Designed to simplify financial complexity instead of increasing cognitive load.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="light-card fade-rise-delay-1 border border-slate-200/80 bg-white p-8 md:p-10">
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
