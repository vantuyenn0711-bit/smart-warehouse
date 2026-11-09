"""Run an optional, workspace-isolated Windows PostgreSQL distribution.

Download/extract the official EDB Windows PostgreSQL binaries to .runtime/pgsql.
No Windows service is installed and no existing database is modified or removed.
An ASCII subst path works around PostgreSQL Windows command-line path encoding.
"""
import argparse
import os
import secrets
import subprocess
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("--drive", default="W:")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This optional helper is Windows-only. Use Docker Compose on Linux.")
    drive = args.drive.upper()
    if len(drive) != 2 or not drive[0].isalpha() or drive[1] != ":":
        parser.error("--drive must be a drive letter such as W:")
    drive_root = Path(drive + "\\")
    if drive_root.exists():
        if not os.path.samefile(drive_root, ROOT):
            parser.error(f"{drive} is in use by another path. Choose another --drive.")
    else:
        subprocess.run(["subst", drive, str(ROOT)], check=True)
    runtime = drive_root / ".runtime"
    pg_bin = runtime / "pgsql" / "bin"
    pg_data = runtime / "pgdata"
    if not (pg_bin / "pg_ctl.exe").exists():
        parser.error("Extract PostgreSQL Windows binaries to .runtime/pgsql first.")
    env = dotenv_values(ROOT / ".env")
    port = str(env.get("LOCAL_POSTGRES_PORT", "55432"))
    if not port.isdigit() or not 1024 <= int(port) <= 65535:
        parser.error("LOCAL_POSTGRES_PORT must be between 1024 and 65535.")
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW}

    def pg_run(*arguments, check=True):
        # pg_ctl's detached server inherits output handles on Windows; a PIPE
        # would keep communicate() waiting after pg_ctl itself has exited.
        with (runtime / "pg-command.log").open("ab") as output:
            result = subprocess.run(list(map(str, arguments)), stdout=output,
                                    stderr=subprocess.STDOUT, **flags)
        if check:
            result.check_returncode()
        return result

    if args.action == "status":
        return pg_run(pg_bin / "pg_ctl.exe", "status", "-D", pg_data, check=False).returncode
    if args.action == "stop":
        return pg_run(pg_bin / "pg_ctl.exe", "stop", "-D", pg_data, "-m", "fast", "-w").returncode
    admin_file = runtime / "pgadmin-password.txt"
    if not (pg_data / "PG_VERSION").exists():
        if pg_data.exists() and any(pg_data.iterdir()):
            parser.error("pgdata is not empty and has no PG_VERSION; inspect it manually.")
        if not admin_file.exists():
            with admin_file.open("x", encoding="ascii") as stream:
                stream.write(secrets.token_urlsafe(40))
        pg_run(pg_bin / "initdb.exe", "-D", pg_data, "-U", "postgres", "--pwfile", admin_file,
               "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C")
    status = subprocess.run([str(pg_bin / "pg_ctl.exe"), "status", "-D", str(pg_data)],
                            capture_output=True, **flags)
    if status.returncode:
        pg_run(pg_bin / "pg_ctl.exe", "start", "-D", pg_data, "-l", runtime / "postgres.log",
               "-o", f"-p {port} -h 127.0.0.1", "-w")
    admin_password = admin_file.read_text(encoding="ascii").strip()
    with psycopg.connect(host="127.0.0.1", port=port, dbname="postgres", user="postgres",
                         password=admin_password, autocommit=True) as conn:
        username, dbname = env.get("POSTGRES_USER", "warehouse"), env.get("POSTGRES_DB", "warehouse")
        password = env.get("POSTGRES_PASSWORD")
        if not password:
            parser.error("POSTGRES_PASSWORD is missing from .env. Run scripts/init_env.py first.")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [username]).fetchone():
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEROLE CREATEDB PASSWORD {}").format(sql.Identifier(username), sql.Literal(password)))
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", [dbname]).fetchone():
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(dbname), sql.Identifier(username)))
    print(f"Local PostgreSQL is ready at 127.0.0.1:{port}. Secrets were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
