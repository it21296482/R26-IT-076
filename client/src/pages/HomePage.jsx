import { Link } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";

const flowSteps = [
  {
    title: "Select stock",
    text: "Choose a listed company to begin a focused market review.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M4 7h16M4 12h10M4 17h16" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    title: "Upload report",
    text: "Add the latest report if you want deeper company-level understanding.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M12 16V4m0 0 4 4m-4-4L8 8M5 20h14" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    title: "System analyzes",
    text: "The platform combines market behavior, reports, and external signals automatically.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M5 17 9 9l4 5 6-8" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="5" cy="17" r="1.3" fill="currentColor" stroke="none" />
        <circle cx="9" cy="9" r="1.3" fill="currentColor" stroke="none" />
        <circle cx="13" cy="14" r="1.3" fill="currentColor" stroke="none" />
        <circle cx="19" cy="6" r="1.3" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    title: "View insights",
    text: "Receive clear explanations designed to support decisions without overwhelming detail.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M3 12c2.4-4 5.4-6 9-6s6.6 2 9 6c-2.4 4-5.4 6-9 6s-6.6-2-9-6Z" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="2.7" />
      </svg>
    ),
  },
];

const noveltyCards = [
  {
    color: "from-sky-400/30 to-sky-500/8",
    border: "border-sky-400/25",
    title: "Market behavior understanding",
    description: "Analyzes market patterns to identify meaningful changes and risk signals.",
    novelty: [
      "Goes beyond simple trends and explains what changed",
      "Connects multiple influencing factors",
      "Detects unusual market behavior automatically",
    ],
    value: "Understand what is happening in the market clearly",
  },
  {
    color: "from-emerald-400/30 to-emerald-500/8",
    border: "border-emerald-400/25",
    title: "Financial information simplification",
    description: "Converts complex financial reports into structured and understandable insights.",
    novelty: [
      "Transforms unstructured financial data into clear outputs",
      "Removes complexity of traditional financial analysis",
      "Focuses only on decision-relevant information",
    ],
    value: "Understand company performance without reading full reports",
  },
  {
    color: "from-amber-400/30 to-amber-500/8",
    border: "border-amber-400/25",
    title: "Contextual market awareness",
    description: "Captures external signals and contextual factors that influence market behavior.",
    novelty: [
      "Integrates external influences into market analysis",
      "Adds real-world context beyond charts",
      "Explains what is impacting the market environment",
    ],
    value: "Know what is driving market movements",
  },
  {
    color: "from-rose-400/30 to-rose-500/8",
    border: "border-rose-400/25",
    title: "Human-centered insight delivery",
    description:
      "Transforms complex system outputs into understandable insights using multiple explanation approaches and continuous refinement.",
    novelty: [
      "Presents the same insight in multiple explanation formats",
      "Measures actual understanding, not just usability",
      "Continuously improves based on interaction and comprehension",
    ],
    value: "Not just seeing data, actually understanding it",
  },
];

const dashboardPreview = [
  { label: "Trend chart", value: "Momentum strengthening", tone: "bg-sky-400/15 text-sky-200" },
  { label: "Anomaly highlight", value: "Unusual price movement detected", tone: "bg-amber-400/15 text-amber-200" },
  { label: "Explanation panel", value: "Confidence weakened after external pressure", tone: "bg-emerald-400/15 text-emerald-200" },
  { label: "Risk indicator", value: "Elevated short-term uncertainty", tone: "bg-rose-400/15 text-rose-200" },
];

function HomePage() {
  return (
    <div className="min-h-screen pb-16">
      <SiteHeader />

      <main className="shell space-y-24">
        <section className="grid items-center gap-10 pt-6 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-8">
            <div className="fade-rise space-y-5">
              <p className="eyebrow">AI Powered Stock Market Insight Generator for the Colombo Stock Exchange</p>
              <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-white md:text-7xl">
                Understand why the market moves — not just what happened.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-300 md:text-xl">
                Analyze stocks, reports, and market signals in one place and get clear, easy-to-understand insights.
              </p>
            </div>

            <div className="fade-rise-delay-1 flex flex-wrap gap-4">
              <Link className="primary-cta" to="/login">
                Start Analysis
              </Link>
              <a className="secondary-cta" href="#dashboard-preview">
                View Demo
              </a>
            </div>

            <div className="fade-rise-delay-2 grid gap-4 sm:grid-cols-3">
              {[
                ["Clarity first", "Designed for fast understanding"],
                ["Simple language", "Built for non-expert investors"],
                ["Decision support", "Guides insight, not information overload"],
              ].map(([title, text]) => (
                <div className="glass-card rounded-[24px] p-5" key={title}>
                  <p className="text-lg font-semibold text-white">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{text}</p>
                  <div className="panel-line mt-4" />
                </div>
              ))}
            </div>
          </div>

          <div className="fade-rise-delay-3 relative min-h-[560px] overflow-visible">
            <div className="chart-grid dark-card relative h-full overflow-visible p-6">
              <div className="trend-path absolute left-6 right-6 top-20 h-44 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
              <div className="relative mx-auto w-full max-w-[calc(100%-5rem)] overflow-hidden rounded-[30px] border border-white/10 shadow-[0_30px_80px_rgba(2,12,20,0.34)]">
                <img alt="Stock market trend chart" className="h-full w-full object-cover opacity-90" src="/assets/WhatIsVolumeofaStock-12741bcb2f4348b1a7b684ddc1a6e1d7.jpg" />
              </div>
              <div className="absolute bottom-8 left-8 right-8 rounded-[26px] border border-white/10 bg-slate-950/78 p-5 backdrop-blur-xl">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                  From complex data to clear understanding
                </p>
                <p className="mt-3 text-2xl font-semibold text-white">One intelligent view for stock behavior, reports, and market signals.</p>
                <div className="mt-4 flex items-center gap-4 rounded-2xl bg-white/5 px-4 py-3 text-sm text-slate-300">
                  <img alt="Bull and bear market" className="h-14 w-20 rounded-xl object-cover" src="/assets/360_F_754695855_hkDMu3QQ8Yu1kQZbyHHwgokSpmkXqqff.jpg" />
                  <span>Clarity over complexity. Meaning over raw numbers.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-8 fade-rise">
          <div className="max-w-2xl space-y-4">
            <p className="eyebrow !text-slate-500">Simple user flow</p>
            <h2 className="section-title">Clear steps from input to insight</h2>
            <p className="section-copy">
              The platform guides users through a short, understandable flow so they know exactly what to do next.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            {flowSteps.map((step, index) => (
              <div className="light-card relative p-6 fade-rise" key={step.title} style={{ animationDelay: `${index * 0.08}s` }}>
                <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-sky-200">
                  {step.icon}
                </div>
                <h3 className="text-xl font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{step.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-8 fade-rise">
          <div className="max-w-3xl space-y-4">
            <p className="eyebrow !text-slate-500">What makes this system different</p>
            <h2 className="section-title">Designed to transform complex financial data into clear, understandable insights</h2>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            {noveltyCards.map((card, index) => (
              <article
                className={`relative overflow-hidden rounded-[30px] border ${card.border} bg-gradient-to-br ${card.color} p-7 shadow-[0_22px_70px_rgba(15,23,42,0.08)] backdrop-blur-sm fade-rise`}
                key={card.title}
                style={{ animationDelay: `${index * 0.08}s` }}
              >
                <div className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-emerald-300 via-sky-300 to-amber-300" />
                <h3 className="text-2xl font-semibold text-slate-900">{card.title}</h3>
                <p className="mt-3 text-base leading-8 text-slate-700">{card.description}</p>
                <div className="mt-6 space-y-3">
                  {card.novelty.map((point) => (
                    <div className="flex gap-3" key={point}>
                      <span className="mt-2 h-2.5 w-2.5 rounded-full bg-slate-900" />
                      <p className="text-sm leading-7 text-slate-700">{point}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-6 rounded-2xl bg-slate-900/85 px-4 py-4 text-sm leading-7 text-slate-100">
                  <span className="block text-xs font-semibold uppercase tracking-[0.24em] text-amber-300">User value</span>
                  <span className="mt-2 block">{card.value}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="light-card p-8 fade-rise">
            <p className="eyebrow !text-slate-500">From complex data to clear understanding</p>
            <div className="mt-6 space-y-5">
              <div className="rounded-[22px] border border-slate-200 bg-slate-50 px-5 py-5">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Before</span>
                <p className="mt-3 text-lg leading-8 text-slate-700">
                  Market volatility increased due to multiple interacting variables.
                </p>
              </div>
              <div className="rounded-[22px] border border-emerald-200 bg-emerald-50 px-5 py-5">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-600">After</span>
                <p className="mt-3 text-lg leading-8 text-slate-800">
                  Prices changed because external conflict reduced investor confidence.
                </p>
              </div>
            </div>
          </div>

          <div className="dark-card relative overflow-hidden p-8 text-white fade-rise-delay-1">
            <div className="chart-grid absolute inset-0 opacity-30" />
            <div className="trend-path absolute left-8 right-8 top-14 h-32 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
            <div className="relative z-10">
              <p className="eyebrow">Built for understanding, not complexity</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-tight">A decision-support product, not a data display.</h2>
              <div className="mt-8 grid gap-4 md:grid-cols-2">
                {[
                  "Not just charts",
                  "Not just raw financial data",
                  "Clear explanations",
                  "Context-aware insights",
                  "Unified system",
                  "Designed for non-expert investors",
                ].map((item, index) => (
                  <div
                    className={`rounded-2xl border px-4 py-4 text-sm leading-7 ${
                      index < 2 ? "border-white/10 bg-white/6 text-slate-300" : "border-emerald-300/18 bg-emerald-300/8 text-white"
                    }`}
                    key={item}
                  >
                    {index < 2 ? "✕ " : "✓ "}
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr]" id="dashboard-preview">
          <div className="space-y-4 fade-rise">
            <p className="eyebrow !text-slate-500">Dashboard preview</p>
            <h2 className="section-title">Clarity over detail</h2>
            <p className="section-copy">
              The dashboard is organized to guide understanding first: highlight direction, signal unusual behavior,
              explain meaning, and show risk in a simple way.
            </p>
          </div>

          <div className="dark-card chart-grid relative overflow-hidden p-6 fade-rise-delay-1">
            <div className="trend-path absolute left-6 right-6 top-10 h-28 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
            <div className="relative z-10 grid gap-4">
              <div className="overflow-hidden rounded-[24px] border border-white/10">
                <img alt="Investor dashboard preview" className="h-56 w-full object-cover opacity-90" src="/assets/Blogs_Paytm_Bond-Market-vs.-Stock-Market_-Whats-the-Difference_-1.jpg" />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {dashboardPreview.map((item) => (
                  <div className={`rounded-2xl border border-white/10 ${item.tone} p-4`} key={item.label}>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em]">{item.label}</p>
                    <p className="mt-2 text-base font-medium text-white">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default HomePage;
