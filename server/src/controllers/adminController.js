const Stock = require("../models/Stock");
const User = require("../models/User");
const parseStockCsv = require("../utils/parseStockCsv");

const listUsers = async (req, res) => {
  const users = await User.find()
    .select("name email role createdAt lastLoginAt updatedAt")
    .sort({ createdAt: -1 });

  return res.status(200).json({ users });
};

const createUser = async (req, res) => {
  const { name, email, password, role } = req.body;
  const normalizedEmail = email.toLowerCase().trim();

  const existingUser = await User.findOne({ email: normalizedEmail });

  if (existingUser) {
    return res.status(409).json({ message: "An account already exists for this email." });
  }

  const user = await User.create({
    name: name.trim(),
    email: normalizedEmail,
    password,
    role,
  });

  return res.status(201).json({
    message: `User created successfully for ${user.email}.`,
    user,
  });
};

const updateUser = async (req, res) => {
  const { userId } = req.params;
  const { name, email, role } = req.body;
  const normalizedEmail = email.toLowerCase().trim();

  const user = await User.findById(userId);

  if (!user) {
    return res.status(404).json({ message: "User not found." });
  }

  const emailOwner = await User.findOne({ email: normalizedEmail });

  if (emailOwner && emailOwner._id.toString() !== userId) {
    return res.status(409).json({ message: "Another account already uses this email." });
  }

  user.name = name.trim();
  user.email = normalizedEmail;
  user.role = role;
  await user.save();

  return res.status(200).json({
    message: `User updated successfully for ${user.email}.`,
    user,
  });
};

const resetUserPassword = async (req, res) => {
  const { userId } = req.params;
  const { newPassword } = req.body;

  const user = await User.findById(userId).select("+password");

  if (!user) {
    return res.status(404).json({ message: "User not found." });
  }

  user.password = newPassword;
  await user.save();

  return res.status(200).json({
    message: `Password reset completed for ${user.email}.`,
  });
};

const deleteUser = async (req, res) => {
  const { userId } = req.params;

  if (req.user._id.toString() === userId) {
    return res.status(400).json({ message: "You cannot delete the currently signed-in admin account." });
  }

  const user = await User.findById(userId);

  if (!user) {
    return res.status(404).json({ message: "User not found." });
  }

  await user.deleteOne();

  return res.status(200).json({
    message: `User deleted successfully for ${user.email}.`,
  });
};

const updateStockRecord = async (req, res) => {
  const { stockId } = req.params;
  const {
    symbol,
    companyName,
    tradeDate,
    open,
    high,
    low,
    close,
    adjustedClose,
    volume,
    notes,
  } = req.body;

  const stock = await Stock.findById(stockId);

  if (!stock) {
    return res.status(404).json({ message: "Stock record not found." });
  }

  stock.symbol = symbol.trim().toUpperCase();
  stock.companyName = companyName.trim();
  stock.tradeDate = new Date(tradeDate);
  stock.open = Number(open);
  stock.high = Number(high);
  stock.low = Number(low);
  stock.close = Number(close);
  stock.adjustedClose = adjustedClose === "" || adjustedClose === null ? null : Number(adjustedClose);
  stock.volume = Number(volume);
  stock.notes = notes?.trim() || "";
  await stock.save();

  return res.status(200).json({
    message: `Stock record updated for ${stock.symbol}.`,
    stock,
  });
};

const deleteStockRecord = async (req, res) => {
  const { stockId } = req.params;
  const stock = await Stock.findById(stockId);

  if (!stock) {
    return res.status(404).json({ message: "Stock record not found." });
  }

  await stock.deleteOne();

  return res.status(200).json({
    message: `Stock record deleted for ${stock.symbol}.`,
  });
};

const uploadStockCsv = async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ message: "Please upload a CSV file." });
  }

  const records = parseStockCsv(req.file.buffer);
  const symbol = req.body.symbol.toUpperCase().trim();
  const companyName = req.body.companyName.trim();
  const notes = req.body.notes?.trim() || "";
  const source = `csv-upload:${req.file.originalname}`;

  const operations = records.map((record) => ({
    updateOne: {
      filter: {
        symbol,
        tradeDate: record.tradeDate,
      },
      update: {
        $set: {
          ...record,
          symbol,
          companyName,
          notes,
          source,
          createdBy: req.user._id,
        },
      },
      upsert: true,
    },
  }));

  const result = await Stock.bulkWrite(operations, { ordered: false });

  return res.status(201).json({
    message: `Imported ${records.length} historical price rows for ${companyName}.`,
    importSummary: {
      matched: result.matchedCount,
      modified: result.modifiedCount,
      upserted: result.upsertedCount,
      totalRows: records.length,
    },
  });
};

const getAdminOverview = async (req, res) => {
  const [userCount, adminCount, stockRecordCount, companyCount, latestStocks] = await Promise.all([
    User.countDocuments({ role: "user" }),
    User.countDocuments({ role: "admin" }),
    Stock.countDocuments(),
    Stock.distinct("symbol").then((items) => items.length),
    Stock.find().sort({ tradeDate: -1, createdAt: -1 }).limit(8),
  ]);

  return res.status(200).json({
    metrics: {
      userCount,
      adminCount,
      stockRecordCount,
      companyCount,
    },
    latestStocks,
  });
};

module.exports = {
  getAdminOverview,
  listUsers,
  createUser,
  updateUser,
  resetUserPassword,
  deleteUser,
  updateStockRecord,
  deleteStockRecord,
  uploadStockCsv,
};
