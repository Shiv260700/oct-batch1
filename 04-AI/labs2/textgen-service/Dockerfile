# Text-generation API (lab 5's small GPT). Build from the labs2 folder:
#   docker build -f textgen-service/Dockerfile -t textgen-api:v1 .
FROM python:3.12-slim

WORKDIR /app

# 1. Libraries (change rarely → cached layer; keep everything that changes more often below)
COPY textgen-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Settings: override any of them at run time (docker run -e …, or env: in Kubernetes)
# TORCH_THREADS=1 is fastest for this small model (measured: 1.9 s vs 3.9 s with 4 threads for 200 characters)
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MODEL_DIR=/app/model MODEL_VERSION=v1 TORCH_THREADS=1 MAX_CHARS_LIMIT=500

# 2. Model files (7 MB) and the shared model code, then the API (changes most often → last)
COPY models/textgen/weights.pt models/textgen/config.json ./model/
COPY textgen/ ./textgen/
COPY textgen-service/app.py .

# 3. Run as a non-root user
RUN useradd --uid 10001 --no-create-home appuser
USER 10001

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
