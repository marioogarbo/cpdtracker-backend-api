FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory in the container
WORKDIR /app 

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml ./

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project code into the container
COPY . .

# Collect static files (important for Django)
RUN python manage.py collectstatic --noinput

# Set the PORT environment variable,
ENV PORT 8080

# Expose port 8080 for Django
EXPOSE 8080

# Run gunicorn as the WSGI server
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 config.wsgi:application