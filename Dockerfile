# Dockerfile for SOXauto PG-01 Application
# Multi-stage build for optimized production image

# Stage 1: Build stage with all dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver for SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage with minimal footprint
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    unixodbc \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver for SQL Server (runtime only)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Create application directory
WORKDIR /app

# Copy application code with new structure
COPY --chown=appuser:appuser src/ /app/src/

# Set ownership and permissions
RUN chown -R appuser:appuser /app \
    && chmod +x /app

# Switch to non-root user
USER appuser

# Expose port for Cloud Run
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set environment variables for AWS
ENV PORT=8080
ENV AWS_REGION=${AWS_REGION}

# Command to run the application
# Use gunicorn for production WSGI server with module syntax
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 --worker-class gthread src.core.main:app