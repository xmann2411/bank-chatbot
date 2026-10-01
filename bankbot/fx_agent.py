"""Tečajna lista i preračun valuta (HNB, srednji tečaj)."""

import json

from . import audit, fx, llm, nlu
from .texts import money, t

MAIN_CURRENCIES = ("USD", "GBP", "CHF", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "BAM", "RSD")

EXTRACT_SYSTEM = """Ti si dio chatbota banke. Iz poruke klijenta izvuci zahtjev za tečaj ili preračun valuta.

Vrati SAMO JSON objekt, bez drugog teksta:
{"amount": broj | null, "from": ISO kod valute | null, "to": ISO kod valute | null, "currency": ISO kod | null}

- "koliko je 100 dolara u eurima" -> {"amount": 100, "from": "USD", "to": "EUR", "currency": null}
- "koliko franaka dobijem za 500 eura" -> {"amount": 500, "from": "EUR", "to": "CHF", "currency": null}
- "koji je tečaj funte" -> {"amount": null, "from": null, "to": null, "currency": "GBP"}
- "tečajna lista" -> sve null
Ako je u polju "pending_currency" valuta, a klijent napiše samo iznos, iznos je u toj valuti i preračunava se u EUR."""


def _simulate_extract(message, pending_currency):
    amount, amount_cur = nlu.extract_amount(message)
    currencies = nlu.find_currencies(message)
    if amount is not None:
        if amount_cur is None and pending_currency:
            return {"amount": amount, "from": pending_currency, "to": "EUR", "currency": None}
        src = amount_cur or (currencies[0] if currencies else None)
        others = [c for c in currencies if c != src]
        if src:
            return {"amount": amount, "from": src, "to": others[0] if others else ("EUR" if src != "EUR" else None), "currency": None}
    non_eur = [c for c in currencies if c != "EUR"]
    return {"amount": None, "from": None, "to": None, "currency": non_eur[0] if non_eur else None}


def _fmt_rate(v, lang):
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") if lang == "hr" else s


def handle(message, state):
    lang = state.lang
    pending_currency = state.pending["currency"] if state.pending and state.pending["kind"] == "fx_amount" else None
    state.pending = None

    prompt = json.dumps({"pending_currency": pending_currency, "message": message}, ensure_ascii=False)
    req = llm.ask_json("extract_fx", EXTRACT_SYSTEM, [{"role": "user", "content": prompt}],
                       lambda: _simulate_extract(message, pending_currency))
    audit.log("fx_request", request=req)

    try:
        if req.get("amount") is not None and req.get("from") and req.get("to"):
            src, dst = req["from"].upper(), req["to"].upper()
            result, used = fx.convert(float(req["amount"]), src, dst)
            day = next(iter(used.values()))["datum"] if used else ""
            return t("fx_converted", lang, src=money(float(req["amount"]), lang, src), dst=money(result, lang, dst), date=day)

        if req.get("currency"):
            cur = req["currency"].upper()
            r = fx.get_rate(cur)
            state.pending = {"kind": "fx_amount", "currency": cur}
            return t("fx_rate", lang, cur=cur, country=r["drzava"], date=r["datum"],
                     buy=_fmt_rate(r["kupovni"], lang), mid=_fmt_rate(r["srednji"], lang), sell=_fmt_rate(r["prodajni"], lang))

        rates = fx.get_rates()
        rows = [f"  {c}  {_fmt_rate(rates[c]['srednji'], lang)}" for c in MAIN_CURRENCIES if c in rates]
        day = next(iter(rates.values()))["datum"]
        return t("fx_list", lang, date=day, rows="\n".join(rows))
    except fx.UnknownCurrency as e:
        return t("fx_unknown_currency", lang, cur=e.currency)
    except fx.FxError:
        return t("fx_unavailable", lang)
