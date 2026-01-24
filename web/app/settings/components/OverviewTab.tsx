"use client";

import { useEffect, useState } from "react";
import {
  Brain,
  Database,
  Volume2,
  Search,
  Check,
  AlertCircle,
  Server,
  RefreshCw,
  Zap,
} from "lucide-react";
import { apiUrl } from "@/lib/api";
import { FullStatus, PortsInfo, ConfigType } from "../types";

interface OverviewTabProps {
  status: FullStatus | null;
  ports: PortsInfo | null;
  onRefresh: () => void;
  t: (key: string) => string;
}

interface RealTimeXStatus {
  connected: boolean;
  mode: string | null;
  appId: string | null;
  timestamp: string | null;
  error: string | null;
}

const services: {
  key: ConfigType;
  label: string;
  icon: typeof Brain;
  color: string;
}[] = [
  { key: "llm", label: "LLM", icon: Brain, color: "purple" },
  { key: "embedding", label: "Embedding", icon: Database, color: "indigo" },
  { key: "tts", label: "TTS", icon: Volume2, color: "emerald" },
  { key: "search", label: "Search", icon: Search, color: "amber" },
];

export default function OverviewTab({
  status,
  ports,
  onRefresh,
  t,
}: OverviewTabProps) {
  const [rtxStatus, setRtxStatus] = useState<RealTimeXStatus | null>(null);

  // Load RealTimeX status
  useEffect(() => {
    loadRealTimeXStatus();
  }, []);

  const loadRealTimeXStatus = async () => {
    try {
      const res = await fetch(apiUrl("/api/v1/realtimex/status"));
      if (res.ok) {
        const data = await res.json();
        setRtxStatus(data);
      }
    } catch (e) {
      console.error("Failed to load RealTimeX status:", e);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Refresh Button */}
      <div className="flex justify-end">
        <button
          onClick={() => {
            onRefresh();
            loadRealTimeXStatus();
          }}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t("Refresh")}
        </button>
      </div>

      {/* RealTimeX Connection Status */}
      {rtxStatus && rtxStatus.connected && (
        <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-800/50">
                <Zap className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h3 className="font-semibold text-emerald-900 dark:text-emerald-100">
                  RealTimeX Connected
                </h3>
                <p className="text-sm text-emerald-600 dark:text-emerald-400">
                  Running via RealTimeX Desktop App
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <Check className="w-5 h-5 text-emerald-500" />
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-700">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {rtxStatus.mode && (
                <div>
                  <span className="text-emerald-600 dark:text-emerald-400">
                    Mode:
                  </span>
                  <span className="ml-2 font-mono text-emerald-700 dark:text-emerald-300">
                    {rtxStatus.mode}
                  </span>
                </div>
              )}
              {rtxStatus.appId && (
                <div>
                  <span className="text-emerald-600 dark:text-emerald-400">
                    App ID:
                  </span>
                  <span className="ml-2 font-mono text-emerald-700 dark:text-emerald-300">
                    {rtxStatus.appId}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Service Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {services.map((service) => {
          const s = status?.[service.key];
          const Icon = service.icon;
          const isConfigured = s?.configured;

          return (
            <div
              key={service.key}
              className={`p-4 rounded-xl border ${
                isConfigured
                  ? "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20"
                  : "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2 rounded-lg ${
                      isConfigured
                        ? "bg-green-100 dark:bg-green-800/50"
                        : "bg-slate-100 dark:bg-slate-700"
                    }`}
                  >
                    <Icon
                      className={`w-5 h-5 ${
                        isConfigured
                          ? "text-green-600 dark:text-green-400"
                          : "text-slate-400"
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                      {service.label}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {s?.active_config_name || t("Not configured")}
                    </p>
                  </div>
                </div>
                {isConfigured ? (
                  <Check className="w-5 h-5 text-green-500" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-slate-400" />
                )}
              </div>
              {s?.model && (
                <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-500 dark:text-slate-400">
                      {t("Model")}:
                    </span>
                    <span className="font-mono text-slate-700 dark:text-slate-300">
                      {s.model}
                    </span>
                  </div>
                  {s.provider && (
                    <div className="flex items-center gap-2 text-sm mt-1">
                      <span className="text-slate-500 dark:text-slate-400">
                        {t("Provider")}:
                      </span>
                      <span className="text-slate-700 dark:text-slate-300">
                        {s.provider}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Port Information */}
      {ports && (
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-5 h-5 text-slate-400" />
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">
              {t("Port Configuration")}
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {t("Backend Port")}
              </span>
              <p className="font-mono text-lg text-slate-700 dark:text-slate-300">
                {ports.backend_port}
              </p>
            </div>
            <div>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {t("Frontend Port")}
              </span>
              <p className="font-mono text-lg text-slate-700 dark:text-slate-300">
                {ports.frontend_port}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
