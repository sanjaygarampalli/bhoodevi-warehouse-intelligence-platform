"""Explicit synthetic signing configuration; never alter application credentials."""
import os

os.environ.setdefault("SECRET_KEY", "bwip-tests-only-signing-key-never-deploy-2026")
os.environ.setdefault("AUTH_RATE_LIMIT", "10000")
os.environ.setdefault("EXPENSIVE_RATE_LIMIT", "10000")
