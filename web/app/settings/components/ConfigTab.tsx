"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Trash2, Loader2, Pencil, Zap } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { ConfigItem, ConfigType } from "../types";
import ConfigForm from "./ConfigForm";
import RTXModelSelector from "./RTXModelSelector";

interface ConfigTabProps {
  configType: ConfigType;
  title: string;
  description: string;
  onUpdate: () => void;
  showDimensions?: boolean;
  showVoice?: boolean;
  isSearchConfig?: boolean;
  t: (key: string) => string;
}

export default function ConfigTab({
  configType,
  title,
  description,
  onUpdate,
  showDimensions = false,
  showVoice = false,
  isSearchConfig = false,
  t,
}: ConfigTabProps) {
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ConfigItem | null>(null);
  const [showRTXSelector, setShowRTXSelector] = useState(false);
  const [rtxConfig, setRtxConfig] = useState<ConfigItem | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const loadConfigs = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/v1/config/${configType}`));
      if (res.ok) {
        const data = await res.json();
        setConfigs(data.configs || []);
      }
    } catch (e) {
      console.error(`Failed to load ${configType} configs:`, e);
    } finally {
      setLoading(false);
    }
  }, [configType]);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const setActive = async (configId: string) => {
    try {
      const res = await fetch(
        apiUrl(`/api/v1/config/${configType}/${configId}/active`),
        {
          method: "POST",
        },
      );
      if (res.ok) {
        loadConfigs();
        onUpdate();
      }
    } catch (e) {
      console.error("Failed to set active config:", e);
    }
  };

  const deleteConfig = async (configId: string) => {
    if (!confirm(t("Are you sure you want to delete this configuration?")))
      return;

    try {
      const res = await fetch(
        apiUrl(`/api/v1/config/${configType}/${configId}`),
        {
          method: "DELETE",
        },
      );
      if (res.ok) {
        loadConfigs();
        onUpdate();
      }
    } catch (e) {
      console.error("Failed to delete config:", e);
    }
  };

  const testConnection = async (config: ConfigItem) => {
    if (isSearchConfig) return;

    setTesting(config.id);
    setTestResult(null);

    try {
      const res = await fetch(
        apiUrl(`/api/v1/config/${configType}/${config.id}/test`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ success: false, message: t("Connection test failed") });
    } finally {
      setTesting(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {description}
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t("Add Configuration")}
        </button>
      </div>

      {/* Add/Edit Form */}
      {(showAddForm || editingConfig) && (
        <ConfigForm
          configType={configType}
          showDimensions={showDimensions}
          showVoice={showVoice}
          isSearchConfig={isSearchConfig}
          editConfig={editingConfig}
          t={t}
          onSuccess={() => {
            setShowAddForm(false);
            setEditingConfig(null);
            loadConfigs();
            onUpdate();
          }}
          onCancel={() => {
            setShowAddForm(false);
            setEditingConfig(null);
          }}
        />
      )}

      {/* Test Result */}
      {testResult && (
        <div
          className={`mb-4 p-3 rounded-lg text-sm ${
            testResult.success
              ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800"
              : "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
          }`}
        >
          {testResult.message}
        </div>
      )}

      {/* Configuration List */}
      <div className="space-y-3">
        {configs.map((config) => {
          const isRTX = config.source === "realtimex" || config.id === "rtx";

          return (
          <div
            key={config.id}
            className={`p-4 rounded-xl border transition-all ${
              config.is_active
                ? isRTX
                  ? "border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-900/20"
                  : "border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20"
                : "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {config.is_active && (
                  <div className={`w-2 h-2 rounded-full ${isRTX ? "bg-emerald-500" : "bg-blue-500"}`} />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {config.name}
                    </span>
                    {isRTX && (
                      <span className="px-2 py-0.5 text-xs bg-emerald-100 dark:bg-emerald-800 text-emerald-700 dark:text-emerald-300 rounded flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {t("RealTimeX")}
                      </span>
                    )}
                    {config.is_default && (
                      <span className="px-2 py-0.5 text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded">
                        {t("Default")}
                      </span>
                    )}
                    {config.is_active && (
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        isRTX
                          ? "bg-emerald-100 dark:bg-emerald-800 text-emerald-700 dark:text-emerald-300"
                          : "bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300"
                      }`}>
                        {t("Active")}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-sm text-slate-500 dark:text-slate-400">
                    <span>
                      {t("Provider")}: {config.provider}
                    </span>
                    {config.model && (
                      <span>
                        {t("Model")}: {config.model}
                      </span>
                    )}
                    {showDimensions && config.dimensions && (
                      <span>
                        {t("Dimensions")}: {config.dimensions}
                      </span>
                    )}
                    {showVoice && config.voice && (
                      <span>
                        {t("Voice")}: {config.voice}
                      </span>
                    )}
                    {config.speed && (
                      <span>
                        {t("Speed")}: {config.speed}x
                      </span>
                    )}
                    {config.quality && (
                      <span>
                        {t("Quality")}: {config.quality}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {!config.is_active && (
                  <button
                    onClick={() => setActive(config.id)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      isRTX
                        ? "text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30"
                        : "text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30"
                    }`}
                  >
                    {t("Set Active")}
                  </button>
                )}
                {!isSearchConfig && !isRTX && (
                  <button
                    onClick={() => testConnection(config)}
                    disabled={testing === config.id}
                    className="px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                  >
                    {testing === config.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      t("Test")
                    )}
                  </button>
                )}
                {/* Edit button for RTX configs opens RTXModelSelector */}
                {isRTX && (
                  <button
                    onClick={() => {
                      setRtxConfig(config);
                      setShowRTXSelector(true);
                    }}
                    className="p-1.5 text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                    title={t("Edit")}
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                )}
                {/* Edit button for regular configs */}
                {!config.is_default && !isRTX && (
                  <button
                    onClick={() => {
                      setEditingConfig(config);
                      setShowAddForm(false);
                    }}
                    className="p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                    title={t("Edit")}
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                )}
                {!config.is_default && !isRTX && (
                  <button
                    onClick={() => deleteConfig(config.id)}
                    className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                    title={t("Delete")}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
          );
        })}

        {configs.length === 0 && (
          <div className="text-center py-8 text-slate-500 dark:text-slate-400">
            {t("No configurations found. Add one to get started.")}
          </div>
        )}
      </div>

      {/* RTX Model Selector Modal */}
      {showRTXSelector && (
        <RTXModelSelector
          configType={configType}
          currentProvider={rtxConfig?.provider}
          currentModel={rtxConfig?.model}
          currentVoice={rtxConfig?.voice}
          currentSpeed={rtxConfig?.speed}
          currentQuality={rtxConfig?.quality}
          onSave={() => {
            setShowRTXSelector(false);
            setRtxConfig(null);
            loadConfigs();
            onUpdate();
          }}
          onClose={() => {
            setShowRTXSelector(false);
            setRtxConfig(null);
          }}
          t={t}
        />
      )}
    </div>
  );
}
