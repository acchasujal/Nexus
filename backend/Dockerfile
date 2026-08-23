# CaseClock Backend — Production Docker Image
#
# Build from the repo root:
#   docker build -t caseclock-backend -f backend/Dockerfile .
#
# Run locally (development variables):
#   docker run --rm -p 8000:8000 \
#     -e CASECLOCK_REPOSITORY=local \
#     -e ENVIRONMENT=development \
#     -e CORS_ORIGINS=http://localhost:5173 \
#     caseclock-backend
#
# Health check after start:
#   curl http://localhost:8000/health

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the shared contracts package (required by backend imports)
COPY shared/ ./shared/

# Copy the backend application code
COPY backend/app/ ./app/
COPY backend/app-config.json ./app-config.json

# Copy the synthetic graph artifact (used by in-memory repository)
COPY artifacts/synthetic_graph/synthetic_graph.json ./app/db/synthetic_graph.json

# Runtime environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV CASECLOCK_REPOSITORY=local
ENV ENVIRONMENT=production

EXPOSE 8000

# Start CaseClock backend via AppSail-compatible entry point
CMD ["sh", "-c", "python app/appsail_server.py"]
