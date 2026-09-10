FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

# Dependency layer — cached unless the manifests change. README.md is copied
# because pyproject.toml references it.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000

# --no-sync: the venv is already built above; don't touch it at container start.
CMD ["uv", "run", "--no-sync", "uvicorn", "backend.app.api_main:app", "--host", "0.0.0.0", "--port", "8000"]
