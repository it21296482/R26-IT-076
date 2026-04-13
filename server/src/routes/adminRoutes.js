const express = require("express");
const { body } = require("express-validator");
const multer = require("multer");
const {
  getAdminOverview,
  listUsers,
  createUser,
  updateUser,
  resetUserPassword,
  deleteUser,
  updateStockRecord,
  deleteStockRecord,
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
  "/users",
  [
    body("name").trim().isLength({ min: 2, max: 80 }).withMessage("Name must be 2 to 80 characters."),
    body("email").isEmail().withMessage("Enter a valid email address."),
    body("password")
      .isLength({ min: 8, max: 64 })
      .withMessage("Password must be between 8 and 64 characters."),
    body("role").isIn(["admin", "user"]).withMessage("Role must be either admin or user."),
  ],
  validate,
  createUser
);
router.put(
  "/users/:userId",
  [
    body("name").trim().isLength({ min: 2, max: 80 }).withMessage("Name must be 2 to 80 characters."),
    body("email").isEmail().withMessage("Enter a valid email address."),
    body("role").isIn(["admin", "user"]).withMessage("Role must be either admin or user."),
  ],
  validate,
  updateUser
);
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
router.delete("/users/:userId", deleteUser);
router.put(
  "/stocks/:stockId",
  [
    body("symbol")
      .trim()
      .isLength({ min: 2, max: 20 })
      .withMessage("Symbol must be between 2 and 20 characters."),
    body("companyName")
      .trim()
      .isLength({ min: 2, max: 120 })
      .withMessage("Company name must be between 2 and 120 characters."),
    body("tradeDate").isISO8601().withMessage("Enter a valid trade date."),
    body("open").isFloat({ min: 0 }).withMessage("Open price must be a non-negative number."),
    body("high").isFloat({ min: 0 }).withMessage("High price must be a non-negative number."),
    body("low").isFloat({ min: 0 }).withMessage("Low price must be a non-negative number."),
    body("close").isFloat({ min: 0 }).withMessage("Close price must be a non-negative number."),
    body("adjustedClose")
      .optional({ values: "falsy" })
      .isFloat({ min: 0 })
      .withMessage("Adjusted close must be a non-negative number."),
    body("volume").isFloat({ min: 0 }).withMessage("Volume must be a non-negative number."),
    body("notes")
      .optional()
      .trim()
      .isLength({ max: 300 })
      .withMessage("Notes cannot exceed 300 characters."),
  ],
  validate,
  updateStockRecord
);
router.delete("/stocks/:stockId", deleteStockRecord);

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
