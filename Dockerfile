FROM python:3.11-slim

# Optional: Corporate proxy / MITM CA certificates
# Place .crt files in the certs/ directory to have them trusted at build time.
COPY certs/ /usr/local/share/ca-certificates/custom/
RUN update-ca-certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

RUN apt-get update && apt-get install -y \
    wget gnupg libgl1 libglib2.0-0 tesseract-ocr \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    "mcp[cli]" \
    requests \
    httpx \
    Pillow \
    PyYAML \
    pathspec \
    "pymupdf>=1.24" \
    python-docx \
    python-pptx \
    openpyxl \
    beautifulsoup4 \
    lxml \
    html2text \
    markdownify \
    pytesseract \
    tabulate

COPY server.py .

ENTRYPOINT ["python", "/app/server.py"]