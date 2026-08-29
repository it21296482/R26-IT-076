import { Link } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";

const differenceCards = [
  {
    code: "01",
    title: "Market behaviour understanding",
    description: "Recognizes meaningful price changes, unusual movement, and risk signals.",
    points: ["Explains what changed", "Connects related market factors", "Flags unusual behaviour"],
    value: "Understand what is happening in the market.",
  },
  {
    code: "02",
    title: "Financial information simplification",
    description: "Turns a dense company report into structured, understandable takeaways.",
    points: ["Removes report complexity", "Highlights decision-relevant facts", "Keeps source evidence visible"],
    value: "Understand company performance without reading every page.",
  },
  {
    code: "03",
    title: "Contextual market awareness",
    description: "Adds relevant company, local-market, and wider economic context.",
    points: ["Connects current events", "Adds context beyond charts", "Separates association from cause"],
    value: "See what may be influencing the market environment.",
  },
  {
    code: "04",
    title: "Human-centred insight delivery",
    description: "Presents the complete picture in clear language, with risk and uncertainty beside it.",
    points: ["More than a static chart", "Designed for different ways of understanding", "Focused on comprehension"],
    value: "Do not just see the data. Understand what it means.",
  },
];

const workflowSteps = [
  ["01", "Select stock", "Choose a supported Colombo Stock Exchange company."],
  ["02", "Upload report", "Attach the company's latest quarterly or annual PDF report."],
  ["03", "Analyze", "Let the system connect the available market, report, and event evidence."],
  ["04", "View insights", "Read one clear picture of potential, risk, context, and uncertainty."],
];

function HomePage() {
  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader />

      <main className="shell space-y-10 pb-8">
        <section className="market-hero relative overflow-hidden p-6 fade-rise md:p-10 lg:p-12">
          <div className="market-orb absolute -right-24 -top-28 h-80 w-80 opacity-65" />
          <div className="relative z-10 grid gap-9 lg:grid-cols-[1.02fr_0.98fr] lg:items-center">
            <div>
              <p className="eyebrow !text-blue-100">Designed for Colombo Stock Exchange investors</p>
              <h1 className="mt-5 max-w-4xl text-5xl font-semibold tracking-tight text-white md:text-7xl">
                Understand why the market moves, not just what happened.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 md:text-xl">
                Analyze stocks, reports, and market signals in one place and get clear, easy-to-understand insights.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link className="rounded-full bg-amber-400 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-300" to="/login">
                  Start Analysis
                </Link>
                <a className="rounded-full border border-white/20 bg-white/8 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/12" href="#preview">
                  View Demo
                </a>
              </div>
              <div className="mt-9 grid gap-3 sm:grid-cols-3">
                {["Plain language", "CSE focused", "Risk made visible"].map((label) => (
                  <div className="rounded-[20px] border border-white/10 bg-white/8 px-4 py-4 text-sm font-semibold text-slate-200" key={label}>{label}</div>
                ))}
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-[620px] overflow-visible">
              <div className="overflow-hidden rounded-[32px] border border-white/12 bg-white/8 p-3 shadow-[0_30px_90px_rgba(2,8,23,0.38)]">
                <img alt="Investor reviewing market trends" className="h-full min-h-[440px] w-full rounded-[24px] object-cover" src="/assets/How+to+Negotiate+a+Financial+Analyst+Salary.webp" />
              </div>
              <div className="absolute -bottom-5 left-5 right-5 rounded-[24px] border border-white/12 bg-slate-950/90 p-5 backdrop-blur-xl md:left-auto md:right-[-18px] md:w-[78%]">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200">One guided path</p>
                <p className="mt-2 text-sm font-semibold leading-6 text-white">Choose a company → attach its report → analyze → understand the complete picture</p>
              </div>
            </div>
          </div>
        </section>

        <section className="surface-panel fade-rise">
          <div className="max-w-3xl">
            <p className="eyebrow">A simple four-step flow</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">From company selection to clear understanding.</h2>
          </div>
          <div className="mt-8 grid gap-4 lg:grid-cols-4">
            {workflowSteps.map(([code, title, text]) => (
              <article className="interactive-card rounded-[24px] border border-slate-200 bg-slate-50 p-5" key={code}>
                <p className="text-xs font-semibold text-blue-700">{code}</p>
                <h3 className="mt-4 text-xl font-semibold text-slate-950">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="surface-panel fade-rise">
          <div className="max-w-4xl">
            <p className="eyebrow">What makes this system different</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">Designed to transform complex financial data into clear, understandable insights.</h2>
          </div>
          <div className="mt-8 grid gap-5 lg:grid-cols-2">
            {differenceCards.map((card) => (
              <article className="interactive-card rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_16px_50px_rgba(15,23,42,0.06)]" key={card.code}>
                <div className="flex items-start justify-between gap-4"><p className="text-xs font-semibold tracking-[0.2em] text-blue-700">{card.code}</p><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">Equal focus</span></div>
                <h3 className="mt-5 text-2xl font-semibold text-slate-950">{card.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{card.description}</p>
                <div className="mt-5 grid gap-2">{card.points.map((point) => <p className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700" key={point}>{point}</p>)}</div>
                <p className="mt-5 border-t border-slate-200 pt-5 text-sm font-semibold text-blue-800">{card.value}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <article className="surface-panel fade-rise">
            <p className="eyebrow">From complex data to clear understanding</p>
            <div className="mt-6 grid gap-4">
              <div className="rounded-[24px] border border-rose-100 bg-rose-50 p-5"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700">Before</p><p className="mt-3 text-base leading-7 text-rose-950">Market volatility increased due to multiple interacting variables.</p></div>
              <div className="rounded-[24px] border border-emerald-100 bg-emerald-50 p-5"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">After</p><p className="mt-3 text-base leading-7 text-emerald-950">Prices became less stable while conflict-related news lowered investor confidence. The evidence shows a relationship, but not proof that the event alone caused the move.</p></div>
            </div>
          </article>

          <article className="surface-panel fade-rise-delay-1">
            <p className="eyebrow">Built for understanding, not complexity</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Less noise. More meaning.</h2>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {["Not just charts", "Not just raw figures", "Clear explanations", "Context-aware insights", "One connected view", "Designed for non-experts"].map((item, index) => (
                <div className={`rounded-[20px] p-4 text-sm font-semibold ${index < 2 ? "bg-slate-100 text-slate-500" : "bg-blue-50 text-blue-900"}`} key={item}>{index < 2 ? "Not " : ""}{item.replace("Not ", "")}</div>
              ))}
            </div>
          </article>
        </section>

        <section className="market-hero p-6 fade-rise md:p-9" id="preview">
          <div className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:items-center">
            <div>
              <p className="eyebrow !text-blue-100">Dashboard preview</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-tight text-white">Clarity over detail.</h2>
              <p className="mt-4 text-base leading-8 text-slate-300">The result brings the price path, unusual movement, report takeaways, outside context, risk, and uncertainty into one readable view.</p>
              <Link className="mt-7 inline-flex rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950" to="/register">Create free account</Link>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-[24px] border border-white/10 bg-white/8 p-5 sm:col-span-2"><p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Trend view</p><svg className="mt-4 h-auto w-full" viewBox="0 0 620 150"><polyline fill="none" points="20,115 105,95 190,103 275,62 360,76 445,45 600,58" stroke="#67e8f9" strokeLinecap="round" strokeLinejoin="round" strokeWidth="6" /></svg></div>
              <div className="rounded-[24px] border border-amber-300/20 bg-amber-300/10 p-5"><p className="text-xs uppercase tracking-[0.18em] text-amber-200">Unusual movement</p><p className="mt-3 text-sm leading-7 text-slate-200">Expected and actual prices are compared with a clear deviation signal.</p></div>
              <div className="rounded-[24px] border border-rose-300/20 bg-rose-300/10 p-5"><p className="text-xs uppercase tracking-[0.18em] text-rose-200">Risk and uncertainty</p><p className="mt-3 text-sm leading-7 text-slate-200">Limitations stay next to the insight instead of being hidden.</p></div>
              <div className="rounded-[24px] border border-white/10 bg-white/8 p-5 sm:col-span-2"><p className="text-xs uppercase tracking-[0.18em] text-blue-100">Plain-language explanation</p><p className="mt-3 text-base leading-7 text-white">See what the current evidence suggests, what may be influencing it, and what could change the picture.</p></div>
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-14"><section className="footer-shell"><div className="shell py-5 text-center text-sm text-white/65">Copyright © 2026 CSE Insight Generator. All rights reserved.</div></section></footer>
    </div>
  );
}

export default HomePage;
