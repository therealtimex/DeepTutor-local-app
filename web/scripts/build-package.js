#!/usr/bin/env node
/**
 * Build script for npm packaging.
 *
 * This script:
 * 1. Runs `next build` to generate the standalone output
 * 2. Reorganizes the output into a clean `dist/` directory
 * 3. Copies static assets and public files
 *
 * The resulting `dist/` folder is what gets published to npm.
 */

const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const DIST = path.join(ROOT, 'dist')

function log(msg) {
  console.log(`[build-package] ${msg}`)
}

function rmrf(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true })
  }
}

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true })
}

function copyDir(src, dest) {
  mkdirp(dest)
  const entries = fs.readdirSync(src, { withFileTypes: true })
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name)
    const destPath = path.join(dest, entry.name)
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath)
    } else {
      fs.copyFileSync(srcPath, destPath)
    }
  }
}

function main() {
  log('Starting build for npm packaging...')

  // Step 1: Run next build
  log('Running next build...')
  const buildEnv = {
    ...process.env,
    API_BASE_URL:
      process.env.API_BASE_URL ||
      'http://localhost:8004/realtimex',
  }
  try {
    execSync('npm run build', { cwd: ROOT, stdio: 'inherit', env: buildEnv })
  } catch (e) {
    console.error('Build failed')
    process.exit(1)
  }

  // Step 2: Clean and create dist directory
  log('Preparing dist directory...')
  rmrf(DIST)
  mkdirp(DIST)

  // Step 3: Find the standalone output
  // Next.js preserves the full path structure, so we need to find the actual app directory
  const standaloneBase = path.join(ROOT, '.next', 'standalone')

  // Find the standalone app directory containing server.js and package.json
  // The standalone output preserves the original path structure
  function findStandaloneApp(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    const hasServerJs = entries.some(e => e.isFile() && e.name === 'server.js')
    const hasPackageJson = entries.some(e => e.isFile() && e.name === 'package.json')
    const hasNextDir = entries.some(e => e.isDirectory() && e.name === '.next')

    // The app root has server.js, package.json, and .next directory
    if (hasServerJs && hasPackageJson && hasNextDir) {
      return dir
    }

    // Recurse into subdirectories
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const result = findStandaloneApp(path.join(dir, entry.name))
        if (result) return result
      }
    }
    return null
  }
  const findServerJs = findStandaloneApp

  const standaloneAppDir = findServerJs(standaloneBase)
  if (!standaloneAppDir) {
    console.error('Could not find standalone server.js')
    process.exit(1)
  }
  log(`Found standalone app at: ${standaloneAppDir}`)

  // Step 4: Copy standalone output to dist
  log('Copying standalone output...')
  copyDir(standaloneAppDir, DIST)

  // Step 4b: Wrap server.js to allow runtime env overrides
  const serverPath = path.join(DIST, 'server.js')
  const serverNextPath = path.join(DIST, 'server.next.js')
  if (fs.existsSync(serverPath)) {
    fs.renameSync(serverPath, serverNextPath)
    const wrapper = [
      '#!/usr/bin/env node',
      "'use strict';",
      'process.env.API_BASE_URL =',
      '  process.env.API_BASE_URL ||',
      "  'http://localhost:8004/realtimex';",
      "require('./server.next.js');",
      '',
    ].join('\n')
    fs.writeFileSync(serverPath, wrapper)
    log('Wrapped server.js for runtime env injection')
  }

  // Step 5: Copy static assets
  // Static assets need to be at dist/.next/static/
  const staticSrc = path.join(ROOT, '.next', 'static')
  const staticDest = path.join(DIST, '.next', 'static')
  if (fs.existsSync(staticSrc)) {
    log('Copying static assets...')
    copyDir(staticSrc, staticDest)
  }

  // Step 6: Copy public folder
  const publicSrc = path.join(ROOT, 'public')
  const publicDest = path.join(DIST, 'public')
  if (fs.existsSync(publicSrc)) {
    log('Copying public assets...')
    copyDir(publicSrc, publicDest)
  }

  // Step 7: Remove ALL .env files from dist (users provide their own at runtime)
  // This includes .env, .env.local, .env.production, .env.development, etc.
  const distEntries = fs.readdirSync(DIST)
  const envFiles = distEntries.filter(f => f.startsWith('.env'))
  for (const envFile of envFiles) {
    const envPath = path.join(DIST, envFile)
    if (fs.statSync(envPath).isFile()) {
      fs.unlinkSync(envPath)
      log(`Removed ${envFile} from dist`)
    }
  }
  if (envFiles.length > 0) {
    log('Environment files removed - users must provide env vars at runtime')
  }

  // Step 8: Remove build-time packages from dist/node_modules
  // Next.js standalone sometimes includes packages that aren't needed at runtime
  const buildOnlyPackages = ['typescript']
  const nodeModulesDir = path.join(DIST, 'node_modules')
  if (fs.existsSync(nodeModulesDir)) {
    for (const pkg of buildOnlyPackages) {
      const pkgPath = path.join(nodeModulesDir, pkg)
      if (fs.existsSync(pkgPath)) {
        rmrf(pkgPath)
        log(`Removed ${pkg} from dist/node_modules (not needed at runtime)`)
      }
    }
  }

  // Done
  const distSize = execSync(`du -sh "${DIST}"`, { encoding: 'utf8' }).trim()
  log(`Build complete! dist size: ${distSize.split('\t')[0]}`)
}

main()
