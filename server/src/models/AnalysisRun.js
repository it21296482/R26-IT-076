const mongoose = require("mongoose");

const analysisRunSchema = new mongoose.Schema(
  {
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    report: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "FinancialReport",
      required: true,
    },
    stockSymbol: {
      type: String,
      required: true,
      uppercase: true,
      trim: true,
      index: true,
    },
    companyName: {
      type: String,
      required: true,
      trim: true,
    },
    status: {
      type: String,
      enum: ["processing", "completed", "partial", "failed"],
      default: "processing",
      index: true,
    },
    outputs: {
      market: { type: mongoose.Schema.Types.Mixed, default: null },
      report: { type: mongoose.Schema.Types.Mixed, default: null },
      externalContext: { type: mongoose.Schema.Types.Mixed, default: null },
      unifiedInsight: { type: mongoose.Schema.Types.Mixed, default: null },
    },
    warnings: {
      type: [String],
      default: [],
    },
    failureMessage: {
      type: String,
      default: "",
    },
    expiresAt: {
      type: Date,
      required: true,
      index: { expires: 0 },
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model("AnalysisRun", analysisRunSchema);

