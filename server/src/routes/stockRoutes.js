const express = require("express");
const { listStocks, getStockUniverse, getMarketPrices } = require("../controllers/stockController");
const { protect } = require("../middleware/auth");

const router = express.Router();

router.use(protect);
router.get("/", listStocks);
router.get("/universe", getStockUniverse);
router.get("/prices", getMarketPrices);

module.exports = router;
