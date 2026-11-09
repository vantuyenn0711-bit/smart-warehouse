"""Start the existing local Warehouse environment without changing Windows policies."""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def existing_warehouse(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    url = f"http://127.0.0.1:{port}"
    try:
        with opener.open(url + "/health/", timeout=3) as response:
            healthy = json.load(response).get("status") == "ok"
        with opener.open(url + "/login/", timeout=3) as response:
            page = response.read(200_000).decode("utf-8", errors="replace")
        return healthy and "Smart Warehouse</title>" in page
    except (OSError, ValueError):
        return False


def start_docker(port, open_browser=False):
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker Desktop is required for Docker mode. See README.md.")
    docker_config = ROOT / ".runtime" / "docker-config"
    docker_config.mkdir(parents=True, exist_ok=True)
    docker_args = [docker, "--config", str(docker_config)]
    probe_args = docker_args + ["info", "--format", "{{.ServerVersion}}"]

    def engine_ready():
        try:
            return subprocess.run(probe_args, capture_output=True, timeout=5).returncode == 0
        except subprocess.TimeoutExpired:
            return False

    if not engine_ready():
        flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        subprocess.run(docker_args + ["desktop", "start", "--detach"], check=True, **flags)
        deadline = time.monotonic() + 60
        while not engine_ready():
            if time.monotonic() >= deadline:
                raise SystemExit("Docker Engine did not become ready. Open Docker Desktop and retry.")
            time.sleep(1)
    compose = docker_args + ["compose", "--project-directory", str(ROOT), "--env-file",
                             str(ROOT / ".env"), "-f", str(ROOT / "compose.yaml")]
    environment = os.environ.copy()
    environment["APP_PORT"] = str(port)
    commands = [
        ["build"],
        ["up", "-d", "--wait", "--wait-timeout", "90", "db"],
        ["run", "--rm", "app", "python", "manage.py", "migrate", "--noinput"],
        ["run", "--rm", "app", "python", "manage.py", "seed_demo", "--if-empty"],
        ["up", "-d", "--wait", "--wait-timeout", "90", "app"],
    ]
    for command in commands:
        subprocess.run(compose + command, check=True, env=environment)
    url = f"http://127.0.0.1:{port}/"
    print(f"Smart Warehouse is ready: {url}")
    print("Docker mode keeps the app running. Stop it with: docker compose stop")
    if open_browser:
        webbrowser.open(url)
    return 0


def main():
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8", line_buffering=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8010)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--docker", action="store_true", help="Run Django/PostgreSQL in local Docker.")
    modes.add_argument("--native", action="store_true", help="Use the current Python/PostgreSQL environment.")
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    root = ROOT
    docker_mode = args.docker or (os.name == "nt" and not args.native)
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535.")
    if not (root / ".env").is_file():
        parser.error("Create .env using scripts/init_env.py first; see README.md.")
    with socket.socket() as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError:
            if docker_mode and existing_warehouse(args.port):
                url = f"http://127.0.0.1:{args.port}/"
                print(f"Smart Warehouse is already running: {url}")
                if args.open_browser:
                    webbrowser.open(url)
                return 0
            parser.error(f"Port {args.port} is in use. Stop your Warehouse server or choose --port.")
    os.chdir(root)
    if docker_mode:
        return start_docker(args.port, args.open_browser)
    driver = subprocess.run([sys.executable, "-c", "import psycopg"], capture_output=True)
    if driver.returncode:
        parser.error("Native PostgreSQL driver is unavailable or blocked. Use --docker; no Windows policy change is required.")
    if os.name == "nt" and (root / ".runtime/pgsql/bin/pg_ctl.exe").is_file():
        subprocess.run([sys.executable, "scripts/local_postgres.py", "start"], check=True)
    subprocess.run([sys.executable, "manage.py", "check"], check=True)
    print(f"Smart Warehouse: http://127.0.0.1:{args.port}/ (Ctrl+C to stop)")
    if args.open_browser:
        webbrowser.open(f"http://127.0.0.1:{args.port}/")
    try:
        return subprocess.run([sys.executable, "manage.py", "runserver", f"127.0.0.1:{args.port}", "--noreload"]).returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
