const AnalysisRun = require("../models/AnalysisRun");
const FinancialReport = require("../models/FinancialReport");
const Stock = require("../models/Stock");
const { collectExternalContext } = require("../services/externalContextService");
const { loadMarketInsight } = require("../services/marketInsightService");
const { analyzeFinancialReport } = require("../services/reportInsightService");
const { generateUnifiedInsight } = require("../services/unifiedInsightService");

const temporaryExpiry = () => new Date(Date.now() + 24 * 60 * 60 * 1000);

const safeWarning = (value) => {
  const message = String(value || "Analysis input was unavailable.");
  if (/missing azure openai settings/i.test(message)) {
    return "The explanation service is not configured with a valid server credential.";
  }
  if (/invalid subscription key|access denied.*subscription key|wrong api endpoint/i.test(message)) {
    return "The explanation service rejected the configured server credential or endpoint.";
  }
  if (/modulenotfounderror/i.test(message)) {
    return "A required server dependency for this analysis is unavailable.";
  }
  if (/command failed/i.test(message)) {
    return "A server analysis process could not complete.";
  }
  return message
    .replace(/azure openai/gi, "explanation service")
    .replace(/api[_ -]?key[^,.;]*/gi, "server credential")
    .replace(/\b(?:llm|lstm|shap|machine learning)\b/gi, "analysis")
    .replace(/\/Users\/[^\s]+/g, "a server file")
    .replace(/[\r\n]+/g, " ")
    .slice(0, 500);
};

const resultOrNull = (settledResult) => (
  settledResult.status === "fulfilled" ? settledResult.value : null
);

const warningsFrom = (settledResult, label) => {
  if (settledResult.status === "rejected") {
    return [`${label}: ${safeWarning(settledResult.reason?.message)}`];
  }
  return Array.isArray(settledResult.value?.warnings)
    ? settledResult.value.warnings.map((warning) => `${label}: ${safeWarning(warning)}`)
    : [];
};

const compactFusionEvidence = ({ stockSymbol, companyName, market, report, externalContext }) => ({
  selected_stock: { symbol: stockSymbol, company_name: companyName },
  market_evidence: market,
  report_evidence: report
    ? {
        status: report.status,
        report: report.report,
        insight: report.insight,
        evidence_validation: report.evidence_validation,
        warnings: report.warnings,
      }
    : { status: "unavailable" },
  external_context: externalContext
    ? {
        article_count: externalContext.articleCount,
        sentiment_counts: externalContext.sentimentCounts,
        articles: externalContext.articles.slice(0, 12).map((article) => ({
          title: article.title,
          source: article.source,
          published_at: article.publishedAt,
          url: article.url,
          scope: article.scope,
          sentiment: article.sentiment,
          event_tags: article.eventTags,
        })),
        external_factors: externalContext.externalFactors,
        warnings: externalContext.warnings,
      }
    : { status: "unavailable" },
});

const createAnalysis = async (req, res) => {
  const stockSymbol = String(req.body.stockSymbol || "").toUpperCase();
  const [latestStock, report] = await Promise.all([
    Stock.findOne({ symbol: stockSymbol }).sort({ tradeDate: -1 }).lean(),
    FinancialReport.findOne({
      _id: req.body.reportId,
      uploadedBy: req.user._id,
      stockSymbol,
    }),
  ]);

  if (!latestStock) {
    return res.status(404).json({ message: "The selected stock is not available." });
  }
  if (!report) {
    return res.status(400).json({
      message: "A financial report uploaded for the selected company is required.",
    });
  }

  const analysis = await AnalysisRun.create({
    user: req.user._id,
    report: report._id,
    stockSymbol,
    companyName: latestStock.companyName,
    status: "processing",
    expiresAt: temporaryExpiry(),
  });

  report.processingStatus = "processing";
  await report.save();

  try {
    const [marketResult, reportResult, contextResult] = await Promise.allSettled([
      loadMarketInsight(stockSymbol),
      analyzeFinancialReport({
        pdfPath: report.storagePath,
        companyName: latestStock.companyName,
        symbol: stockSymbol,
      }),
      collectExternalContext({ stockSymbol, symbol: stockSymbol, companyName: latestStock.companyName }),
    ]);

    const market = resultOrNull(marketResult);
    const reportOutput = resultOrNull(reportResult);
    const externalContext = resultOrNull(contextResult);
    if (Array.isArray(reportOutput?.warnings)) {
      reportOutput.warnings = reportOutput.warnings.map(safeWarning);
    }
    if (Array.isArray(externalContext?.warnings)) {
      externalContext.warnings = externalContext.warnings.map(safeWarning);
    }
    const warnings = [
      ...warningsFrom(marketResult, "Market analysis"),
      ...warningsFrom(reportResult, "Financial report"),
      ...warningsFrom(contextResult, "External context"),
    ];

    if (reportOutput) {
      report.processingStatus = reportOutput.status === "completed" ? "processed" : reportOutput.status;
      report.summary = reportOutput.insight?.investor_friendly_insight?.summary || "";
    } else {
      report.processingStatus = "failed";
    }
    await report.save();

    let unifiedInsight = null;
    if (market || reportOutput || externalContext) {
      try {
        unifiedInsight = await generateUnifiedInsight(compactFusionEvidence({
          stockSymbol,
          companyName: latestStock.companyName,
          market,
          report: reportOutput,
          externalContext,
        }));
        if (Array.isArray(unifiedInsight.warnings)) {
          warnings.push(...unifiedInsight.warnings.map((warning) => `Unified explanation: ${safeWarning(warning)}`));
        }
      } catch (error) {
        warnings.push(`Unified explanation: ${safeWarning(error.message)}`);
      }
    }

    const requiredInputsComplete = Boolean(
      market && reportOutput?.status === "completed" && externalContext && unifiedInsight?.status === "completed"
    );
    analysis.status = requiredInputsComplete ? "completed" : "partial";
    analysis.outputs = { market, report: reportOutput, externalContext, unifiedInsight };
    analysis.warnings = [...new Set(warnings)];
    await analysis.save();

    return res.status(201).json({
      message: requiredInputsComplete
        ? "Your stock insight is ready."
        : "The analysis completed with evidence or service limitations.",
      analysis,
    });
  } catch (error) {
    analysis.status = "failed";
    analysis.failureMessage = safeWarning(error.message);
    await analysis.save();
    report.processingStatus = "failed";
    await report.save();
    throw error;
  }
};

const getAnalysis = async (req, res) => {
  const analysis = await AnalysisRun.findOne({ _id: req.params.analysisId, user: req.user._id }).lean();
  if (!analysis) {
    return res.status(404).json({ message: "This analysis is unavailable or has expired." });
  }
  return res.status(200).json({ analysis });
};

module.exports = { createAnalysis, getAnalysis };
