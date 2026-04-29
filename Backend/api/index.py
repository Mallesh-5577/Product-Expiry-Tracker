import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app  # noqa: E402

# Vercel looks for a top-level WSGI app object.
application = app
