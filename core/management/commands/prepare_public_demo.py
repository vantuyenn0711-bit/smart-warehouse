"""Prepare synthetic data in an owned schema, never copy the operational data."""
import os
import secrets

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.test.utils import override_settings

from core.demo import DATASET_VERSION, demo_bootstrap


class Command(BaseCommand):
    help = "Chuẩn bị dữ liệu giả lập tách riêng cho chế độ xem demo công khai."

    def handle(self, *args, **options):
        if not settings.PUBLIC_DEMO_ENABLED:
            self.stdout.write("Public demo is disabled; no data was changed.")
            return
        database = connections["demo"]
        if database.in_atomic_block:
            raise CommandError("Run prepare_public_demo outside an existing transaction.")
        schema = settings.PUBLIC_DEMO_SCHEMA
        quoted = database.ops.quote_name(schema)
        marker = f"{quoted}._public_demo_dataset"
        locked = False
        previous_password = os.environ.get("DEMO_PASSWORD")
        try:
            with database.cursor() as cursor:
                cursor.execute("SET default_transaction_read_only = off")
                cursor.execute("SELECT pg_advisory_lock(%s)", [913237026])
                locked = True
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s", [schema])
                tables = {row[0] for row in cursor.fetchall()}
                if tables and "_public_demo_dataset" not in tables:
                    raise CommandError("Demo schema contains unverified tables; refusing to expose or modify them.")
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted}")
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {marker} (id SMALLINT PRIMARY KEY CHECK (id = 1), version VARCHAR(80) NOT NULL, ready BOOLEAN NOT NULL DEFAULT FALSE)")
                cursor.execute(f"SELECT version FROM {marker} WHERE id = 1")
                existing = cursor.fetchone()
                if existing and existing[0] != DATASET_VERSION:
                    raise CommandError("Unrecognized demo dataset; no data was replaced.")
                if not existing:
                    if tables:
                        raise CommandError("Demo dataset ownership is not established; refusing to continue.")
                    cursor.execute(f"INSERT INTO {marker} (id, version, ready) VALUES (1, %s, FALSE)", [DATASET_VERSION])
            call_command("migrate", database="demo", interactive=False, verbosity=0)
            # Fake document actors receive random unusable-in-practice credentials.
            # These identities are never used to authenticate the public session.
            os.environ["DEMO_PASSWORD"] = secrets.token_urlsafe(40)
            with demo_bootstrap(), override_settings(DEMO_MODE=True), transaction.atomic(using="demo"):
                call_command("seed_demo", if_empty=True, verbosity=0)
                with database.cursor() as cursor:
                    cursor.execute(f"UPDATE {marker} SET ready = TRUE WHERE id = 1")
        finally:
            if previous_password is None:
                os.environ.pop("DEMO_PASSWORD", None)
            else:
                os.environ["DEMO_PASSWORD"] = previous_password
            with database.cursor() as cursor:
                if locked:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", [913237026])
                cursor.execute("SET default_transaction_read_only = on")
        self.stdout.write("Public demo dataset is ready. Operational data was not copied or changed.")
