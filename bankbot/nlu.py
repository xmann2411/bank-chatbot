"""Prepoznavanje iz teksta pomoću pravila: jezik, namjera, parametri kredita, valute.

Ovo koristi simulirani mod (bez API ključa). U pravom modu isti posao radi LLM,
a ove funkcije ostaju kao rezerva ako model ne odgovori.
"""

import re

from .retrieval import normalize

# ---------------------------------------------------------------------------
# Jezik
# ---------------------------------------------------------------------------

HR_WORDS = set(
    "je li koliko kako gdje sto sta mogu zelim trebam kredit kredita rata ratu mjesecna "
    "godina godine mjeseci banka banke tecaj tecajna da ne hvala molim bok pozdrav "
    "imate koje koji kada radno vrijeme racun kartica stambeni gotovinski drzavljanin "
    "nisam jesam sam iznos rok".split()
)
EN_WORDS = set(
    "what how where when is are can could would i want need loan rate monthly payment "
    "years months bank exchange yes no thanks thank please hello hi do you have which "
    "open hours account card housing mortgage cash citizen not am amount term the".split()
)


def detect_language(text, default="hr"):
    if re.search(r"[čćžšđČĆŽŠĐ]", text):
        return "hr"
    words = re.findall(r"[a-z]+", normalize(text))
    hr = sum(w in HR_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    if en > hr:
        return "en"
    if hr > en:
        return "hr"
    return default


# ---------------------------------------------------------------------------
# Valute
# ---------------------------------------------------------------------------

CURRENCY_WORDS = {
    "EUR": ["eur", "euro", "eura", "eure", "eurima", "€"],
    "USD": ["usd", "dolar", "dolara", "dolare", "dolarima", "dollar", "dollars", "$"],
    "GBP": ["gbp", "funta", "funti", "funte", "funtama", "pound", "pounds", "£"],
    "CHF": ["chf", "franak", "franka", "franke", "francima", "franc", "francs"],
    "JPY": ["jpy", "jen", "jena", "jene", "yen"],
    "CAD": ["cad"], "AUD": ["aud"], "SEK": ["sek"], "NOK": ["nok"], "DKK": ["dkk"],
    "PLN": ["pln", "zlot", "zlota", "zloti"], "CZK": ["czk"], "HUF": ["huf", "forinta", "forint"],
    "BAM": ["bam", "konvertibilna", "konvertibilnih", "km"], "RSD": ["rsd", "dinar", "dinara", "dinare"],
    "RON": ["ron"], "TRY": ["try", "lira", "lire"], "CNY": ["cny", "juan"],
}
_WORD_TO_CUR = {w: c for c, words in CURRENCY_WORDS.items() for w in words}


def find_currencies(text):
    """Valute u redoslijedu pojavljivanja."""
    found = []
    for tok in re.findall(r"[a-z]+|[€$£]", normalize(text)):
        cur = _WORD_TO_CUR.get(tok)
        if cur and (not found or found[-1] != cur):
            found.append(cur)
    return found


# ---------------------------------------------------------------------------
# Brojevi
# ---------------------------------------------------------------------------

_NUM = r"\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?"


def parse_number(s):
    s = s.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):  # 10.000,50
        return float(s.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):  # 10,000.50
        return float(s.replace(",", ""))
    return float(s.replace(",", "."))


def _numbers_with_suffix(text):
    """(broj, sufiks) parovi. Sufiks je riječ odmah iza broja, npr. 'tisuca', 'godina'."""
    t = normalize(text)
    out = []
    for m in re.finditer(rf"({_NUM})\s*(k\b|tisuc\w*|hiljad\w*|thousand\w*|mil\w*)?\s*([a-z€$£]*)", t):
        value = parse_number(m.group(1))
        mult = m.group(2) or ""
        if mult.startswith(("k", "tisuc", "hiljad", "thousand")):
            value *= 1000
        elif mult.startswith("mil"):
            value *= 1_000_000
        out.append((value, m.group(3) or "", m.start(), m.end()))
    return out


TERM_YEAR = ("god", "year", "yr")
TERM_MONTH = ("mj", "mjesec", "month", "mes")


def extract_term_months(text):
    for value, suffix, *_ in _numbers_with_suffix(text):
        if suffix.startswith(TERM_YEAR):
            return int(round(value * 12))
        if suffix.startswith(TERM_MONTH):
            return int(round(value))
    return None


def extract_amount(text):
    """(iznos, valuta) ili (None, None). Valuta je None ako nije navedena."""
    candidates = []
    for value, suffix, start, end in _numbers_with_suffix(text):
        if suffix.startswith(TERM_YEAR + TERM_MONTH) or suffix in ("posto", "percent", "%"):
            continue
        cur = _WORD_TO_CUR.get(suffix)
        if not cur:
            # "€ 10.000" ili "EUR 10000"
            before = normalize(text)[max(0, start - 5) : start]
            for w, c in _WORD_TO_CUR.items():
                if before.rstrip().endswith(w) and len(w) > 0:
                    cur = c
        candidates.append((value, cur))
    if not candidates:
        return None, None
    # Ako ima više brojeva, iznos je onaj uz valutu, inače najveći.
    with_cur = [c for c in candidates if c[1]]
    return max(with_cur or candidates, key=lambda c: c[0])


# ---------------------------------------------------------------------------
# Parametri kredita
# ---------------------------------------------------------------------------


def extract_loan_type(text):
    t = normalize(text)
    if re.search(r"stamben|stan\b|stana\b|stanu\b|kuc[aeu]|nekretnin|mortgage|housing|home loan|apartment|house", t):
        return "stambeni"
    if re.search(r"gotovinsk|nenamjensk|cash|personal loan|consumer", t):
        return "gotovinski"
    return None


def extract_client_type(text, awaiting=None):
    t = normalize(text)
    if re.search(r"\b(nisam|nije|nismo|ne)\b.{0,25}drzavlja|nedrzavlja|stranac|strankinja|strani drzavlja|"
                 r"foreign|not a (croatian )?citizen|non.?citizen|i'?m not croatian|am not croatian", t):
        return "nedrzavljanin"
    if re.search(r"drzavlja|hrvatsk\w* drzav|croatian citizen|\bcitizen\b|\bcroatian\b|\bhrvat", t):
        return "drzavljanin"
    if awaiting == "client_type":
        if re.search(r"^\s*(da|jesam|jesam\.|yes|yep|i am|naravno|da,)\b", t):
            return "drzavljanin"
        if re.search(r"^\s*(ne|nisam|no|nope|i'?m not)\b", t):
            return "nedrzavljanin"
    return None


def is_yes(text):
    return bool(re.search(r"^\s*(da|moze|može|ok|okej|u redu|naravno|yes|sure|yep|please|go ahead|y)\b", normalize(text)))


def is_no(text):
    return bool(re.search(r"^\s*(ne|nemoj|no|nope|n)\b", normalize(text)))


def extract_loan_params(text, awaiting=None):
    """Parametri koje prepoznamo u poruci. Nedostajući ostaju None."""
    params = {
        "loan_type": extract_loan_type(text),
        "client_type": extract_client_type(text, awaiting),
        "months": extract_term_months(text),
        "amount": None,
        "currency": None,
    }
    amount, cur = extract_amount(text)
    # Goli broj bez jedinice je iznos samo ako smo pitali za iznos ili je dovoljno velik.
    if amount is not None and (cur or awaiting == "amount" or amount >= 500):
        params["amount"], params["currency"] = amount, cur
    if params["months"] is None and awaiting == "months" and amount is not None and not cur:
        # Na pitanje o roku korisnik često napiše samo "5" ili "60".
        params["months"] = int(amount * 12) if amount <= 40 else int(amount)
        params["amount"] = None
    return params


# ---------------------------------------------------------------------------
# Namjera
# ---------------------------------------------------------------------------

# "ukup(a)?n" hvata ukupno, ukupna, ukupnu i ukupan (nepostojano a).
DETAIL_RE = r"otplatn\w* plan|plan otplate|ukupa?n|iznos otplate|koliko cu (ukupno )?(platiti|vratiti|otplatiti)|" \
            r"koliko (je|iznosi) kamat|po godinama|po mjesecima|detalj|vise info|total|schedule|amortization|" \
            r"breakdown|how much will i pay|in total|more detail|overall|interest paid"
FX_RE = r"tecaj|tecajn|preracun|konverz|convert|exchange|currency|valut"
LOAN_RE = r"kredit(?!a?n)|gotovinsk|stamben|rata|ratu|rate\b|mjesecn|anuitet|posudit|zaduzi|loan|installment|monthly payment|borrow|mortgage|izracun|calculat"
GREETING_RE = r"^\s*(bok|pozdrav|hej|zdravo|dobar dan|dobro jutro|dobra vecer|hello|hi|hey|good (morning|afternoon|evening))\b[\s!.,]*$"
THANKS_RE = r"^\s*(hvala|zahvaljujem|thanks|thank you|ty)\b"


CALC_CUE_RE = r"\brat[aeu]\b|\brate\b|izracun|kalkul|koliko bi|mjesecn|anuitet|zelim|zelio|zeljela|trebam|treba mi|" \
              r"htio|htjela|htjeo|posudit|zaduzi|podic|dignut|calculat|payment|installment|i want|i need|i'd like|borrow"


def is_ambiguous_loan(text):
    """Poruka spominje kredit, ali ne pita ni za izračun ni za nešto konkretno ("stambeni kredit", "kredit?")."""
    t = normalize(text)
    if not re.search(LOAN_RE, t) or re.search(r"\d", t):
        return False
    if re.search(CALC_CUE_RE, t) or extract_client_type(text) or extract_term_months(text):
        return False
    return True


def classify_intent(text, context=None):
    """Namjera poruke: greeting, thanks, loan_details, loan_calc, fx, info.

    `context` je stanje razgovora (npr. je li u tijeku izračun kredita).
    """
    context = context or {}
    t = normalize(text)

    if re.search(GREETING_RE, t):
        return "greeting"
    if re.search(THANKS_RE, t) and len(t) < 40:
        return "thanks"
    if context.get("has_result") and re.search(DETAIL_RE, t):
        return "loan_details"

    currencies = [c for c in find_currencies(text) if c != "EUR"]
    wants_fx = re.search(FX_RE, t) or (currencies and re.search(r"\bu\b|\bto\b|\binto\b|\bin\b", t) and not re.search(LOAN_RE, t))
    if wants_fx:
        return "fx"

    # Pitanja tipa "koji su uvjeti za stambeni kredit" su informativna, ne izračun.
    info_like = re.search(
        r"uvjet|dokument|potrebn|naknad|osiguran|prijevremen|ranije|jamac|tko moze|traje|odobrava|obrad|mirovin|"
        r"umirovljen|penzi|dob\b|godine zivota|who can|requirement|document|fee|insurance|early repay|how long|pension",
        t,
    )
    has_numbers = re.search(r"\d", t)
    if re.search(LOAN_RE, t) and (has_numbers or not info_like):
        return "loan_calc"

    if context.get("loan_in_progress"):
        # Usred izračuna kratki odgovori ("da", "5 godina") idu kalkulatoru,
        # a pitanje tipa "koje dokumente trebam?" ide u pretragu.
        return "info" if info_like and not has_numbers else "loan_calc"
    return "info"
