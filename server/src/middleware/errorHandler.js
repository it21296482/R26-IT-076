const errorHandler = (error, req, res, next) => {
  if (res.headersSent) {
    return next(error);
  }

  if (error.name === "ValidationError") {
    return res.status(400).json({
      message: "Validation failed.",
      errors: Object.values(error.errors).map((item) => item.message),
    });
  }

  if (error.code === 11000) {
    return res.status(409).json({
      message: "A record with this unique value already exists.",
    });
  }

  if (error.name === "MulterError") {
    return res.status(400).json({
      message:
        error.code === "LIMIT_FILE_SIZE"
          ? "CSV upload must be 5MB or smaller."
          : "Please upload a valid CSV file.",
    });
  }

  return res.status(error.statusCode || 500).json({
    message: error.message || "Internal server error.",
  });
};

module.exports = errorHandler;
