import { useEffect, useState } from "react";
import { LANGUAGE_STORAGE_KEY, LanguageContext, supportedLanguages } from "./languageStore";
import { translate } from "../i18n/messages";

const validLanguage = (value) => supportedLanguages.some(({ code }) => code === value) ? value : "en";

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    try { return validLanguage(localStorage.getItem(LANGUAGE_STORAGE_KEY)); }
    catch { return "en"; }
  });
  const setLanguage = (nextLanguage) => {
    const next = validLanguage(nextLanguage);
    try { localStorage.setItem(LANGUAGE_STORAGE_KEY, next); }
    catch { /* Language selection still works when browser storage is disabled. */ }
    setLanguageState(next);
  };

  useEffect(() => { document.documentElement.lang = language; }, [language]);
  const value = {
    language, setLanguage, supportedLanguages,
    locale: language === "en" ? "en-LK" : `${language}-LK`,
    t: (text, values) => translate(text, language, values),
  };
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
