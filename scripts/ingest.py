"""PDF i Word dokumenti -> markdown u data/knowledge/, pa ponovna izgradnja indeksa.

Dokumente stavite u data/raw/pdf/ i data/raw/docx/ i pokrenite:

    python -m scripts.ingest
"""

import pymupdf4llm
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from bankbot.config import RAW_DIR
from bankbot.retrieval import build_index
from scripts.common import write_markdown


def pdf_to_markdown(path):
    return pymupdf4llm.to_markdown(str(path), show_progress=False)


def _table_to_markdown(table):
    rows = [[c.text.strip().replace("\n", " ").replace("|", "/") for c in row.cells] for row in table.rows]
    if not rows:
        return ""
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def _heading_level(style_name):
    """'Heading 2' / 'Naslov 2' -> 2, 'Title' -> 1, inače None."""
    name = (style_name or "").lower()
    if name in ("title", "naslov"):
        return 1
    for prefix in ("heading ", "naslov "):
        if name.startswith(prefix) and name[len(prefix):].isdigit():
            return int(name[len(prefix):])
    return None


def docx_to_markdown(path):
    doc = Document(str(path))
    parts = []
    # Idemo po tijelu dokumenta redom da tablice ostanu na svom mjestu između odlomaka.
    for el in doc.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(el, doc)
            text = p.text.strip()
            if not text:
                continue
            level = _heading_level(p.style.name if p.style else "")
            if level:
                parts.append("#" * level + " " + text)
            elif "list" in (p.style.name or "").lower():
                parts.append("- " + text)
            else:
                parts.append(text)
        elif tag == "tbl":
            parts.append(_table_to_markdown(Table(el, doc)))
    # Uzastopne stavke liste idu bez praznog retka između.
    out, prev_list = [], False
    for part in parts:
        is_list = part.startswith("- ")
        if out:
            out.append("\n" if is_list and prev_list else "\n\n")
        out.append(part)
        prev_list = is_list
    return "".join(out)


def _title(md, fallback):
    for line in md.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip().strip("*")
    return fallback


def main():
    written = []
    for path in sorted((RAW_DIR / "pdf").glob("*.pdf")):
        md = pdf_to_markdown(path)
        written.append(write_markdown(path.stem, _title(md, path.stem), path.name, "pdf", md))
    for path in sorted((RAW_DIR / "docx").glob("*.docx")):
        md = docx_to_markdown(path)
        written.append(write_markdown(path.stem, _title(md, path.stem), path.name, "docx", md))
    for p in written:
        print("  zapisano:", p.name)
    chunks = build_index()
    print(f"Indeks: {len(chunks)} chunkova.")


if __name__ == "__main__":
    main()
