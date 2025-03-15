# First stage: build the application with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads to use the system interpreter across both images
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /bot
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
ADD . /bot
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Second stage: final image without uv
FROM python:3.12-slim-bookworm
# Using the same Python version as the builder

# Create a non-root user
RUN useradd -m bot

# Copy the application from the builder
COPY --from=builder --chown=bot:bot /bot /bot

# Set working directory
WORKDIR /bot

# Place executables in the environment at the front of the path
ENV PATH="/bot/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER bot

# Run the bot
CMD ["python", "main.py"]
