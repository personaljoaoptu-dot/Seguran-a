FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g., build-essential, libffi-dev for bcrypt build if no prebuilt wheels)
# But slim should have pip wheels for win/linux.
RUN pip install --no-cache-dir pg8000 bcrypt

# Copy dashboard application files
COPY . .

# Expose server port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Start the web server
CMD ["python", "server.py"]
