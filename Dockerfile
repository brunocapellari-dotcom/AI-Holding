FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# The upstream slim image can lag Debian security point releases even when the
# tag itself is freshly pulled. Apply only published package upgrades during
# the immutable image build, then remove package indexes from the runtime.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home appuser

COPY pyproject.toml README.md ./
COPY app ./app
COPY apps ./apps
COPY services ./services
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN pip install --no-cache-dir .

USER appuser
EXPOSE 8080
CMD ["sh", "-c", "uvicorn apps.control_plane.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
