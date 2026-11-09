FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.13.6 \
    && addgroup --system warehouse \
    && adduser --system --ingroup warehouse warehouse

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=warehouse:warehouse . .
RUN SECRET_KEY=build-only-public-placeholder-not-a-runtime-secret \
    DATABASE_URL=postgresql://unused:unused@127.0.0.1:5432/unused \
    DJANGO_DEBUG=true \
    python manage.py collectstatic --noinput

USER warehouse
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=4)" || exit 1
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
