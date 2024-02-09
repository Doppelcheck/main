# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copies the local code to the container
COPY . /app

# Install dependencies via pip
RUN pip install --upgrade pip && pip install -r requirements.txt && playwright install

# Copy the config.example.json to config.json
COPY config.example.json config.json

# Expose the port the app runs on
EXPOSE 8000

# Command to run the server
# Replace this CMD with the command to run your app, e.g., python3 main.py
# Note: Using CMD here as you mentioned running once; adjust if you need the app to be restarted automatically.
CMD ["python3", "main.py"]
