FROM python:3.11-slim

WORKDIR /app

# Copy requirements files
COPY pyproject.toml uv.lock ./

# Install uv
RUN pip install --no-cache-dir uv

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["uv", "run", "main.py"]
