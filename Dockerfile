# 1. Base Image (Lightweight Python)
FROM python:3.12-slim

# 2. Set working directory
WORKDIR /app

# 3. Install System Dependencies (Needed for Postgres driver)
RUN apt-get update && apt-get install -y libpq-dev gcc

# 4. Copy Requirements and Install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your Code
COPY . .

# 6. Command to run the app
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}