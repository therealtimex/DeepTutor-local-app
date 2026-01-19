#!/usr/bin/env node
"use strict";

const { spawn, spawnSync } = require("child_process");
const path = require("path");

function printHelp() {
  console.log(
    [
      "Usage: opentutor-web [options] [-- <next-args>]",
      "",
      "Options:",
      "  --dev                 Start Next.js dev server (default)",
      "  --start               Start Next.js production server",
      "  --build               Build before starting production server",
      "  -p, --port <port>      Port to listen on",
      "  -H, --hostname <host>  Hostname to bind (e.g., 0.0.0.0)",
      "  --api-base <url>       Sets NEXT_PUBLIC_API_BASE",
      "  -h, --help             Show help",
      "",
      "Examples:",
      "  npx @realtimex/opentutor-web",
      "  npx @realtimex/opentutor-web --api-base http://localhost:8004/realtimex",
      "  npx @realtimex/opentutor-web --start --build",
    ].join("\n")
  );
}

const rawArgs = process.argv.slice(2);
const nextArgs = [];
let mode = "dev";
let runBuild = false;
let port;
let hostname;
let apiBase;

for (let i = 0; i < rawArgs.length; i += 1) {
  const arg = rawArgs[i];
  if (arg === "--") {
    nextArgs.push(...rawArgs.slice(i + 1));
    break;
  }
  if (arg === "-h" || arg === "--help") {
    printHelp();
    process.exit(0);
  }
  if (arg === "--dev") {
    mode = "dev";
    continue;
  }
  if (arg === "--start") {
    mode = "start";
    continue;
  }
  if (arg === "--build") {
    runBuild = true;
    continue;
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
  nextArgs.push(arg);
}

const projectRoot = path.resolve(__dirname, "..");
const nextBin = require.resolve("next/dist/bin/next", { paths: [projectRoot] });

if (mode === "start" && runBuild) {
  const buildArgs = [nextBin, "build"];
  if (port) {
    buildArgs.push("-p", String(port));
  }
  if (hostname) {
    buildArgs.push("-H", String(hostname));
  }
  buildArgs.push(...nextArgs);
  const buildResult = spawnSync(process.execPath, buildArgs, {
    cwd: projectRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      ...(apiBase ? { NEXT_PUBLIC_API_BASE: apiBase } : {}),
    },
  });
  if (buildResult.status !== 0) {
    process.exit(buildResult.status ?? 1);
  }
}

const cmdArgs = [nextBin, mode === "start" ? "start" : "dev"];
if (port) {
  cmdArgs.push("-p", String(port));
}
if (hostname) {
  cmdArgs.push("-H", String(hostname));
}
cmdArgs.push(...nextArgs);

const child = spawn(process.execPath, cmdArgs, {
  cwd: projectRoot,
  stdio: "inherit",
  env: {
    ...process.env,
    ...(apiBase ? { NEXT_PUBLIC_API_BASE: apiBase } : {}),
  },
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
