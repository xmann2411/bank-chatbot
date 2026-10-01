"""Odgovori na pitanja o banci: pretraga baze znanja (top 3 chunka) + odgovor."""

import re

from . import audit, llm, retrieval
from .clarify import ask_clarification
from .texts import t

REWRITE_SYSTEM = """Pretvori pitanje klijenta banke u upit za pretragu hrvatskih dokumenata banke.
Uzmi u obzir prethodni razgovor ako je pitanje nastavak (npr. "a za stambeni?").
Vrati SAMO nekoliko ključnih riječi na hrvatskom, bez objašnjenja."""

ANSWER_SYSTEM = """Ti si virtualni asistent Banke Demo d.d.
Odgovaraš na pitanja klijenata ISKLJUČIVO na temelju izvadaka iz dokumentacije banke koji su priloženi u poruci.

Pravila:
- Odgovori na jeziku na kojem je klijent pitao ({language}).
- Koristi samo informacije iz izvadaka. Ako odgovor nije u njima, reci da tu informaciju nemaš i uputi klijenta na Kontakt centar (0800 1234).
- Ne izmišljaj iznose, kamatne stope, naknade ni rokove.
- Ne daješ financijske savjete ni preporuke što bi klijent trebao odabrati.
- Klijenti pišu i s tipfelerima ili razgovorno; pokušaj zaključiti što su mislili iz pitanja i prethodnog razgovora.
- Ako izvadci odgovaraju samo djelomično i pitanje se može shvatiti na više načina, ne nagađaj: kratko pitaj
  "Jeste li mislili na ...?" i ponudi 2-3 moguća značenja.
- Budi kratak i jasan. Na kraju navedi izvor u obliku "Izvor: <naziv dokumenta>".
- Za izračun rate kredita ili tečaj valuta klijent se može obratiti tebi, jer imaš i kalkulator i tečajnu listu."""

LANG_NAMES = {"hr": "hrvatski", "en": "engleski"}


def _search_query(message, state):
    def simulate():
        return retrieval.translate_query(message) if state.lang == "en" else message

    if llm.MODE != "real":
        return simulate()
    history = state.recent(4)
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    prompt = f"Prethodni razgovor:\n{convo}\n\nPitanje: {message}"
    return llm.ask("rewrite_query", REWRITE_SYSTEM, [{"role": "user", "content": prompt}], simulate, max_tokens=2000)


def _context_block(hits):
    parts = []
    for i, h in enumerate(hits, 1):
        c = h.chunk
        parts.append(f"[Izvadak {i}] Izvor: {c['source']} | Sekcija: {c['section']}\n{c['text']}")
    return "\n\n".join(parts)


def _simulate_answer(query, hits, lang):
    """Bez modela: iz najboljeg chunka izdvoji rečenice/retke koji najbolje odgovaraju pitanju."""
    q = set(retrieval.tokenize(retrieval.expand_synonyms(query)))

    def excerpt(chunk):
        text = chunk["text"].strip()
        if len(text) <= 700:
            return text
        lines = [ln for ln in re.split(r"\n+|(?<=[.!?])\s+(?=[A-ZČĆŽŠĐ])", text) if ln.strip()]
        overlap = [len(q & set(retrieval.tokenize(ln))) for ln in lines]
        ranked = sorted((i for i in range(len(lines)) if overlap[i]), key=lambda i: -overlap[i])
        keep = set(ranked[:5]) or set(range(min(5, len(lines))))
        # Tablica bez zaglavlja nema smisla, pa ga dodajemo ako smo uzeli redak tablice.
        table_rows = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("|")]
        if keep & set(table_rows):
            keep |= set(table_rows[:2])
            # Pitanje odgovara zaglavlju, ali nijednom retku ("radno vrijeme poslovnica"): prikaži cijelu tablicu.
            if not keep & set(table_rows[2:]):
                keep |= set(table_rows)
        return "\n".join(lines[i].strip() for i in sorted(keep))

    best = hits[0].chunk
    parts = [f"**{best['section'].split(' > ')[-1]}**\n{excerpt(best)}"]
    sources = [best["source"]]
    # Ako je drugi chunk gotovo jednako relevantan, i on ide u odgovor.
    if len(hits) > 1 and hits[1].score >= 0.85 * hits[0].score:
        second = hits[1].chunk
        parts.append(f"**{second['section'].split(' > ')[-1]}**\n{excerpt(second)}")
        if second["source"] not in sources:
            sources.append(second["source"])
    return f"{t('rag_intro', lang)}\n\n" + "\n\n".join(parts) + f"\n\n{t('source', lang)}: {', '.join(sources)}"


def handle(message, state):
    query = _search_query(message, state)
    hits = retrieval.search(query)
    audit.log("retrieval", query=query, hits=[{"id": h.chunk["id"], "score": round(h.score, 2), "source": h.chunk["source"]} for h in hits])
    if not hits:
        weak = retrieval.search_weak(query)
        if weak:
            # Nešto slično postoji, ali nije sigurno da je to ono što klijent pita: ponudi teme.
            options, seen = [], set()
            for h in weak:
                title = h.chunk["section"].split(" > ")[-1].strip()
                if title.lower() not in seen:
                    seen.add(title.lower())
                    options.append({"label": title.rstrip("?"), "message": title})
            audit.log("clarify_retrieval", query=query, options=[o["label"] for o in options])
            return ask_clarification(state, options)
        return t("no_info", state.lang)

    system = ANSWER_SYSTEM.format(language=LANG_NAMES[state.lang])
    messages = state.recent(6) + [
        {"role": "user", "content": f"Izvadci iz dokumentacije:\n\n{_context_block(hits)}\n\nPitanje klijenta: {message}"}
    ]
    return llm.ask("answer", system, messages, lambda: _simulate_answer(query, hits, state.lang))
