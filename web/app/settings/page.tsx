"use client";

import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Sun,
  Moon,
  Globe,
  Save,
  RotateCcw,
  Loader2,
  Check,
  Server,
  AlertCircle,
  Database,
  Search,
  MessageSquare,
  Volume2,
  Cpu,
  Key,
  Brain,
  Eye,
  EyeOff,
  RefreshCw,
  CheckCircle,
  XCircle,
  Info,
  Sliders,
} from "lucide-react";
import { apiUrl } from "@/lib/api";
import { getTranslation } from "@/lib/i18n";

import { useGlobal } from "@/context/GlobalContext";

// --- Types matching backend ---

interface UISettings {
  theme: "light" | "dark";
  language: "zh" | "en";
  output_language: "zh" | "en";
}

interface EnvInfo {
  model: string;
  [key: string]: string;
}

// Config is dynamic, but we know some structure
interface ConfigData {
  system?: {
    language?: string;
    [key: string]: any;
  };
  tools?: {
    rag_tool?: {
      kb_base_dir?: string;
      default_kb?: string;
      [key: string]: any;
    };
    run_code?: {
      workspace?: string;
      allowed_roots?: string[];
      language?: string;
      timeout?: number;
      sandbox?: boolean;
      [key: string]: any;
    };
    web_search?: {
      enabled?: boolean;
      max_results?: number;
      [key: string]: any;
    };
    [key: string]: any;
  };
  logging?: {
    level?: string;
    [key: string]: any;
  };
  tts?: {
    default_voice?: string;
    default_language?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

interface FullSettingsResponse {
  ui: UISettings;
  config: ConfigData;
  env: EnvInfo;
}

// Environment variable types
interface EnvVarInfo {
  key: string;
  value: string;
  description: string;
  category: string;
  required: boolean;
  default: string;
  sensitive: boolean;
  is_set: boolean;
}

interface EnvCategoryInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface EnvConfigResponse {
  variables: EnvVarInfo[];
  categories: EnvCategoryInfo[];
}

interface TestResults {
  llm: { status: string; model: string | null; error: string | null };
  embedding: { status: string; model: string | null; error: string | null };
  tts: { status: string; model: string | null; error: string | null };
}

// Tab types
type SettingsTab = "general" | "environment";

export default function SettingsPage() {
  const { uiSettings, refreshSettings } = useGlobal();
  const t = (key: string) => getTranslation(uiSettings.language, key);
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [data, setData] = useState<FullSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState("");

  // Edit states
  const [editedConfig, setEditedConfig] = useState<ConfigData | null>(null);
  const [editedUI, setEditedUI] = useState<UISettings | null>(null);

  // Environment variables states
  const [envConfig, setEnvConfig] = useState<EnvConfigResponse | null>(null);
  const [editedEnvVars, setEditedEnvVars] = useState<Record<string, string>>(
    {},
  );
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>(
    {},
  );
  const [envSaving, setEnvSaving] = useState(false);
  const [envSaveSuccess, setEnvSaveSuccess] = useState(false);
  const [envError, setEnvError] = useState("");
  const [testResults, setTestResults] = useState<TestResults | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetchSettings();
    fetchEnvConfig();
  }, [uiSettings]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(apiUrl("/api/v1/settings"));
      if (res.ok) {
        const responseData = await res.json();
        setData(responseData);
        setEditedConfig(JSON.parse(JSON.stringify(responseData.config)));
        if (!editedUI) {
          setEditedUI(JSON.parse(JSON.stringify(responseData.ui)));
        }
        if (responseData.ui.theme) {
          applyTheme(responseData.ui.theme);
        }
      } else {
        setError("Failed to load settings");
      }
    } catch (err) {
      setError("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  const fetchEnvConfig = async () => {
    try {
      const res = await fetch(apiUrl("/api/v1/settings/env"));
      if (res.ok) {
        const responseData: EnvConfigResponse = await res.json();
        setEnvConfig(responseData);
        const initialValues: Record<string, string> = {};
        responseData.variables.forEach((v) => {
          initialValues[v.key] = v.value;
        });
        setEditedEnvVars(initialValues);
        // Auto test on load
        testEnvConfig();
      }
    } catch (err) {
      console.error("Failed to fetch env config:", err);
    }
  };

  const handleEnvVarChange = (key: string, value: string) => {
    setEditedEnvVars((prev) => ({ ...prev, [key]: value }));
  };

  const toggleSensitiveVisibility = (key: string) => {
    setShowSensitive((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleEnvSave = async () => {
    setEnvSaving(true);
    setEnvSaveSuccess(false);
    setEnvError("");

    try {
      const updates = Object.entries(editedEnvVars)
        .filter(([key, value]) => {
          const original = envConfig?.variables.find((v) => v.key === key);
          if (
            original?.sensitive &&
            value.includes("*") &&
            value === original.value
          ) {
            return false;
          }
          return true;
        })
        .map(([key, value]) => ({ key, value }));

      const res = await fetch(apiUrl("/api/v1/settings/env"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variables: updates }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(
          errorData.detail?.errors?.join(", ") || "Failed to save",
        );
      }

      setEnvSaveSuccess(true);
      setTimeout(() => setEnvSaveSuccess(false), 2000);

      await fetchEnvConfig();
      await testEnvConfig();
    } catch (err: any) {
      setEnvError(err.message || "Failed to save environment variables");
    } finally {
      setEnvSaving(false);
    }
  };

  const testEnvConfig = async () => {
    setTesting(true);
    try {
      const res = await fetch(apiUrl("/api/v1/settings/env/test"), {
        method: "POST",
      });
      if (res.ok) {
        const results = await res.json();
        setTestResults(results);
      }
    } catch (err) {
      console.error("Failed to test env config:", err);
    } finally {
      setTesting(false);
    }
  };

  const getCategoryIcon = (iconName: string) => {
    switch (iconName) {
      case "brain":
        return <Brain className="w-4 h-4" />;
      case "database":
        return <Database className="w-4 h-4" />;
      case "volume":
        return <Volume2 className="w-4 h-4" />;
      case "search":
        return <Search className="w-4 h-4" />;
      case "settings":
        return <SettingsIcon className="w-4 h-4" />;
      default:
        return <Key className="w-4 h-4" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "configured":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "not_configured":
        return <XCircle className="w-4 h-4 text-amber-500" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Info className="w-4 h-4 text-slate-400" />;
    }
  };

  const applyTheme = (theme: "light" | "dark") => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const handleSave = async () => {
    if (!editedConfig || !editedUI) return;
    setSaving(true);
    setSaveSuccess(false);
    setError("");

    try {
      const configRes = await fetch(apiUrl("/api/v1/settings/config"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config: editedConfig }),
      });

      if (!configRes.ok) throw new Error("Failed to save configuration");

      const uiRes = await fetch(apiUrl("/api/v1/settings/ui"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editedUI),
      });

      if (!uiRes.ok) throw new Error("Failed to save UI settings");

      const newConfig = await configRes.json();
      const newUI = await uiRes.json();

      setData((prev) =>
        prev ? { ...prev, config: newConfig, ui: newUI } : null,
      );

      await refreshSettings();

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleConfigChange = (
    section: string,
    key: string,
    value: any,
    subSection?: string,
  ) => {
    setEditedConfig((prev) => {
      if (!prev) return null;
      const newConfig = { ...prev };

      if (subSection) {
        if (!newConfig[section]) newConfig[section] = {};
        if (!newConfig[section][subSection])
          newConfig[section][subSection] = {};
        newConfig[section][subSection][key] = value;
      } else {
        if (!newConfig[section]) newConfig[section] = {};
        newConfig[section][key] = value;
      }
      return newConfig;
    });
  };

  const handleUIChange = (key: keyof UISettings, value: any) => {
    setEditedUI((prev) => {
      if (!prev) return null;
      const newUI = { ...prev, [key]: value };
      if (key === "theme") applyTheme(value);
      return newUI;
    });
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-4rem)] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400" />
      </div>
    );
  }

  if (!editedConfig || !editedUI)
    return (
      <div className="p-8 text-red-500 dark:text-red-400">
        Error loading data
      </div>
    );

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto animate-fade-in">
      <div className="max-w-4xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
              <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-xl">
                <SettingsIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              {t("System Settings")}
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-2 ml-1">
              {t("Manage system configuration and preferences")}
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl mb-6">
          <button
            onClick={() => setActiveTab("general")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "general"
                ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <Sliders className="w-4 h-4" />
            {t("General Settings")}
          </button>
          <button
            onClick={() => setActiveTab("environment")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "environment"
                ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <Key className="w-4 h-4" />
            {t("Environment Variables")}
            {testResults && (
              <span
                className={`ml-1 w-2 h-2 rounded-full ${
                  Object.values(testResults).every(
                    (r) => r.status === "configured",
                  )
                    ? "bg-green-500"
                    : Object.values(testResults).some(
                          (r) => r.status === "error",
                        )
                      ? "bg-red-500"
                      : "bg-amber-500"
                }`}
              />
            )}
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-center gap-3 text-red-700 dark:text-red-400 font-medium">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        {/* General Settings Tab */}
        {activeTab === "general" && (
          <div className="space-y-6">
            {/* 1. Interface Settings (UI) */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Globe className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("Interface Preferences")}
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Theme Mode */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                    {t("Theme")}
                  </label>
                  <div className="flex bg-slate-100 dark:bg-slate-700 p-1 rounded-xl">
                    {["light", "dark"].map((themeOption) => (
                      <button
                        key={themeOption}
                        onClick={() =>
                          handleUIChange("theme", themeOption as any)
                        }
                        className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all ${
                          editedUI.theme === themeOption
                            ? "bg-white dark:bg-slate-600 text-blue-600 dark:text-blue-400 shadow-sm"
                            : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                        }`}
                      >
                        {themeOption === "light" ? (
                          <Sun className="w-4 h-4" />
                        ) : (
                          <Moon className="w-4 h-4" />
                        )}
                        <span>
                          {themeOption === "light"
                            ? t("Light Mode")
                            : t("Dark Mode")}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Interface Language */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                    {t("Language")}
                  </label>
                  <select
                    value={editedUI.language}
                    onChange={(e) => handleUIChange("language", e.target.value)}
                    className="w-full p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  >
                    <option value="en">{t("English")}</option>
                    <option value="zh">{t("Chinese")}</option>
                  </select>
                </div>
              </div>
            </section>

            {/* 2. System Configuration */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Server className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("System Configuration")}
                </h2>
              </div>
              <div className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t("System Language")}
                  </label>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mb-3">
                    {t("Default language for system operations")}
                  </p>
                  <select
                    value={editedConfig.system?.language || "en"}
                    onChange={(e) =>
                      handleConfigChange("system", "language", e.target.value)
                    }
                    className="w-full md:w-1/2 p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  >
                    <option value="en">English</option>
                    <option value="zh">Chinese</option>
                  </select>
                </div>
              </div>
            </section>

            {/* 3. Research Tools */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Search className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("Research Tools")}
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Web Search */}
                <div className="p-5 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
                      <Globe className="w-4 h-4 text-blue-500 dark:text-blue-400" />{" "}
                      {t("Web Search")}
                    </span>
                    <div className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={
                          editedConfig.tools?.web_search?.enabled ?? true
                        }
                        onChange={(e) =>
                          handleConfigChange(
                            "tools",
                            "enabled",
                            e.target.checked,
                            "web_search",
                          )
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-200 dark:bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-100 dark:peer-focus:ring-blue-900 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 dark:after:border-slate-500 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                      {t("Max Results")}
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={editedConfig.tools?.web_search?.max_results || 5}
                      onChange={(e) =>
                        handleConfigChange(
                          "tools",
                          "max_results",
                          parseInt(e.target.value),
                          "web_search",
                        )
                      }
                      className="w-full p-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-slate-100"
                    />
                  </div>
                </div>

                {/* RAG / Knowledge Base */}
                <div className="p-5 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
                      <Database className="w-4 h-4 text-purple-500 dark:text-purple-400" />{" "}
                      {t("Knowledge Base")}
                    </span>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                        {t("Default KB")}
                      </label>
                      <input
                        type="text"
                        value={editedConfig.tools?.rag_tool?.default_kb || ""}
                        onChange={(e) =>
                          handleConfigChange(
                            "tools",
                            "default_kb",
                            e.target.value,
                            "rag_tool",
                          )
                        }
                        className="w-full p-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                        {t("Base Directory")}
                      </label>
                      <input
                        type="text"
                        value={editedConfig.tools?.rag_tool?.kb_base_dir || ""}
                        onChange={(e) =>
                          handleConfigChange(
                            "tools",
                            "kb_base_dir",
                            e.target.value,
                            "rag_tool",
                          )
                        }
                        className="w-full p-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm font-mono text-slate-600 dark:text-slate-300"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* 4. TTS Settings */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("Text-to-Speech")}
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    {t("Default Voice")}
                  </label>
                  <input
                    type="text"
                    value={editedConfig.tts?.default_voice || "Cherry"}
                    onChange={(e) =>
                      handleConfigChange("tts", "default_voice", e.target.value)
                    }
                    className="w-full p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    {t("Default Language")}
                  </label>
                  <input
                    type="text"
                    value={editedConfig.tts?.default_language || "English"}
                    onChange={(e) =>
                      handleConfigChange(
                        "tts",
                        "default_language",
                        e.target.value,
                      )
                    }
                    className="w-full p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100"
                  />
                </div>
              </div>
            </section>

            {/* Active Models Status */}
            {data?.env && (
              <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
                <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                      {t("Active Models")}
                    </h2>
                  </div>
                  <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-1 rounded">
                    {t("Status")}
                  </span>
                </div>
                <div className="p-6">
                  <div className="flex items-center p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-100 dark:border-emerald-800">
                    <div className="p-3 bg-white dark:bg-slate-700 rounded-full shadow-sm mr-4">
                      <Server className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-sm text-emerald-800 dark:text-emerald-300 font-medium mb-1">
                        {t("Active LLM Model")}
                      </p>
                      <p className="text-lg font-bold text-emerald-900 dark:text-emerald-200 font-mono">
                        {data.env.model || t("Not configured")}
                      </p>
                      <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                        {t("Configure in Environment Variables tab")}
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* Save Button */}
            <div className="flex justify-center pt-4 pb-8">
              <button
                onClick={handleSave}
                disabled={saving}
                className={`w-full max-w-sm py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition-all ${
                  saving
                    ? "bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                    : saveSuccess
                      ? "bg-green-500 text-white shadow-xl shadow-green-500/30 scale-105"
                      : "bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:shadow-xl hover:shadow-blue-500/30 hover:-translate-y-1"
                }`}
              >
                {saving ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : saveSuccess ? (
                  <Check className="w-6 h-6" />
                ) : (
                  <Save className="w-6 h-6" />
                )}
                {saveSuccess ? t("Configuration Saved") : t("Save All Changes")}
              </button>
            </div>
          </div>
        )}

        {/* Environment Variables Tab */}
        {activeTab === "environment" && envConfig && (
          <div className="space-y-6">
            {/* Status Overview */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                  <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                    {t("Configuration Status")}
                  </h2>
                </div>
                <button
                  onClick={testEnvConfig}
                  disabled={testing}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg flex items-center gap-1.5 transition-colors"
                >
                  {testing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5" />
                  )}
                  {t("Refresh Status")}
                </button>
              </div>

              <div className="p-6">
                {/* Info Banner */}
                <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
                  <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">
                      {t("Runtime Configuration")}
                    </p>
                    <p className="text-blue-600 dark:text-blue-400">
                      {t("Environment variables are loaded from")}{" "}
                      <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">
                        .env
                      </code>{" "}
                      {t("file on startup")}.{" "}
                      {t(
                        "Changes made here take effect immediately but are not saved to file",
                      )}
                      . {t("On restart, values will be reloaded from")} .env.
                    </p>
                  </div>
                </div>

                {/* Test Results */}
                {testResults && (
                  <div className="grid grid-cols-3 gap-3">
                    {Object.entries(testResults).map(([key, result]) => (
                      <div
                        key={key}
                        className={`p-4 rounded-xl border ${
                          result.status === "configured"
                            ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                            : result.status === "not_configured"
                              ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
                              : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          {getStatusIcon(result.status)}
                          <span className="text-sm font-semibold uppercase text-slate-700 dark:text-slate-200">
                            {key}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 dark:text-slate-400 truncate font-mono">
                          {result.model || result.error || "Not configured"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {/* Environment Variables by Category */}
            {envConfig.categories.map((category) => {
              const categoryVars = envConfig.variables.filter(
                (v) => v.category === category.id,
              );
              if (categoryVars.length === 0) return null;

              return (
                <section
                  key={category.id}
                  className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200"
                >
                  <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                    <div className="text-blue-500 dark:text-blue-400">
                      {getCategoryIcon(category.icon)}
                    </div>
                    <div>
                      <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                        {category.name}
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {category.description}
                      </p>
                    </div>
                  </div>

                  <div className="p-6 space-y-5">
                    {categoryVars.map((envVar) => (
                      <div key={envVar.key} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                            <code className="bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded text-slate-800 dark:text-slate-200 text-xs">
                              {envVar.key}
                            </code>
                            {envVar.required && (
                              <span className="text-red-500 text-[10px] font-semibold">
                                REQUIRED
                              </span>
                            )}
                            {envVar.is_set && (
                              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                            )}
                          </label>
                          {envVar.sensitive && (
                            <button
                              onClick={() =>
                                toggleSensitiveVisibility(envVar.key)
                              }
                              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-1"
                            >
                              {showSensitive[envVar.key] ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </button>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {envVar.description}
                        </p>
                        <input
                          type={
                            envVar.sensitive && !showSensitive[envVar.key]
                              ? "password"
                              : "text"
                          }
                          value={editedEnvVars[envVar.key] || ""}
                          onChange={(e) =>
                            handleEnvVarChange(envVar.key, e.target.value)
                          }
                          placeholder={envVar.default || `Enter ${envVar.key}`}
                          className="w-full p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100 font-mono placeholder:text-slate-300 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                        />
                      </div>
                    ))}
                  </div>
                </section>
              );
            })}

            {/* Save Environment Variables */}
            <div className="pt-4 pb-8">
              {envError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4" />
                  <span>{envError}</span>
                </div>
              )}
              <button
                onClick={handleEnvSave}
                disabled={envSaving}
                className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition-all ${
                  envSaving
                    ? "bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                    : envSaveSuccess
                      ? "bg-green-500 text-white shadow-xl shadow-green-500/30 scale-[1.02]"
                      : "bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:shadow-xl hover:shadow-orange-500/30 hover:-translate-y-1"
                }`}
              >
                {envSaving ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : envSaveSuccess ? (
                  <Check className="w-6 h-6" />
                ) : (
                  <Key className="w-6 h-6" />
                )}
                {envSaveSuccess
                  ? t("Environment Updated!")
                  : t("Apply Environment Changes")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
