function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function validateEntities(article) {
  const articleText = normalize(
    `${article.title || ""} ${article.description || ""}`
  );

  const entities = article.entities || [];

  const genericWords = new Set([
    "plc",
    "limited",
    "ltd",
    "company",
    "companies",
    "holdings",
    "group",
    "bank",
    "finance",
    "financial"
  ]);

  return entities.filter((entity) => {
    const companyName = normalize(entity.name);

    const importantWords = companyName
      .split(" ")
      .filter(
        (word) =>
          word.length >= 4 &&
          !genericWords.has(word)
      );

    if (importantWords.length === 0) {
      return false;
    }

    const matchedWords = importantWords.filter((word) =>
      articleText.includes(word)
    );

    // Single distinctive company name:
    // "Hayleys" → one match is enough
    if (importantWords.length === 1) {
      return matchedWords.length === 1;
    }

    // Multi-word company:
    // require at least 2 distinctive words
    return matchedWords.length >= 2;
  });
}

module.exports = {
  validateEntities
};