# Use a lightweight Alpine-based Python image as the base
FROM python:3.11-alpine

WORKDIR /app

# Set environment variables to prevent writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apk update && apk add --no-cache \
    build-base \
    python3-dev \
    pkgconf

# Upgrade pip and install Python packages
RUN pip install --upgrade pip setuptools wheel
RUN pip install redis asyncio python-dotenv

COPY delayed_msgs.py /app

CMD [ "python3", "delayed_msgs.py" ]