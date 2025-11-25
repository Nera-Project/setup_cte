# core/env_loader.py
import os
from dotenv import load_dotenv

_ENV_LOADED = False

def load_env(path: str = ".env"):
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(path)
        _ENV_LOADED = True

def get_env(key: str, default=None):
    return os.getenv(key, default)
