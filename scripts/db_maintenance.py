"""Local PostgreSQL dump/restore without putting passwords in command arguments."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parent.parent


def main():
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--confirm-restore", action="store_true")
    parser.add_argument("--drive", default="W:", help="Optional ASCII Windows drive mapping for a Unicode workspace.")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    connection_url = os.environ.get("DATABASE_URL", "")
    if not connection_url:
        parser.error("DATABASE_URL is required in the environment or local .env.")
    try:
        connection = conninfo_to_dict(connection_url)
    except psycopg.ProgrammingError:
        parser.error("DATABASE_URL is not a valid PostgreSQL connection URL.")
    connection["host"] = os.environ.get("DATABASE_HOST", connection.get("host", "127.0.0.1"))
    connection["port"] = os.environ.get("DATABASE_PORT", connection.get("port", "5432"))
    if connection["host"] not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("This runbook supports local databases only. Remote operations need a separate reviewed procedure.")
    ascii_root = ROOT
    if os.name == "nt" and not str(ROOT).isascii():
        drive = args.drive.upper()
        if len(drive) != 2 or not drive[0].isalpha() or drive[1] != ":":
            parser.error("--drive must be an unused drive letter such as W:")
        ascii_root = Path(drive + "\\")
        if ascii_root.exists():
            if not os.path.samefile(ascii_root, ROOT):
                parser.error("The selected drive is already in use by another path. Choose --drive.")
        else:
            subprocess.run(["subst", drive, str(ROOT)], check=True, capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)

    def client_path(path):
        resolved = Path(path).resolve()
        if resolved.is_relative_to(ROOT):
            return str(ascii_root / resolved.relative_to(ROOT))
        if os.name == "nt" and not str(resolved).isascii():
            parser.error("Choose an ASCII path or a path inside the mapped project workspace.")
        return str(resolved)

    executable_name = "pg_dump" if args.action == "backup" else "pg_restore"
    suffix = ".exe" if os.name == "nt" else ""
    candidates = [args.pg_bin / (executable_name + suffix)] if args.pg_bin else []
    candidates += [ROOT / ".runtime" / "pgsql" / "bin" / (executable_name + suffix)]
    executable = next((str(path) for path in candidates if path.is_file()), shutil.which(executable_name))
    if not executable:
        parser.error("Install PostgreSQL client tools or supply --pg-bin pointing to their bin directory.")
    executable = client_path(executable)
    target = args.file.resolve()
    if args.action == "backup":
        if target.exists():
            parser.error("The backup file already exists. Choose a new filename; no file was overwritten.")
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [executable, "--format=custom", "--no-owner", "--file", client_path(target)]
    else:
        if not args.confirm_restore:
            parser.error("Restore requires --confirm-restore and an explicitly configured empty local database.")
        if not target.is_file():
            parser.error("The specified backup file does not exist.")
        connection.setdefault("connect_timeout", "10")
        with psycopg.connect(**connection) as database:
            tables = database.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'").fetchone()[0]
            if tables:
                parser.error("Restore target is not empty. Existing tables were left unchanged; use a new database.")
        command = [executable, "--dbname", connection["dbname"], "--single-transaction", "--exit-on-error", "--no-owner", "--no-privileges", client_path(target)]
    client_env = os.environ.copy()
    for setting, variable in {"host": "PGHOST", "port": "PGPORT", "user": "PGUSER", "password": "PGPASSWORD", "dbname": "PGDATABASE", "sslmode": "PGSSLMODE"}.items():
        if setting in connection:
            client_env[variable] = connection[setting]
    client_env["PGCONNECT_TIMEOUT"] = "10"
    result = subprocess.run(command, env=client_env, capture_output=True, text=True, check=False)
    if result.returncode:
        diagnostic = result.stderr.strip()
        for secret in (connection_url, connection.get("password", "")):
            if secret:
                diagnostic = diagnostic.replace(secret, "[REDACTED]")
        print(f"PostgreSQL client failed (exit {result.returncode}): {diagnostic}", file=sys.stderr)
        raise SystemExit(result.returncode)
    print(f"{'Backup created' if args.action == 'backup' else 'Backup restored into empty database'}: {target}")


if __name__ == "__main__":
    main()
