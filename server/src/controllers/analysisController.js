const AnalysisRun = require("../models/AnalysisRun");
const FinancialReport = require("../models/FinancialReport");
const { refreshAvailableStockQuotes } = require("../services/cseQuoteService");
const { collectMarketRiskContext, collectNewsSentiment } = require("../services/externalContextService");
const { loadMarketInsight } = require("../services/marketInsightService");
const { analyzeFinancialReport } = require("../services/reportInsightService");
const { inspectFinancialReport } = require("../services/reportValidationService");
const { assessRiskImpact } = require("../services/riskImpactService");
const { generateUnifiedInsight } = require("../services/unifiedInsightService");
const { translateAnalysis } = require("../services/translationService");
const { updateProgress, subscribeProgress } = require("../services/analysisProgressService");
const { ensureStockPrepared, requireListedCompany } = require("../services/stockPreparationService");
const { runQueuedAnalysis } = require("../services/analysisQueueService");

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
          assessment_scope: "one_step_expected_price_only",
          plain_assessment: quality.advanced_model_beats_naive_mae === false
            ? "The daily expected-price check did not improve on an unchanged-price comparison. Each longer forecast has a separate accuracy check and remains uncertain."
            : "The daily expected-price check improved on the available comparison. This does not validate every forecast horizon; check each range's own caution note.",
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

const publicNewsOutput = (newsSentiment) => (
  newsSentiment ? structuredClone(newsSentiment) : null
);

const publicMarketRiskContextOutput = (marketRiskContext) => {
  if (!marketRiskContext) return null;
  const output = structuredClone(marketRiskContext);
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
  delete output.model_scope;
  delete output.model_validation;
  delete output.training;
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

const compactRiskEvidence = (riskImpact) => riskImpact
  ? {
      status: riskImpact.status,
      risk_level: riskImpact.risk_level,
      plain_explanation: riskImpact.plain_explanation,
      top_drivers: (riskImpact.top_drivers || []).map(({ label, meaning, supports_classification }) => ({
        label,
        meaning,
        supports_classification,
      })),
      global_drivers: (riskImpact.global_drivers || []).map(({ label, meaning, supports_classification }) => ({
        label,
        meaning,
        supports_classification,
      })),
      factor_dates: riskImpact.factor_dates,
    }
  : { status: "unavailable" };

const compactFusionEvidence = ({ stockSymbol, companyName, market, report, newsSentiment, marketRiskContext, riskImpact }) => ({
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
  news_sentiment_evidence: newsSentiment
    ? {
        article_count: newsSentiment.articleCount,
        sentiment_counts: newsSentiment.sentimentCounts,
        articles: newsSentiment.articles.slice(0, 12).map((article) => ({
          title: article.title,
          source: article.source,
          published_at: article.publishedAt,
          url: article.url,
          scope: article.scope,
          sentiment: article.sentiment,
          event_tags: article.eventTags,
        })),
        warnings: newsSentiment.warnings,
      }
    : { status: "unavailable" },
  market_risk_context: marketRiskContext
    ? {
        external_factors: marketRiskContext.externalFactors,
        warnings: marketRiskContext.warnings,
      }
    : { status: "unavailable" },
  risk_evidence: compactRiskEvidence(riskImpact),
});

const performAnalysis = async (req, res) => {
  const progress = (update) => updateProgress(req.user._id, req.body.clientRequestId, update);
  const stockSymbol = String(req.body.stockSymbol || "").toUpperCase();
  const company = await requireListedCompany(stockSymbol);
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
  progress({ percent: 5, stage: "validating_report", status: "processing" });
  const report = await FinancialReport.findOne({
      _id: req.body.reportId,
      uploadedBy: req.user._id,
      stockSymbol,
    });
  if (!report) {
    return res.status(400).json({
      message: "A financial report uploaded for the selected company is required.",
    });
  }

  const reportValidation = await inspectFinancialReport({
    pdfPath: report.storagePath,
    companyName: company.companyName,
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
    companyName: company.companyName,
    status: "processing",
    expiresAt: temporaryExpiry(),
  });

  report.processingStatus = "processing";
  await report.save();

  try {
    progress({ percent: 8, stage: "preparing_stock", status: "processing" });
    let preparation = null, preparationError = null;
    try {
      preparation = await ensureStockPrepared({ symbol: stockSymbol, company, createdBy: req.user._id });
      console.info(`[analysis:${analysis._id}] history prepared: ${preparation.mode}`);
    } catch (error) {
      preparationError = error;
      console.warn(`[analysis:${analysis._id}] history preparation: ${safeWarning(error.message)}`);
    }
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
    const [marketResult, reportResult, newsResult, riskResult] = await Promise.allSettled([
      runStage("market", "Market behaviour and unusual movement", () => {
        if (preparationError) throw preparationError;
        if (!preparation.forecastReady) throw new Error(`Only ${preparation.validRows} genuine sessions and ${preparation.recentActiveSessions} recent active sessions were available. The four-horizon forecast requires 1000 observations and 80 recent active sessions; no missing prices were invented.`);
        return loadMarketInsight(stockSymbol, {
        refreshHistory: async () => preparation.refresh || { applied: true, source: preparation.sourceNote },
        onProgress: ({ percent, ...detail }) => progress({ ...detail, percent: 10 + percent * .75, status: "processing" }),
      }); }),
      runStage("report", "Verified company report", () => analyzeFinancialReport({
        pdfPath: report.storagePath,
        companyName: company.companyName,
        symbol: stockSymbol,
      })),
      runStage("newsSentiment", "News, events, and sentiment", () => collectNewsSentiment({
        symbol: stockSymbol,
        companyName: company.companyName,
      })),
      runStage("riskImpact", "External-market risk and explanation", async () => {
        if (preparationError) throw preparationError;
        const marketRiskContext = await collectMarketRiskContext({ symbol: stockSymbol });
        const riskImpact = await assessRiskImpact({ symbol: stockSymbol, marketRiskContext });
        return { marketRiskContext, riskImpact, warnings: [...(marketRiskContext.warnings || []), ...(riskImpact.warnings || [])] };
      }),
    ]);

    const market = resultOrNull(marketResult);
    progress({ percent: 88, stage: "combining_evidence", status: "processing" });
    const reportOutput = resultOrNull(reportResult);
    const newsSentiment = resultOrNull(newsResult);
    const riskBundle = resultOrNull(riskResult);
    const marketRiskContext = riskBundle?.marketRiskContext || null;
    const riskImpact = riskBundle?.riskImpact || null;
    if (Array.isArray(reportOutput?.warnings)) {
      reportOutput.warnings = reportOutput.warnings.map(safeWarning);
    }
    if (Array.isArray(newsSentiment?.warnings)) {
      newsSentiment.warnings = newsSentiment.warnings.map(safeWarning);
    }
    if (Array.isArray(marketRiskContext?.warnings)) {
      marketRiskContext.warnings = marketRiskContext.warnings.map(safeWarning);
    }
    const warnings = [
      ...(priceRefreshWarning ? [priceRefreshWarning] : []),
      ...warningsFrom(marketResult, "Market analysis"),
      ...warningsFrom(reportResult, "Financial report"),
      ...warningsFrom(newsResult, "News and sentiment"),
      ...warningsFrom(riskResult, "External-market risk"),
    ];

    if (reportOutput) {
      report.processingStatus = reportOutput.status === "completed" ? "processed" : reportOutput.status;
      report.summary = reportOutput.insight?.investor_friendly_insight?.summary || "";
    } else {
      report.processingStatus = "failed";
    }
    await report.save();

    let unifiedInsight = null;
    if (market || reportOutput || newsSentiment || marketRiskContext || riskImpact) {
      try {
        unifiedInsight = await runStage("integration", "Plain-language integrated stock picture", () => generateUnifiedInsight(compactFusionEvidence({
          stockSymbol,
          companyName: company.companyName,
          market,
          report: reportOutput,
          newsSentiment,
          marketRiskContext,
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
      market && reportOutput?.status === "completed" && newsSentiment && marketRiskContext && riskImpact && unifiedInsight?.status === "completed"
    );
    analysis.status = requiredInputsComplete ? "completed" : "partial";
    analysis.outputs = {
      market: publicMarketOutput(market),
      report: publicReportOutput(reportOutput),
      newsSentiment: publicNewsOutput(newsSentiment),
      marketRiskContext: publicMarketRiskContextOutput(marketRiskContext),
      externalContext: null,
      riskImpact: publicRiskOutput(riskImpact),
      unifiedInsight,
      workflow,
      priceRefresh,
      historyPreparation: preparation && { ...preparation, auditId: undefined },
    };
    analysis.warnings = [...new Set(warnings)];
    await analysis.save();
    progress({ percent: 100, stage: requiredInputsComplete ? "completed" : "partial", status: requiredInputsComplete ? "completed" : "partial" });

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

const createAnalysis = async (req, res) => {
  updateProgress(req.user._id, req.body.clientRequestId, { percent: 1, stage: "refreshing_prices", status: "processing" });
  try {
    await runQueuedAnalysis(req.user._id, () => performAnalysis(req, res), () =>
      updateProgress(req.user._id, req.body.clientRequestId, { percent: 1, stage: "queued", status: "processing" }));
    if (res.statusCode >= 400) updateProgress(req.user._id, req.body.clientRequestId, { stage: "failed", status: "failed" });
  } catch (error) {
    updateProgress(req.user._id, req.body.clientRequestId, { stage: "failed", status: "failed" });
    throw error;
  }
};

const getAnalysisProgress = (req, res) => {
  res.set({ "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive", "X-Accel-Buffering": "no" });
  res.flushHeaders();
  let unsubscribe;
  const heartbeat = setInterval(() => res.write(": heartbeat\n\n"), 20000);
  try {
    unsubscribe = subscribeProgress(req.user._id, req.params.requestId, (state) => {
      res.write(`data: ${JSON.stringify(state)}\n\n`);
    });
  } catch (error) {
    clearInterval(heartbeat);
    res.end();
    return;
  }
  req.on("close", () => { clearInterval(heartbeat); unsubscribe(); });
};

const getAnalysis = async (req, res) => {
  const analysis = await AnalysisRun.findOne({ _id: req.params.analysisId, user: req.user._id }).lean();
  if (!analysis) {
    return res.status(404).json({ message: "This analysis is unavailable or has expired." });
  }
  const translatedAnalysis = await translateAnalysis(analysis, req.query.language);
  return res.status(200).json({ analysis: translatedAnalysis, language: translatedAnalysis.localization?.requestedLanguage || "en" });
};

module.exports = { createAnalysis, getAnalysis, getAnalysisProgress };
