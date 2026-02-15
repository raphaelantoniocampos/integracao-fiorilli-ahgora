# Use python 3.13-slim as base
FROM python:3.13-slim

# Install system dependencies for Selenium / Firefox
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Geckodriver
RUN GECKO_VERSION=$(wget -qO- https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/') \
    && wget https://github.com/mozilla/geckodriver/releases/download/$GECKO_VERSION/geckodriver-$GECKO_VERSION-linux64.tar.gz \
    && tar -xzf geckodriver-$GECKO_VERSION-linux64.tar.gz -C /usr/local/bin \
    && rm geckodriver-$GECKO_VERSION-linux64.tar.gz

# Set working directory
WORKDIR /app

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (only production)
RUN uv sync --frozen --no-dev

# Copy the rest of the application
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
