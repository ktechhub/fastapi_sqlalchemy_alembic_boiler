FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /app/

# Install system dependencies and Python dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    build-essential \
    python3-dev \
    wget \
    curl

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . /app

CMD ["python3", "-m", "app.services.redis_main"]
