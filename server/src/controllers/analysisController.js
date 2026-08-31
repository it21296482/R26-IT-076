const AnalysisRun = require("../models/AnalysisRun");
const FinancialReport = require("../models/FinancialReport");
const Stock = require("../models/Stock");
const { refreshAvailableStockQuotes } = require("../services/cseQuoteService");
const { collectExternalContext } = require("../services/externalContextService");
const { loadMarketInsight } = require("../services/marketInsightService");
const { analyzeFinancialReport } = require("../services/reportInsightService");
const { inspectFinancialReport } = require("../services/reportValidationService");
const { assessRiskImpact } = require("../services/riskImpactService");
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

const publicMarketOutput = (market) => {
  if (!market) return null;
  const publicMarket = structuredClone(market);
  const quality = publicMarket.model_quality;
  delete publicMarket.source_file;
  delete publicMarket.top_factors;
  delete publicMarket.limitations;
  delete publicMarket.model_quality;
  return {
    ...publicMarket,
    estimate_quality: quality
      ? {
          test_error_lkr: quality.test_mae_lkr,
          unchanged_price_error_lkr: quality.naive_test_mae_lkr,
          estimate_beats_unchanged_price: quality.advanced_model_beats_naive_mae,
          plain_assessment: quality.advanced_model_beats_naive_mae === false
            ? "Use these price ranges with extra caution because an unchanged-price comparison performed better in testing."
            : "The price ranges passed the available comparison check.",
        }
      : null,
    limitations: [
      "Price ranges are uncertain and are not promises or financial advice.",
      "Unusual-movement checks have a limited number of independently verified examples.",
      "Historical price sources should be checked against official exchange records when possible.",
    ],
  };
};

const publicReportOutput = (reportOutput) => {
  if (!reportOutput) return null;
  const output = structuredClone(reportOutput);
  if (output.insight?.metadata) delete output.insight.metadata.prompt_id;
  if (output.evidence_validation) {
    output.evidence_validation = {
      valid_count: output.evidence_validation.valid_count,
      rejected_count: output.evidence_validation.rejected_count,
    };
  }
  return output;
};

const publicExternalOutput = (externalContext) => {
  if (!externalContext) return null;
  const output = structuredClone(externalContext);
  if (output.externalFactors) {
    output.externalFactors.method = "Compared one year of shared daily stock and factor movements. Results describe association, not cause.";
    output.externalFactors.factors = (output.externalFactors.factors || []).map(({ sensitivityBeta, ...factor }) => factor);
  }
  return output;
};

const publicRiskOutput = (riskImpact) => {
  if (!riskImpact) return null;
  const output = structuredClone(riskImpact);
  delete output.class_probabilities;
  delete output.explanation_method;
  output.top_drivers = (output.top_drivers || []).map(({ impact, factor, ...driver }) => driver);
  output.global_drivers = (output.global_drivers || []).map(({ impact, factor, ...driver }) => driver);
  return output;
};

const warningsFrom = (settledResult, label) => {
  if (settledResult.status === "rejected") {
    return [`${label}: ${safeWarning(settledResult.reason?.message)}`];
  }
  return Array.isArray(settledResult.value?.warnings)
    ? settledResult.value.warnings.map((warning) => `${label}: ${safeWarning(warning)}`)
    : [];
};

const compactFusionEvidence = ({ stockSymbol, companyName, market, report, externalContext, riskImpact }) => ({
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
  risk_evidence: riskImpact || { status: "unavailable" },
});

const createAnalysis = async (req, res) => {
  const stockSymbol = String(req.body.stockSymbol || "").toUpperCase();
  let priceRefresh = null;
  let priceRefreshWarning = "";
  console.info(`[analysis:${stockSymbol}] priceRefresh: started`);
  try {
    priceRefresh = await refreshAvailableStockQuotes();
    console.info(`[analysis:${stockSymbol}] priceRefresh: updated ${priceRefresh.updatedSymbols.length} symbols`);
  } catch (error) {
    priceRefreshWarning = `Latest CSE prices: ${safeWarning(error.message)}`;
    console.info(`[analysis:${stockSymbol}] priceRefresh: unavailable`);
  }
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

  const reportValidation = await inspectFinancialReport({
    pdfPath: report.storagePath,
    companyName: latestStock.companyName,
    symbol: stockSymbol,
  });
  if (!reportValidation.accepted) {
    return res.status(422).json({
      message: reportValidation.message,
      reportValidation,
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
    const workflow = {};
    const runStage = async (key, label, task) => {
      const started = Date.now();
      console.info(`[analysis:${analysis._id}] ${key}: started`);
      try {
        const output = await task();
        workflow[key] = { label, status: "completed", durationMs: Date.now() - started };
        console.info(`[analysis:${analysis._id}] ${key}: completed in ${workflow[key].durationMs} ms`);
        return output;
      } catch (error) {
        workflow[key] = { label, status: "unavailable", durationMs: Date.now() - started };
        console.info(`[analysis:${analysis._id}] ${key}: unavailable after ${workflow[key].durationMs} ms`);
        throw error;
      }
    };
    const [marketResult, reportResult, contextResult] = await Promise.allSettled([
      runStage("market", "Market behaviour and unusual movement", () => loadMarketInsight(stockSymbol)),
      runStage("report", "Verified company report", () => analyzeFinancialReport({
        pdfPath: report.storagePath,
        companyName: latestStock.companyName,
        symbol: stockSymbol,
      })),
      runStage("externalContext", "External events and market factors", () => collectExternalContext({
        stockSymbol,
        symbol: stockSymbol,
        companyName: latestStock.companyName,
      })),
    ]);

    const market = resultOrNull(marketResult);
    const reportOutput = resultOrNull(reportResult);
    const externalContext = resultOrNull(contextResult);
    let riskResult = { status: "rejected", reason: new Error("External context was unavailable for the risk assessment.") };
    if (externalContext) {
      riskResult = await Promise.allSettled([
        runStage("riskImpact", "Explainable global-market risk impact", () => assessRiskImpact({
          symbol: stockSymbol,
          externalContext,
        })),
      ]).then(([result]) => result);
    } else {
      workflow.riskImpact = {
        label: "Explainable global-market risk impact",
        status: "unavailable",
        durationMs: 0,
      };
    }
    const riskImpact = resultOrNull(riskResult);
    if (Array.isArray(reportOutput?.warnings)) {
      reportOutput.warnings = reportOutput.warnings.map(safeWarning);
    }
    if (Array.isArray(externalContext?.warnings)) {
      externalContext.warnings = externalContext.warnings.map(safeWarning);
    }
    const warnings = [
      ...(priceRefreshWarning ? [priceRefreshWarning] : []),
      ...warningsFrom(marketResult, "Market analysis"),
      ...warningsFrom(reportResult, "Financial report"),
      ...warningsFrom(contextResult, "External context"),
      ...warningsFrom(riskResult, "Market risk"),
    ];

    if (reportOutput) {
      report.processingStatus = reportOutput.status === "completed" ? "processed" : reportOutput.status;
      report.summary = reportOutput.insight?.investor_friendly_insight?.summary || "";
    } else {
      report.processingStatus = "failed";
    }
    await report.save();

    let unifiedInsight = null;
    if (market || reportOutput || externalContext || riskImpact) {
      try {
        unifiedInsight = await runStage("integration", "Plain-language integrated stock picture", () => generateUnifiedInsight(compactFusionEvidence({
          stockSymbol,
          companyName: latestStock.companyName,
          market,
          report: reportOutput,
          externalContext,
          riskImpact,
        })));
        if (Array.isArray(unifiedInsight.warnings)) {
          warnings.push(...unifiedInsight.warnings.map((warning) => `Unified explanation: ${safeWarning(warning)}`));
        }
      } catch (error) {
        warnings.push(`Unified explanation: ${safeWarning(error.message)}`);
      }
    }

    const requiredInputsComplete = Boolean(
      market && reportOutput?.status === "completed" && externalContext && riskImpact && unifiedInsight?.status === "completed"
    );
    analysis.status = requiredInputsComplete ? "completed" : "partial";
    analysis.outputs = {
      market: publicMarketOutput(market),
      report: publicReportOutput(reportOutput),
      externalContext: publicExternalOutput(externalContext),
      riskImpact: publicRiskOutput(riskImpact),
      unifiedInsight,
      workflow,
      priceRefresh,
    };
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
