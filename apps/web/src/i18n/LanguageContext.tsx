import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { TRANSLATIONS, type Locale, type TranslationKey } from "./translations";

const STORAGE_KEY = "synapse.lang";

interface LanguageContextValue {
  locale: Locale;
  setLocale: (next: Locale) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

function resolveInitialLocale(): Locale {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "tr") {
      return saved;
    }
  } catch {
    // Ignore storage access failures in hardened browser sandboxes.
  }
  if (
    typeof navigator !== "undefined" &&
    !navigator.userAgent.includes("jsdom") &&
    navigator.language.toLowerCase().startsWith("tr")
  ) {
    return "tr";
  }
  return "en";
}

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocaleState] = useState<Locale>(resolveInitialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore storage write failures.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.title = TRANSLATIONS[locale].docTitle;
  }, [locale]);

  const t = useCallback((key: TranslationKey) => TRANSLATIONS[locale][key], [locale]);

  return (
    <LanguageContext.Provider value={{ locale, setLocale, t }}>{children}</LanguageContext.Provider>
  );
};

export function useI18n(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useI18n must be used within a LanguageProvider");
  }
  return ctx;
}
