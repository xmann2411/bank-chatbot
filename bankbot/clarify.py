"""Pitanja "Jeste li mislili...?" kad bot nije siguran što je klijent htio.

Opcije se pamte u state.pending = {"kind": "clarify", "options": [...]}, a klijent
odgovara brojem, riječju ("prvo"), s "da" (kad je ponuđena jedna opcija) ili klikom
na gumb u webu (šalje tekst opcije).
"""

from difflib import SequenceMatcher

from . import nlu
from .texts import t

ORDINALS = {
    1: ("1", "prvo", "prva", "prvi", "first"),
    2: ("2", "drugo", "druga", "drugi", "second"),
    3: ("3", "trece", "treca", "treci", "third"),
}


def ask_clarification(state, options, question=None):
    """Postavi pitanje s ponuđenim značenjima. options: [{"label": tekst gumba, "message": što se obrađuje}]."""
    state.pending = {"kind": "clarify", "options": options}
    if len(options) == 1:
        state.quick_replies = [t("yes", state.lang), t("no", state.lang)]
        return question or t("did_you_mean_one", state.lang, text=options[0]["label"])
    state.quick_replies = [o["label"] for o in options]
    listed = "\n".join(f"{i}. {o['label']}" for i, o in enumerate(options, 1))
    return (question or t("did_you_mean_many", state.lang)) + "\n" + listed + "\n\n" + t("pick_option", state.lang)


def pick_option(message, options):
    """Koju je ponuđenu opciju klijent odabrao (broj, 'prvo', 'da', ili tekst opcije). None ako nijednu."""
    norm = nlu.normalize(message).strip(" .!?")
    if len(options) == 1 and nlu.is_yes(message):
        return options[0]
    first = norm.split()[0] if norm else ""
    for i, words in ORDINALS.items():
        if i <= len(options) and (norm in words or first in words):
            return options[i - 1]
    best, best_ratio = None, 0.0
    for o in options:
        ratio = SequenceMatcher(None, norm, nlu.normalize(o["label"])).ratio()
        if ratio > best_ratio:
            best, best_ratio = o, ratio
    return best if best_ratio >= 0.75 else None
