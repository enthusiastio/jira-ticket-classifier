# Use Python 3.12 as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_DEBUG=0

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flask-session

# Create configuration directory
RUN mkdir -p configuration

# Copy the application code
COPY app.py jira_agent.py ./
COPY templates/ ./templates/
COPY configuration/ ./configuration/

# Create flask_session directory with proper permissions
RUN mkdir -p flask_session && chmod 777 flask_session

# Expose port for the Flask app
EXPOSE 5000

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0"]