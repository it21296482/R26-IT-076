const User = require("../models/User");

const seedAdmin = async () => {
  const name = process.env.ADMIN_SEED_NAME;
  const email = process.env.ADMIN_SEED_EMAIL;
  const password = process.env.ADMIN_SEED_PASSWORD;

  if (!name || !email || !password) {
    return;
  }

  const existingAdmin = await User.findOne({ email: email.toLowerCase() });

  if (!existingAdmin) {
    await User.create({
      name,
      email: email.toLowerCase(),
      password,
      role: "admin",
    });
    // eslint-disable-next-line no-console
    console.log(`Seeded admin account for ${email}`);
  }
};

module.exports = seedAdmin;
