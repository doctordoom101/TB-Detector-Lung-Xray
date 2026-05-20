# ==========================================
# Stage 1: Build & Install Dependencies
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /app

# Install tools yang dibutuhkan untuk kompilasi beberapa library wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install ke folder lokal .local
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Final Runtime Environment (Lightweight)
# ==========================================
FROM python:3.10-slim AS runner

WORKDIR /app

# Salin library yang sudah di-install dari stage builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Salin folder model dan kode API ke dalam container
COPY model/ /app/model/
COPY api/ /app/api/

# Buat folder uploads untuk menampung gambar rontgen pasien
RUN mkdir -p /app/api/uploads

# Set environment variable agar Python tidak menulis file .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Ekspos port 8000 (port default FastAPI)
EXPOSE 8000

# Jalankan server Uvicorn mengarah ke folder api/main.py
WORKDIR /app/api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]