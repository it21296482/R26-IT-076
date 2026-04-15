import { Link } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";

const featureCards = [
  {
    title: "Trend Detection",
    text: "Identifies meaningful direction changes, momentum shifts, and unusual movement across CSE-listed companies.",
  },
  {
    title: "Explainable AI",
    text: "Converts model outputs into plain-language reasoning, feature contribution cues, and confidence signals.",
  },
  {
    title: "Report Analysis",
    text: "Transforms annual reports and dense financial disclosures into structured investor summaries.",
  },
  {
    title: "Sentiment Pulse",
    text: "Bring in market signals, external events, and sentiment context to explain why movement happened.",
  },
];

const workflowSteps = [
  "Choose a listed company from the CSE universe.",
  "Upload the latest financial report for deeper company context.",
  "Review trend, risk, and explanation panels in one guided workspace.",
  "Understand the market with less noise and more reasoning.",
];

const marketStats = [
  ["CSE Focus", "Sri Lankan market-first investor experience"],
  ["AI Modules", "Trend, reports, sentiment, and explainability"],
  ["Investor Style", "Designed for beginners and retail decision-makers"],
];

const researchOverviewCards = [
  {
    title: "Problem",
    text: "Retail investors often struggle to understand stock trends, financial reports, news sentiment, and risk signals.",
  },
  {
    title: "Approach",
    text: "The platform combines machine learning, explainable AI, financial document understanding, and sentiment/event analysis.",
  },
  {
    title: "Outcome",
    text: "The system generates clear, interpretable insights that support better market understanding and confident decisions.",
  },
];

const researchGaps = [
  "Existing platforms mainly present price charts, tables, and technical indicators.",
  "Many AI prediction systems provide limited reasoning behind their outputs.",
  "Financial reports, sentiment, events, and historical data are often analyzed separately.",
  "Investor understanding and cognitive load are rarely evaluated in stock insight tools.",
];

const frameworkSteps = [
  "CSE market data",
  "ML trend analysis",
  "Anomaly detection",
  "XAI explanation",
  "Report understanding",
  "Sentiment and events",
  "Insight dashboard",
];

const systemComponents = [
  {
    title: "Market Modeling and XAI",
    text: "Detects trends, unusual movements, volatility behavior, and explains contributing market factors.",
  },
  {
    title: "Financial Document Understanding",
    text: "Extracts company-level indicators and simplifies complex annual report information.",
  },
  {
    title: "Sentiment and Event Analysis",
    text: "Analyzes financial news, announcements, and external signals that influence investor behavior.",
  },
  {
    title: "Insight Visualization",
    text: "Presents outputs through an interpretable dashboard focused on trust, clarity, and user understanding.",
  },
];

const evaluationItems = [
  ["Model metrics", "Accuracy, precision, recall, F1-score, and anomaly detection quality."],
  ["Usability", "SUS and task completion measure how easily investors use the platform."],
  ["Comprehension", "FICS checks whether users understand generated financial insights."],
  ["Cognitive load", "NASA-TLX evaluates mental workload while interpreting AI outputs."],
];

const contributionItems = [
  "CSE-focused AI insight generation for local retail investors.",
  "Fusion of structured market data and unstructured financial information.",
  "Explainable AI outputs designed for beginner-friendly investor understanding.",
  "Human-centered evaluation of usability, comprehension, and trust.",
];

function HomePage() {
  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader />

      <main className="shell space-y-10 pb-6">
        <section className="grid gap-8 pt-6 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-8 fade-rise">
            <div className="space-y-5">
              <span className="brand-badge">AI-Powered Stock Insight Platform for the Colombo Stock Exchange</span>
              <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-slate-950 md:text-7xl">
                AI powered market intelligence, built around the CSE.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-600 md:text-xl">
                A modern investor workspace that combines market trends, explainable AI, financial report reasoning,
                and sentiment signals into one realistic decision-support experience.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Link className="primary-cta" to="/register">
                Get started free
              </Link>
              <Link className="secondary-cta" to="/login">
                View demo workspace
              </Link>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {marketStats.map(([label, text]) => (
                <div className="metric-card p-5" key={label}>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#1d4aa8]">{label}</p>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="fade-rise-delay-1">
            <div className="hero-shell p-5">
              <div className="relative overflow-hidden rounded-[28px] border border-[#d5e4ff] bg-[#081b49] p-5 text-white shadow-[0_24px_60px_rgba(8,27,73,0.26)]">
                <div className="market-orb absolute -right-16 -top-16 h-52 w-52 opacity-75" />
                <div className="market-orb absolute -bottom-12 -left-10 h-36 w-36 opacity-45" />
                <div className="relative z-10 space-y-5">
                  <div className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/8 px-4 py-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-blue-100/75">Live market intelligence</p>
                      <p className="mt-1 text-xl font-semibold">CSE Portfolio Command View</p>
                    </div>
                    <div className="rounded-full bg-emerald-400/18 px-3 py-1 text-xs font-semibold text-emerald-200">
                      Confidence 89.4%
                    </div>
                  </div>

                  <img
                    alt="Colombo Stock Exchange trading floor"
                    className="h-64 w-full rounded-[24px] object-cover"
                    src="/assets/cse-trading-floor.jpg"
                  />

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-[22px] border border-white/10 bg-white/8 p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-blue-100/75">Anomaly alert</p>
                      <p className="mt-2 text-sm leading-7 text-slate-200">
                        Volume spike detected against the weekly baseline. Explanation panel highlights likely pressure
                        factors.
                      </p>
                    </div>
                    <div className="rounded-[22px] border border-white/10 bg-white/8 p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-blue-100/75">Insight stack</p>
                      <p className="mt-2 text-sm leading-7 text-slate-200">
                        Trends, financial disclosures, risk markers, and market sentiment appear in one connected view.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="surface-panel fade-rise">
          <div className="grid gap-8 lg:grid-cols-[0.72fr_0.28fr] lg:items-center">
            <div className="max-w-3xl space-y-3">
              <p className="eyebrow">Key capabilities</p>
              <h2 className="section-title max-w-4xl">Financial intelligence, explained through four core capabilities.</h2>
              <p className="section-copy">
                The platform brings together technical signals, explanation support, company report understanding, and
                market context so investors can move from raw data to clearer reasoning.
              </p>
            </div>
            <div className="hidden rounded-[26px] border border-[#dbe7fb] bg-[#f8fbff] p-6 lg:block">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#1d4aa8]">Focus</p>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                Explainable AI, sentiment analysis, report intelligence, and investor-focused visualization.
              </p>
            </div>
          </div>

          <div className="mt-8 grid gap-4 xl:grid-cols-4">
            {featureCards.map((card) => (
              <article className="interactive-card metric-card p-5" key={card.title}>
                <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-[#eaf1ff] text-[#1d4aa8]">
                  <span className="text-lg font-semibold">{card.title[0]}</span>
                </div>
                <h3 className="text-lg font-semibold text-slate-900">{card.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{card.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="surface-panel fade-rise">
          <div className="grid gap-8 lg:grid-cols-[0.78fr_0.22fr] lg:items-center">
            <div className="max-w-3xl space-y-4">
              <p className="eyebrow">Platform overview</p>
              <h2 className="section-title max-w-4xl">An explainable AI platform for smarter CSE market understanding.</h2>
              <p className="section-copy max-w-3xl">
                We are building an AI-powered stock market insight platform for the Colombo Stock Exchange that helps
                retail investors understand market behavior through clear, interpretable insights instead of only raw
                charts and numerical indicators.
              </p>
            </div>
            <div className="hidden rounded-[26px] border border-[#dbe7fb] bg-[#f8fbff] p-6 lg:block">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#1d4aa8]">CSE-ready</p>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                Designed around local market data, investor needs, and explainable insight delivery.
              </p>
            </div>
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {researchOverviewCards.map((card) => (
              <article className="interactive-card metric-card p-6" key={card.title}>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#1d4aa8]">{card.title}</p>
                <p className="mt-4 text-sm leading-7 text-slate-600">{card.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.92fr_1.08fr]">
          <article className="surface-panel fade-rise">
            <p className="eyebrow">Why this platform is needed</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              CSE investors need insight that explains market behavior.
            </h2>
            <p className="mt-4 text-base leading-8 text-slate-600">
              Retail investors often face difficulty interpreting stock movements because price trends, financial
              reports, market sentiment, and external events are complex. This platform reduces that complexity by
              converting multiple financial signals into clear explanations.
            </p>
          </article>

          <article className="surface-panel fade-rise-delay-1">
            <p className="eyebrow">Gap in existing platforms</p>
            <div className="mt-5 grid gap-3">
              {researchGaps.map((gap) => (
                <div className="rounded-2xl border border-[#dbe7fb] bg-[#f8fbff] px-4 py-4 text-sm leading-7 text-slate-600" key={gap}>
                  {gap}
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="surface-panel fade-rise">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="eyebrow">Proposed AI-powered framework</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
                A multi-source pipeline from market data to interpretable insight.
              </h2>
            </div>
            <p className="max-w-md text-sm leading-7 text-slate-600">
              The framework combines <strong>market modeling</strong>, <strong>document intelligence</strong>,{" "}
              <strong>sentiment analysis</strong>, and <strong>visualization</strong> into a single investor-facing workflow.
            </p>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-7">
            {frameworkSteps.map((step, index) => (
              <div className="pipeline-step interactive-card" key={step}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{step}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="surface-panel fade-rise">
          <div className="max-w-3xl">
            <p className="eyebrow">System components</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              Four connected modules support the complete insight experience.
            </h2>
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-2">
            {systemComponents.map((component) => (
              <article className="interactive-card research-card" key={component.title}>
                <h3 className="text-xl font-semibold text-slate-950">{component.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{component.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <article className="surface-panel fade-rise">
            <p className="eyebrow">Evaluation strategy</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              The platform is evaluated for both technical quality and user understanding.
            </h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {evaluationItems.map(([title, text]) => (
                <div className="interactive-card metric-card p-5" key={title}>
                  <p className="font-semibold text-slate-950">{title}</p>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="market-hero relative overflow-hidden p-8 text-white fade-rise-delay-1">
            <div className="market-orb absolute right-0 bottom-0 h-52 w-52 opacity-75" />
            <div className="relative z-10">
              <p className="eyebrow !text-blue-100">Expected contribution</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">Explainable insight for responsible investing.</h2>
              <div className="mt-6 space-y-3">
                {contributionItems.map((item) => (
                  <p className="rounded-2xl border border-white/10 bg-white/8 px-4 py-4 text-sm leading-7 text-slate-200" key={item}>
                    {item}
                  </p>
                ))}
              </div>
            </div>
          </article>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <article className="surface-panel fade-rise">
            <p className="eyebrow">Workflow</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Your portfolio’s new commanding view</h2>
            <div className="mt-6 space-y-4">
              {workflowSteps.map((step, index) => (
                <div className="interactive-card flex gap-4 rounded-[22px] border border-slate-200 bg-white px-4 py-4" key={step}>
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#1d4aa8] text-sm font-semibold text-white">
                    0{index + 1}
                  </div>
                  <p className="text-sm leading-7 text-slate-600">{step}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="market-hero relative overflow-hidden p-8 text-white fade-rise-delay-1">
            <div className="market-orb absolute right-0 top-0 h-56 w-56 opacity-80" />
            <div className="relative z-10 grid gap-4 md:grid-cols-2">
              <div className="rounded-[24px] border border-white/10 bg-white/8 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-blue-100/75">Trend score</p>
                <p className="mt-3 text-4xl font-semibold">+12.4%</p>
                <p className="mt-2 text-sm text-slate-200">Momentum strengthened after sector-wide accumulation.</p>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-white/8 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-blue-100/75">Risk watch</p>
                <p className="mt-3 text-4xl font-semibold">Moderate</p>
                <p className="mt-2 text-sm text-slate-200">Short-term volatility is elevated, but explainable by event context.</p>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-white/8 p-5 md:col-span-2">
                <p className="text-xs uppercase tracking-[0.22em] text-blue-100/75">Why it moved</p>
                <p className="mt-3 text-lg leading-8 text-slate-100">
                  The platform merges structured market records, report intelligence, and sentiment cues so users see
                  both the signal and the reason behind it.
                </p>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-white/8 p-5 md:col-span-2">
                <p className="text-xs uppercase tracking-[0.22em] text-blue-100/75">Insight confidence</p>
                <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full w-[82%] rounded-full bg-gradient-to-r from-emerald-300 to-sky-300" />
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {["Report signal", "Sentiment context", "Market anomaly"].map((label) => (
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 px-4 py-3 text-sm text-slate-200" key={label}>
                      {label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>
        </section>

        <section className="cta-band fade-rise">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-100/80">Ready to outpace the market?</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">
              Start your AI-powered investment journey with a more realistic CSE workflow.
            </h2>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-white px-6 py-3 text-sm font-semibold text-[#081b49] transition hover:bg-slate-100" to="/register">
              Create free account
            </Link>
            <Link className="rounded-full border border-white/20 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/8" to="/login">
              Sign in
            </Link>
          </div>
        </section>
      </main>

      <footer className="mt-14">
        <section className="footer-shell">
          <div className="shell py-5">
            <div className="text-center text-sm text-white/65">
              Copyright © 2026 CSE Insight Generator. All rights reserved. Terms & Conditions.
            </div>
          </div>
        </section>
      </footer>
    </div>
  );
}

export default HomePage;
