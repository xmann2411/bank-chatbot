"""Ispravljanje tipfelera (simulirani mod).

Svaku riječ poruke uspoređujemo s rječnikom: riječima iz baze znanja i
ključnim riječima bota (vrste kredita, valute, rokovi...). Riječ koje nema u
rječniku zamijenimo najsličnijom:

  - vrlo slična (npr. "kartcu" -> "karticu")   ispravimo bez pitanja
  - donekle slična                              ne ispravljamo sami, ali agent
                                                može pitati "Jeste li mislili...?"

S pravim modelom ovo nije potrebno jer model sam razumije tipfelere.
"""

import json
import re
from collections import Counter
from difflib import SequenceMatcher, get_close_matches
from functools import lru_cache

from . import nlu, retrieval
from .config import INDEX_FILE

MIN_LEN = 4  # kraće riječi (je, li, ak...) ne diramo
SURE = 0.86  # sličnost iznad koje ispravljamo bez pitanja
UNSURE = 0.78  # između UNSURE i SURE pitamo klijenta

# Riječi koje bot mora prepoznati, a možda ih nema u dokumentima u tom obliku.
EXTRA_WORDS = """
kredit kredita kreditu kredite gotovinski gotovinskog gotovinskom stambeni stambenog stambenom nenamjenski
rata ratu rate mjesečna mjesečnu mjesečno izračun izračunaj izračunati izračunajte kalkulator
godina godine godinu mjeseci mjeseca mjesec državljanin državljanka državljanstvo nedržavljanin stranac
tečaj tečajna tečajnu tečajnica preračun preračunaj preračunati valuta valute euro eura eure eurima
dolar dolara dolare dolarima franak franka franke funta funte funti kamata kamatu kamate kamatna
otplata otplate otplatu otplatni ukupno ukupan ukupna ukupnu iznos iznosa plan
mirovina mirovini umirovljenik penzioner kartica karticu kartice blokirati blokada poslovnica poslovnicu
poslovnice radno vrijeme štednja štednju štednje račun računa računu bankomat bankomata naknada naknade
hvala molim pozdrav dobar jutro večer
loan loans cash housing mortgage payment monthly rate rates interest exchange currency dollar dollars
euro euros pound pounds citizen croatian years months total schedule card block branch opening hours
account savings fee fees documents hello thanks thank please calculate
"""


def _collapse_repeats(word):
    """'mjeseciiiiii' -> 'mjeseci' (3 ili više istih slova zaredom)."""
    return re.sub(r"(.)\1{2,}", r"\1", word)


@lru_cache(maxsize=1)
def lexicon():
    """normalizirana riječ -> najčešći izvorni oblik (s dijakriticima)."""
    forms = Counter()
    texts = [EXTRA_WORDS]
    if INDEX_FILE.exists():
        for c in json.loads(INDEX_FILE.read_text(encoding="utf-8")):
            texts.append(c["section"] + " " + c["text"])
    for text in texts:
        for w in re.findall(r"[A-Za-zČĆŽŠĐčćžšđ]+", text):
            forms[w.lower()] += 1
    words = set(retrieval.STOPWORDS) | nlu.HR_WORDS | nlu.EN_WORDS | set(retrieval.EN_HR) | set(retrieval.HR_SYNONYMS)
    words |= {w for ws in nlu.CURRENCY_WORDS.values() for w in ws}
    lex = {w: w for w in words}
    for form, _ in forms.most_common():
        lex.setdefault(retrieval.normalize(form), form)
    return lex


@lru_cache(maxsize=1)
def _targets():
    """Riječi u koje smijemo ispraviti: bez stop-riječi i kratkih riječi."""
    return [w for w in lexicon() if len(w) >= MIN_LEN and w not in retrieval.STOPWORDS]


@lru_cache(maxsize=1)
def _known_stems():
    return {retrieval.stem(w) for w in lexicon()}


def _is_transposition(a, b):
    """Dva susjedna slova zamijenjena: 'tecja' / 'tecaj', 'kerdit' / 'kredit'."""
    if len(a) != len(b):
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def _best_match(norm):
    candidates = get_close_matches(norm, _targets(), n=5, cutoff=UNSURE - 0.06)
    if not candidates:
        return None, 0.0
    for c in candidates:
        if _is_transposition(norm, c):
            return c, 1.0
    best = max(candidates, key=lambda c: SequenceMatcher(None, norm, c).ratio())
    ratio = SequenceMatcher(None, norm, best).ratio()
    return (best, ratio) if ratio >= UNSURE else (None, 0.0)


def correct(text):
    """Vraća (sigurno_ispravljeno, s_nesigurnim_ispravcima ili None, popis izmjena)."""
    lex = lexicon()
    sure_changes, unsure_changes = [], []

    def fix(word, include_unsure):
        norm = retrieval.normalize(_collapse_repeats(word))
        if norm in lex:
            return word if norm == retrieval.normalize(word) else lex[norm]
        # Drugi padež poznate riječi (Splitu, kreditan...) nije tipfeler.
        if len(norm) < MIN_LEN or retrieval.stem(norm) in _known_stems():
            return word if norm == retrieval.normalize(word) else norm
        best, ratio = _best_match(norm)
        if best is None:
            return word
        if ratio >= SURE:
            if include_unsure is False:
                sure_changes.append((word, lex[best]))
            return lex[best]
        if include_unsure:
            unsure_changes.append((word, lex[best]))
            return lex[best]
        return word

    pattern = r"[A-Za-zČĆŽŠĐčćžšđ]+"
    sure = re.sub(pattern, lambda m: fix(m.group(0), False), text)
    with_unsure = re.sub(pattern, lambda m: fix(m.group(0), True), text)
    return sure, (with_unsure if unsure_changes else None), sure_changes + unsure_changes
