# Use a lightweight official Python image
# This reduces image size and improves deployment speed
FROM python:3.12-slim

# Set the working directory inside the container
# All subsequent commands will run relative to this folder
WORKDIR /app

# Copy the requirements file first
# This allows Docker to cache dependency installation
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size by not storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy your backend application code into the container
# Only backend is needed since frontend is hosted on S3
COPY backend/ backend/

# Start the application using Gunicorn (production-ready server)
# -w 2 -> number of worker processes
# -b 0.0.0.0:80 -> bind to all interfaces on port 80
# backend.app:app -> points to Flask app object
# This ensures the container listens on port 80, which is required for ECS + Load Balancer
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "backend.app:app"]