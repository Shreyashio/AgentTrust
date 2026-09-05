#!/usr/bin/env bash
# Build script for Render (see render.yaml).
# Installs backend deps, builds the React dashboard, prepares the data dir.
set -euo pipefail

echo "==> Installing backend dependencies"
pip install -r requirements.txt

echo "==> Building React dashboard"
if [ -d frontend ]; then
  (cd frontend && npm install && npm run build)
else
  echo "No frontend/ directory found; skipping dashboard build"
fi

echo "==> Preparing SQLite data directory (mounted at runtime via persistent disk)"
mkdir -p /var/data || echo "(note: /var/data unavailable during build — disk mounts at runtime)"

echo "==> Build complete"