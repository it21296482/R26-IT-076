import { jsPDF } from "jspdf";
import { autoTable } from "jspdf-autotable";

const NAVY = [8, 27, 73];
const BLUE = [29, 74, 168];
const TEXT = [30, 41, 59];
const MUTED = [100, 116, 139];
const BORDER = [219, 231, 251];
const LIGHT_BLUE = [248, 251, 255];
const PAGE_WIDTH = 210;
const PAGE_HEIGHT = 297;
const MARGIN = 16;

// PDF colors intentionally match the CSE blue and white application palette.
const sectionLabels = {
  company_overview: "Company Overview",
  financial_performance: "Financial Performance",
  financial_position: "Financial Position",
  cash_flow: "Cash Flow",
  investor_ratios: "Investor Ratios",
  shareholder_information: "Shareholder Information",
  risk_factors: "Risk Factors",
  management_governance: "Management and Governance",
  future_outlook: "Future Outlook",
};

const cleanText = (value) =>
  String(value ?? "")
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/[\u2013\u2014]/g, "-")
    .replace(/[^\x20-\x7E\n]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const titleCase = (value) => cleanText(value).replaceAll("_", " ").replaceAll(".", " / ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const displayValue = (value) => {
  if (value === null || value === undefined || value === "") return "Not found";
  if (Array.isArray(value)) return value.length ? value.map(cleanText).join(", ") : "Not found";
  if (typeof value === "object") return cleanText(JSON.stringify(value));
  return cleanText(value);
};

const addFooter = (doc) => {
  // Footers are applied after content generation because the final page count is then known.
  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page);
    doc.setDrawColor(...BORDER);
    doc.line(MARGIN, 282, PAGE_WIDTH - MARGIN, 282);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...MUTED);
    doc.text("CSE Insight Generator | Informational report only", MARGIN, 288);
    doc.text(`Page ${page} of ${pages}`, PAGE_WIDTH - MARGIN, 288, { align: "right" });
  }
};

const ensureSpace = (doc, y, needed = 24) => {
  // Every content helper uses this guard to prevent text from overlapping the footer.
  if (y + needed <= 276) return y;
  doc.addPage();
  return 20;
};

const addHeading = (doc, text, y) => {
  const safeY = ensureSpace(doc, y, 14);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(...NAVY);
  doc.text(cleanText(text), MARGIN, safeY);
  doc.setDrawColor(...BLUE);
  doc.setLineWidth(0.7);
  doc.line(MARGIN, safeY + 3, MARGIN + 24, safeY + 3);
  return safeY + 10;
};

const addParagraph = (doc, text, y, options = {}) => {
  const lines = doc.splitTextToSize(cleanText(text) || options.fallback || "Not available", PAGE_WIDTH - MARGIN * 2);
  const safeY = ensureSpace(doc, y, lines.length * 5.2 + 4);
  doc.setFont("helvetica", options.bold ? "bold" : "normal");
  doc.setFontSize(options.size || 10);
  doc.setTextColor(...(options.color || TEXT));
  doc.text(lines, MARGIN, safeY);
  return safeY + lines.length * 5.2 + 4;
};

const addList = (doc, items, y, fallback) => {
  const values = items?.length ? items : [fallback];
  let cursor = y;
  values.forEach((item) => {
    const lines = doc.splitTextToSize(`- ${cleanText(item)}`, PAGE_WIDTH - MARGIN * 2 - 2);
    cursor = ensureSpace(doc, cursor, lines.length * 5 + 3);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(...TEXT);
    doc.text(lines, MARGIN + 2, cursor);
    cursor += lines.length * 5 + 3;
  });
  return cursor;
};

const addFactTable = (doc, title, facts, y) => {
  const entries = Object.entries(facts || {});
  if (!entries.length) return y;
  const startY = addHeading(doc, title, y);
  // Tables repeat their header after automatic page breaks, keeping long reports readable.
  autoTable(doc, {
    startY,
    margin: { left: MARGIN, right: MARGIN, bottom: 20 },
    head: [["Information", "Report value"]],
    body: entries.map(([field, value]) => [titleCase(field), displayValue(value)]),
    theme: "grid",
    styles: { font: "helvetica", fontSize: 9, cellPadding: 3, lineColor: BORDER, lineWidth: 0.2, textColor: TEXT, overflow: "linebreak" },
    headStyles: { fillColor: BLUE, textColor: [255, 255, 255], fontStyle: "bold" },
    columnStyles: { 0: { cellWidth: 55, fillColor: LIGHT_BLUE, fontStyle: "bold" }, 1: { cellWidth: "auto" } },
  });
  return doc.lastAutoTable.finalY + 9;
};

const safeFilename = (value) => cleanText(value).replace(/[^a-z0-9-_]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();

const createInvestorReportPdf = ({ extraction, report, ticker }) => {
  // Build a standalone A4 research output from the same validated data shown in the UI.
  const doc = new jsPDF({ unit: "mm", format: "a4", orientation: "portrait" });
  const metadata = extraction?.metadata || {};
  const facts = extraction?.extracted_facts || {};
  const insight = extraction?.investor_friendly_insight || {};
  const companyName = metadata.company_name || report?.companyName || "Annual Report Insight";
  const reportingYear = metadata.reporting_year || "Reporting year unavailable";
  const confidence = Math.round(Math.max(0, Math.min(1, Number(extraction?.confidence_score) || 0)) * 100);

  doc.setFillColor(...NAVY);
  doc.rect(0, 0, PAGE_WIDTH, 54, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(158, 190, 255);
  doc.text("CSE INSIGHT GENERATOR", MARGIN, 14);
  doc.setFontSize(22);
  doc.setTextColor(255, 255, 255);
  doc.text("Annual Report Insight", MARGIN, 28);
  doc.setFontSize(13);
  doc.text(cleanText(companyName), MARGIN, 40);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(203, 213, 225);
  doc.text(`${cleanText(ticker || report?.stockSymbol || "")} | ${cleanText(reportingYear)}`, MARGIN, 47);

  autoTable(doc, {
    startY: 60,
    margin: { left: MARGIN, right: MARGIN },
    body: [["Analysis", "Beginner-friendly AI analysis"], ["Confidence", `${confidence}%`], ["Verified evidence", `${extraction?.source_evidence?.length || 0} quotations`]],
    theme: "plain",
    styles: { font: "helvetica", fontSize: 9, cellPadding: 2.5, textColor: TEXT },
    columnStyles: { 0: { cellWidth: 38, textColor: MUTED }, 1: { fontStyle: "bold" } },
  });

  let y = doc.lastAutoTable.finalY + 10;
  y = addHeading(doc, "Investor Summary", y);
  y = addParagraph(doc, insight.summary, y, { fallback: "No summary was generated." });
  y = addHeading(doc, "Key Strengths", y);
  y = addList(doc, insight.key_strengths, y, "No strengths were identified.");
  y = addHeading(doc, "Key Concerns", y);
  y = addList(doc, insight.key_concerns, y, "No concerns were identified.");
  y = addHeading(doc, "Risk Explanation", y);
  y = addParagraph(doc, insight.risk_level_explanation, y, { fallback: "No risk explanation was generated." });

  Object.entries(facts).forEach(([section, sectionFacts]) => {
    y = addFactTable(doc, sectionLabels[section] || titleCase(section), sectionFacts, y);
  });

  y = addHeading(doc, "Verified Report Evidence", y);
  if (extraction?.source_evidence?.length) {
    extraction.source_evidence.forEach((item) => {
      y = addParagraph(doc, `"${displayValue(item.source_quote)}"`, y, { size: 9 });
      y = addParagraph(doc, `${titleCase(item.field || "Report fact")} | ${cleanText(item.source_id)}${item.page_number ? ` | Page ${item.page_number}` : ""}`, y - 2, { size: 8, color: MUTED });
    });
  } else {
    y = addParagraph(doc, "No verified quotations are available.", y, { color: MUTED });
  }

  y = addHeading(doc, "Information Not Found", y);
  y = addList(doc, extraction?.missing_fields?.map(titleCase), y, "All expected information was found.");
  y = addHeading(doc, "Important Notice", y);
  addParagraph(doc, insight.non_advisory_note || "This is an informational summary only and not financial advice.", y, { bold: true });

  addFooter(doc);
  return {
    doc,
    filename: `${safeFilename(ticker || report?.stockSymbol || companyName) || "annual-report"}-investor-insight.pdf`,
  };
};

const downloadInvestorReportPdf = (options) => {
  // jsPDF performs the browser download without sending report data to another service.
  const { doc, filename } = createInvestorReportPdf(options);
  doc.save(filename);
};

export { createInvestorReportPdf, downloadInvestorReportPdf };
