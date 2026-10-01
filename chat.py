"""Chat u terminalu.

    python chat.py
"""

import sys

from bankbot import audit, llm
from bankbot.agent import Conversation, reply
from bankbot.config import MODEL
from bankbot.texts import t


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")

    state = Conversation()
    audit.set_session(state.session_id)
    mode = f"pravi model ({MODEL})" if llm.MODE == "real" else "simulirani mod (bez API ključa)"
    print(f"Banka Demo - chatbot | {mode}")
    print("Za izlaz upišite 'izlaz' ili 'exit'.\n")
    print(f"Bot: {t('greeting', 'hr')}\n")

    while True:
        try:
            message = input("Vi: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in ("izlaz", "exit", "quit", "kraj"):
            break
        print(f"\nBot: {reply(message, state)}")
        if state.quick_replies:
            print("     [" + "]  [".join(state.quick_replies) + "]")
        print()


if __name__ == "__main__":
    main()
