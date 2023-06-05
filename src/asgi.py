import sys

sys.path.insert(0, "/app/src")
from .main import App  # noqa

app = App().create_app()
