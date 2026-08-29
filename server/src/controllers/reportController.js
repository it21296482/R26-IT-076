const fs = require("fs/promises");
const FinancialReport = require("../models/FinancialReport");
const { inspectFinancialReport } = require("../services/reportValidationService");

// Keeps the API response focused on the fields the workspace needs to render upload status.
const buildReportResponse = (report) => ({
  _id: report._id,
  stockSymbol: report.stockSymbol,
  companyName: report.companyName,
  originalFilename: report.originalFilename,
  mimeType: report.mimeType,
  sizeBytes: report.sizeBytes,
  processingStatus: report.processingStatus,
  reportType: report.reportType,
  reportingPeriodEnd: report.reportingPeriodEnd,
  summary: report.summary,
  uploadedAt: report.createdAt,
});

const listUserReports = async (req, res) => {
  const reports = await FinancialReport.find({ uploadedBy: req.user._id })
    .sort({ createdAt: -1 })
    .limit(8);

  return res.status(200).json({
    reports: reports.map(buildReportResponse),
  });
};

const uploadFinancialReport = async (req, res) => {
  const symbol = req.body.symbol?.trim().toUpperCase();
  const companyName = req.body.companyName?.trim();

  if (!symbol || !companyName) {
    return res.status(400).json({
      message: "Company name and stock symbol are required.",
    });
  }

  if (!req.file) {
    return res.status(400).json({
      message: "Please upload a PDF report.",
    });
  }

  let validation;
  try {
    validation = await inspectFinancialReport({
      pdfPath: req.file.path,
      companyName,
      symbol,
    });
  } catch (error) {
    await fs.unlink(req.file.path).catch(() => {});
    throw error;
  }

  if (!validation.accepted) {
    await fs.unlink(req.file.path).catch(() => {});
    return res.status(422).json({
      message: validation.message,
      reportValidation: validation,
    });
  }

  const report = await FinancialReport.create({
    stockSymbol: symbol,
    companyName,
    originalFilename: req.file.originalname,
    storedFilename: req.file.filename,
    mimeType: req.file.mimetype,
    sizeBytes: req.file.size,
    storagePath: req.file.path,
    processingStatus: "queued",
    reportType: validation.report_type,
    reportingPeriodEnd: new Date(validation.reporting_period_end),
    latestRequiredPeriodEnd: new Date(validation.latest_required_period_end),
    summary: "Report received and ready for analysis.",
    uploadedBy: req.user._id,
  });

  return res.status(201).json({
    message: `Financial report uploaded for ${companyName}.`,
    report: buildReportResponse(report),
  });
};

module.exports = {
  listUserReports,
  uploadFinancialReport,
};
