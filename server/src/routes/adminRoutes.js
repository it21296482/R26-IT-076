const express = require("express");
const { body } = require("express-validator");
const multer = require("multer");
const {
  getAdminOverview,
  listUsers,
  resetUserPassword,
  uploadStockCsv,
} = require("../controllers/adminController");
const { protect, authorize } = require("../middleware/auth");
const validate = require("../middleware/validate");

const router = express.Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 5 * 1024 * 1024,
  },
  fileFilter(req, file, callback) {
    if (file.originalname.toLowerCase().endsWith(".csv")) {
      return callback(null, true);
    }

    return callback(new multer.MulterError("LIMIT_UNEXPECTED_FILE", "file"));
  },
});

router.use(protect, authorize("admin"));

router.get("/overview", getAdminOverview);
router.get("/users", listUsers);
router.post(
  "/users/:userId/reset-password",
  [
    body("newPassword")
      .isLength({ min: 8, max: 64 })
      .withMessage("New password must be between 8 and 64 characters."),
  ],
  validate,
  resetUserPassword
);

router.post(
  "/stocks/upload-csv",
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
    body("notes")
      .optional()
      .trim()
      .isLength({ max: 300 })
      .withMessage("Notes cannot exceed 300 characters."),
  ],
  validate,
  uploadStockCsv
);

module.exports = router;
