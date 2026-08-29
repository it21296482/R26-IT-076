require("dotenv").config();
const axios = require("axios");

const BASE_URL =
  "https://api.marketaux.com/v1/entity/search";

const companies = [
  "Browns Investments",
  "John Keells",
  "John Keells Holdings PLC",
  "JKH",

  "NDB",
  "NDB Bank",
  "National Development Bank PLC",
  
  "Hayleys",
  "Commercial Bank of Ceylon",
  "Dialog Axiata",
  "Sampath Bank",
  "Nations Trust Bank"
];

async function findCompanySymbols() {
  const apiKey = process.env.MARKETAUX_API_KEY;

  for (const company of companies) {
    try {
      const response = await axios.get(BASE_URL, {
        params: {
          api_token: apiKey,
          search: company,
          countries: "lk"
        }
      });

      console.log("\n==============================");
      console.log("SEARCH:", company);
      console.log("==============================");

      console.table(
        (response.data.data || []).map((entity) => ({
          name: entity.name,
          symbol: entity.symbol,
          type: entity.type,
          exchange: entity.exchange,
          country: entity.country
        }))
      );

    } catch (error) {
      console.error(
        "Failed:",
        company,
        error.response?.data || error.message
      );
    }
  }
}

findCompanySymbols();