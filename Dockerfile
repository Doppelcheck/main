# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copies the local code to the container
COPY . /app

# Install dependencies via pip
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the config.example.json to config.json and
# Here you would manually add the [storage_secret] to config.json
# Since Dockerfile doesn't support interactive inputs or secret management at build time,
# You should handle secrets using environment variables or Docker secrets in Swarm mode.
# This step is left as a placeholder to remind you to configure your secrets appropriately.
COPY config.example.json config.json

# Expose the port the app runs on
EXPOSE 8000

# Command to run the server
# Replace this CMD with the command to run your app, e.g., python3 main.py
# Note: Using CMD here as you mentioned running once; adjust if you need the app to be restarted automatically.
CMD ["python3", "main.py"]
