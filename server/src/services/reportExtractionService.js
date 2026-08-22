const fs = require("fs/promises");
const path = require("path");
const { PDFParse } = require("pdf-parse");
const OpenAI = require("openai");
const { AzureOpenAI } = OpenAI;
const { retrieveInvestorEvidence } = require("./reportRagService");
const {
  BEST_PROMPT_FILE,
  BEST_PROMPT_ID,
  BEST_PROMPT_NAME,
  BEST_PROMPT_PATH,
  EXTRACTION_TEMPLATE,
} = require("./selectedReportPrompt");

const SYSTEM_PROMPT = [
  "You extract structured financial information from retrieved annual-report evidence.",
  "Return only valid JSON and never include markdown fences or extra commentary.",
  "Use only the supplied RAG evidence. Do not use outside knowledge or infer an undisclosed fact.",
  "Keep unavailable extracted facts as null and list their dot-paths in missing_fields.",
  "For source_evidence, return objects with field, value, source_id, page_number, and source_quote.",
  "Every source_id must match a supplied RAG source ID and every source_quote must be copied exactly from that source.",
  "Ratios may be calculated only when all source values are present; state that the value is calculated.",
  "Preserve disclosed units and express Sri Lankan Rupee monetary amounts using the Rs. prefix.",
].join(" ");

// Reuse the Azure configuration from the research component without overwriting server-specific values.
require("dotenv").config({
  path: path.resolve(__dirname, "../../../component_2/.env"),
  override: false,
  quiet: true,
});

const isConfiguredSecret = (value) => {
  const normalized = String(value || "").trim().toLowerCase();
  return Boolean(normalized) && !normalized.includes("replace") && !normalized.includes("your_");
};

const isStandardOpenAIKey = (value) => /^sk-[a-z0-9_-]+$/i.test(String(value || "").trim());

const supportsTemperature = (model) => {
  const normalized = (model || "").trim().toLowerCase();
  return !normalized.startsWith("gpt-5") && !normalized.startsWith("o1") && !normalized.startsWith("o3") && !normalized.startsWith("o4");
};

const getModelSettings = () => {
  const temperature = Number(process.env.OPENAI_TEMPERATURE || 0);
  const maxInputChars = Number(process.env.REPORT_MAX_INPUT_CHARS || 80000);

  // Standard OpenAI keys and Azure resource keys use different clients and endpoints.
  if (isStandardOpenAIKey(process.env.OPENAI_API_KEY)) {
    return {
      client: new OpenAI({ apiKey: process.env.OPENAI_API_KEY }),
      model: process.env.OPENAI_MODEL || "gpt-4.1",
      temperature,
      maxInputChars,
    };
  }

  const azureSettings = {
    apiKey: process.env.AZURE_OPENAI_API_KEY,
    endpoint: process.env.AZURE_OPENAI_ENDPOINT,
    apiVersion: process.env.AZURE_OPENAI_API_VERSION,
    deployment: process.env.AZURE_OPENAI_DEPLOYMENT,
  };
  if (isConfiguredSecret(azureSettings.apiKey) && azureSettings.endpoint && azureSettings.apiVersion && azureSettings.deployment) {
    return {
      client: new AzureOpenAI({
        apiKey: azureSettings.apiKey,
        endpoint: azureSettings.endpoint,
        apiVersion: azureSettings.apiVersion,
      }),
      model: azureSettings.deployment,
      temperature,
      maxInputChars,
    };
  }

  const configError = new Error(
    "Configure OPENAI_API_KEY in server/.env or Azure OpenAI settings in component_2/.env before extracting reports."
  );
  configError.statusCode = 500;
  throw configError;
};

const stripCodeFences = (value) => {
  const trimmed = value.trim();
  if (!trimmed.startsWith("```")) return trimmed;
  const lines = trimmed.split("\n").slice(1);
  if (lines.at(-1)?.trim().startsWith("```")) lines.pop();
  return lines.join("\n").trim();
};

const cloneTemplate = () => JSON.parse(JSON.stringify(EXTRACTION_TEMPLATE));

const normalizeFromTemplate = (template, candidate) => {
  // Recursively remove unexpected keys and restore fields omitted by the model.
  if (Array.isArray(template)) return Array.isArray(candidate) ? candidate : [];
  if (template === null) return candidate === undefined || candidate === "" ? null : candidate;
  if (typeof template === "number") {
    const numericValue = Number(candidate);
    return Number.isFinite(numericValue) ? numericValue : template;
  }
  if (typeof template === "string") return typeof candidate === "string" ? candidate.trim() : template;
  if (template && typeof template === "object") {
    const source = candidate && typeof candidate === "object" && !Array.isArray(candidate) ? candidate : {};
    return Object.fromEntries(
      Object.entries(template).map(([key, nestedTemplate]) => [key, normalizeFromTemplate(nestedTemplate, source[key])])
    );
  }
  return candidate;
};

const collectMissingFields = (facts) => {
  const missing = [];
  for (const [section, fields] of Object.entries(facts || {})) {
    for (const [field, value] of Object.entries(fields || {})) {
      if (value === null || value === "" || (Array.isArray(value) && !value.length)) missing.push(`${section}.${field}`);
    }
  }
  return missing;
};

const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim().toLowerCase();

const validateSourceEvidence = (evidence, validationSources) => {
  if (!Array.isArray(evidence)) return [];
  const sourcesById = new Map(validationSources.map((source) => [source.sourceId, source]));

  // A citation is accepted only when its exact quote exists in its declared evidence passage.
  // This is the runtime safeguard against unsupported or hallucinated source references.
  return evidence.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const source = sourcesById.get(item.source_id);
    const quote = String(item.source_quote || "").trim();
    if (!source || quote.length < 8 || !normalizeText(source.text).includes(normalizeText(quote))) return [];
    return [{
      field: String(item.field || "").trim(),
      value: item.value ?? null,
      source_id: source.sourceId,
      page_number: source.estimatedPage || null,
      source_quote: quote,
    }];
  });
};

const normalizeExtractionShape = (value, metadata, validationSources) => {
  // Model-controlled metadata is replaced with trusted runtime values for reproducibility.
  const normalized = normalizeFromTemplate(cloneTemplate(), value);
  normalized.metadata = {
    ...normalized.metadata,
    pdf_name: metadata.pdfName,
    prompt_id: BEST_PROMPT_ID,
    model: metadata.model,
    generated_at: new Date().toISOString(),
  };
  normalized.source_evidence = validateSourceEvidence(value?.source_evidence, validationSources);
  normalized.missing_fields = [...new Set([
    ...collectMissingFields(normalized.extracted_facts),
    ...(Array.isArray(value?.missing_fields) ? value.missing_fields.map(String) : []),
  ])];
  normalized.confidence_score = Math.max(0, Math.min(1, normalized.confidence_score));
  normalized.investor_friendly_insight.non_advisory_note =
    "This is an informational summary only and not financial advice.";
  return normalized;
};

const extractPdfText = async (pdfPath) => {
  // pdf-parse v2 uses an explicit parser lifecycle; destroy() releases memory after large reports.
  const parser = new PDFParse({ data: await fs.readFile(pdfPath) });
  try {
    const pdfData = await parser.getText();
    return { text: (pdfData.text || "").trim(), pageCount: pdfData.total || pdfData.pages?.length || null };
  } finally {
    await parser.destroy();
  }
};

const loadSelectedPrompt = async () => {
  try {
    return await fs.readFile(BEST_PROMPT_PATH, "utf8");
  } catch (error) {
    const promptError = new Error(`Selected research prompt could not be loaded from ${BEST_PROMPT_PATH}.`);
    promptError.statusCode = 500;
    promptError.cause = error;
    throw promptError;
  }
};

const summarizeExtraction = (output) =>
  output.investor_friendly_insight.summary ||
  `Prompt 08 extracted ${Object.keys(output.extracted_facts).length} investor information sections.`;

const extractAnnualReport = async ({ pdfPath, pdfName }) => {
  // End-to-end Component 2 pipeline: PDF text -> relevant evidence -> selected prompt -> validated JSON.
  const [promptText, pdfResult] = await Promise.all([loadSelectedPrompt(), extractPdfText(pdfPath)]);
  if (!pdfResult.text) {
    const extractionError = new Error("The uploaded PDF did not produce readable text. It may require OCR.");
    extractionError.statusCode = 400;
    throw extractionError;
  }

  const { client, model, temperature, maxInputChars } = getModelSettings();
  const ragResult = retrieveInvestorEvidence(pdfResult.text, {
    estimatedPageCount: pdfResult.pageCount,
    topK: process.env.REPORT_RAG_TOP_K,
  });
  const ragContext = ragResult.context.slice(0, maxInputChars);
  const request = {
    model,
    instructions: SYSTEM_PROMPT,
    input: `${promptText}\n\nReport file: ${pdfName}\n\nRetrieved RAG Evidence:\n${ragContext}`,
  };
  if (supportsTemperature(model)) request.temperature = temperature;

  let response;
  try {
    response = await client.responses.create(request);
  } catch (error) {
    const providerError = new Error(
      error.status === 401
        ? "The configured AI provider rejected its credentials. Check the OpenAI or Azure OpenAI settings."
        : error.status === 429
          ? "The AI provider rate limit or quota was reached. Please try again later or check the deployment quota."
          : `The AI provider could not process this report${error.status ? ` (HTTP ${error.status})` : ""}.`
    );
    providerError.statusCode = error.status && error.status < 500 ? error.status : 502;
    throw providerError;
  }
  const rawOutput = (response.output_text || "").trim();
  if (!rawOutput) {
    const responseError = new Error("The model returned an empty extraction response.");
    responseError.statusCode = 502;
    throw responseError;
  }

  let modelOutput;
  try {
    modelOutput = JSON.parse(stripCodeFences(rawOutput));
  } catch (error) {
    const parseError = new Error(`The extraction response was not valid JSON. ${error.message}`);
    parseError.statusCode = 502;
    throw parseError;
  }

  // Persist only the normalized schema and evidence that passed exact-quote validation.
  const parsedOutput = normalizeExtractionShape(modelOutput, { pdfName, model }, ragResult.validationSources);
  return {
    promptFileName: BEST_PROMPT_FILE,
    promptId: BEST_PROMPT_ID,
    promptName: BEST_PROMPT_NAME,
    ragSources: ragResult.sources,
    ragChunkCount: ragResult.chunkCount,
    ragSelectedCount: ragResult.selectedCount,
    rawOutput,
    parsedOutput,
    summary: summarizeExtraction(parsedOutput),
  };
};

module.exports = {
  BEST_PROMPT_ID,
  extractAnnualReport,
  extractPdfText,
  getModelSettings,
  isStandardOpenAIKey,
  normalizeExtractionShape,
  validateSourceEvidence,
};
