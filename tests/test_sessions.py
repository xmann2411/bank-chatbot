"""Spremanje razgovora: serijalizacija i oba spremišta (Redis preko fakeredis, bez pravog servera)."""

import json
import os
import unittest
from unittest import mock

import fakeredis

from bankbot import llm
from bankbot.agent import Conversation, reply
from web.sessions import MemorySessionStore, RedisSessionStore, make_store


def chat(state, *messages):
    return [reply(m, state) for m in messages]


@mock.patch.object(llm, "MODE", "simulated")
class SerializationTest(unittest.TestCase):
    def test_roundtrip_mid_calculation(self):
        state = Conversation()
        chat(state, "gotovinski kredit 15000 eur na 5 godina")
        restored = Conversation.from_dict(json.loads(json.dumps(state.to_dict())))
        self.assertEqual(restored.loan, state.loan)
        self.assertEqual(restored.awaiting, "client_type")
        # Razgovor se nastavlja točno gdje je stao.
        self.assertIn("292,02 EUR", reply("da", restored))

    def test_roundtrip_with_result_recalculates_schedule(self):
        state = Conversation()
        chat(state, "gotovinski kredit 15000 eur na 5 godina", "da")
        data = state.to_dict()
        self.assertNotIn("schedule", json.dumps(data))  # plan se ne sprema, preračuna se
        restored = Conversation.from_dict(json.loads(json.dumps(data)))
        self.assertEqual(restored.last_result.monthly_payment, 292.02)
        self.assertEqual(len(restored.last_result.schedule), 60)
        self.assertIn("17.521,09 EUR", reply("da", restored))  # ponuda detalja je preživjela

    def test_history_is_capped(self):
        state = Conversation(history=[{"role": "user", "content": str(i)} for i in range(100)])
        self.assertEqual(len(state.to_dict()["history"]), Conversation.MAX_STORED_HISTORY)


class StoreContract:
    """Isti testovi za oba spremišta."""

    def make(self, ttl=60):
        raise NotImplementedError

    def test_create_load_save(self):
        store = self.make()
        state = store.create("en")
        loaded = store.load(state.session_id)
        self.assertEqual(loaded.lang, "en")
        self.assertEqual(loaded.channel, "web")
        loaded.loan = {"loan_type": "stambeni", "amount": None, "months": None, "client_type": None}
        store.save(loaded)
        self.assertEqual(store.load(state.session_id).loan["loan_type"], "stambeni")

    def test_unknown_session(self):
        self.assertIsNone(self.make().load("nepostojeci"))

    def test_lock(self):
        store = self.make()
        state = store.create("hr")
        with store.lock(state.session_id):
            pass


class MemoryStoreTest(StoreContract, unittest.TestCase):
    def make(self, ttl=60):
        return MemorySessionStore(ttl=ttl)

    def test_expires(self):
        store = self.make(ttl=0)
        state = store.create("hr")
        self.assertIsNone(store.load(state.session_id))


class RedisStoreTest(StoreContract, unittest.TestCase):
    def make(self, ttl=60):
        self.client = fakeredis.FakeRedis(decode_responses=True)
        return RedisSessionStore(self.client, ttl=ttl)

    def test_stored_as_json_with_ttl(self):
        store = self.make(ttl=1800)
        state = store.create("hr")
        key = RedisSessionStore.PREFIX + state.session_id
        self.assertEqual(json.loads(self.client.get(key))["session_id"], state.session_id)
        self.assertTrue(0 < self.client.ttl(key) <= 1800)

    def test_survives_new_store_instance(self):
        # Kao restart servera: novi objekt spremišta, isti Redis.
        store = self.make()
        state = store.create("hr")
        state.awaiting = "amount"
        store.save(state)
        again = RedisSessionStore(self.client)
        self.assertEqual(again.load(state.session_id).awaiting, "amount")


REDIS_TEST_URL = os.getenv("REDIS_TEST_URL", "")


@unittest.skipUnless(REDIS_TEST_URL, "REDIS_TEST_URL nije postavljen (u CI-ju se testira s pravim Redisom)")
class RealRedisStoreTest(StoreContract, unittest.TestCase):
    """Isti testovi protiv pravog Redisa. Koristite zasebnu bazu, npr. redis://localhost:6379/15."""

    def make(self, ttl=60):
        store = RedisSessionStore.from_url(REDIS_TEST_URL, ttl=ttl)
        self.addCleanup(lambda: [store.r.delete(k) for k in store.r.scan_iter(RedisSessionStore.PREFIX + "*")])
        return store

    def test_survives_new_store_instance(self):
        store = self.make()
        state = store.create("hr")
        state.awaiting = "amount"
        store.save(state)
        self.assertEqual(RedisSessionStore.from_url(REDIS_TEST_URL).load(state.session_id).awaiting, "amount")


class MakeStoreTest(unittest.TestCase):
    def test_no_url_means_memory(self):
        self.assertEqual(make_store(url="").kind, "memory")

    def test_unreachable_redis_falls_back_to_memory(self):
        messages = []
        store = make_store(url="redis://127.0.0.1:1/0", log=messages.append)
        self.assertEqual(store.kind, "memory")
        self.assertIn("nije dostupan", messages[0])


if __name__ == "__main__":
    unittest.main()
