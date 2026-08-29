require("dotenv").config();
const axios = require("axios");

async function test() {
  const response = await axios.get(
    "https://api.marketaux.com/v1/news/all",
    {
      params: {
        api_token: process.env.MARKETAUX_API_KEY,
        symbols: "NDB.N0000",
        limit: 3
      }
    }
  );

  console.log(response.data);
}

test().catch(console.error);