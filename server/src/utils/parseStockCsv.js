const { parse } = require("csv-parse/sync");

const normalizeValue = (value) => String(value ?? "").trim();

const normalizeNumber = (value) => {
  const sanitized = normalizeValue(value).replace(/,/g, "");

  if (!sanitized) {
    return null;
  }

  const parsed = Number(sanitized);

  if (Number.isNaN(parsed)) {
    throw new Error(`Invalid numeric value "${value}" found in CSV.`);
  }

  return parsed;
};

const getField = (row, aliases, required = false) => {
  const normalizedEntries = Object.entries(row).reduce((result, [key, value]) => {
    result[String(key).toLowerCase().replace(/[^a-z0-9]/g, "")] = value;
    return result;
  }, {});

  for (const alias of aliases) {
    const normalizedAlias = alias.toLowerCase().replace(/[^a-z0-9]/g, "");

    if (normalizedEntries[normalizedAlias] !== undefined && normalizedEntries[normalizedAlias] !== "") {
      return normalizedEntries[normalizedAlias];
    }
  }

  if (required) {
    throw new Error(`Missing required CSV column. Expected one of: ${aliases.join(", ")}`);
  }

  return null;
};

const parseStockCsv = (buffer) => {
  const records = parse(buffer, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
  });

  if (!records.length) {
    throw new Error("The uploaded CSV file is empty.");
  }

  return records.map((row, index) => {
    const tradeDate = getField(row, ["tradeDate", "date", "tradingDate"], true);
    const open = normalizeNumber(getField(row, ["open", "openingPrice"], true));
    const high = normalizeNumber(getField(row, ["high", "highPrice"], true));
    const low = normalizeNumber(getField(row, ["low", "lowPrice"], true));
    const close = normalizeNumber(getField(row, ["close", "closingPrice"], true));
    const adjustedClose = normalizeNumber(getField(row, ["adjustedClose", "adjClose", "adjustedclose"]));
    const volume = normalizeNumber(getField(row, ["volume", "tradeVolume"], true));

    if (!tradeDate || Number.isNaN(new Date(tradeDate).getTime())) {
      throw new Error(`Invalid trade date at CSV row ${index + 2}.`);
    }

    return {
      tradeDate: new Date(tradeDate),
      open,
      high,
      low,
      close,
      adjustedClose,
      volume,
    };
  });
};

module.exports = parseStockCsv;
