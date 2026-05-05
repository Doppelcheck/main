# syntax=docker/dockerfile:1

# Use official PyTorch image with both CUDA and ROCm support
FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-runtime

# Install system dependencies and Ollama dependencies
RUN apt-get update && \
    apt-get install -y git ffmpeg libsm6 libxext6 curl ca-certificates gnupg lsb-release sudo \
    libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 libdbus-glib-1-2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app


# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt && \
    python -m spacy download de_core_news_lg && \
    python -m playwright install-deps && \
    python -m playwright install && \
    python -c "import stanza; stanza.download('multilingual')"

# Copy the rest of the code
COPY . .

# Expose port (default from config)
EXPOSE 5000

# Set environment variables for GPU support (NVIDIA/ROCm)
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV HSA_VISIBLE_DEVICES=all

# Default command
CMD ["python", "main.py"]
