const express = require("express");
const path = require("path");
const fs = require("fs");
const multer = require("multer");
const { body } = require("express-validator");
const { listUserReports, uploadFinancialReport } = require("../controllers/reportController");
const { protect, authorize } = require("../middleware/auth");
const validate = require("../middleware/validate");

const router = express.Router();
const uploadDirectory = path.join(__dirname, "../../uploads/reports");

const storage = multer.diskStorage({
  destination(req, file, callback) {
    // Ensure the local report archive exists before Multer writes the uploaded PDF.
    fs.mkdirSync(uploadDirectory, { recursive: true });
    callback(null, uploadDirectory);
  },
  filename(req, file, callback) {
    // Normalize the stored filename so repeated uploads stay filesystem-safe and unique.
    const extension = path.extname(file.originalname).toLowerCase() || ".pdf";
    const safeBaseName = path.basename(file.originalname, extension).replace(/[^a-zA-Z0-9-_]/g, "-");
    callback(null, `${Date.now()}-${safeBaseName}${extension}`);
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024,
  },
  fileFilter(req, file, callback) {
    const isPdf = file.mimetype === "application/pdf" || file.originalname.toLowerCase().endsWith(".pdf");

    if (isPdf) {
      return callback(null, true);
    }

    return callback(new multer.MulterError("LIMIT_UNEXPECTED_FILE", "file"));
  },
});

router.use(protect, authorize("user"));

// The workspace uses this list to show a student's recent report intake activity.
router.get("/", listUserReports);
router.post(
  "/upload",
  upload.single("file"),
  [
    body("symbol")
      .trim()
      .isLength({ min: 2, max: 20 })
      .withMessage("Symbol must be between 2 and 20 characters."),
    body("companyName")
      .trim()
      .isLength({ min: 2, max: 120 })
      .withMessage("Company name must be between 2 and 120 characters."),
  ],
  validate,
  uploadFinancialReport
);

module.exports = router;
