import { useLanguage } from "../context/languageStore";
import { supportedLanguages } from "../context/languageStore";

function LanguageSelector() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <label className="flex items-center gap-2 text-xs font-semibold text-slate-600" title={t("Choose your language")}>
      <span className="hidden sm:inline">{t("Language")}</span>
      <select
        aria-label={t("Choose your language")}
        className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none transition focus:border-blue-400"
        onChange={(event) => setLanguage(event.target.value)}
        value={language}
      >
        {supportedLanguages.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
      </select>
    </label>
  );
}

export default LanguageSelector;
