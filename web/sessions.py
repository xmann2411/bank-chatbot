"""Spremište web razgovora.

  RedisSessionStore   razgovori u Redisu: prežive restart servera i rade s više procesa/servera
  MemorySessionStore  razgovori u memoriji procesa (kad Redis nije podešen ili nije dostupan)

Oba imaju isto sučelje:

    state = store.create(lang)
    with store.lock(session_id):        # dvije poruke istog razgovora ne obrađuju se istovremeno
        state = store.load(session_id)  # None ako ne postoji ili je istekao
        ...
        store.save(state)

Razgovor istječe nakon SESSION_TTL sekundi neaktivnosti (svaki load/save produži rok).
"""

import json
import secrets
import threading
import time
from contextlib import contextmanager

from bankbot.agent import Conversation
from bankbot.config import REDIS_URL, SESSION_TTL


def _new_state(lang):
    return Conversation(lang=lang, session_id=secrets.token_urlsafe(16), channel="web")


class MemorySessionStore:
    kind = "memory"
    MAX_SESSIONS = 1000

    def __init__(self, ttl=SESSION_TTL):
        self.ttl = ttl
        self._items = {}  # id -> (Conversation, last_seen)
        self._locks = {}
        self._guard = threading.Lock()

    def create(self, lang):
        state = _new_state(lang)
        with self._guard:
            self._cleanup()
            if len(self._items) >= self.MAX_SESSIONS:
                oldest = min(self._items, key=lambda k: self._items[k][1])
                self._drop(oldest)
            self._items[state.session_id] = (state, time.time())
            self._locks[state.session_id] = threading.Lock()
        return state

    def load(self, session_id):
        with self._guard:
            item = self._items.get(session_id)
            if not item or time.time() - item[1] > self.ttl:
                return None
            self._items[session_id] = (item[0], time.time())
            return item[0]

    def save(self, state):
        with self._guard:
            self._items[state.session_id] = (state, time.time())

    @contextmanager
    def lock(self, session_id):
        with self._guard:
            lock = self._locks.setdefault(session_id, threading.Lock())
        with lock:
            yield

    def _drop(self, session_id):
        self._items.pop(session_id, None)
        self._locks.pop(session_id, None)

    def _cleanup(self):
        now = time.time()
        for k in [k for k, (_, seen) in self._items.items() if now - seen > self.ttl]:
            self._drop(k)


class RedisSessionStore:
    """Svaki razgovor je jedan JSON pod ključem bankbot:session:<id>, s rokom trajanja (EXPIRE)."""

    kind = "redis"
    PREFIX = "bankbot:session:"

    def __init__(self, client, ttl=SESSION_TTL):
        self.r = client
        self.ttl = ttl

    @classmethod
    def from_url(cls, url, **kw):
        import redis

        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=5)
        client.ping()  # odmah javi ako Redis nije dostupan
        return cls(client, **kw)

    def _key(self, session_id):
        return self.PREFIX + session_id

    def create(self, lang):
        state = _new_state(lang)
        self.save(state)
        return state

    def load(self, session_id):
        raw = self.r.get(self._key(session_id))
        if raw is None:
            return None
        self.r.expire(self._key(session_id), self.ttl)
        return Conversation.from_dict(json.loads(raw))

    def save(self, state):
        self.r.set(self._key(state.session_id), json.dumps(state.to_dict(), ensure_ascii=False), ex=self.ttl)

    @contextmanager
    def lock(self, session_id):
        # Redis lock radi i kad ima više procesa ili servera; sam se otpusti nakon 30 s ako proces padne.
        with self.r.lock(self._key(session_id) + ":lock", timeout=30, blocking_timeout=30):
            yield


def make_store(url=REDIS_URL, log=print):
    """Redis ako je REDIS_URL podešen i dostupan, inače memorija (uz upozorenje)."""
    if not url:
        return MemorySessionStore()
    try:
        store = RedisSessionStore.from_url(url)
        log(f"Sesije: Redis ({url})")
        return store
    except Exception as e:
        log(f"UPOZORENJE: Redis na {url} nije dostupan ({e}). Sesije se drže u memoriji i nestaju kod restarta.")
        return MemorySessionStore()
