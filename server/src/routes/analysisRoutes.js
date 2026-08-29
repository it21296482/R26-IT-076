const express = require("express");
const { body, param } = require("express-validator");
const { createAnalysis, getAnalysis } = require("../controllers/analysisController");
const { protect, authorize } = require("../middleware/auth");
const validate = require("../middleware/validate");

const router = express.Router();

router.use(protect, authorize("user"));
router.post(
  "/",
  [
    body("stockSymbol").trim().isLength({ min: 2, max: 20 }).withMessage("Select a valid stock."),
    body("reportId").isMongoId().withMessage("Upload a valid financial report."),
  ],
  validate,
  createAnalysis
);
router.get(
  "/:analysisId",
  [param("analysisId").isMongoId().withMessage("Invalid analysis identifier.")],
  validate,
  getAnalysis
);

module.exports = router;

