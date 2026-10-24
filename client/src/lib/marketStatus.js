export const anomalyHeading = (market) => {
  if (typeof market?.anomaly?.detected !== "boolean") return "This check was unavailable.";
  return market.anomaly.detected
    ? "An unusual deviation was detected"
    : "No unusual deviation at the latest check";
};
