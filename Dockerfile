# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copies the local code to the container
COPY . /app

# Install the required dependencies
#RUN apt-get update && apt-get install -y libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0  \
#    libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 libdbus-glib-1-2
# Install the required dependencies
RUN apt-get update && apt-get install -y \
    # Playwright dependencies
    libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 \
    libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 libdbus-glib-1-2 \
    # Build dependencies
    build-essential gcc g++ python3-dev

# Install dependencies via pip
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt && playwright install

# Copy the config.example.json to config.json
COPY config.example.json config.json

# Expose the port the app runs on
EXPOSE 8000

# Command to run the server
CMD ["python3", "main.py"]
