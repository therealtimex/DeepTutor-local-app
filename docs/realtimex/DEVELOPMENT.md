# DeepTutor Development Guide

**Audience**: Developers new to this project  
**Purpose**: Setup, development, building, and publishing workflows

---

## Quick Start

### Prerequisites

- **Python 3.10+** (backend)
- **Node.js 18+** (frontend)
- **uv** (Python package manager) - Install: `pip install uv`

### Running the Application

**Production Mode** (uses published frontend package):
```bash
uvx realtimex-deeptutor
```

**Development Mode** (runs frontend from source):
```bash
FRONTEND_DEV_MODE=true uvx realtimex-deeptutor
```

**Custom Ports**:
```bash
FRONTEND_PORT=4001 BACKEND_PORT=8002 uvx realtimex-deeptutor
```

---

## Project Structure

```
realtimex-deeptutor/
├── src/                    # Backend (Python/FastAPI)
│   ├── api/               # API endpoints
│   ├── agents/            # AI agents
│   ├── cli/               # CLI entry points
│   └── services/          # Core services
├── web/                   # Frontend (Next.js/React)
│   ├── app/              # Next.js app directory
│   ├── components/       # React components
│   ├── bin/              # Published package bin
│   └── package.json      # Frontend dependencies
├── scripts/               # Startup scripts
│   └── start_web.py      # Main launcher
└── pyproject.toml        # Python package config
```

---

## Frontend Development

### Setup

```bash
cd web
npm install
```

### Development

**Option 1**: Run standalone (frontend only)
```bash
cd web
API_BASE_URL=http://localhost:8001 npm run dev
```

**Option 2**: Run with backend (recommended)
```bash
# From project root
FRONTEND_DEV_MODE=true realtimex-deeptutor
```

### Building

```bash
cd web
npm run build              # Build Next.js app
npm run build:package      # Build publishable package
```

**What `build:package` does**:
1. Builds Next.js in standalone mode
2. Copies standalone output to `dist/`
3. Packages bin script (`bin/opentutor-web.js`)
4. Prepares for NPM publish

### Publishing Frontend

**1. Update Version**

Edit `web/package.json`:
```json
{
  "name": "@realtimex/opentutor-web",
  "version": "0.2.1"  // Bump this
}
```

**2. Build Package**

```bash
cd web
npm run build:package
```

**3. Publish to NPM**

```bash
cd web
npm publish --access public
```

**4. Verify Published**

```bash
npx @realtimex/opentutor-web@latest --help
```

### Frontend Package Usage

Users run the published package via:
```bash
# Auto-installs and runs latest version
npx -y @realtimex/opentutor-web -p 4001 --api-base http://localhost:8001
```

---

## Backend Development

### Setup

```bash
# Sync dependencies and install in editable mode
uv sync
```

### Development

**Run backend only**:
```bash
python src/api/run_server.py
```

**Run full stack**:
```bash
realtimex-deeptutor
```

### Configuration

Backend settings are in `config/main.yaml`:
```yaml
ports:
  backend: 8001
  frontend: 3782

llm:
  model: "gpt-4o-mini"
  # ...
```

### Publishing Backend

**1. Update Version**

Edit `pyproject.toml`:
```toml
[project]
name = "realtimex-deeptutor"
version = "0.6.2"  # Bump this
```

**2. Build Package**

```bash
# Clean previous builds
rm -rf dist/

# Build wheel and source distribution
uv build
```

**3. Publish to PyPI**

```bash
# Test publish (optional)
uv publish --publish-url https://test.pypi.org/legacy/

# Production publish
uv publish
```

**4. Verify Published**

```bash
uvx realtimex-deeptutor@latest --help
```

---

## Version Management

### When to Bump Versions

**Frontend** (`web/package.json`):
- **Patch** (0.2.0 → 0.2.1): Bug fixes, minor UI tweaks
- **Minor** (0.2.1 → 0.3.0): New features, component changes
- **Major** (0.3.0 → 1.0.0): Breaking API changes, major redesign

**Backend** (`pyproject.toml`):
- **Patch** (0.6.0 → 0.6.1): Bug fixes, minor improvements
- **Minor** (0.6.1 → 0.7.0): New endpoints, new features
- **Major** (0.7.0 → 1.0.0): Breaking API changes

### Coordinating Frontend + Backend Updates

If both need updates:

1. **Develop**: Make changes in both directories
2. **Test**: Run with `FRONTEND_DEV_MODE=true` to test from source
3. **Version**: Bump versions in both `package.json` and `pyproject.toml`
4. **Publish Frontend First**: `npm run build:package && npm publish`
5. **Publish Backend**: `uv build && uv publish`
6. **Verify**: Test with `uvx realtimex-deeptutor` (uses published package)

---

## Common Development Tasks

### Adding a New Backend Endpoint

1. Create endpoint in `src/api/` (e.g., `src/api/my_endpoint.py`)
2. Register in `src/api/main.py`
3. Test with backend running
4. Commit and push

### Adding a New Frontend Component

1. Create component in `web/components/`
2. Import and use in pages (`web/app/`)
3. Test with `FRONTEND_DEV_MODE=true`
4. Build and publish when ready

### Updating Dependencies

**Frontend**:
```bash
cd web
npm update              # Update within semver ranges
npm install pkg@latest  # Update specific package
npm audit fix           # Fix security issues
```

**Backend**:
```bash
# Update pyproject.toml dependencies
uv sync
```

### Running Tests

**Backend**:
```bash
pytest tests/
```

**Frontend**:
```bash
cd web
npm run lint
npm run audit  # Playwright UI tests
```

---

## Deployment Modes

### Development

```bash
# Both from source
FRONTEND_DEV_MODE=true realtimex-deeptutor
```

### Production (Local)

```bash
# Uses published frontend, local backend
realtimex-deeptutor
```

### Production (Full Published)

```bash
# Install from PyPI/NPM
uv tool install realtimex-deeptutor
realtimex-deeptutor
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `FRONTEND_PORT` | Frontend port | 3782 |
| `BACKEND_PORT` | Backend port | 8001 |
| `FRONTEND_DEV_MODE` | Run frontend from source | `false` |
| `API_BASE_URL` | Backend API URL | Auto-configured |
| `LOG_LEVEL` | Logging verbosity | INFO |

---

## Troubleshooting

### "npx: command not found"

Install Node.js: https://nodejs.org/

Or use development mode:
```bash
FRONTEND_DEV_MODE=true realtimex-deeptutor
```

### Frontend not updating after code changes

You're in production mode. Use development mode:
```bash
FRONTEND_DEV_MODE=true realtimex-deeptutor
```

### Port already in use

Check and kill processes:
```bash
lsof -i :8001  # Backend
lsof -i :3782  # Frontend
kill -9 <PID>
```

Or use different ports:
```bash
FRONTEND_PORT=4001 BACKEND_PORT=8002 realtimex-deeptutor
```

### Published package not reflecting changes

1. Verify version was bumped
2. Check NPM registry: `npm view @realtimex/opentutor-web`
3. Clear npx cache: `npx clear-npx-cache`

---

## Workflow Summary

### Regular Development
1. Make changes in `src/` or `web/`
2. Test with `FRONTEND_DEV_MODE=true realtimex-deeptutor`
3. Commit and push

### Publishing Update
1. **Bump version** in `package.json` and/or `pyproject.toml`
2. **Build**: `npm run build:package` and/or `uv build`
3. **Publish**: `npm publish` and/or `uv publish`
4. **Verify**: Test with published versions
5. **Tag release**: `git tag v0.x.x && git push --tags`

### Handing Off to Team
1. Ensure all changes are committed
2. Update this documentation if workflows changed
3. Verify latest versions are published
4. Test clean install: `uvx realtimex-deeptutor`

---

## Next Steps

- **Features**: See project README for feature documentation
- **Architecture**: See `docs/` for technical details
- **Issues**: Check GitHub issues for known problems
- **Contributing**: Follow standard Git workflow (fork → branch → PR)
