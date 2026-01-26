"""
Unified startup entry point for DeepTutor.

Design Philosophy:
- Configuration over code: Behavior driven by config files + CLI args
- Fail fast: Validate early with actionable error messages
- Extensible: Easy to add new modes and commands
- Maintainable: Clean separation between CLI and core logic

Usage:
    uvx realtimex-deeptutor                    # Start with defaults
    uvx realtimex-deeptutor --port 4001        # Custom frontend port
    uvx realtimex-deeptutor --backend-only     # Backend only (future)
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def create_parser() -> argparse.ArgumentParser:
    """
    Create CLI argument parser following Unix conventions.

    Design: Minimal CLI options, environment-driven configuration.
    """
    parser = argparse.ArgumentParser(
        prog="realtimex-deeptutor",
        description="DeepTutor - AI-Powered Personalized Learning Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uvx realtimex-deeptutor                       # Start with defaults
  FRONTEND_PORT=4001 uvx realtimex-deeptutor    # Custom frontend port
  BACKEND_PORT=8002 uvx realtimex-deeptutor     # Custom backend port

Environment Variables:
  FRONTEND_PORT       Frontend port (default: 3782)
  BACKEND_PORT        Backend port (default: 8001)
  AUTO_KILL_PORTS     Auto-kill processes using required ports (default: false)
  RTX_APP_ID          RealTimeX App ID (auto-detected)
  API_BASE_URL        Backend API URL (auto-configured)
  LOG_LEVEL           Logging level (DEBUG, INFO, WARNING, ERROR)

For more information: https://github.com/therealtimex/DeepTutor-local-app
        """,
    )

    # Mode selection (future extensibility)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--backend-only",
        action="store_true",
        help="Start backend only (FastAPI) [NOT YET IMPLEMENTED]",
    )
    mode_group.add_argument(
        "--frontend-only",
        action="store_true",
        help="Start frontend only (Next.js) [NOT YET IMPLEMENTED]",
    )

    # Logging configuration
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO)",
    )

    return parser


def find_project_root() -> Path:
    """
    Find DeepTutor project root directory.

    Strategy:
    1. Use __file__ location (works for both installed and development)
    2. Fall back to pyproject.toml search for development mode

    Returns:
        Path: Absolute path to project root

    Raises:
        RuntimeError: If project root cannot be determined
    """
    # Primary strategy: Use __file__ location
    # This file is at: <root>/src/cli/start.py
    # So root is 3 levels up: start.py -> cli -> src -> root
    package_root = Path(__file__).resolve().parent.parent.parent

    # Validate by checking for essential package content (not pyproject.toml)
    if (package_root / "src" / "api").is_dir():
        return package_root

    # Fallback: Development mode - look for pyproject.toml
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent

    # Last fallback: return computed root without strict validation
    # This allows the package to attempt startup even if structure is unusual
    return package_root


def validate_environment(project_root: Path) -> None:
    """
    Validate environment and dependencies.

    Args:
        project_root: Path to project root

    Raises:
        RuntimeError: If validation fails
    """
    # Check for start_web.py
    start_script = project_root / "scripts" / "start_web.py"
    if not start_script.exists():
        raise RuntimeError(
            f"Required script not found: {start_script}\n"
            f"Project root: {project_root}\n"
            "Please ensure DeepTutor is properly installed."
        )

    # Check for web directory only in development mode
    # In production mode, frontend is served via npx @realtimex/opentutor-web
    dev_mode = os.environ.get("FRONTEND_DEV_MODE", "").lower() in ("true", "1", "yes")
    if dev_mode:
        web_dir = project_root / "web"
        if not web_dir.exists():
            raise RuntimeError(
                f"Frontend directory not found: {web_dir}\n"
                "FRONTEND_DEV_MODE is enabled but web/ directory is missing.\n"
                "Either disable dev mode or run from the project source directory."
            )


def main():
    """
    Main CLI entry point.

    Flow:
    1. Parse arguments
    2. Find and validate project root
    3. Build environment
    4. Delegate to appropriate launcher
    """
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Find project root
        project_root = find_project_root()

        # Validate environment
        validate_environment(project_root)

        # Build environment for subprocess
        # All configuration comes from environment variables
        env = os.environ.copy()

        # Set log level
        env["LOG_LEVEL"] = args.log_level

        # Handle mode selection
        if args.backend_only:
            print("⚠️  Backend-only mode not yet implemented")
            print("   Use 'uvx realtimex-deeptutor' for full-stack startup")
            print("   Or use 'deeptutor-backend' for backend-only")
            sys.exit(1)

        if args.frontend_only:
            print("⚠️  Frontend-only mode not yet implemented")
            print("   Use 'uvx realtimex-deeptutor' for full-stack startup")
            print("   Or use 'npx @realtimex/opentutor-web' for frontend-only")
            sys.exit(1)

        # Full-stack mode: delegate to start_web.py
        print("🚀 Starting DeepTutor (Full Stack)...")
        print(f"📁 Project root: {project_root}")

        script_path = project_root / "scripts" / "start_web.py"

        # Launch start_web.py with updated environment
        subprocess.run([sys.executable, str(script_path)], env=env, cwd=project_root, check=True)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        sys.exit(0)

    except RuntimeError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

    except subprocess.CalledProcessError as e:
        # start_web.py already printed error messages
        sys.exit(e.returncode)

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
