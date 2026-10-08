import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { messages, translate } from "../src/i18n/messages.js";

test("every UI dictionary entry has both Sinhala and Tamil with matching placeholders", () => {
  for (const [english, translations] of Object.entries(messages)) {
    const placeholders = (text) => (text.match(/\{\w+\}/g) || []).sort();
    assert.equal(translations.length, 2, english);
    for (const [index, value] of translations.entries()) {
      assert.ok(value.trim(), english);
      assert.match(value, index === 0 ? /[\u0D80-\u0DFF]/ : /[\u0B80-\u0BFF]/, english);
      assert.deepEqual(placeholders(value), placeholders(english), english);
    }
  }
});

test("switching languages preserves ticker, user input, and numeric placeholders", () => {
  for (const language of ["en", "si", "ta"]) {
    assert.ok(translate("Ready to analyze {symbol}", language, { symbol: "JKH.N0000" }).includes("JKH.N0000"));
    const result = translate("Page {page} of {total}", language, { page: 2, total: 10 });
    assert.ok(result.includes("2") && result.includes("10"));
    assert.equal(translate("BIL.N0000", language), "BIL.N0000");
    assert.equal(translate(19.80, language), 19.80);
  }
});

test("English, unknown text, and invalid language have safe defaults", () => {
  assert.equal(translate("Start Analysis", "en"), "Start Analysis");
  assert.equal(translate("Start Analysis", "fr"), "Start Analysis");
  assert.equal(translate("Original source quote", "si"), "Original source quote");
  assert.equal(translate("Sign In", "si"), "පිවිසෙන්න");
  assert.equal(translate("Sign In", "ta"), "உள்நுழையவும்");
});

test("all explicit translated UI phrases exist in the bilingual dictionary", () => {
  const files = [
    "components/LanguageSelector", "components/SiteHeader", "components/AuthShell",
    "components/BrandLogo", "components/ProtectedRoute", "pages/HomePage",
    "pages/UserLoginPage", "pages/RegisterPage", "pages/AdminLoginPage",
    "pages/UserDashboardPage", "pages/InsightPreviewPage", "pages/AdminDashboardPage",
  ];
  for (const file of files) {
    const source = readFileSync(new URL(`../src/${file}.jsx`, import.meta.url), "utf8");
    for (const [, phrase] of source.matchAll(/\bt\("([^"\\]*(?:\\.[^"\\]*)*)"/g)) {
      const text = JSON.parse(`"${phrase}"`);
      assert.ok(Object.hasOwn(messages, text), `${file}: missing translation for ${text}`);
    }
  }
});

test("dynamic admin feedback is localized without changing email, company, or counts", () => {
  for (const language of ["si", "ta"]) {
    const user = translate("Password reset completed for user+test@example.com.", language);
    assert.ok(user.includes("user+test@example.com"));
    assert.ok(!user.includes("Password reset completed"));
    const csv = translate("Imported 250 historical price rows for John Keells Holdings PLC.", language);
    assert.ok(csv.includes("250") && csv.includes("John Keells Holdings PLC"));
    assert.ok(!csv.includes("historical price rows"));
  }
});
