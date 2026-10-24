FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 1001 app && mkdir -p /app/uploads && chown -R app /app
USER app
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD curl -fs http://127.0.0.1:8001/api/health || exit 1
# one worker: the reminder scheduler runs inside the API process
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips", "*"]
