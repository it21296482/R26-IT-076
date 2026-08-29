import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Link,
  useSearchParams,
} from "react-router-dom";

import SiteHeader from "../components/SiteHeader";
import api from "../lib/api";

const ANIM = `
  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(14px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes barGrow {
    from {
      width: 0%;
    }
  }

  .au {
    opacity: 0;
    animation: fadeUp .42s cubic-bezier(.22,1,.36,1) forwards;
  }

  .chov {
    transition:
      box-shadow .18s ease,
      transform .18s ease;
  }

  .chov:hover {
    transform: translateY(-2px);
    box-shadow:
      0 6px 24px rgba(0,0,0,.07);
  }

  .phov {
    transition: opacity .15s ease;
  }

  .phov:hover {
    opacity: .75;
  }

  .bar {
    animation:
      barGrow .85s cubic-bezier(.22,1,.36,1)
      forwards;
  }
`;

const S = {
  positive: {
    pill:
      "bg-[#EAF3DE] text-[#27500A] border border-[#C0DD97]",
    score:
      "text-[#3B6D11]",
    bar:
      "#639922",
    track:
      "#EAF3DE",
  },

  negative: {
    pill:
      "bg-[#FCEBEB] text-[#791F1F] border border-[#F7C1C1]",
    score:
      "text-[#791F1F]",
    bar:
      "#E24B4A",
    track:
      "#FCEBEB",
  },

  neutral: {
    pill:
      "bg-[#F1EFE8] text-[#444441] border border-[#D3D1C7]",
    score:
      "text-[#444441]",
    bar:
      "#B4B2A9",
    track:
      "#F1EFE8",
  },
};

function fmt(value) {
  const number =
    Number(value || 0);

  return number > 0
    ? `+${number.toFixed(2)}`
    : number.toFixed(2);
}

function fmtConf(value) {
  return `${Math.round(
    Number(value || 0) * 100
  )}%`;
}

function Pill({
  sentiment,
  label,
}) {
  const style =
    S[sentiment] ||
    S.neutral;

  return (
    <span
      className={`phov inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${style.pill}`}
    >
      {label || sentiment}
    </span>
  );
}

export default function SentimentPage() {
  const [searchParams] =
    useSearchParams();

  const selectedSymbol =
    searchParams.get("symbol") ||
    "";

  const [articles, setArticles] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [filter, setFilter] =
    useState("all");

  const [visible, setVisible] =
    useState(false);

  const styleRef =
    useRef(false);

  useEffect(() => {
    if (styleRef.current) {
      return;
    }

    styleRef.current = true;

    const style =
      document.createElement(
        "style"
      );

    style.textContent =
      ANIM;

    document.head.appendChild(
      style
    );

    return () => {
      style.remove();
      styleRef.current = false;
    };
  }, []);

  useEffect(() => {
    const loadNews = async () => {
      try {
        setLoading(true);
        setError("");

        const { data } =
          await api.get(
            "/news"
          );

        setArticles(
          Array.isArray(
            data?.data
          )
            ? data.data
            : []
        );

        requestAnimationFrame(
          () =>
            setTimeout(
              () =>
                setVisible(
                  true
                ),
              30
            )
        );
      } catch (err) {
        setError(
          err.response?.data
            ?.message ||
            "Unable to load sentiment analysis."
        );
      } finally {
        setLoading(false);
      }
    };

    loadNews();
  }, []);

  const relevant =
    useMemo(() => {
      if (!selectedSymbol) {
        return articles;
      }

      return articles.filter(
        (article) => {
          const companyMatch =
            (
              article.companies ||
              []
            ).some(
              (company) =>
                company.symbol ===
                selectedSymbol
            );

          return (
            companyMatch ||
            article.marketImpact ===
              true
          );
        }
      );
    }, [
      articles,
      selectedSymbol,
    ]);

  const displayed =
    useMemo(() => {
      if (filter === "all") {
        return relevant;
      }

      return relevant.filter(
        (article) =>
          article.sentiment ===
          filter
      );
    }, [
      relevant,
      filter,
    ]);

  const summary =
    useMemo(() => {
      const positive =
        relevant.filter(
          (article) =>
            article.sentiment ===
            "positive"
        ).length;

      const negative =
        relevant.filter(
          (article) =>
            article.sentiment ===
            "negative"
        ).length;

      const neutral =
        relevant.filter(
          (article) =>
            article.sentiment ===
            "neutral"
        ).length;

      const total =
        relevant.length;

      const avg =
        total > 0
          ? relevant.reduce(
              (
                sum,
                article
              ) =>
                sum +
                Number(
                  article.sentimentScore ||
                    0
                ),
              0
            ) / total
          : 0;

      const overall =
        avg >= 0.2
          ? "positive"
          : avg <= -0.2
            ? "negative"
            : "neutral";

      return {
        positive,
        negative,
        neutral,
        total,
        avg,
        overall,
      };
    }, [relevant]);

  const overallStyle =
    S[summary.overall] ||
    S.neutral;

  const anim =
    (delay) => ({
      animationDelay:
        `${delay}ms`,
      animationFillMode:
        "forwards",
    });

  const circumference =
    2 *
    Math.PI *
    32;

  const heroColor =
    summary.overall ===
    "positive"
      ? "#3B6D11"
      : summary.overall ===
          "negative"
        ? "#791F1F"
        : "#444441";

  const avgPct =
    Math.min(
      Math.max(
        (
          (summary.avg + 1) /
          2
        ) * 100,
        0
      ),
      100
    );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <SiteHeader compact />

      <main className="mx-auto max-w-5xl space-y-4 px-6 py-10">
        <div
          className={`flex items-start justify-between ${
            visible
              ? "au"
              : "opacity-0"
          }`}
          style={anim(0)}
        >
          <div>
            <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-slate-400">
              Sentiment component
            </p>

            <h1 className="text-2xl font-semibold text-slate-900">
              News & market
              sentiment
            </h1>
          </div>

          <div className="mt-1 flex items-center gap-2">
            {selectedSymbol && (
              <span className="phov inline-flex items-center gap-1 rounded-full border border-[#B5D4F4] bg-[#E6F1FB] px-3 py-1 text-xs font-medium text-[#0C447C]">
                <i
                  className="ti ti-building-bank text-[13px]"
                  aria-hidden="true"
                />

                {
                  selectedSymbol
                }
              </span>
            )}

            <Link
              to="/dashboard/insight-preview"
              className="phov inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 hover:border-slate-300"
            >
              <i
                className="ti ti-arrow-left text-[13px]"
                aria-hidden="true"
              />

              Back to analysis
            </Link>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-[#F7C1C1] bg-[#FCEBEB] px-5 py-4 text-sm text-[#791F1F]">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-5">
            <div className="h-5 w-5 flex-shrink-0 animate-spin rounded-full border-2 border-slate-200 border-t-slate-500" />

            <p className="text-sm text-slate-400">
              Loading financial
              news and sentiment
              signals…
            </p>
          </div>
        )}

        {!loading &&
          !error && (
            <>
              <div
                className={`chov rounded-2xl border border-slate-200 bg-white px-6 py-5 ${
                  visible
                    ? "au"
                    : "opacity-0"
                }`}
                style={anim(60)}
              >
                <div className="grid grid-cols-[1fr_auto] items-center gap-6">
                  <div>
                    <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-slate-400">
                      Overall
                      sentiment
                    </p>

                    <div className="mb-2 flex items-center gap-3">
                      <p
                        className="text-3xl font-semibold capitalize"
                        style={{
                          color:
                            heroColor,
                        }}
                      >
                        {
                          summary.overall
                        }
                      </p>

                      <Pill
                        sentiment={
                          summary.overall
                        }
                        label={
                          summary.overall
                        }
                      />
                    </div>

                    <p className="mb-4 text-xs text-slate-400">
                      Derived from{" "}
                      {summary.total}{" "}
                      articles
                      {selectedSymbol
                        ? ` filtered to ${selectedSymbol}`
                        : ""}
                    </p>

                    <div className="space-y-2.5">
                      {[
                        {
                          label:
                            "Positive",
                          value:
                            summary.positive,
                          style:
                            S.positive,
                        },
                        {
                          label:
                            "Negative",
                          value:
                            summary.negative,
                          style:
                            S.negative,
                        },
                        {
                          label:
                            "Neutral",
                          value:
                            summary.neutral,
                          style:
                            S.neutral,
                        },
                      ].map(
                        ({
                          label,
                          value,
                          style,
                        }) => {
                          const pct =
                            summary.total
                              ? Math.round(
                                  (
                                    value /
                                    summary.total
                                  ) *
                                    100
                                )
                              : 0;

                          return (
                            <div
                              key={
                                label
                              }
                            >
                              <div className="mb-1 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span
                                    className="h-2 w-2 flex-shrink-0 rounded-full"
                                    style={{
                                      background:
                                        style.bar,
                                    }}
                                  />

                                  <span className="text-xs text-slate-500">
                                    {
                                      label
                                    }
                                  </span>
                                </div>

                                <span
                                  className="text-xs font-medium"
                                  style={{
                                    color:
                                      style.bar,
                                  }}
                                >
                                  {
                                    pct
                                  }
                                  %
                                </span>
                              </div>

                              <div
                                className="h-[4px] w-full overflow-hidden rounded-full"
                                style={{
                                  background:
                                    style.track,
                                }}
                              >
                                <div
                                  className={
                                    visible
                                      ? "bar h-full rounded-full"
                                      : "h-full rounded-full"
                                  }
                                  style={{
                                    width:
                                      `${pct}%`,
                                    background:
                                      style.bar,
                                    animationDelay:
                                      "200ms",
                                    animationFillMode:
                                      "forwards",
                                  }}
                                />
                              </div>
                            </div>
                          );
                        }
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col items-center gap-3">
                    <svg
                      width="96"
                      height="96"
                      viewBox="0 0 64 64"
                    >
                      <circle
                        cx="32"
                        cy="32"
                        r="26"
                        fill="none"
                        stroke={
                          overallStyle.track
                        }
                        strokeWidth="7"
                      />

                      <circle
                        cx="32"
                        cy="32"
                        r="26"
                        fill="none"
                        stroke={
                          overallStyle.bar
                        }
                        strokeWidth="7"
                        strokeDasharray={`${(
                          (
                            avgPct /
                            100
                          ) *
                          circumference
                        ).toFixed(
                          1
                        )} ${circumference}`}
                        strokeDashoffset={
                          circumference /
                          4
                        }
                        strokeLinecap="round"
                        transform="rotate(-90 32 32)"
                        style={
                          visible
                            ? {
                                transition:
                                  "stroke-dasharray 1s cubic-bezier(.22,1,.36,1)",
                              }
                            : {
                                strokeDasharray:
                                  `0 ${circumference}`,
                              }
                        }
                      />

                      <text
                        x="32"
                        y="36"
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight="500"
                        fill={
                          heroColor
                        }
                      >
                        {fmt(
                          summary.avg
                        )}
                      </text>
                    </svg>

                    <div className="text-center">
                      <p className="text-[11px] font-medium uppercase tracking-widest text-slate-400">
                        Score
                      </p>

                      <p
                        className="text-lg font-semibold"
                        style={{
                          color:
                            heroColor,
                        }}
                      >
                        {fmt(
                          summary.avg
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3">
                {[
                  {
                    label:
                      "Articles",
                    value:
                      summary.total,
                    color:
                      "text-slate-900",
                    delay:
                      120,
                  },
                  {
                    label:
                      "Positive",
                    value:
                      summary.positive,
                    color:
                      "text-[#3B6D11]",
                    delay:
                      180,
                  },
                  {
                    label:
                      "Negative",
                    value:
                      summary.negative,
                    color:
                      "text-[#791F1F]",
                    delay:
                      240,
                  },
                  {
                    label:
                      "Neutral",
                    value:
                      summary.neutral,
                    color:
                      "text-[#444441]",
                    delay:
                      300,
                  },
                ].map(
                  ({
                    label,
                    value,
                    color,
                    delay,
                  }) => (
                    <div
                      key={
                        label
                      }
                      className={`chov rounded-2xl border border-slate-200 bg-white px-4 py-4 ${
                        visible
                          ? "au"
                          : "opacity-0"
                      }`}
                      style={anim(
                        delay
                      )}
                    >
                      <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-slate-400">
                        {
                          label
                        }
                      </p>

                      <p
                        className={`text-2xl font-semibold ${color}`}
                      >
                        {
                          value
                        }
                      </p>
                    </div>
                  )
                )}
              </div>

              <div
                className={`rounded-2xl border border-slate-200 bg-white px-5 py-5 ${
                  visible
                    ? "au"
                    : "opacity-0"
                }`}
                style={anim(360)}
              >
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-slate-400">
                      Financial news
                      feed
                    </p>

                    <p className="text-base font-semibold text-slate-800">
                      Recent
                      sentiment
                      evidence
                    </p>
                  </div>

                  <div className="flex gap-1.5">
                    {[
                      "all",
                      "positive",
                      "negative",
                      "neutral",
                    ].map(
                      (
                        item
                      ) => (
                        <button
                          key={
                            item
                          }
                          type="button"
                          onClick={() =>
                            setFilter(
                              item
                            )
                          }
                          className={`phov rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors ${
                            filter ===
                            item
                              ? item ===
                                "positive"
                                ? "bg-[#EAF3DE] text-[#27500A] border-[#C0DD97]"
                                : item ===
                                    "negative"
                                  ? "bg-[#FCEBEB] text-[#791F1F] border-[#F7C1C1]"
                                  : item ===
                                      "neutral"
                                    ? "bg-[#F1EFE8] text-[#444441] border-[#D3D1C7]"
                                    : "bg-slate-900 text-white border-slate-900"
                              : "bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:text-slate-700"
                          }`}
                        >
                          {
                            item
                          }
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div className="space-y-3">
                  {displayed.map(
                    (
                      article,
                      index
                    ) => {
                      const sentiment =
                        article.sentiment ||
                        "neutral";

                      const style =
                        S[
                          sentiment
                        ] ||
                        S.neutral;

                      const confidence =
                        Math.min(
                          Math.max(
                            Number(
                              article.confidence ||
                                0
                            ) *
                              100,
                            0
                          ),
                          100
                        );

                      return (
                        <div
                          key={
                            article.url ||
                            article.title
                          }
                          className={`chov rounded-xl border border-slate-100 bg-slate-50 p-4 ${
                            visible
                              ? "au"
                              : "opacity-0"
                          }`}
                          style={anim(
                            400 +
                              index *
                                55
                          )}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                                <Pill
                                  sentiment={
                                    sentiment
                                  }
                                  label={
                                    sentiment
                                  }
                                />

                                <span className="phov inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-[11px] font-medium text-slate-500">
                                  {article.type ===
                                  "company"
                                    ? "Company news"
                                    : "Market news"}
                                </span>

                                {article.marketImpact && (
                                  <span className="phov inline-flex items-center rounded-full border border-[#B5D4F4] bg-[#E6F1FB] px-2.5 py-0.5 text-[11px] font-medium text-[#0C447C]">
                                    Market
                                    impact
                                  </span>
                                )}
                              </div>

                              <h3 className="mb-1 text-sm font-semibold leading-snug text-slate-800">
                                {
                                  article.title
                                }
                              </h3>

                              {article.description && (
                                <p
                                  className="mb-2 overflow-hidden text-xs leading-relaxed text-slate-400"
                                  style={{
                                    display:
                                      "-webkit-box",
                                    WebkitLineClamp:
                                      2,
                                    WebkitBoxOrient:
                                      "vertical",
                                  }}
                                >
                                  {
                                    article.description
                                  }
                                </p>
                              )}

                              <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-400">
                                {article.source && (
                                  <span>
                                    {
                                      article.source
                                    }
                                  </span>
                                )}

                                {article.publishedAt && (
                                  <span>
                                    {
                                      article.publishedAt
                                    }
                                  </span>
                                )}
                              </div>

                              {article.companies
                                ?.length >
                                0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {article.companies.map(
                                    (
                                      company
                                    ) => (
                                      <span
                                        key={
                                          company.key ||
                                          company.name
                                        }
                                        className="rounded-full bg-[#E6F1FB] px-2.5 py-0.5 text-[11px] font-medium text-[#0C447C]"
                                      >
                                        {
                                          company.name
                                        }
                                      </span>
                                    )
                                  )}
                                </div>
                              )}
                            </div>

                            <div className="w-36 flex-shrink-0 rounded-xl border border-slate-200 bg-white p-3">
                              <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-slate-400">
                                Score
                              </p>

                              <p
                                className={`mb-3 text-xl font-semibold ${style.score}`}
                              >
                                {fmt(
                                  article.sentimentScore
                                )}
                              </p>

                              <p className="mb-1 flex justify-between text-[11px] text-slate-400">
                                <span>
                                  Confidence
                                </span>

                                <span className="font-medium text-slate-600">
                                  {fmtConf(
                                    article.confidence
                                  )}
                                </span>
                              </p>

                              <div
                                className="h-[4px] w-full overflow-hidden rounded-full"
                                style={{
                                  background:
                                    style.track,
                                }}
                              >
                                <div
                                  className={
                                    visible
                                      ? "bar h-full rounded-full"
                                      : "h-full rounded-full"
                                  }
                                  style={{
                                    width:
                                      `${confidence}%`,
                                    background:
                                      style.bar,
                                    animationDelay:
                                      `${400 + index * 55}ms`,
                                    animationFillMode:
                                      "forwards",
                                  }}
                                />
                              </div>

                              {article.url && (
                                <a
                                  href={
                                    article.url
                                  }
                                  target="_blank"
                                  rel="noreferrer"
                                  className="phov mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-[#185FA5] hover:underline"
                                >
                                  Read
                                  article

                                  <i
                                    className="ti ti-external-link text-[11px]"
                                    aria-hidden="true"
                                  />
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    }
                  )}

                  {displayed.length ===
                    0 && (
                    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
                      <i
                        className="ti ti-article-off mb-2 block text-2xl text-slate-300"
                        aria-hidden="true"
                      />

                      <p className="text-sm font-medium text-slate-600">
                        No matching
                        articles
                      </p>

                      <p className="mt-1 text-xs text-slate-400">
                        Try a
                        different
                        sentiment
                        filter.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div
                className={`grid grid-cols-2 gap-3 ${
                  visible
                    ? "au"
                    : "opacity-0"
                }`}
                style={anim(480)}
              >
                <div className="rounded-2xl border border-slate-200 bg-white px-5 py-5">
                  <p className="mb-2 text-[11px] font-medium uppercase tracking-widest text-slate-400">
                    How to
                    interpret it
                  </p>

                  <p className="mb-2 text-sm font-semibold leading-snug text-slate-800">
                    Sentiment is
                    supporting
                    evidence, not
                    a standalone
                    prediction.
                  </p>

                  <p className="text-xs leading-relaxed text-slate-400">
                    Positive and
                    negative
                    signals
                    provide
                    market
                    context that
                    supports the
                    wider stock,
                    risk, and
                    explainable AI
                    components.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white px-5 py-5">
                  <p className="mb-2 text-[11px] font-medium uppercase tracking-widest text-slate-400">
                    Selected
                    stock
                  </p>

                  <p className="mb-2 text-sm font-semibold text-slate-800">
                    {selectedSymbol ||
                      "Market-wide analysis"}
                  </p>

                  <p className="mb-4 text-xs leading-relaxed text-slate-400">
                    Company-specific
                    articles are
                    combined with
                    market-impact
                    news to
                    capture both
                    direct and
                    broader
                    external
                    signals.
                  </p>

                  <Link
                    to="/dashboard/insight-preview"
                    className="phov inline-flex items-center gap-1 text-xs font-medium text-[#185FA5] hover:underline"
                  >
                    <i
                      className="ti ti-arrow-left text-[11px]"
                      aria-hidden="true"
                    />

                    Return to
                    module view
                  </Link>
                </div>
              </div>
            </>
          )}
      </main>
    </div>
  );
}