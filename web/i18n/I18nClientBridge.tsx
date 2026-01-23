"use client";

import { useGlobal } from "@/context/GlobalContext";
import { I18nProvider } from "./I18nProvider";

export function I18nClientBridge({ children }: { children: React.ReactNode }) {
  const { uiSettings } = useGlobal();
  return <I18nProvider language={uiSettings.language}>{children}</I18nProvider>;
}
