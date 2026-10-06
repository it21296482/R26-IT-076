import { useMemo, useState } from "react";
import { LANGUAGE_STORAGE_KEY, LanguageContext, supportedLanguages } from "./languageStore";

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => localStorage.getItem(LANGUAGE_STORAGE_KEY) || "en");
  const setLanguage = (nextLanguage) => {
    const next = supportedLanguages.some(({ code }) => code === nextLanguage) ? nextLanguage : "en";
    localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
    setLanguageState(next);
  };

  const value = useMemo(() => ({ language, setLanguage, supportedLanguages }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
