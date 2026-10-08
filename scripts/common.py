"""Zajedničko za ingest i scrape: zapis markdowna s zaglavljem i ponovna izgradnja indeksa."""

import re
from datetime import date

from bankbot.config import KNOWLEDGE_DIR


def slugify(text):
    text = text.lower()
    for a, b in (("č", "c"), ("ć", "c"), ("ž", "z"), ("š", "s"), ("đ", "d")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:80] or "dokument"


def write_markdown(name, title, source, kind, body):
    """Sprema data/knowledge/<name>.md s YAML zaglavljem koje chunker čita."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    header = f"---\nnaslov: {title}\nizvor: {source}\ntip: {kind}\nobradeno: {date.today().isoformat()}\n---\n\n"
    path = KNOWLEDGE_DIR / f"{slugify(name)}.md"
    # newline="\n": isti kraj redaka na Windowsima i Linuxu, pa git ne javlja lažne izmjene
    path.write_text(header + body + "\n", encoding="utf-8", newline="\n")
    return path
