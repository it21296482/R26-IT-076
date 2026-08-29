const mongoose = require("mongoose");

const newsSchema = new mongoose.Schema(
  {
    title: {
      type: String,
      required: true
    },

    description: {
      type: String,
      default: ""
    },

    source: String,

    url: {
      type: String,
      required: true,
      unique: true
    },

    publishedAt: Date,

    entities: [
      {
        name: String,
        symbol: String,
        exchange: String
      }
    ],

    sentiment: {
      mlPrediction: String,
      rulePrediction: String,
      ruleScore: Number,
      finalPrediction: String,
      decisionReason: String
    }
  },
  {
    timestamps: true
  }
);

module.exports = mongoose.model("News", newsSchema);