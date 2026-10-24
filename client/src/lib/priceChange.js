export const priceChangeClass = (change) => {
  if (typeof change !== "number" || !Number.isFinite(change)) return "";
  if (change > 0) return "text-emerald-700";
  if (change < 0) return "text-red-700";
  return "";
};
