import unittest
from unittest import mock

from bankbot import llm
import web.app as web_app
from web.app import app
from web.sessions import MemorySessionStore


@mock.patch.object(llm, "MODE", "simulated")
class WebApiTest(unittest.TestCase):
    def setUp(self):
        # Testovi ne smiju pisati u pravi Redis iz .env.
        web_app.sessions = MemorySessionStore()
        self.client = app.test_client()

    def start(self, lang="hr"):
        res = self.client.post("/api/session", json={"lang": lang})
        self.assertEqual(res.status_code, 200)
        return res.get_json()

    def say(self, sid, message):
        return self.client.post("/api/chat", json={"session_id": sid, "message": message})

    def test_session_and_greeting(self):
        data = self.start("en")
        self.assertIn("virtual assistant", data["greeting"])
        self.assertEqual(data["mode"], "simulated")
        self.assertGreaterEqual(len(data["session_id"]), 16)

    def test_loan_conversation_and_csv(self):
        sid = self.start()["session_id"]
        self.assertIn("državljanin", self.say(sid, "gotovinski 15000 eur na 5 godina").get_json()["reply"])
        self.assertIn("292,02 EUR", self.say(sid, "da").get_json()["reply"])
        reply = self.say(sid, "pokaži otplatni plan").get_json()["reply"]
        self.assertIn(f"/api/schedule/{sid}.csv", reply)

        csv = self.client.get(f"/api/schedule/{sid}.csv")
        self.assertEqual(csv.status_code, 200)
        text = csv.get_data(as_text=True)
        self.assertIn("mjesec;rata;kamata;glavnica;ostatak", text)
        self.assertEqual(len(text.strip().splitlines()), 61)  # zaglavlje + 60 mjeseci

    def test_sessions_are_separate(self):
        a, b = self.start()["session_id"], self.start()["session_id"]
        self.say(a, "stambeni kredit")
        # Druga sesija ne zna da je prva pitala za stambeni kredit.
        self.assertIn("gotovinskom ili stambenom", self.say(b, "želim kredit").get_json()["reply"])

    def test_errors(self):
        self.assertEqual(self.say("nepostojeci", "bok").status_code, 410)
        sid = self.start()["session_id"]
        self.assertEqual(self.say(sid, "   ").status_code, 400)
        self.assertEqual(self.say(sid, "x" * 1001).status_code, 400)
        self.assertEqual(self.client.get("/api/schedule/nepostojeci.csv").status_code, 404)

    def test_serves_site_and_widget(self):
        for path, expected in [("/", b"Banka Demo"), ("/asistent.html", b"bankbot-page"), ("/widget/chat-widget.js", b"bankbot")]:
            with self.client.get(path) as res:
                self.assertEqual(res.status_code, 200)
                self.assertIn(expected, res.data)


if __name__ == "__main__":
    unittest.main()
