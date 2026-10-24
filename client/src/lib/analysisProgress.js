export const progressLabel = (stage) => ({
  upload: "Uploading and checking your report", waiting: "Waiting for analysis to start",
  refreshing_prices: "Refreshing prices from CSE", validating_report: "Checking the company report",
  loading_history: "Loading stock history", validating_history: "Checking historical prices",
  preparing_stock: "Fetching and checking this stock's history",
  queued: "Waiting for an analysis slot", partial: "Analysis completed with limited evidence",
  building_features: "Preparing price and volume patterns", sequence_training: "Training the expected-price model",
  anomaly_calibration: "Calculating deviations and anomaly thresholds", explanations: "Checking the reasons behind unusual movements",
  forecast_training: "Training price paths for each forecast period", checking_output: "Validating price paths and calculations",
  market_complete: "Price analysis finished; waiting for remaining evidence", combining_evidence: "Preparing the final stock explanation",
  completed: "Analysis completed", failed: "Analysis could not finish", market_unavailable: "Market analysis needs review",
}[stage] || "Analysis in progress");

export const progressUrl = (baseUrl, requestId, origin) => {
  const base = new URL(baseUrl || "/api", origin);
  return `${base.href.replace(/\/$/, "")}/analysis/progress/${encodeURIComponent(requestId)}`;
};
