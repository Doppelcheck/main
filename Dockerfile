# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
ENV PYTHONWARNINGS="ignore::UserWarning"
ENV CFLAGS="-Wno-unused-result -Wsign-compare"

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Playwright dependencies
    libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 \
    libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 libdbus-glib-1-2 \
    # Build dependencies
    build-essential gcc g++ python3-dev \
    # Additional dependencies for numpy/scipy
    gfortran libopenblas-dev \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copies the local code to the container
COPY . /app

# Upgrade pip and setuptools first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Cython first (required for some dependencies)
RUN pip install --no-cache-dir Cython

# Install the main requirements
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright
RUN playwright install

# Copy the config.example.json to config.json
COPY config.example.json config.json

# Expose the port the app runs on
EXPOSE 8000

# Command to run the server
CMD ["python3", "main.py"]