const mongoose = require("mongoose");

const connectDatabase = async () => {
  const { MONGODB_URI } = process.env;

  if (!MONGODB_URI) {
    throw new Error("MONGODB_URI is not configured.");
  }

  await mongoose.connect(MONGODB_URI);
  // eslint-disable-next-line no-console
  console.log("MongoDB connected");
};

module.exports = connectDatabase;
