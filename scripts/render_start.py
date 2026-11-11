"""Release tasks and a signal-safe Gunicorn process for the Render free demo."""
import os
import subprocess
import sys
from pathlib import Path


def gunicorn_command(environment):
    port = int(environment.get("PORT", "10000"))
    workers = int(environment.get("WEB_CONCURRENCY", "1"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535.")
    if not 1 <= workers <= 4:
        raise ValueError("WEB_CONCURRENCY must be between 1 and 4.")
    return [
        "gunicorn", "config.wsgi:application", "--bind", f"0.0.0.0:{port}",
        "--workers", str(workers), "--threads", "2", "--timeout", "120",
        "--access-logfile", "-", "--error-logfile", "-",
    ]


def main():
    command = gunicorn_command(os.environ)
    os.chdir(Path(__file__).resolve().parent.parent)
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
    if os.environ.get("DEMO_MODE", "false").lower() == "true":
        subprocess.run([sys.executable, "manage.py", "seed_demo", "--if-empty"], check=True)
    subprocess.run([sys.executable, "manage.py", "prepare_public_demo"], check=True)
    # Replace the launcher so Render's SIGTERM reaches Gunicorn directly.
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
