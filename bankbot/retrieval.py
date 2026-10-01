"""RAG pretraga: markdown -> chunkovi -> BM25 -> top 3.

BM25 je pretraga po ključnim riječima i radi bez ikakvog API ključa.
Hrvatski ima puno padeža (kredit, kredita, kreditu...) pa riječima skidamo
česte nastavke i skraćujemo ih na prvih 6 slova. To je grubo, ali za ovu
veličinu baze radi dobro.
"""

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from .config import INDEX_FILE, KNOWLEDGE_DIR, MIN_COVERAGE, MIN_SCORE, TOP_K, WEAK_COVERAGE

STEM_LEN = 6
SUFFIXES = ("ovima", "evima", "ama", "ima", "ega", "emu", "oga", "omu", "iju", "om", "em", "og", "oj", "ih", "im",
            "u", "a", "e", "i", "o")
CHUNK_CHARS = 900

STOPWORDS = set(
    """
    a ako ali bi bih bio bila bili bilo biti da do dok ga i ih ili im iz ja je jer
    joj ju kad kada kako koja koje koji kojih kojim koju kod li me mi mo moj moze
    mozes mogu na nad nas ne nego neki nema ni niti no o od on ona one oni ono pa
    po pod pri s sa se si sto su sve svi ta taj te ti to tu u uz va vam vas vi za
    zbog biste bismo jesam jest sam smo ste koliko koja gdje sta sto kao kolika koliki
    treba trebam trebati trebaju nalazi nalaze moram imate imam ima zanima htio htjela
    zelim zelio zeljela recite reci molim mozete postoji nekako jel jeli dobit dobiti dobijem
    uzeti uzet dignut dignuti dici ak al kak kaj kolko kolk nes nest ono dal dali
    
    the an and are be can do does for from have how i in is it me my of on or
    that this to what when where which who will with you your
    """.split()
)

# Hrvatski sinonimi za riječi kojih u dokumentima nema u tom obliku.
HR_SYNONYMS = {
    "stranac": "nisu drzavljani", "strankinja": "nisu drzavljani", "stranci": "nisu drzavljani",
    "strance": "nisu drzavljani", "stranca": "nisu drzavljani", "strancima": "nisu drzavljani", "puli": "pula",
    "strani": "nisu drzavljani", "nedrzavljanin": "nisu drzavljani", "nedrzavljani": "nisu drzavljani",
    "blokada": "blokirati", "blokiram": "blokirati", "izgubio": "izgubljenu", "izgubila": "izgubljenu",
    "ukraden": "ukradenu", "ukradena": "ukradenu", "otvoreno": "radno vrijeme", "rade": "radno vrijeme",
    "stan": "stambeni", "stana": "stambeni", "kuca": "stambeni", "kucu": "stambeni",
    "papiri": "dokumentacija", "papire": "dokumentacija", "ranije": "prijevremeno",
    "kosta": "naknada", "kostaju": "naknada", "cijena": "naknada", "cijene": "naknada",
    "umirovljenik": "mirovina", "umirovljenica": "mirovina", "umirovljenici": "mirovina",
    "penzioner": "mirovina", "penzionerka": "mirovina", "penzija": "mirovina", "penziji": "mirovina", "penzije": "mirovina",
    "obavezno": "obvezno", "obavezan": "obvezan", "obavezna": "obvezna", "rijeci": "rijeka",
    "slanje": "uplata placanje", "poslati": "uplata placanje", "novca": "",
    "podignuti": "podizanje gotovine bankomat", "podici": "podizanje gotovine bankomat",
    "novac": "gotovine", "kes": "gotovine",
}


def expand_synonyms(text):
    text = normalize(text)
    # Rokovi su u dokumentima često u mjesecima: "3 godine" -> "3 godine 36 mjeseci".
    text = re.sub(r"\b(\d{1,2})\s*(god\w*|year\w*)", lambda m: f"{m.group(0)} {int(m.group(1)) * 12} mjeseci", text)
    return " ".join(HR_SYNONYMS.get(w, w) for w in re.findall(r"[a-z0-9]+", text))


# Pitanja na engleskom tražimo po hrvatskim dokumentima, pa prevodimo ključne pojmove.
# U pravom modu to radi LLM (vidi agent.py), ovo je rezerva za simulirani mod.
EN_HR = {
    "loan": "kredit", "loans": "kredit", "mortgage": "stambeni kredit", "housing": "stambeni",
    "cash": "gotovinski", "interest": "kamatna stopa", "rate": "stopa", "fee": "naknada",
    "fees": "naknada", "account": "racun", "accounts": "racun", "card": "kartica",
    "cards": "kartica", "branch": "poslovnica", "branches": "poslovnica", "hours": "radno vrijeme",
    "open": "radno vrijeme", "opening": "radno vrijeme", "contact": "kontakt", "phone": "telefon",
    "email": "e-mail", "address": "adresa", "savings": "stednja", "deposit": "stednja",
    "documents": "dokumentacija", "documentation": "dokumentacija", "insurance": "osiguranje",
    "early": "prijevremena", "repayment": "otplata", "block": "blokirati blokada", "lost": "izgubljena",
    "stolen": "ukradena", "mobile": "mobilno bankarstvo", "app": "aplikacija", "internet": "internet",
    "transfer": "prijenos", "payment": "placanje", "atm": "bankomat", "salary": "placa",
    "foreigner": "nedrzavljanin", "foreigners": "nedrzavljanin", "citizen": "drzavljanin",
    "age": "dob", "guarantor": "jamac", "collateral": "osiguranje", "processing": "obrada",
    "requirements": "uvjeti", "conditions": "uvjeti", "about": "o banci", "bank": "banka",
    "overdraft": "prekoracenje", "limit": "limit", "maximum": "najvise", "minimum": "najmanje",
    "term": "rok", "period": "rok", "grace": "pocek",
}


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.replace("đ", "d")


def stem(word):
    for suf in SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            word = word[: -len(suf)]
            break
    # Nepostojano a: centar/centra, Zadar/Zadru, stranac/stranca -> centr, zadr, stranc
    if len(word) >= 5 and re.search(r"[^aeiou]a[rcklmn]$", word):
        word = word[:-2] + word[-1]
    return word[:STEM_LEN]


def tokenize(text):
    words = re.findall(r"[a-z0-9]+", normalize(text))
    return [stem(w) for w in words if w not in STOPWORDS and (len(w) > 1 or w.isdigit())]


def translate_query(text):
    """Englesko pitanje -> hrvatski pojmovi za pretragu (simulirani mod).

    Engleske riječi ne bi pronašle ništa u hrvatskim dokumentima, a spuštale bi
    pokrivenost upita, pa pretražujemo samo prevedenim pojmovima.
    """
    extra = [EN_HR[w] for w in re.findall(r"[a-z]+", text.lower()) if w in EN_HR]
    return " ".join(extra) if extra else text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _parse_front_matter(md):
    meta = {}
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            for line in md[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            md = md[end + 4 :]
    return meta, md


def _split_long(text):
    """Dugačku sekciju reže po odlomcima na komade od ~CHUNK_CHARS, s jednim odlomkom preklapanja."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], []
    for p in paras:
        if current and sum(len(x) for x in current) + len(p) > CHUNK_CHARS:
            chunks.append("\n\n".join(current))
            current = [current[-1]]
        current.append(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_markdown(md, source_name):
    meta, body = _parse_front_matter(md)
    source = meta.get("izvor", source_name)
    title = meta.get("naslov", source_name)

    chunks = []
    heading_path = [title]
    buf = []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            for piece in _split_long(text):
                chunks.append({"source": source, "file": source_name, "section": " > ".join(heading_path), "text": piece})
        buf.clear()

    for line in body.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            flush()
            level = len(m.group(1))
            heading_path = heading_path[: level - 1] + [m.group(2).strip()]
        else:
            buf.append(line)
    flush()
    return chunks


# ---------------------------------------------------------------------------
# Indeks
# ---------------------------------------------------------------------------


def build_index():
    chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), path.name))
    for i, c in enumerate(chunks):
        c["id"] = i
    INDEX_FILE.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    return chunks


@dataclass
class Hit:
    score: float
    chunk: dict
    coverage: float = 1.0  # koliki dio (idf-težinski) pitanja chunk pokriva
    matched: int = 0  # koliko različitih pojmova iz pitanja se pojavljuje u chunku


class BM25Index:
    def __init__(self, chunks, k1=1.5, b=0.5):
        self.chunks = chunks
        self.k1, self.b = k1, b
        # Naslov sekcije je jak signal: cijela putanja ide u indeks, a zadnji naslov dvaput.
        self.docs = [tokenize(f"{c['section']} {c['section'].split(' > ')[-1]} {c['text']}") for c in chunks]
        self.tf = [Counter(d) for d in self.docs]
        self.avgdl = sum(len(d) for d in self.docs) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query, k=TOP_K):
        terms = set(tokenize(query))
        # Riječ koje nema nigdje u bazi dobiva najveći idf: ako je bitan dio pitanja
        # ("koliko je vrijeme u Tokiju"), pokrivenost pada i ne vraćamo krivi odgovor.
        max_idf = math.log(1 + (len(self.docs) + 0.5) / 0.5)
        total_idf = sum(self.idf.get(t, max_idf) for t in terms) or 1.0
        scored = []
        for i, tf in enumerate(self.tf):
            dl = len(self.docs[i])
            s, matched, n_matched = 0.0, 0.0, 0
            for t in terms:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
                    matched += self.idf[t]
                    n_matched += 1
            if s > 0:
                scored.append(Hit(s, self.chunks[i], matched / total_idf, n_matched))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]


_index = None


def get_index():
    global _index
    if _index is None:
        if not INDEX_FILE.exists():
            build_index()
        _index = BM25Index(json.loads(INDEX_FILE.read_text(encoding="utf-8")))
    return _index


def search(query, k=TOP_K):
    """Top-k chunkova. Prazna lista ako ništa nije dovoljno relevantno."""
    hits = get_index().search(expand_synonyms(query), k)
    return [h for h in hits if h.score >= MIN_SCORE and h.coverage >= MIN_COVERAGE]


def search_weak(query, k=3):
    """Djelomični pogoci kad search() ne nađe ništa dovoljno dobro: za pitanje "Jeste li mislili na...?".

    Traži da chunk pogodi barem dva pojma iz pitanja, da jedna slučajna riječ
    ("koliko je sati u Tokiju" -> "8 do 20 sati") ne izazove besmisleno pitanje.
    """
    hits = get_index().search(expand_synonyms(query), k * 3)
    return [h for h in hits if h.score >= MIN_SCORE and h.coverage >= WEAK_COVERAGE and h.matched >= 2][:k]

