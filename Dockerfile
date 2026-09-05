# AgentTrust — single-container image.
# Stage 1: build the React dashboard with Node.
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
# VITE_CLERK_PUBLISHABLE_KEY is required by the frontend at build time.
# Pass it as a Docker build arg (Render: build-time env var). It is public data.
ARG VITE_CLERK_PUBLISHABLE_KEY=""
ARG VITE_API_URL=""
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY \
    VITE_API_URL=$VITE_API_URL
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime serving API + storefront + built dashboard.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY main.py config.py database.py models.py schemas.py governance.py \
     agent_service.py razorpay_service.py auth.py seed.py seed_merchant.py \
     policies.json requirements.txt ./
COPY routers/ ./routers/
COPY storefront/ ./storefront/

EXPOSE 8000
CMD ["sh", "-c", "mkdir -p /var/data && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]