# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /app

# Install system dependencies needed for building/installing certain python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.10-slim AS runner

WORKDIR /app

# Install runtime system dependencies
# libglib2.0-0 is required by opencv-python-headless
# libgl1-mesa-glx might be needed for some cv2 operations (optional for headless but safe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Environment variables to optimize TensorFlow and Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    CUDA_VISIBLE_DEVICES=-1

# Copy models first (better for caching if code changes more often than models)
COPY model/ /app/model/

# Copy API code
COPY api/ /app/api/

# Ensure the uploads directory exists within the API folder
RUN mkdir -p /app/api/uploads

# Set working directory to the api folder for execution
WORKDIR /app/api

# Expose FastAPI port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
