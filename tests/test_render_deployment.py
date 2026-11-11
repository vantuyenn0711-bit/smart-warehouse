import json
import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import override_settings

from scripts import render_start


def settings_snapshot(*, render_host="", debug="false"):
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith(("RENDER", "DJANGO_")):
            environment.pop(key)
    environment.update(
        SECRET_KEY="test-only-not-a-production-secret-" * 3,
        DATABASE_URL="postgresql://unused:unused@127.0.0.1:5432/unused",
        DJANGO_DEBUG=debug,
        DJANGO_ALLOWED_HOSTS="localhost, 127.0.0.1",
        DJANGO_CSRF_TRUSTED_ORIGINS="https://custom.example.com",
        RENDER_EXTERNAL_HOSTNAME=render_host,
    )
    code = """import json
from config import settings
print(json.dumps({key: getattr(settings, key, None) for key in (
    'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'SECURE_PROXY_SSL_HEADER',
    'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', 'SECURE_SSL_REDIRECT',
    'SECURE_REDIRECT_EXEMPT')}))
"""
    result = subprocess.run([sys.executable, "-c", code], env=environment, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_render_hostname_and_https_are_trusted_without_wildcard():
    result = settings_snapshot(render_host="warehouse-example.onrender.com")
    assert "warehouse-example.onrender.com" in result["ALLOWED_HOSTS"]
    assert "*" not in result["ALLOWED_HOSTS"]
    assert "https://warehouse-example.onrender.com" in result["CSRF_TRUSTED_ORIGINS"]
    assert "https://custom.example.com" in result["CSRF_TRUSTED_ORIGINS"]
    assert result["SECURE_PROXY_SSL_HEADER"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert result["SESSION_COOKIE_SECURE"] and result["CSRF_COOKIE_SECURE"]
    assert result["SECURE_SSL_REDIRECT"]


def test_local_development_does_not_trust_forwarded_protocol():
    result = settings_snapshot(debug="true")
    assert result["ALLOWED_HOSTS"] == ["localhost", "127.0.0.1"]
    assert result["SECURE_PROXY_SSL_HEADER"] is None
    assert result["SECURE_SSL_REDIRECT"] is None


@override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^health/$"])
def test_readiness_reports_database_failure_instead_of_https_redirect(client):
    with patch("reports.views.connection.cursor", side_effect=OperationalError("test-only-unavailable")):
        response = client.get("/health/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
def test_tls_proxy_does_not_cause_login_redirect_loop(client):
    assert client.get("/login/").status_code == 301
    response = client.get("/login/", HTTP_X_FORWARDED_PROTO="https")
    assert response.status_code == 200


def test_gunicorn_binds_assigned_port_and_uses_small_worker_count():
    command = render_start.gunicorn_command({"PORT": "12345"})
    assert command[command.index("--bind") + 1] == "0.0.0.0:12345"
    assert command[command.index("--workers") + 1] == "1"


@pytest.mark.parametrize("environment", [{"PORT": "0"}, {"PORT": "70000"}, {"WEB_CONCURRENCY": "0"}])
def test_invalid_render_startup_options_fail_before_release_tasks(environment):
    with pytest.raises(ValueError):
        render_start.gunicorn_command(environment)


def test_failed_migration_prevents_gunicorn_start(monkeypatch):
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    with patch.object(render_start.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["migrate"])), patch.object(render_start.os, "execvp") as execute:
        with pytest.raises(subprocess.CalledProcessError):
            render_start.main()
    execute.assert_not_called()


def test_demo_startup_seeds_only_with_if_empty(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    with patch.object(render_start.subprocess, "run") as run, patch.object(render_start.os, "execvp") as execute:
        render_start.main()
    assert run.call_args_list[0].args[0][-2:] == ["migrate", "--noinput"]
    assert run.call_args_list[1].args[0][-2:] == ["seed_demo", "--if-empty"]
    execute.assert_called_once()
