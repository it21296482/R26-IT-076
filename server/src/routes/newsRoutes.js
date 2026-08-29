const express = require("express");

const {
  getNews
} = require("../controllers/newsController");

const router = express.Router();

router.get("/", getNews);

module.exports = router;