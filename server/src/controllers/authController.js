const User = require("../models/User");
const createToken = require("../utils/createToken");

const cookieOptions = {
  httpOnly: true,
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
  maxAge: 7 * 24 * 60 * 60 * 1000,
};

const buildAuthResponse = (user) => ({
  _id: user._id,
  name: user.name,
  email: user.email,
  role: user.role,
  createdAt: user.createdAt,
});

const registerUser = async (req, res) => {
  const { name, email, password } = req.body;

  const existingUser = await User.findOne({ email: email.toLowerCase() });

  if (existingUser) {
    return res.status(409).json({ message: "An account already exists for this email." });
  }

  const user = await User.create({
    name,
    email: email.toLowerCase(),
    password,
    role: "user",
  });

  return res.status(201).json({
    message: "User account created successfully.",
    user: buildAuthResponse(user),
  });
};

const loginWithRole = async (req, res, expectedRole) => {
  const { email, password } = req.body;

  const user = await User.findOne({ email: email.toLowerCase() }).select("+password");

  if (!user || user.role !== expectedRole) {
    return res.status(401).json({ message: "Invalid credentials for this portal." });
  }

  const isMatch = await user.comparePassword(password);

  if (!isMatch) {
    return res.status(401).json({ message: "Invalid email or password." });
  }

  user.lastLoginAt = new Date();
  await user.save();

  const token = createToken({ userId: user._id, role: user.role });
  res.cookie("token", token, cookieOptions);

  return res.status(200).json({
    message: `${expectedRole === "admin" ? "Admin" : "User"} login successful.`,
    user: buildAuthResponse(user),
  });
};

const loginUser = async (req, res) => loginWithRole(req, res, "user");

const loginAdmin = async (req, res) => loginWithRole(req, res, "admin");

const logout = async (req, res) => {
  res.clearCookie("token", cookieOptions);
  return res.status(200).json({ message: "Logged out successfully." });
};

const getCurrentUser = async (req, res) =>
  res.status(200).json({
    user: buildAuthResponse(req.user),
  });

module.exports = {
  registerUser,
  loginUser,
  loginAdmin,
  logout,
  getCurrentUser,
};
