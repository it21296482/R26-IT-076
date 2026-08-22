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
  extractionPrompt: report.extractionPrompt,
  selectedPromptId: report.selectedPromptId,
  selectedPromptName: report.selectedPromptName,
  ragSources: report.ragSources,
  ragChunkCount: report.ragChunkCount,
  ragSelectedCount: report.ragSelectedCount,
  parsedExtraction: report.parsedExtraction,
  extractionError: report.extractionError,
  processedAt: report.processedAt,
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
    processingStatus: "uploaded",
    summary: "Report uploaded and awaiting extraction.",
    uploadedBy: req.user._id,
  });

  try {
    const { extractAnnualReport } = require("../services/reportExtractionService");
    // Processing is synchronous so the API returns either a complete insight or a clear failure state.
    const extractionResult = await extractAnnualReport({
      pdfPath: report.storagePath,
      pdfName: report.originalFilename,
    });

    // Store research metadata with the output so the selected method remains auditable.
    report.processingStatus = "processed";
    report.summary = extractionResult.summary;
    report.extractionPrompt = extractionResult.promptFileName;
    report.selectedPromptId = extractionResult.promptId;
    report.selectedPromptName = extractionResult.promptName;
    report.ragSources = extractionResult.ragSources;
    report.ragChunkCount = extractionResult.ragChunkCount;
    report.ragSelectedCount = extractionResult.ragSelectedCount;
    report.parsedExtraction = extractionResult.parsedOutput;
    report.rawExtractionOutput = extractionResult.rawOutput;
    report.extractionError = "";
    report.processedAt = new Date();
    await report.save();
  } catch (error) {
    report.processingStatus = "failed";
    report.summary = "Annual report extraction failed.";
    report.extractionError = error.message;
    report.processedAt = new Date();
    await report.save();
    throw error;
  }

  return res.status(201).json({
    message: `Financial report uploaded and extracted for ${companyName}.`,
    report: buildReportResponse(report),
  });
};

module.exports = {
  listUserReports,
  uploadFinancialReport,
};
