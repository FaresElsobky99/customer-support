# ---- build: resolve the dependency venv with uv ----
FROM python:3.11-slim AS build

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
RUN pip install --no-cache-dir uv

# README.md is copied because pyproject.toml references it.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev


# ---- runtime ----
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Run as a non-root user.
RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .

USER app
EXPOSE 8000

CMD ["uvicorn", "backend.app.api_main:app", "--host", "0.0.0.0", "--port", "8000"]
