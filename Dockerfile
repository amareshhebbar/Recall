# # --- Stage 1: The Builder (Python-based for easy pip/playwright setup) ---
# FROM python:3.11-slim as builder
# FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# WORKDIR /app

# # Install build dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     wget gnupg ca-certificates && \
#     rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Install Chromium and its OS dependencies
# RUN playwright install chromium
# RUN playwright install-deps chromium

# # --- Stage 2: The Final Ubuntu Environment ---
# FROM ubuntu:22.04

# # Avoid prompts during installation
# ENV DEBIAN_FRONTEND=noninteractive \
#     PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
#     PYTHONUNBUFFERED=1

# WORKDIR /app

# # 1. Install Python and the necessary system libs for Chromium to run on Ubuntu
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     python3.11 \
#     python3-pip \
#     libnss3 libnspr4 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
#     libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 \
#     libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
#     libgbm1 libpango-1.0-0 libcairo2 \
#     && rm -rf /var/lib/apt/lists/*

# # COPY --from=builder /usr/local/lib/ /usr/local/lib/
# # COPY --from=builder /usr/local/bin/ /usr/local/bin/
# # COPY --from=builder /ms-playwright /ms-playwright

# # 3. Environment setup
# ENV LD_LIBRARY_PATH=/usr/local/lib
# # We use 'ln -sf' to FORCE the link if it exists, ensuring /usr/bin/python3.11 points to our version
# RUN ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
# # 3. Copy your app code
# COPY . .

# # Ensure we use python3.11 explicitly
# CMD ["python3.11", "main.py"]



# This image IS Ubuntu 22.04 + Python 3.11 + Playwright pre-installed
# FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# # 1. Environment variables
# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# WORKDIR /app

# # 2. Install dependencies (Cached Layer)
# # If your file is named 'r.txt' instead of 'requirements.txt', change this line!
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # 3. Copy your code
# # (When using docker-compose with volumes, this is just for the build)
# COPY . .

# # 4. Run the script
# # Note: Use 'python3' as it's the standard command in this image
# CMD ["python3", "index.py"]

FROM python:3.11-slim

# 1. Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libgbm1 \
    libnss3 \
    libasound2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt ./

# 2. Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install Playwright browsers and their OS dependencies
# This command automatically detects and installs exactly what's missing
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "index.py"]
