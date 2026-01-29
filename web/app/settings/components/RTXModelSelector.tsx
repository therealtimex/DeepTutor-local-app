/* eslint-disable i18n/no-literal-ui-text */
"use client";

import { useState, useEffect } from "react";
import { Zap, X, Check, Loader2 } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { ConfigType } from "../types";

interface RTXProviderConfig {
  voices?: string[];
  speed?: { min: number; max: number; default: number };
  quality?: { min: number; max: number; default: number; description?: string };
}

interface RTXProvider {
  provider: string;
  name?: string;
  models: { id: string; name: string }[];
  config?: RTXProviderConfig;
}

interface RTXModelSelectorProps {
  configType: ConfigType;
  currentProvider?: string;
  currentModel?: string;
  currentVoice?: string;
  currentSpeed?: number;
  currentQuality?: number;
  onSave: () => void;
  onClose: () => void;
  t: (key: string) => string;
}

export default function RTXModelSelector({
  configType,
  currentProvider,
  currentModel,
  currentVoice,
  currentSpeed,
  currentQuality,
  onSave,
  onClose,
  t,
}: RTXModelSelectorProps) {
  const [providers, setProviders] = useState<RTXProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected values
  const [selectedProvider, setSelectedProvider] = useState(currentProvider || "");
  const [selectedModel, setSelectedModel] = useState(currentModel || "");
  const [selectedVoice, setSelectedVoice] = useState(currentVoice || ""); // For TTS
  const [selectedSpeed, setSelectedSpeed] = useState<number | undefined>(currentSpeed);
  const [selectedQuality, setSelectedQuality] = useState<number | undefined>(currentQuality);

  // Load providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const res = await fetch(apiUrl("/api/v1/realtimex/providers"));
      if (res.ok) {
        const data = await res.json();
        let providerList = [];
        
        if (configType === "llm") providerList = data.llm;
        else if (configType === "embedding") providerList = data.embedding;
        else if (configType === "tts") providerList = data.tts || []; // Handle TTS providers if available

        setProviders(providerList || []);

        // Set initial selection if not already set
        if (!selectedProvider && providerList?.length > 0) {
          const firstProvider = providerList[0];
          setSelectedProvider(firstProvider.provider);
          
          if (configType === "tts") {
            // For TTS, model is usually fixed or default, but we might have voices
            const voices = firstProvider.config?.voices || [];
            if (voices.length > 0) {
              setSelectedVoice(voices[0]);
            }
          } else {
            if (firstProvider.models?.length > 0) {
              setSelectedModel(firstProvider.models[0].id);
            }
          }
        }
      }
    } catch (e) {
      setError(t("Failed to load providers"));
    } finally {
      setLoading(false);
    }
  };

  // Get models for selected provider
  const currentProviderData = providers.find((p) => p.provider === selectedProvider);
  const models = currentProviderData?.models || [];
  
  // Get config metadata
  const providerConfig = currentProviderData?.config;
  const voices = providerConfig?.voices || [];

  // Update model/voice/speed/quality when provider changes
  useEffect(() => {
    if (configType === "tts") {
      // Voice
      if (voices.length > 0 && !voices.includes(selectedVoice)) {
        setSelectedVoice(voices[0]);
      }
      
      // Speed (only reset if not set or out of bounds, otherwise keep user selection if possible)
      if (providerConfig?.speed) {
        if (selectedSpeed === undefined) {
          setSelectedSpeed(providerConfig.speed.default);
        }
      } else {
        setSelectedSpeed(undefined);
      }

      // Quality
      if (providerConfig?.quality) {
        if (selectedQuality === undefined) {
          setSelectedQuality(providerConfig.quality.default);
        }
      } else {
        setSelectedQuality(undefined);
      }

    } else {
      if (models.length > 0 && !models.find((m) => m.id === selectedModel)) {
        setSelectedModel(models[0].id);
      }
    }
  }, [selectedProvider, models, selectedModel, configType, currentProviderData, selectedVoice, voices, providerConfig, selectedSpeed, selectedQuality]);

  const handleSave = async () => {
    if (!selectedProvider || !selectedModel) return;

    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        config_type: configType,
        provider: selectedProvider,
        model: selectedModel,
      };

      // Add voice/speed/quality for TTS
      if (configType === "tts") {
        if (selectedVoice) payload.voice = selectedVoice;
        if (selectedSpeed !== undefined) payload.speed = selectedSpeed;
        if (selectedQuality !== undefined) payload.quality = selectedQuality;
      }

      const res = await fetch(apiUrl("/api/v1/realtimex/config/apply"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        onSave();
      } else {
        const data = await res.json();
        setError(data.detail || t("Failed to save configuration"));
      }
    } catch (e) {
      setError(t("Failed to save configuration"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-800/50">
              <Zap className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                {t("RealTimeX")} {configType === "llm" ? "LLM" : configType === "embedding" ? t("Embedding") : "TTS"}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t("Select provider and model")}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
            </div>
          ) : providers.length === 0 && configType !== "tts" ? ( // Allow TTS even if no providers listed (using defaults)
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              {t("No providers available")}
            </div>
          ) : (
            <>
              {/* Provider Select */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                  {t("Provider")}
                </label>
                {providers.length > 0 ? (
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
                  >
                    {providers.map((p, idx) => (
                      <option key={`${p.provider}-${idx}`} value={p.provider}>
                        {p.name || p.provider}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={selectedProvider || "realtimexai"}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
                    placeholder="realtimexai"
                  />
                )}
              </div>

              {/* Model Select */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                  {t("Model")}
                </label>
                {models.length > 0 ? (
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={models.length === 0}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none disabled:opacity-50"
                  >
                    {models.map((m, idx) => (
                      <option key={`${m.id}-${idx}`} value={m.id}>
                        {m.name || m.id}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={selectedModel || (configType === "tts" ? "tts-1" : "")}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
                    placeholder={configType === "tts" ? "tts-1" : "Model ID"}
                  />
                )}
              </div>

              {/* Voice Select (TTS Only) */}
              {configType === "tts" && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      {t("Default Voice")}
                    </label>
                    {voices.length > 0 ? (
                      <select
                        value={selectedVoice}
                        onChange={(e) => setSelectedVoice(e.target.value)}
                        className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
                      >
                        <option value="">{t("Select a voice")}</option>
                        {voices.map((voice: string, idx: number) => (
                          <option key={`${voice}-${idx}`} value={voice}>
                            {voice}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <>
                        <input
                          type="text"
                          value={selectedVoice}
                          onChange={(e) => setSelectedVoice(e.target.value)}
                          className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
                          placeholder="alloy"
                        />
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {t("Leave empty to use system default")}
                        </p>
                      </>
                    )}
                  </div>

                  {/* Speed Control */}
                  {providerConfig?.speed && (
                    <div>
                      <div className="flex justify-between mb-1.5">
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                          {t("Speed")}
                        </label>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {selectedSpeed}x
                        </span>
                      </div>
                      <input
                        type="range"
                        min={providerConfig.speed.min}
                        max={providerConfig.speed.max}
                        step={0.1}
                        value={selectedSpeed ?? providerConfig.speed.default}
                        onChange={(e) => setSelectedSpeed(parseFloat(e.target.value))}
                        className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                      />
                      <div className="flex justify-between text-xs text-slate-400 mt-1">
                        <span>{providerConfig.speed.min}x</span>
                        <span>{providerConfig.speed.max}x</span>
                      </div>
                    </div>
                  )}

                  {/* Quality Control */}
                  {providerConfig?.quality && (
                    <div>
                      <div className="flex justify-between mb-1.5">
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                          {t("Quality")}
                        </label>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {selectedQuality}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={providerConfig.quality.min}
                        max={providerConfig.quality.max}
                        step={1}
                        value={selectedQuality ?? providerConfig.quality.default}
                        onChange={(e) => setSelectedQuality(parseInt(e.target.value, 10))}
                        className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                      />
                      <div className="flex justify-between text-xs text-slate-400 mt-1">
                        <span>{providerConfig.quality.min}</span>
                        <span>{providerConfig.quality.max}</span>
                      </div>
                      {providerConfig.quality.description && (
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {providerConfig.quality.description}
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}

              {/* Info */}
              <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                <span className="text-sm text-emerald-700 dark:text-emerald-300">
                  {t("No API key required - uses RealTimeX SDK")}
                </span>
              </div>

              {/* Error */}
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm">
                  {error}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-4 border-t border-slate-200 dark:border-slate-700 flex-shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            {t("Cancel")}
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !selectedProvider || !selectedModel}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t("Saving...")}
              </>
            ) : (
              t("Save")
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
