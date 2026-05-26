FROM python:3.12-bookworm
 
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
 
# Set working directory
WORKDIR /app
 
# Copy dependency files first (for Docker layer caching)
COPY pyproject.toml .
 
# Install dependencies
RUN uv sync --no-dev
 
# Copy the rest of the source code
COPY src/ src/
 
# Expose the port
EXPOSE 8000
 
# Run the app with uvicorn via uv
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "main:app"]