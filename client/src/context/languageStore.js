import { createContext, useContext } from "react";

export const LANGUAGE_STORAGE_KEY = "cse-insight-language";
export const supportedLanguages = [
  { code: "en", label: "English" },
  { code: "si", label: "සිංහල" },
  { code: "ta", label: "தமிழ்" },
];

export const LanguageContext = createContext(null);
export const useLanguage = () => useContext(LanguageContext);
