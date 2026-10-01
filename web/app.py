"""Web server: stranica Banke Demo + chat API.

    python -m web.app
    -> http://localhost:5000/

  GET  /                          stranica banke (data/raw/web) s chat prozorom
  GET  /widget/<datoteka>         JS i CSS chat prozora
  POST /api/session               novi razgovor -> {session_id, greeting, mode}
  POST /api/chat                  {session_id, message} -> {reply, quick_replies}
  GET  /api/schedule/<id>.csv     otplatni plan zadnjeg izračuna u tom razgovoru
  GET  /api/health                gdje se spremaju sesije (redis / memory)

Razgovori se spremaju u Redis ako je u .env postavljen REDIS_URL (vidi web/sessions.py),
inače u memoriju servera. Brišu se nakon 30 min neaktivnosti.
"""

from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from bankbot import audit, llm
from bankbot.agent import reply
from bankbot.calculator_agent import schedule_csv, schedule_filename
from bankbot.config import MODEL, RAW_DIR
from bankbot.texts import t
from web.sessions import make_store

SITE_DIR = RAW_DIR / "web"
STATIC_DIR = Path(__file__).parent / "static"

MAX_MESSAGE_CHARS = 1000

app = Flask(__name__, static_folder=None)
sessions = make_store()

STORE_DOWN = "Razgovor trenutno nije moguće spremiti. Pokušajte ponovno za minutu."


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    return jsonify(sessions=sessions.kind, mode=llm.MODE)


@app.post("/api/session")
def new_session():
    data = request.get_json(silent=True) or {}
    lang = data.get("lang") if data.get("lang") in ("hr", "en") else "hr"
    try:
        state = sessions.create(lang)
    except Exception:
        app.logger.exception("Spremište sesija nije dostupno")
        return jsonify(error=STORE_DOWN), 503
    audit.set_session(state.session_id)
    audit.log("session_start", channel="web", lang=lang, store=sessions.kind)
    return jsonify(
        session_id=state.session_id,
        greeting=t("greeting", lang),
        mode=llm.MODE,
        model=MODEL if llm.MODE == "real" else None,
    )


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify(error="Poruka je prazna."), 400
    if len(message) > MAX_MESSAGE_CHARS:
        return jsonify(error=f"Poruka je predugačka (najviše {MAX_MESSAGE_CHARS} znakova)."), 400
    session_id = str(data.get("session_id", ""))

    try:
        with sessions.lock(session_id):
            state = sessions.load(session_id)
            if state is None:
                # Razgovor je istekao (ili ga nikad nije bilo): klijent treba započeti novi.
                return jsonify(error="session_expired"), 410
            audit.set_session(state.session_id)
            try:
                answer = reply(message, state)
            except Exception as e:  # klijent ne smije dobiti stack trace
                audit.log("error", error=repr(e))
                app.logger.exception("Greška u obradi poruke")
                return jsonify(error="Došlo je do greške. Pokušajte ponovno."), 500
            sessions.save(state)
    except Exception:
        app.logger.exception("Spremište sesija nije dostupno")
        return jsonify(error=STORE_DOWN), 503
    return jsonify(reply=answer, lang=state.lang, quick_replies=state.quick_replies)


@app.get("/api/schedule/<session_id>.csv")
def schedule(session_id):
    try:
        state = sessions.load(session_id)
    except Exception:
        app.logger.exception("Spremište sesija nije dostupno")
        abort(503)
    if state is None or state.last_result is None:
        abort(404)
    result = state.last_result
    body = "\ufeff" + schedule_csv(result)  # BOM da Excel ispravno prikaže č, ć...
    name = schedule_filename(result)
    return Response(body, mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------------------------------------------------------------------------
# Statika
# ---------------------------------------------------------------------------


@app.get("/widget/<path:filename>")
def widget(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.get("/")
@app.get("/<path:filename>")
def site(filename="index.html"):
    return send_from_directory(SITE_DIR, filename)


if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", "5000"))
    mode = f"pravi model ({MODEL})" if llm.MODE == "real" else "simulirani mod (bez API ključa)"
    print(f"Banka Demo chatbot | {mode}\nOtvorite http://localhost:{port}/")
    # use_reloader: server se sam restarta kad se promijeni Python kod (samo za razvoj; RELOAD=0 isključuje).
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=os.getenv("RELOAD", "1") == "1")
