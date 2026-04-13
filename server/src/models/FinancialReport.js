const mongoose = require("mongoose");

// Stores the intake record for each uploaded company report before downstream AI processing begins.
const financialReportSchema = new mongoose.Schema(
  {
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
    originalFilename: {
      type: String,
      required: true,
      trim: true,
    },
    storedFilename: {
      type: String,
      required: true,
      trim: true,
    },
    mimeType: {
      type: String,
      required: true,
      trim: true,
    },
    sizeBytes: {
      type: Number,
      required: true,
      min: 1,
    },
    storagePath: {
      type: String,
      required: true,
      trim: true,
    },
    processingStatus: {
      type: String,
      enum: ["uploaded", "queued", "processed", "failed"],
      default: "uploaded",
      index: true,
    },
    summary: {
      type: String,
      trim: true,
      default: "",
    },
    uploadedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
  },
  {
    timestamps: true,
  }
);

module.exports = mongoose.model("FinancialReport", financialReportSchema);
