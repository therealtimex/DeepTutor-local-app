#!/usr/bin/env node
"use strict";

const { spawn } = require("child_process");
const path = require("path");

function printHelp() {
  console.log(
    [
      "Usage: opentutor-web [options]",
      "",
      "Options:",
      "  -p, --port <port>      Port to listen on (default: 3000)",
      "  -H, --hostname <host>  Hostname to bind (default: 0.0.0.0)",
      "  --api-base <url>       Sets NEXT_PUBLIC_API_BASE",
      "  -h, --help             Show help",
      "",
      "Environment variables:",
      "  PORT                   Port to listen on",
      "  HOSTNAME               Hostname to bind",
      "  NEXT_PUBLIC_API_BASE   Backend API URL",
      "",
      "Examples:",
      "  npx @realtimex/opentutor-web",
      "  npx @realtimex/opentutor-web --port 8080",
      "  npx @realtimex/opentutor-web --api-base http://localhost:8004/realtimex",
    ].join("\n")
  );
}

const rawArgs = process.argv.slice(2);
let port;
let hostname;
let apiBase;

for (let i = 0; i < rawArgs.length; i += 1) {
  const arg = rawArgs[i];
  if (arg === "-h" || arg === "--help") {
    printHelp();
    process.exit(0);
  }
  if (arg === "-p" || arg === "--port") {
    port = rawArgs[i + 1];
    i += 1;
    continue;
  }
  if (arg === "-H" || arg === "--hostname") {
    hostname = rawArgs[i + 1];
    i += 1;
    continue;
  }
  if (arg === "--api-base") {
    apiBase = rawArgs[i + 1];
    i += 1;
    continue;
  }
}

// Resolve paths relative to the package installation
const distDir = path.resolve(__dirname, "..", "dist");
const serverPath = path.join(distDir, "server.js");

// Build environment with runtime config
const env = {
  ...process.env,
  ...(port ? { PORT: String(port) } : {}),
  ...(hostname ? { HOSTNAME: String(hostname) } : {}),
  ...(apiBase ? { NEXT_PUBLIC_API_BASE: apiBase } : {}),
};

// Start the standalone server
const child = spawn(process.execPath, [serverPath], {
  cwd: distDir,
  stdio: "inherit",
  env,
});

child.on("error", (err) => {
  console.error("Failed to start server:", err.message);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
