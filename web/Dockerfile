FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the Flask app code
COPY . /app/

# Flask listens on 5000 by default
EXPOSE 5000

# Default environment
ENV FLASK_DEBUG=0 \
    PYTHONUNBUFFERED=1

# Run the app
CMD ["python", "app.py"]