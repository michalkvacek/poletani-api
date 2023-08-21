import os

APP_DEBUG = True
GRAPHIQL = True
API_URL = os.environ.get("API_URL") or "http://localhost:8000"
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY") or "test"
ALLOW_CORS_ORIGINS = os.environ.get("ALLOW_CORS_ORIGINS", "").split()

if not APP_SECRET_KEY:
    raise ValueError("Missing APP_SECRET_KEY!")
