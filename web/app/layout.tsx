import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { GlobalProvider } from "@/context/GlobalContext";
import ThemeScript from "@/components/ThemeScript";
import LayoutWrapper from "@/components/LayoutWrapper";
import { I18nClientBridge } from "@/i18n/I18nClientBridge";

// Use Inter font with swap display for better loading
const font = Inter({
  subsets: ["latin"],
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
});

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "DeepTutor Platform",
  description: "Multi-Agent Teaching & Research Copilot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const runtimeConfig = {
    API_BASE_URL: process.env.API_BASE_URL || "http://localhost:8004/realtimex",
  };

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeScript />
        <script
          dangerouslySetInnerHTML={{
            __html: `window.__RUNTIME_CONFIG__=${JSON.stringify(runtimeConfig)};`,
          }}
        />
      </head>
      <body className={font.className}>
        <GlobalProvider>
          <I18nClientBridge>
            <LayoutWrapper>
              <div className="flex h-screen bg-slate-50 dark:bg-slate-900 overflow-hidden transition-colors duration-200">
                <Sidebar />
                <main className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-900">
                  {children}
                </main>
              </div>
            </LayoutWrapper>
          </I18nClientBridge>
        </GlobalProvider>
      </body>
    </html>
  );
}
