"""Glavni agent: prepozna namjeru poruke i proslijedi je pravom subagentu.

  info          -> info_agent        (RAG nad dokumentacijom banke)
  loan_calc     -> calculator_agent  (izračun mjesečne rate)
  loan_details  -> calculator_agent  (ukupno, kamata, otplatni plan)
  fx            -> fx_agent          (tečajna lista HNB-a, preračun)
  greeting/thanks -> gotov tekst
  clarify       -> bot nije siguran što je klijent mislio i pita ("Jeste li mislili...?")
"""

import json
import uuid
from dataclasses import dataclass, field

from . import audit, calculator, calculator_agent, fx_agent, info_agent, llm, nlu, retrieval, spelling
from .clarify import ask_clarification, pick_option
from .texts import t

INTENTS = ("greeting", "thanks", "info", "loan_calc", "loan_details", "fx", "clarify")

ROUTER_SYSTEM = """Ti si usmjerivač (router) u chatbotu banke. Za poruku klijenta odredi namjeru i jezik.

Namjere:
- "loan_calc": klijent želi izračun rate kredita ili daje podatke za izračun (iznos, rok, vrstu kredita, državljanstvo)
- "loan_details": klijent traži više detalja o već napravljenom izračunu (ukupan iznos otplate, ukupna kamata, otplatni plan)
- "fx": tečaj, tečajna lista, preračun iznosa iz jedne valute u drugu
- "info": bilo koje drugo pitanje o banci, njenim proizvodima, uvjetima, naknadama, poslovnicama...
- "greeting": samo pozdrav
- "thanks": samo zahvala
- "clarify": iz poruke se stvarno ne može zaključiti što klijent želi, ni uz kontekst razgovora

Klijenti često pišu s tipfelerima, bez dijakritika ili razgovorno ("kredt", "tecaj", "ak", "kolko").
Uvijek pokušaj iz poruke i konteksta razgovora zaključiti što je klijent mislio. "clarify" koristi samo
kad su moguća dva ili više bitno različitih značenja i ne možeš procijeniti koje je vjerojatnije.
Tada dodaj "question" (kratko pitanje na jeziku klijenta, npr. "Jeste li mislili na...") i "options"
(2-3 kratke poruke koje opisuju moguća značenja, napisane kao da ih je napisao klijent).

Jezik: "hr" ili "en". Ako se iz poruke ne vidi (npr. samo "5" ili "ok"), vrati jezik iz konteksta.

Kontekst je u polju "context": je li izračun kredita u tijeku, za koji podatak je bot upravo pitao ("awaiting"),
postoji li gotov izračun ("has_result"). Kratki odgovori na pitanje bota idu namjeri koja je to pitanje postavila.

Vrati SAMO JSON: {"intent": "...", "language": "hr" | "en", "question": "...", "options": ["...", "..."]}
(polja "question" i "options" samo za "clarify")."""


@dataclass
class Conversation:
    lang: str = "hr"
    history: list = field(default_factory=list)
    loan: dict | None = None  # parametri kredita koje skupljamo
    awaiting: str | None = None  # podatak za koji je kalkulator upravo pitao
    pending: dict | None = None  # otvoreno pitanje bota, npr. {"kind": "switch_to_cash"}
    last_result: object = None  # zadnji LoanResult
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    channel: str = "cli"  # "cli" ili "web"; utječe samo na to kako se nudi CSV otplatnog plana
    quick_replies: list = field(default_factory=list)  # prijedlozi odgovora za zadnju poruku bota (gumbi u webu)

    def recent(self, n):
        """Zadnjih n poruka, tako da prva bude od korisnika (to API traži)."""
        msgs = self.history[-n:]
        while msgs and msgs[0]["role"] != "user":
            msgs = msgs[1:]
        return msgs

    # Spremanje u Redis: stanje mora stati u JSON.
    MAX_STORED_HISTORY = 40

    def to_dict(self):
        r = self.last_result
        return {
            "lang": self.lang,
            "history": self.history[-self.MAX_STORED_HISTORY:],
            "loan": self.loan,
            "awaiting": self.awaiting,
            "pending": self.pending,
            # Izračun se ne sprema cijeli (otplatni plan ima stotine redaka), nego samo
            # parametri; kod učitavanja se ponovno izračuna istom formulom.
            "last_result": r and {"loan_type": r.loan_type, "client_type": r.client_type, "amount": r.amount, "months": r.months},
            "session_id": self.session_id,
            "channel": self.channel,
            "quick_replies": self.quick_replies,
        }

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        params = data.pop("last_result", None)
        state = cls(**data)
        if params:
            try:
                state.last_result = calculator.calculate(**params)
            except calculator.LoanError:
                state.last_result = None  # npr. granice u rates.json su se u međuvremenu promijenile
        return state

    def context(self):
        return {
            "loan_in_progress": self.loan is not None and self.last_result is None or self.awaiting is not None,
            "awaiting": self.awaiting,
            "has_result": self.last_result is not None,
            "pending": self.pending["kind"] if self.pending else None,
            "language": self.lang,
        }


# ---------------------------------------------------------------------------
# Usmjeravanje
# ---------------------------------------------------------------------------


def _simulate_route(message, state):
    c = state.context()
    # Nakon gotovog izračuna poruka s brojem ili vrstom kredita je novi/izmijenjeni izračun ("a na 10 godina?").
    if state.loan is not None and (
        any(ch.isdigit() for ch in message) or nlu.extract_loan_type(message) or nlu.extract_client_type(message)
    ):
        c["loan_in_progress"] = True
    return {"intent": nlu.classify_intent(message, c), "language": nlu.detect_language(message, state.lang)}


def _route(message, state):
    prompt = json.dumps({"context": state.context(), "message": message}, ensure_ascii=False)
    result = llm.ask_json(
        "route", ROUTER_SYSTEM, [{"role": "user", "content": prompt}], lambda: _simulate_route(message, state), max_tokens=2000
    )
    intent = result.get("intent") if result.get("intent") in INTENTS else _simulate_route(message, state)["intent"]
    lang = result.get("language") if result.get("language") in ("hr", "en") else state.lang
    if intent == "clarify" and not result.get("options"):
        intent = "info"
    return intent, lang, result


PENDING_OWNER = {
    "switch_to_cash": "loan_calc",
    "use_converted_amount": "loan_calc",
    "offer_details": "loan_details",
    "offer_schedule": "loan_details",
    "fx_amount": "fx",
}


def _pending_owner(message, state):
    """Ako je bot postavio pitanje, a klijent kratko odgovori, odgovor ide onome tko je pitao."""
    if not state.pending:
        return None
    kind = state.pending["kind"]
    if kind == "fx_amount":
        # Nakon prikaza tečaja klijent često upiše samo iznos, npr. "250".
        amount, cur = nlu.extract_amount(message)
        return "fx" if amount is not None and len(message) < 25 else None
    if not (nlu.is_yes(message) or nlu.is_no(message)):
        return None
    if kind in ("offer_details", "offer_schedule") and nlu.is_no(message):
        state.pending = None
        return "thanks_no"
    return PENDING_OWNER.get(kind)


# ---------------------------------------------------------------------------
# "Jeste li mislili...?"
# ---------------------------------------------------------------------------

def _loan_ambiguity(message, state):
    """Spominje kredit, ali se ne vidi želi li klijent izračun ili informacije. Vraća opcije ili None."""
    if state.context()["loan_in_progress"] or not nlu.is_ambiguous_loan(message):
        return None
    loan_type = nlu.extract_loan_type(message)
    lang = state.lang
    kind = {"hr": {"gotovinski": "gotovinskog ", "stambeni": "stambenog "}, "en": {"gotovinski": "cash ", "stambeni": "housing "}}
    kind_for = {"hr": {"gotovinski": "gotovinski ", "stambeni": "stambeni "}, "en": kind["en"]}
    k1 = kind[lang].get(loan_type, "")
    k2 = kind_for[lang].get(loan_type, "")
    if lang == "en":
        return [
            {"label": "Calculate the monthly payment", "message": f"I want to calculate the monthly payment for a {k1}loan"},
            {"label": "Loan conditions and interest rates", "message": f"what are the requirements and interest rates for a {k2}loan"},
        ]
    return [
        {"label": "Izračun mjesečne rate", "message": f"želim izračunati mjesečnu ratu {k1}kredita"},
        {"label": "Uvjeti i kamatne stope", "message": f"koji su uvjeti i kamatne stope za {k2}kredit"},
    ]


def _typo_ambiguity(corrected, alternative, intent, state):
    """Nesiguran ispravak tipfelera vrijedi ponuditi samo ako bi promijenio odgovor."""
    if not alternative:
        return False
    alt_intent = _simulate_route(alternative, state)["intent"]
    if alt_intent != intent:
        return True
    return intent == "info" and not retrieval.search(corrected) and bool(retrieval.search(alternative))


# ---------------------------------------------------------------------------
# Glavna funkcija
# ---------------------------------------------------------------------------


def _dispatch(intent, message, state):
    if intent == "greeting":
        return t("greeting", state.lang)
    if intent in ("thanks", "thanks_no"):
        return t("thanks", state.lang)
    if intent == "loan_calc":
        return calculator_agent.handle(message, state)
    if intent == "loan_details":
        return calculator_agent.details(message, state)
    if intent == "fx":
        return fx_agent.handle(message, state)
    return info_agent.handle(message, state)


def _answer(message, state, allow_clarify=True):
    """Obradi poruku i vrati (namjera, odgovor)."""
    corrected, alternative, changes = message, None, []
    if llm.MODE != "real":
        # Pravi model sam razumije tipfelere; u simuliranom modu ih ispravljamo rječnikom.
        corrected, alternative, changes = spelling.correct(message)
        if changes:
            audit.log("spelling", original=message, corrected=corrected, alternative=alternative, changes=changes)

    intent = _pending_owner(corrected, state)
    route = {}
    if intent is None:
        intent, state.lang, route = _route(corrected, state)
    elif len(message) > 3:
        state.lang = nlu.detect_language(corrected, state.lang)

    # Klijent je promijenio temu: zaboravi pitanje koje je ostalo visjeti.
    if intent not in ("loan_calc", "loan_details") and state.awaiting:
        state.awaiting = None
    if state.pending and PENDING_OWNER.get(state.pending["kind"]) != intent:
        state.pending = None

    if allow_clarify:
        if intent == "clarify":
            options = [{"label": o, "message": o} for o in route.get("options", [])[:3]]
            return "clarify", ask_clarification(state, options, route.get("question"))
        if llm.MODE != "real":
            if _typo_ambiguity(corrected, alternative, intent, state):
                return "clarify", ask_clarification(state, [{"label": alternative, "message": alternative}])
            if intent == "loan_calc":
                options = _loan_ambiguity(corrected, state)
                if options:
                    return "clarify", ask_clarification(state, options)
    elif intent == "clarify":
        intent = "info"

    return intent, _dispatch(intent, corrected, state)


def reply(message, state):
    message = message.strip()
    state.quick_replies = []

    if state.pending and state.pending["kind"] == "clarify":
        options = state.pending["options"]
        state.pending = None
        chosen = pick_option(message, options)
        if chosen:
            # Klijent je potvrdio što je mislio: obradi to, bez novog dodatnog pitanja.
            intent, answer = _answer(chosen["message"], state, allow_clarify=False)
        elif nlu.is_no(message):
            intent, answer = "clarify_no", t("rephrase", state.lang)
        else:
            intent, answer = _answer(message, state)
    else:
        intent, answer = _answer(message, state)

    state.history.append({"role": "user", "content": message})
    state.history.append({"role": "assistant", "content": answer})
    audit.log("turn", mode=llm.MODE, intent=intent, lang=state.lang, user=message, bot=answer)
    return answer
