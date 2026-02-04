# Base Python image
FROM python:3.11-slim

# Disable .pyc files + enable stdout logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directory
WORKDIR /app

# Copy requirements
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entrypoint
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Copy rest of project
COPY . /app/

# Entrypoint ensures DB + Redis ready
ENTRYPOINT ["/app/entrypoint.sh"]

# Default Django command (overwritten by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
