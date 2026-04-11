const mongoose = require("mongoose");

const stockSchema = new mongoose.Schema(
  {
    symbol: {
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
    tradeDate: {
      type: Date,
      required: true,
      index: true,
    },
    open: {
      type: Number,
      required: true,
      min: 0,
    },
    high: {
      type: Number,
      required: true,
      min: 0,
    },
    low: {
      type: Number,
      required: true,
      min: 0,
    },
    close: {
      type: Number,
      required: true,
      min: 0,
    },
    adjustedClose: {
      type: Number,
      min: 0,
      default: null,
    },
    volume: {
      type: Number,
      required: true,
      min: 0,
    },
    source: {
      type: String,
      trim: true,
      default: "manual-entry",
    },
    notes: {
      type: String,
      trim: true,
      maxlength: 300,
      default: "",
    },
    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
  },
  {
    timestamps: true,
  }
);

stockSchema.index({ symbol: 1, tradeDate: 1 }, { unique: true });

module.exports = mongoose.model("Stock", stockSchema);
