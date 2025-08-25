# Vercel serverless function for upload endpoint
import os, sys

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
from core.upload import handler
