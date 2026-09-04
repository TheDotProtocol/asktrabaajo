#!/bin/zsh
# Wave 6 local API — isolated sqlite. Does not use backend/.env DATABASE_URL.
set -e
cd "$(dirname "$0")/../backend"
export ENVIRONMENT=development
export DATABASE_URL="sqlite:///$(pwd)/asktrabaajo_wave6.db"
export SECRET_KEY="wave6-local-dev-only-not-for-hosted"
export AI_PROVIDER=none
export PAYMENT_PROVIDER=mock
export CORS_ORIGINS="http://localhost:3000,http://localhost:3001"
exec .venv/bin/python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
