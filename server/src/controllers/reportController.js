const FinancialReport = require("../models/FinancialReport");

// Keeps the API response focused on the fields the workspace needs to render upload status.
const buildReportResponse = (report) => ({
  _id: report._id,
  stockSymbol: report.stockSymbol,
  companyName: report.companyName,
  originalFilename: report.originalFilename,
  mimeType: report.mimeType,
  sizeBytes: report.sizeBytes,
  processingStatus: report.processingStatus,
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

  const report = await FinancialReport.create({
    stockSymbol: symbol,
    companyName,
    originalFilename: req.file.originalname,
    storedFilename: req.file.filename,
    mimeType: req.file.mimetype,
    sizeBytes: req.file.size,
    storagePath: req.file.path,
    processingStatus: "queued",
    // This placeholder summary mirrors the first stage of the research pipeline until parsing is implemented.
    summary:
      "Report received and queued for document parsing, indicator extraction, and explainable insight generation.",
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
