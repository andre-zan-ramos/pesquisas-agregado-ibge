import os

os.environ.setdefault("DJANGO_SECRET_KEY", "isolated-tests-only-no-deployment")
from .settings import *  # noqa: F403

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
