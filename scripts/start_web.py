import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from dotenv import load_dotenv

# Load environment variables from .env file
# This allows users to configure NEXT_PUBLIC_API_BASE for remote access
project_root = Path(__file__).parent.parent
load_dotenv(project_root / "DeepTutor.env", override=False)
load_dotenv(project_root / ".env", override=False)

# Force unbuffered output for the main process
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


class ExecutableResolver:
    """
    Resolves bundled executables (uvx, uv, npx) to their actual paths.
    Ported from ExecutableResolver.js
    """

    def __init__(self):
        self._resources_root = None

    def get_resources_root(self) -> Path | None:
        """
        Get the resources root directory (~/.realtimex.ai)
        Returns path to resources root or None if not found
        """
        if self._resources_root:
            return self._resources_root

        try:
            home = Path.home()
            self._resources_root = home / ".realtimex.ai"
            return self._resources_root
        except Exception as e:
            print_flush(f"⚠️ [ExecutableResolver] Failed to resolve resources directory: {e}")
            return None

    def resolve_from_candidates(
        self, env_var: str | None, candidates: list[Path | str]
    ) -> str | None:
        """
        Find a valid executable from a list of candidate paths
        """
        search_paths = []
        if env_var:
            search_paths.append(Path(env_var))

        search_paths.extend([Path(c) for c in candidates])

        for candidate in search_paths:
            if not candidate:
                continue
            try:
                if candidate.exists() and candidate.is_file():
                    return str(candidate)
            except Exception:
                pass
        return None

    def resolve_npx(self) -> str | None:
        """
        Resolve npx to bundled executable
        """
        resources_dir = self.get_resources_root()
        if not resources_dir:
            return None

        node_version = os.environ.get("REALTIMEX_NPX_NODE_VERSION", "v22.16.0")
        home = Path.home()

        candidates = [
            # User's NVM installation (most common case)
            home / ".nvm" / "versions" / "node" / node_version / "bin" / "npx",
            # NVM-installed node in resources dir (bundled)
            resources_dir / ".nvm" / "versions" / "node" / node_version / "bin" / "npx",
            # Windows NVM
            Path("C:/nvm") / node_version / "npx.cmd",
            # Bundled in Resources
            resources_dir / "Resources" / "envs" / "Scripts" / "npx.cmd",
        ]

        return self.resolve_from_candidates(
            env_var=os.environ.get("REALTIMEX_NPX_PATH"), candidates=candidates
        )


def print_flush(*args, **kwargs):
    """Print with flush=True by default"""
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)


# Windows-specific: Use SetConsoleCtrlHandler to prevent Ctrl+C from propagating to children
# and handle it only in the parent process
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    # Define the handler function type
    HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    # Global flag to track if we received Ctrl+C
    _ctrl_c_received = False

    def _ctrl_handler(ctrl_type):
        """Handle console control events on Windows."""
        global _ctrl_c_received
        if ctrl_type == 0:  # CTRL_C_EVENT
            _ctrl_c_received = True
            return True  # Return True to indicate we handled it
        return False

    # Keep a reference to prevent garbage collection
    _handler = HANDLER_ROUTINE(_ctrl_handler)

    def setup_windows_ctrl_handler():
        """Set up Windows Ctrl+C handler to prevent propagation to children."""
        # Add our handler
        if not kernel32.SetConsoleCtrlHandler(_handler, True):
            print_flush("⚠️ Warning: Failed to set console control handler")

    def check_ctrl_c_received():
        """Check if Ctrl+C was received."""
        return _ctrl_c_received
else:

    def setup_windows_ctrl_handler():
        pass

    def check_ctrl_c_received():
        return False


def find_pid_by_port(port: int) -> int | None:
    """
    Find PID using a port with multiple fallback methods.
    Returns PID or None if not found.
    """
    if os.name == "nt":
        # Windows: use netstat
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        try:
                            return int(parts[-1])
                        except ValueError:
                            pass
        except Exception:
            pass
        return None

    # Unix: Try strategies in order: lsof -> ss -> netstat

    # Strategy 1: lsof (standard)
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                # May return multiple PIDs, take the first one
                return int(result.stdout.strip().split()[0])
            except (ValueError, IndexError):
                pass
    except FileNotFoundError:
        pass  # lsof not installed
    except Exception:
        pass

    # Strategy 2: ss (modern Linux)
    try:
        # ss -lptn 'sport = :8001'
        result = subprocess.run(
            ["ss", "-lptn", f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Output format: Users:(("python",pid=1234,fd=3))
            output = result.stdout
            if f":{port}" in output and "pid=" in output:
                import re

                match = re.search(r"pid=(\d+)", output)
                if match:
                    return int(match.group(1))
    except FileNotFoundError:
        pass  # ss not installed
    except Exception:
        pass

    # Strategy 3: netstat (legacy Unix)
    try:
        # netstat -nlp | grep :8001
        p1 = subprocess.Popen(
            ["netstat", "-nlp"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        p2 = subprocess.Popen(
            ["grep", f":{port}"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True
        )
        if p1.stdout:
            p1.stdout.close()
        output, _ = p2.communicate(timeout=5)

        if output:
            # Expected: tcp 0 0 0.0.0.0:8001 0.0.0.0:* LISTEN 1234/python
            parts = output.split()
            for part in parts:
                if "/" in part and part.split("/")[0].isdigit():
                    return int(part.split("/")[0])
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return None


def check_port_in_use(port: int) -> tuple[bool, int | None]:
    """
    Check if a port is in use and return the PID of the process using it.

    Uses connect test to check if something is actually LISTENING on the port,
    rather than bind test which fails for TIME_WAIT state.

    Args:
        port: Port number to check

    Returns:
        Tuple of (is_in_use, pid_or_none)
    """
    import socket

    # Use connect test to check if something is actually listening
    # This avoids false positives from TIME_WAIT state
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(("localhost", port))
        if result != 0:
            # Connection refused = nothing listening = port is free
            return False, None
    except (OSError, socket.timeout):
        # Connection failed = port is free
        return False, None
    finally:
        try:
            sock.close()
        except Exception:
            pass

    # Port is in use (connection succeeded), try to find the PID
    pid = find_pid_by_port(port)
    return True, pid


def kill_process_on_port(port: int, force: bool = False) -> bool:
    """
    Kill the process using a specific port.

    Args:
        port: Port number
        force: If True, use SIGKILL instead of SIGTERM

    Returns:
        True if process was killed successfully
    """
    in_use, pid = check_port_in_use(port)
    if not in_use:
        return True  # Port is free

    if pid is None:
        print_flush(f"⚠️  Port {port} is in use but couldn't identify the process")
        # Retry detection once with slightly longer delay just in case
        time.sleep(1)
        _, pid = check_port_in_use(port)
        if pid is None:
            return False

    print_flush(f"   Stopping process {pid} on port {port}...")

    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True, capture_output=True)
        else:
            # Try to kill the process group first (handles child processes)
            try:
                pgid = os.getpgid(pid)
                sig = signal.SIGKILL if force else signal.SIGTERM
                os.killpg(pgid, sig)
            except (ProcessLookupError, PermissionError):
                # Fallbck to simple kill if PGID fails
                sig = signal.SIGKILL if force else signal.SIGTERM
                os.kill(pid, sig)

            # Wait a moment for process to terminate
            time.sleep(0.5)
            # Check if still running, force kill if needed
            if not force:
                try:
                    os.kill(pid, 0)  # Check if process exists
                    # If still alive, Force Kill
                    print_flush(f"   Process {pid} still alive, force killing...")
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except:
                        os.kill(pid, signal.SIGKILL)
                    time.sleep(0.3)
                except ProcessLookupError:
                    pass  # Process already terminated

        # Verify port is now free
        time.sleep(0.5)
        in_use, _ = check_port_in_use(port)
        if not in_use:
            print_flush(f"✅ Port {port} is now free")
            return True
        else:
            print_flush(f"⚠️  Port {port} still in use after killing process")
            return False

    except Exception as e:
        print_flush(f"❌ Failed to kill process {pid}: {e}")
        return False


def ensure_ports_available(backend_port: int, frontend_port: int, auto_kill: bool = False) -> bool:
    """
    Ensure required ports are available, optionally killing existing processes.

    Args:
        backend_port: Backend port number
        frontend_port: Frontend port number
        auto_kill: If True, automatically kill processes using the ports

    Returns:
        True if all ports are available
    """
    ports_to_check = [
        (backend_port, "Backend"),
        (frontend_port, "Frontend"),
    ]

    conflicts = []
    for port, name in ports_to_check:
        in_use, pid = check_port_in_use(port)
        if in_use:
            conflicts.append((port, name, pid))

    if not conflicts:
        return True

    print_flush("")
    print_flush("⚠️  Port conflict detected:")
    for port, name, pid in conflicts:
        pid_info = f" (PID: {pid})" if pid else ""
        print_flush(f"   - {name} port {port} is already in use{pid_info}")

    if auto_kill:
        print_flush("")
        print_flush("🔄 AUTO_KILL_PORTS is enabled, cleaning up...")
        all_freed = True
        for port, name, _ in conflicts:
            if not kill_process_on_port(port):
                all_freed = False
        return all_freed
    else:
        print_flush("")
        print_flush("💡 To resolve this, you can either:")
        print_flush("   1. Set AUTO_KILL_PORTS=true to automatically clean up")
        print_flush("   2. Manually kill the processes:")
        for port, name, pid in conflicts:
            if pid:
                if os.name == "nt":
                    print_flush(f"      taskkill /F /PID {pid}")
                else:
                    print_flush(f"      kill -9 {pid}")
            else:
                if os.name == "nt":
                    print_flush(f"      netstat -ano | findstr :{port}")
                else:
                    print_flush(f"      lsof -ti :{port} | xargs kill -9")
        print_flush("   3. Use different ports via environment variables:")
        print_flush("      BACKEND_PORT=8002 FRONTEND_PORT=3783 uvx realtimex-deeptutor")
        print_flush("")
        return False


def terminate_process_tree(process, name="Process", timeout=5):
    """
    Terminate a process and all its children (process group).

    On Unix: Uses process group (PGID) to kill all children including uvicorn workers.
    On Windows: Uses taskkill /T to kill the process tree.

    Args:
        process: subprocess.Popen object
        name: Display name for logging
        timeout: Seconds to wait for graceful termination before SIGKILL
    """
    if process is None or process.poll() is not None:
        return  # Process already terminated

    pid = process.pid
    print_flush(f"🛑 Stopping {name} (PID: {pid})...")

    try:
        if os.name == "nt":
            # Windows: Use taskkill with /T to kill the entire process tree
            # /F = Force termination, /T = Kill child processes too
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                capture_output=True,
                text=True,
            )
            # Wait for process to actually terminate
            try:
                process.wait(timeout=timeout)
                print_flush(f"   ✅ {name} terminated successfully")
            except subprocess.TimeoutExpired:
                print_flush(f"   ⚠️ {name} did not terminate within {timeout}s")
                # Force kill via process.kill() as backup
                try:
                    process.kill()
                    process.wait(timeout=2)
                except Exception:
                    pass
        else:
            # Unix: Kill the entire process group
            pgid = os.getpgid(pid)

            # Step 1: Send SIGTERM to the process group for graceful shutdown
            try:
                os.killpg(pgid, signal.SIGTERM)
                print_flush(f"   Sent SIGTERM to process group {pgid}")
            except ProcessLookupError:
                print_flush(f"   Process group {pgid} already terminated")
                return
            except PermissionError:
                # Fallback: try to terminate just the main process
                print_flush("   Cannot kill process group, trying single process")
                process.terminate()

            # Step 2: Wait for graceful termination
            try:
                process.wait(timeout=timeout)
                print_flush(f"   ✅ {name} terminated gracefully")
                return
            except subprocess.TimeoutExpired:
                print_flush(f"   ⚠️ {name} did not terminate in {timeout}s, sending SIGKILL...")

            # Step 3: Force kill with SIGKILL
            try:
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=2)
                print_flush(f"   ✅ {name} force killed")
            except ProcessLookupError:
                print_flush("   Process group already terminated")
            except Exception as e:
                print_flush(f"   ⚠️ Error during force kill: {e}")
                # Last resort: try to kill just the main process
                try:
                    process.kill()
                    process.wait(timeout=2)
                except Exception:
                    pass

    except Exception as e:
        print_flush(f"   ⚠️ Error stopping {name}: {e}")


def start_backend():
    print_flush(f"🚀 Starting FastAPI Backend using {sys.executable}...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    print_flush(f"📁 Working directory: {base_dir}")
    print_flush(f"📁 Project root: {project_root}")

    # Ensure project root is in Python path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Get port from environment variable (default: 8001)
    from src.services.setup import get_backend_port

    backend_port = get_backend_port()
    print_flush(f"✅ Backend port: {backend_port}")

    # Check if api.main can be imported
    try:
        print_flush("✅ Backend module import successful")
    except Exception as e:
        print_flush(f"❌ Failed to import backend module: {e}")
        import traceback

        traceback.print_exc()
        raise

    # Use custom startup script for better reload handling
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_server_script = os.path.join(project_root, "src", "api", "run_server.py")
    cmd = [sys.executable, run_server_script]

    # Set environment variables for encoding and unbuffered output
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    if os.name == "nt":
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"

    # Use start_new_session=True on Unix to create a new process group
    # This allows us to kill all child processes (including uvicorn workers) at once
    popen_kwargs = {
        "cwd": project_root,  # Run in project root directory, not scripts directory
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "shell": False,
        "encoding": "utf-8",
        "errors": "replace",
        "env": env,
    }

    # On Unix, create a new session so we can kill the entire process group
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    else:
        # On Windows, create a new process group so Ctrl+C doesn't propagate to children
        # This prevents child processes from receiving Ctrl+C signals directly
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(cmd, **popen_kwargs)

    # Start a thread to output logs in real-time
    import threading

    def log_output():
        try:
            for line in iter(process.stdout.readline, ""):
                if line:
                    print_flush(f"[Backend] {line.rstrip()}")
        except Exception as e:
            print_flush(f"[Backend] Log output error: {e}")

    log_thread = threading.Thread(target=log_output, daemon=True)
    log_thread.start()

    print_flush(f"✅ Backend process started (PID: {process.pid})")
    if os.name != "nt":
        print_flush(f"   Process group ID (PGID): {os.getpgid(process.pid)}")
    return process


def start_frontend():
    """
    Start frontend in production or development mode.

    Production mode (default): Uses npx @realtimex/opentutor-web
    Development mode: Uses npm run dev from source (set FRONTEND_DEV_MODE=true)
    """
    print_flush("🚀 Starting Next.js Frontend...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    web_dir = os.path.join(project_root, "web")

    # Ensure project root is in Python path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Get ports
    from pathlib import Path

    from src.services.setup import get_backend_port, get_frontend_port

    frontend_port = get_frontend_port()
    backend_port = get_backend_port(Path(project_root))
    print_flush(f"✅ Frontend port: {frontend_port}")

    # Check mode: development (source) vs production (published package)
    dev_mode = os.environ.get("FRONTEND_DEV_MODE", "").lower() in ("true", "1", "yes")

    if dev_mode:
        print_flush("📦 Development mode: Running from source (npm run dev)")
        return _start_frontend_dev(web_dir, frontend_port, backend_port, project_root)
    else:
        print_flush("📦 Production mode: Using published package (npx @realtimex/opentutor-web)")
        return _start_frontend_npx(frontend_port, backend_port)


def _start_frontend_dev(web_dir, frontend_port, backend_port, project_root):
    """Start frontend from source using npm run dev (development mode)"""

    # Check if npm is available
    npm_path = shutil.which("npm")
    if not npm_path:
        print_flush("❌ Error: 'npm' command not found!")
        print_flush("   Please install Node.js and npm first.")
        print_flush("   You can install it from: https://nodejs.org/")
        print_flush("   Or use a package manager like Homebrew: brew install node")
        raise RuntimeError("npm is not installed or not in PATH")

    print_flush(f"✅ Found npm at: {npm_path}")

    # Check if node_modules exists
    if not os.path.exists(os.path.join(web_dir, "node_modules")):
        print_flush("📦 Installing frontend dependencies...")
        print_flush("   This may take a few minutes, please wait...")
        try:
            npm_cmd = shutil.which("npm") or "npm"
            process = subprocess.Popen(
                [npm_cmd, "install"],
                cwd=web_dir,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in iter(process.stdout.readline, ""):
                if line:
                    if any(
                        keyword in line.lower()
                        for keyword in ["error", "failed", "added", "audited", "vulnerabilities"]
                    ):
                        print_flush(f"   {line.rstrip()}")

            process.wait()

            if process.returncode != 0:
                if os.path.exists(os.path.join(web_dir, "node_modules")):
                    print_flush("✅ Frontend dependencies installed (with warnings)")
                else:
                    print_flush(
                        f"❌ Failed to install frontend dependencies (exit code: {process.returncode})"
                    )
                    raise RuntimeError(f"npm install failed with exit code {process.returncode}")
            else:
                print_flush("✅ Frontend dependencies installed successfully")
        except Exception as e:
            print_flush(f"❌ Failed to install frontend dependencies: {e}")
            raise

    print_flush("🚀 Starting Next.js development server...")
    # Get backend port for frontend API configuration
    from pathlib import Path

    from src.services.setup import get_backend_port

    backend_port = get_backend_port(Path(project_root))

    # Determine API base URL with priority:
    # 1. NEXT_PUBLIC_API_BASE_EXTERNAL (for cloud/remote deployment)
    # 2. NEXT_PUBLIC_API_BASE (custom API URL)
    # 3. Default: http://localhost:{backend_port}
    api_base_url = (
        os.environ.get("NEXT_PUBLIC_API_BASE_EXTERNAL")
        or os.environ.get("NEXT_PUBLIC_API_BASE")
        or f"http://localhost:{backend_port}"
    )

    if os.environ.get("NEXT_PUBLIC_API_BASE_EXTERNAL"):
        print_flush(f"📌 Using external API URL from env: {api_base_url}")
    elif os.environ.get("NEXT_PUBLIC_API_BASE"):
        print_flush(f"📌 Using custom API URL from env: {api_base_url}")
    else:
        print_flush(f"📌 Using default API URL: {api_base_url}")
        print_flush("   💡 For remote access, set NEXT_PUBLIC_API_BASE in .env file")

    # Generate/update .env.local file with port configuration
    # This ensures Next.js can read the backend port even if environment variables are not passed
    env_local_path = os.path.join(web_dir, ".env.local")
    try:
        with open(env_local_path, "w", encoding="utf-8") as f:
            f.write("# ============================================\n")
            f.write("# Auto-generated by start_web.py\n")
            f.write("# ============================================\n")
            f.write("# This file is automatically updated based on config/main.yaml\n")
            f.write(
                "# and environment variables (NEXT_PUBLIC_API_BASE, NEXT_PUBLIC_API_BASE_EXTERNAL)\n"
            )
            f.write("# \n")
            f.write("# To configure for remote access, set in your .env file:\n")
            f.write("#   NEXT_PUBLIC_API_BASE=http://your-server-ip:8001\n")
            f.write("# ============================================\n\n")
            f.write(f"NEXT_PUBLIC_API_BASE={api_base_url}\n")
        print_flush(f"✅ Updated .env.local with API base: {api_base_url}")
    except Exception as e:
        print_flush(f"⚠️ Warning: Failed to update .env.local: {e}")
        print_flush("   Continuing with environment variables only...")

    # Set environment variables for Next.js (as backup)
    env = os.environ.copy()
    env["PORT"] = str(frontend_port)
    env["NEXT_PUBLIC_API_BASE"] = api_base_url
    # Set encoding environment variables for Windows
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    if os.name == "nt":
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"

    npm_cmd = shutil.which("npm") or "npm"

    # Use start_new_session=True on Unix to create a new process group
    # This allows us to kill all child processes (including Next.js workers) at once
    popen_kwargs = {
        "cwd": web_dir,
        "shell": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "env": env,
        "encoding": "utf-8",
        "errors": "replace",
    }

    # On Unix, create a new session so we can kill the entire process group
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    else:
        # On Windows, create a new process group so Ctrl+C doesn't propagate to children
        # This prevents npm from showing "Terminate batch job (Y/N)?" prompt
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "-p", str(frontend_port)],
        **popen_kwargs,
    )

    # Start a thread to output frontend logs in real-time
    import threading

    def log_frontend_output():
        try:
            for line in iter(frontend_process.stdout.readline, ""):
                if line:
                    print_flush(f"[Frontend] {line.rstrip()}")
        except Exception as e:
            print_flush(f"[Frontend] Log output error: {e}")

    log_thread = threading.Thread(target=log_frontend_output, daemon=True)
    log_thread.start()

    print_flush(f"✅ Frontend process started (PID: {frontend_process.pid})")
    if os.name != "nt":
        print_flush(f"   Process group ID (PGID): {os.getpgid(frontend_process.pid)}")
    return frontend_process


def _start_frontend_npx(frontend_port, backend_port):
    """Start frontend using published package via npx (production mode)"""

    # Check if npx is available
    resolver = ExecutableResolver()
    npx_path = resolver.resolve_npx() or shutil.which("npx")

    if not npx_path:
        print_flush("❌ Error: 'npx' command not found!")
        print_flush("   Please install Node.js and npm first.")
        print_flush("   You can install it from: https://nodejs.org/")
        print_flush("   Or set FRONTEND_DEV_MODE=true to run from source")
        raise RuntimeError("npx is not installed or not in PATH")

    print_flush(f"✅ Found npx at: {npx_path}")

    # Determine API base URL
    api_base_url = (
        os.environ.get("NEXT_PUBLIC_API_BASE_EXTERNAL")
        or os.environ.get("NEXT_PUBLIC_API_BASE")
        or os.environ.get("API_BASE_URL")
        or f"http://localhost:{backend_port}"
    )

    print_flush(f"📌 Using API URL: {api_base_url}")

    # Set environment variables
    env = os.environ.copy()
    env["API_BASE_URL"] = api_base_url
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    if os.name == "nt":
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"

    npx_cmd = npx_path or "npx"

    # Process group configuration
    popen_kwargs = {
        "shell": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "env": env,
        "encoding": "utf-8",
        "errors": "replace",
    }

    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    else:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    # Run npx @realtimex/opentutor-web with port and api-base
    # -y flag bypasses "Need to install" confirmation prompt
    frontend_process = subprocess.Popen(
        [
            npx_cmd,
            "-y",
            "@realtimex/opentutor-web",
            "-p",
            str(frontend_port),
            "--api-base",
            api_base_url,
        ],
        **popen_kwargs,
    )

    # Log output thread
    import threading

    def log_frontend_output():
        try:
            for line in iter(frontend_process.stdout.readline, ""):
                if line:
                    print_flush(f"[Frontend] {line.rstrip()}")
        except Exception as e:
            print_flush(f"[Frontend] Log output error: {e}")

    log_thread = threading.Thread(target=log_frontend_output, daemon=True)
    log_thread.start()

    print_flush(f"✅ Frontend process started (PID: {frontend_process.pid})")
    if os.name != "nt":
        print_flush(f"   Process group ID (PGID): {os.getpgid(frontend_process.pid)}")
    return frontend_process


if __name__ == "__main__":
    # Set up Windows-specific Ctrl+C handler before starting any processes
    setup_windows_ctrl_handler()

    print_flush("=" * 50)
    print_flush("DeepTutor Web Platform Launcher")
    print_flush("=" * 50)

    # Initialize user data directories
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from pathlib import Path

        from src.services.setup import init_user_directories

        init_user_directories(Path(project_root))
    except Exception as e:
        print_flush(f"⚠️ Warning: Failed to initialize user directories: {e}")
        print_flush("   Continuing anyway...")

    # Check for port conflicts before starting services
    try:
        from pathlib import Path

        from src.services.setup import get_ports

        backend_port, frontend_port = get_ports(
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )

        auto_kill = os.environ.get("AUTO_KILL_PORTS", "").lower() in ("true", "1", "yes")
        if not ensure_ports_available(backend_port, frontend_port, auto_kill=auto_kill):
            sys.exit(1)
    except Exception as e:
        print_flush(f"⚠️ Warning: Failed to check ports: {e}")
        print_flush("   Continuing anyway...")

    backend = None
    frontend = None

    try:
        backend = start_backend()

        # Get backend port for health check
        from pathlib import Path

        from src.services.setup import get_backend_port

        backend_port = get_backend_port(
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )

        print_flush("⏳ Waiting for backend to start...")
        for i in range(10):
            time.sleep(1)
            if backend.poll() is not None:
                print_flush(f"❌ Backend process exited with code {backend.returncode}")
                if backend.stdout:
                    output = backend.stdout.read()
                    if output:
                        print_flush(f"Backend output:\n{output}")
                break

            import socket

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("localhost", backend_port))
                sock.close()
                if result == 0:
                    print_flush(f"✅ Backend is running on port {backend_port}!")
                    break
            except:
                pass

        if backend.poll() is not None:
            print_flush("❌ Backend failed to start. Please check the error messages above.")
            sys.exit(1)

        frontend = start_frontend()

        # Get ports for display
        from pathlib import Path

        from src.services.setup import get_ports

        backend_port, frontend_port = get_ports(
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )

        print_flush("")
        print_flush("=" * 50)
        print_flush("✅ Services are running!")
        print_flush("=" * 50)
        print_flush(f"   - Backend:  http://localhost:{backend_port}/docs")
        print_flush(f"   - Frontend: http://localhost:{frontend_port}")
        print_flush("=" * 50)
        print_flush("")
        print_flush("Press Ctrl+C to stop all services.")

        while True:
            # Check for Ctrl+C via Windows handler or process exit
            if check_ctrl_c_received():
                print_flush("\n🛑 Ctrl+C detected, stopping services...")
                break
            if backend.poll() is not None:
                print_flush(
                    f"\n❌ Backend process exited unexpectedly (code: {backend.returncode})"
                )
                break
            time.sleep(0.5)  # Check more frequently for responsive shutdown

    except KeyboardInterrupt:
        print_flush("\n🛑 Stopping services...")
    except Exception as e:
        print_flush(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Use terminate_process_tree to properly kill all child processes
        # including uvicorn workers and Next.js child processes
        terminate_process_tree(backend, name="Backend", timeout=5)
        terminate_process_tree(frontend, name="Frontend", timeout=5)

        print_flush("✅ All services stopped.")
