"""Subagent za izračun kredita.

Iz razgovora skuplja četiri podatka (vrsta kredita, iznos, rok, državljanstvo),
pita za ono što nedostaje i onda zove calculator.py. LLM samo izvlači parametre
iz teksta, a sam izračun i tekst s brojevima uvijek radi kod, da nema izmišljenih brojeva.
"""

import csv
import io
import json

from . import audit, fx, llm, nlu
from .calculator import LoanError, calculate, product
from .config import ROOT
from .texts import client_name, loan_name, money, pct, t, term, term_range

SLOTS = ("loan_type", "amount", "months", "client_type")

EXTRACT_SYSTEM = """Ti si dio chatbota banke. Tvoj jedini zadatak je iz poruke klijenta izvući parametre kredita.

Vrati SAMO JSON objekt ovog oblika, bez ikakvog drugog teksta:
{"loan_type": "gotovinski" | "stambeni" | null,
 "amount": broj | null,
 "currency": "EUR" | "USD" | "CHF" | ... (ISO kod) | null,
 "months": cijeli broj mjeseci | null,
 "client_type": "drzavljanin" | "nedrzavljanin" | null}

Pravila:
- Gotovinski = nenamjenski / cash / personal loan. Stambeni = za stan, kuću, nekretninu / mortgage / housing loan.
- Rok pretvori u mjesece (5 godina = 60).
- "10k", "10 tisuća" = 10000.
- client_type: je li klijent državljanin Republike Hrvatske.
- Ako je bot upravo pitao za neki podatak (polje "awaiting"), kratak odgovor ("da", "ne", "5", "20000") odnosi se na to polje.
  Za awaiting=client_type: "da" znači drzavljanin, "ne" znači nedrzavljanin.
  Za awaiting=months: goli broj do 40 su godine, veći broj su mjeseci.
- Poruka može imati tipfelere ili biti napisana razgovorno ("gotovnski", "kredt", "5 god", "10 tisuca") - prepoznaj što je mislio.
- Ako podatak nije spomenut u poruci, stavi null. Ništa ne izmišljaj."""


def _extract(message, state):
    def simulate():
        return nlu.extract_loan_params(message, state.awaiting)

    prompt = json.dumps({"awaiting": state.awaiting, "known": state.loan, "message": message}, ensure_ascii=False)
    params = llm.ask_json("extract_loan_params", EXTRACT_SYSTEM, [{"role": "user", "content": prompt}], simulate)
    return {k: params.get(k) for k in ("loan_type", "amount", "currency", "months", "client_type")}


def _limits(loan_type, lang):
    p = product(loan_type)
    return {
        "name": loan_name(loan_type, lang),
        "min_amount": money(p["min_iznos"], lang),
        "max_amount": money(p["max_iznos"], lang),
        "term_range": term_range(p["min_rok_mjeseci"], p["max_rok_mjeseci"], lang),
        "max_term": p["max_rok_mjeseci"],
    }


def _ask(slot, state):
    state.awaiting = slot
    lang = state.lang
    if slot == "loan_type":
        state.quick_replies = [t("loan_type_cash", lang), t("loan_type_housing", lang)]
        return t("ask_loan_type", lang)
    if slot == "client_type":
        state.quick_replies = _yes_no(lang)
        return t("ask_client_type", lang)
    lim = _limits(state.loan["loan_type"], lang)
    if slot == "amount":
        return t("ask_amount", lang, name=lim["name"], min=lim["min_amount"], max=lim["max_amount"])
    return t("ask_months", lang, name=lim["name"], range=lim["term_range"])


def _yes_no(lang):
    return [t("yes", lang), t("no", lang)]


def _housing_refusal(state):
    state.pending = {"kind": "switch_to_cash"}
    state.quick_replies = _yes_no(state.lang)
    state.awaiting = None
    lim = _limits("gotovinski", state.lang)
    return t("housing_not_for_foreigners", state.lang, min=lim["min_amount"], max=lim["max_amount"], max_term=lim["max_term"])


def _check_range(state):
    """Poruka ako su iznos ili rok izvan granica proizvoda, inače None."""
    loan, lang = state.loan, state.lang
    p = product(loan["loan_type"])
    lim = _limits(loan["loan_type"], lang)
    if loan["amount"] is not None and not p["min_iznos"] <= loan["amount"] <= p["max_iznos"]:
        audit.log("loan_rejected", reason="amount_out_of_range", loan=loan)
        value = money(loan["amount"], lang)
        loan["amount"] = None
        state.awaiting = "amount"
        return t("amount_out_of_range", lang, value=value, name=lim["name"], min=lim["min_amount"], max=lim["max_amount"])
    if loan["months"] is not None and not p["min_rok_mjeseci"] <= loan["months"] <= p["max_rok_mjeseci"]:
        audit.log("loan_rejected", reason="term_out_of_range", loan=loan)
        value = term(loan["months"], lang)
        loan["months"] = None
        state.awaiting = "months"
        return t("term_out_of_range", lang, value=value, name=lim["name"], range=lim["term_range"])
    return None


def _handle_pending(message, state):
    """Odgovor na pitanje da/ne koje je bot postavio. Vraća tekst ili None ako poruka nije da/ne."""
    kind = state.pending["kind"]
    yes, no = nlu.is_yes(message), nlu.is_no(message)
    if not (yes or no):
        return None
    pending = state.pending
    state.pending = None

    if kind == "switch_to_cash":
        if yes:
            state.loan["loan_type"] = "gotovinski"
            return None  # nastavi normalni tok, pitat će što nedostaje
        state.loan = None
        return t("loan_cancelled", state.lang)

    if kind == "use_converted_amount":
        if yes:
            state.loan["amount"] = pending["amount"]
            return None
        state.loan["amount"] = None
        state.awaiting = "amount"
        return t("ask_amount_eur", state.lang)
    return None


def _foreign_currency(amount, currency, state):
    lang = state.lang
    try:
        eur, used = fx.convert(amount, currency, "EUR")
    except fx.FxError:
        state.awaiting = "amount"
        return t("foreign_currency_no_fx", lang)
    eur_round = float(round(eur))
    state.pending = {"kind": "use_converted_amount", "amount": eur_round}
    state.quick_replies = _yes_no(lang)
    state.awaiting = None
    return t(
        "foreign_currency_loan", lang,
        amount=money(amount, lang, currency), date=used[currency]["datum"],
        eur=money(eur, lang), eur_round=money(eur_round, lang),
    )


def handle(message, state):
    if state.loan is None:
        state.loan = dict.fromkeys(SLOTS)

    if state.pending and state.pending["kind"] in ("switch_to_cash", "use_converted_amount"):
        reply = _handle_pending(message, state)
        if reply:
            return reply
        if state.pending:  # nije bio odgovor da/ne, pitanje ostaje otvoreno
            state.pending = None

    params = _extract(message, state)
    currency = (params.get("currency") or "EUR").upper()
    for slot in SLOTS:
        if params.get(slot) is not None and slot != "amount":
            state.loan[slot] = params[slot]

    if params.get("amount") is not None:
        amount = float(params["amount"])
        if currency != "EUR":
            return _foreign_currency(amount, currency, state)
        state.loan["amount"] = amount
    if state.loan["months"] is not None:
        state.loan["months"] = int(state.loan["months"])

    loan = state.loan
    if loan["loan_type"] == "stambeni" and loan["client_type"] == "nedrzavljanin":
        return _housing_refusal(state)

    # Iznos i rok provjeravamo čim ih znamo, da klijent ne odgovara na sva pitanja pa tek onda sazna da iznos ne može.
    if loan["loan_type"]:
        range_error = _check_range(state)
        if range_error:
            return range_error

    for slot in SLOTS:
        if loan[slot] is None:
            return _ask(slot, state)

    state.awaiting = None
    lang = state.lang
    try:
        result = calculate(loan["loan_type"], loan["client_type"], loan["amount"], loan["months"])
    except LoanError as e:
        audit.log("loan_rejected", reason=e.code, loan=loan)
        if e.code == "not_available_for_client":
            return _housing_refusal(state)
        raise

    state.last_result = result
    # Odgovor nudi ukupni iznos i otplatni plan, pa kratko "da" mora doći ovamo.
    state.pending = {"kind": "offer_details"}
    state.quick_replies = [t("qr_totals", lang), t("qr_schedule", lang)]
    audit.log("loan_calculated", loan=loan, rate=result.rate, monthly_payment=result.monthly_payment)
    return t(
        "result", lang,
        name=loan_name(result.loan_type, lang), amount=money(result.amount, lang), term=term(result.months, lang),
        client=client_name(result.client_type, lang), rate=pct(result.rate, lang), payment=money(result.monthly_payment, lang),
    )


# ---------------------------------------------------------------------------
# Detalji: ukupno, kamata, otplatni plan
# ---------------------------------------------------------------------------

SCHEDULE_WORDS = ("plan", "godinama", "schedule", "amortization", "breakdown", "by year", "po godini")


def schedule_csv(result):
    """Otplatni plan po mjesecima kao CSV tekst (točka-zarez, decimalni zarez, za Excel)."""
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["mjesec", "rata", "kamata", "glavnica", "ostatak"])
    for r in result.schedule:
        w.writerow([r["mjesec"]] + [f"{r[k]:.2f}".replace(".", ",") for k in ("rata", "kamata", "glavnica", "ostatak")])
    return out.getvalue()


def schedule_filename(result):
    return f"otplatni-plan-{result.loan_type}-{int(result.amount)}-{result.months}mj.csv"


def _export_csv(result):
    out_dir = ROOT / "exports"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / schedule_filename(result)
    path.write_text(schedule_csv(result), encoding="utf-8-sig")
    return path.relative_to(ROOT)


def _schedule_table(result, lang):
    """Plan po godinama kao markdown tablica (čitljivo i u terminalu i u webu)."""
    cols = t("schedule_cols", lang)
    fmt = lambda v: money(v, lang, "").strip()
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for y in result.yearly_summary():
        lines.append(f"| {y['godina']} | {fmt(y['uplaceno'])} | {fmt(y['kamata'])} | {fmt(y['glavnica'])} | {fmt(y['ostatak'])} |")
    return "\n".join(lines)


def details(message, state):
    result = state.last_result
    lang = state.lang
    if result is None:
        return t("no_result_yet", lang)

    pending = state.pending["kind"] if state.pending else None
    accepted_offer = pending == "offer_schedule" and nlu.is_yes(message)
    wants_schedule = accepted_offer or any(w in nlu.normalize(message) for w in SCHEDULE_WORDS)
    state.pending = None

    # Ako je klijent upravo potvrdio ponudu za plan, ukupne iznose je već vidio.
    parts = [] if accepted_offer else [
        t(
            "totals", lang,
            name=loan_name(result.loan_type, lang), amount=money(result.amount, lang), term=term(result.months, lang),
            rate=pct(result.rate, lang), payment=money(result.monthly_payment, lang),
            total=money(result.total_paid, lang), interest=money(result.total_interest, lang),
        )
    ]
    if wants_schedule:
        parts.append(t("schedule_header", lang) + "\n" + _schedule_table(result, lang))
        if state.channel == "web":
            parts.append(t("schedule_csv_web", lang, url=f"/api/schedule/{state.session_id}.csv"))
        else:
            parts.append(t("schedule_csv", lang, path=_export_csv(result)))
    else:
        state.pending = {"kind": "offer_schedule"}
        state.quick_replies = _yes_no(lang)
        parts.append(t("offer_schedule", lang))
    return "\n\n".join(parts)
