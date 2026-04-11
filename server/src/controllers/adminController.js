const Stock = require("../models/Stock");
const User = require("../models/User");
const parseStockCsv = require("../utils/parseStockCsv");

const listUsers = async (req, res) => {
  const users = await User.find()
    .select("name email role createdAt lastLoginAt updatedAt")
    .sort({ createdAt: -1 });

  return res.status(200).json({ users });
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
  resetUserPassword,
  uploadStockCsv,
};
