# Visanté AI Engine - Docker image for Render
# Use Docker deploy if you need more control than native Python

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY main.py .

# Render sets PORT at runtime
ENV PORT=10000
EXPOSE $PORT

# Run the app
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
