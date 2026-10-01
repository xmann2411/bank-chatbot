"""Tečajna lista HNB-a (https://api.hnb.hr/tecajn-eur/v3). Javni API, ne treba ključ.

Tečaj je izražen kao broj jedinica strane valute za 1 EUR.
Preračun radimo po srednjem tečaju.
"""

import json
from datetime import date

import requests

from .config import CACHE_DIR, HNB_API


class FxError(RuntimeError):
    pass


class UnknownCurrency(FxError):
    def __init__(self, currency):
        super().__init__(f"Valuta {currency} nije na tečajnoj listi HNB-a")
        self.currency = currency


def _to_float(s):
    return float(s.replace(",", "."))


def get_rates(day=None):
    """Sve valute za dan (danas ako nije zadano). Dnevni cache na disku."""
    day = day or date.today().isoformat()
    cache = CACHE_DIR / f"hnb-{day}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    try:
        res = requests.get(HNB_API, params={"datum-primjene": day}, timeout=10)
        res.raise_for_status()
        raw = res.json()
    except (requests.RequestException, ValueError) as e:
        raise FxError(f"HNB API nije dostupan: {e}") from e
    if not raw:
        raise FxError("HNB nema tečajnicu za taj dan")

    rates = {
        r["valuta"]: {
            "valuta": r["valuta"],
            "drzava": r["drzava"],
            "kupovni": _to_float(r["kupovni_tecaj"]),
            "srednji": _to_float(r["srednji_tecaj"]),
            "prodajni": _to_float(r["prodajni_tecaj"]),
            "datum": r["datum_primjene"],
        }
        for r in raw
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rates, ensure_ascii=False), encoding="utf-8")
    return rates


def get_rate(currency):
    rates = get_rates()
    currency = currency.upper()
    if currency not in rates:
        raise UnknownCurrency(currency)
    return rates[currency]


def convert(amount, from_cur, to_cur):
    """Preračun preko EUR po srednjem tečaju. Vraća (iznos, korišteni tečajevi)."""
    from_cur, to_cur = from_cur.upper(), to_cur.upper()
    used = {}
    eur = amount
    if from_cur != "EUR":
        r = get_rate(from_cur)
        used[from_cur] = r
        eur = amount / r["srednji"]
    result = eur
    if to_cur != "EUR":
        r = get_rate(to_cur)
        used[to_cur] = r
        result = eur * r["srednji"]
    return round(result, 2), used
