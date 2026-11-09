"""Create local development secrets once; never overwrite or print them."""

import argparse
import getpass
import json
import secrets
from pathlib import Path
from urllib.parse import quote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-port", type=int, default=5432)
    parser.add_argument("--prompt-demo-password", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.database_port <= 65535:
        parser.error("Database port must be between 1 and 65535.")
    target = Path(__file__).resolve().parent.parent / ".env"
    if target.exists():
        print(".env already exists; it was left unchanged.")
        return
    demo_password = secrets.token_urlsafe(24)
    if args.prompt_demo_password:
        demo_password = getpass.getpass("Choose a demo password (minimum 12 characters): ")
        if len(demo_password) < 12:
            parser.error("Demo password must contain at least 12 characters.")
        if "${" in demo_password:
            parser.error("Choose a password without dotenv variable interpolation syntax ($ followed by an opening brace).")
    database_password = secrets.token_urlsafe(32)
    content = "\n".join([
        "# LOCAL DEVELOPMENT ONLY. Never commit or share this file.",
        f"SECRET_KEY={secrets.token_urlsafe(64)}",
        f"DATABASE_URL=postgresql://warehouse:{quote(database_password, safe='')}@127.0.0.1:{args.database_port}/warehouse",
        "POSTGRES_DB=warehouse",
        "POSTGRES_USER=warehouse",
        f"POSTGRES_PASSWORD={database_password}",
        f"LOCAL_POSTGRES_PORT={args.database_port}",
        "DJANGO_DEBUG=true",
        "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1",
        "DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8010,http://127.0.0.1:8010",
        "APP_PORT=8010",
        "DEMO_MODE=true",
        f"DEMO_PASSWORD={json.dumps(demo_password, ensure_ascii=False)}",
        "",
    ])
    # Exclusive creation also protects against two simultaneous invocations.
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(content)
        target.chmod(0o600)
    except FileExistsError:
        print(".env was created by another process; it was left unchanged.")
        return
    print("Created .env with fresh local secrets. Values were not printed.")
    print("Demo logins use DEMO_PASSWORD from this local file after seed_demo runs.")


if __name__ == "__main__":
    main()
