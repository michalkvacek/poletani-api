import os

APP_DEBUG = True
GRAPHIQL = True

REFRESH_TOKEN_VALIDITY_DAYS = 30

API_URL = os.environ.get("API_URL") or "http://localhost:8000"
ALLOW_CORS_ORIGINS = os.environ.get("ALLOW_CORS_ORIGINS", "").split()
SENTRY_DSN = os.environ.get("SENTRY_DSN")

APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY") or "test"

if not APP_SECRET_KEY:
    raise ValueError("Missing APP_SECRET_KEY!")
