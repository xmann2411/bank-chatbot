"""Putanje i postavke. Sve što se mijenja kroz .env čita se ovdje."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
INDEX_FILE = DATA_DIR / "index.json"
RATES_FILE = DATA_DIR / "rates.json"
SOURCES_FILE = DATA_DIR / "sources.json"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = ROOT / "logs"
AUDIT_FILE = LOG_DIR / "audit.jsonl"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = os.getenv("ANTHROPIC_MODEL", "").strip() or "claude-opus-5-5"

# Koliko chunkova dohvaćamo za odgovor.
TOP_K = 3
# Ispod ovog BM25 scorea smatramo da dokumentacija nema odgovor.
MIN_SCORE = 1.5
# Chunk mora pokriti barem ovoliki dio pitanja (težinski po rijetkosti riječi).
MIN_COVERAGE = 0.5
# Između WEAK_COVERAGE i MIN_COVERAGE bot ne odgovara nego pita "Jeste li mislili na...?".
WEAK_COVERAGE = 0.3

HNB_API = "https://api.hnb.hr/tecajn-eur/v3"

# Web sesije: s REDIS_URL se spremaju u Redis, bez njega u memoriju servera.
REDIS_URL = os.getenv("REDIS_URL", "").strip()
SESSION_TTL = 30 * 60  # sekundi neaktivnosti; chat prozor u pregledniku ima isti rok (IDLE_MS)
