FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system ravenstore \
    && useradd --system --gid ravenstore --create-home ravenstore

WORKDIR /app
COPY pyproject.toml README.md ./
COPY raven_bot ./raven_bot
RUN pip install . && chown -R ravenstore:ravenstore /app

USER ravenstore
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl --fail http://127.0.0.1:8080/health/live || exit 1
CMD ["python", "-m", "raven_bot.main"]
