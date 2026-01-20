// API configuration and utility functions

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: {
      API_BASE_URL?: string;
    };
  }
}

function readRuntimeConfig(): { API_BASE_URL?: string } | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.__RUNTIME_CONFIG__ || null;
}

function resolveApiBaseUrl(): string {
  const runtime = readRuntimeConfig();
  if (runtime?.API_BASE_URL) {
    return runtime.API_BASE_URL;
  }
  if (process.env.API_BASE_URL) {
    return process.env.API_BASE_URL;
  }
  return "http://localhost:8004/realtimex";
}

export const API_BASE_URL = resolveApiBaseUrl();

/**
 * Construct a full API URL from a path
 * @param path - API path (e.g., '/api/v1/knowledge/list')
 * @returns Full URL (e.g., 'http://localhost:8000/api/v1/knowledge/list')
 */
export function apiUrl(path: string): string {
  const baseUrl = resolveApiBaseUrl();
  // Remove leading slash if present to avoid double slashes
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Remove trailing slash from base URL if present
  const base = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;

  return `${base}${normalizedPath}`;
}

/**
 * Construct a WebSocket URL from a path
 * @param path - WebSocket path (e.g., '/api/v1/solve')
 * @returns WebSocket URL (e.g., 'ws://localhost:{backend_port}/api/v1/solve')
 * Note: backend_port is configured in config/main.yaml
 */
export function wsUrl(path: string): string {
  // Security Hardening: Convert http to ws and https to wss.
  // In production environments (where API_BASE_URL starts with https), this ensures secure websockets.
  const base = resolveApiBaseUrl()
    .replace(/^http:/, "ws:")
    .replace(/^https:/, "wss:");

  // Remove leading slash if present to avoid double slashes
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Remove trailing slash from base URL if present
  const normalizedBase = base.endsWith("/") ? base.slice(0, -1) : base;

  return `${normalizedBase}${normalizedPath}`;
}
