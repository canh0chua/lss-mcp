FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget gnupg libgl1 libglib2.0-0 tesseract-ocr \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    "mcp[cli]" \
    crawl4ai \
    docling \
    requests \
    playwright \
    Pillow \
    PyYAML \
    pathspec

RUN playwright install --with-deps chromium

COPY server.py .

CMD ["python", "/app/server.py"]
