export const ANALYSIS_OUTPUTS = [
  { key: "market", number: "01", label: "Price behaviour", controls: "section-market section-market-check" },
  { key: "report", number: "02", label: "Company report", controls: "section-report" },
  { key: "news", number: "03", label: "News & sentiment", controls: "section-news-articles" },
  { key: "risk", number: "04", label: "External-market risk", controls: "section-risk" },
  { key: "overall", number: "05", label: "Overall insight", controls: "section-overall-balance section-overall" },
];

export const outputVisibility = (selected) => {
  const active = ANALYSIS_OUTPUTS.some(({ key }) => key === selected) ? selected : "";
  return Object.fromEntries(ANALYSIS_OUTPUTS.map(({ key }) => [key, !active || active === key]));
};
