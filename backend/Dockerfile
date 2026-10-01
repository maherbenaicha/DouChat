FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/models

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY sample_docs ./sample_docs
COPY eval ./eval
COPY entrypoint.sh .

RUN useradd --create-home appuser \
    && mkdir -p /models && chown -R appuser /models /app \
    && sed -i "s/\r$//" entrypoint.sh && chmod +x entrypoint.sh
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

ENTRYPOINT ["./entrypoint.sh"]
