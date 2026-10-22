# -*- coding: utf-8 -*-
"""Load Exa API keys from the environment for the one-off research scripts.

Keys never live in the source tree: set EXA_API_KEYS to one or more keys
separated by whitespace or commas, either in the shell or in the repo .env.
"""
import os
import re
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def load_keys():
    raw = os.environ.get("EXA_API_KEYS", "")
    keys = [part for part in re.split(r"[\s,]+", raw) if part]
    if not keys:
        raise SystemExit(
            "EXA_API_KEYS is empty. Set one or more Exa keys (whitespace or comma "
            "separated) in the environment or in .env."
        )
    return keys
