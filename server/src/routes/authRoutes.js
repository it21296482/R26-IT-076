const express = require("express");
const { body } = require("express-validator");
const {
  registerUser,
  loginUser,
  loginAdmin,
  logout,
  getCurrentUser,
} = require("../controllers/authController");
const { protect } = require("../middleware/auth");
const validate = require("../middleware/validate");

const router = express.Router();

const emailValidator = body("email").isEmail().withMessage("Enter a valid email address.");
const passwordValidator = body("password")
  .isLength({ min: 8 })
  .withMessage("Password must contain at least 8 characters.");

router.post(
  "/register",
  [
    body("name").trim().isLength({ min: 2, max: 80 }).withMessage("Name must be 2 to 80 characters."),
    emailValidator,
    passwordValidator,
  ],
  validate,
  registerUser
);

router.post("/login/user", [emailValidator, passwordValidator], validate, loginUser);
router.post("/login/admin", [emailValidator, passwordValidator], validate, loginAdmin);
router.post("/logout", logout);
router.get("/me", protect, getCurrentUser);

module.exports = router;
