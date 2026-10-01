"""Cijeli razgovori u simuliranom modu. Tečajna lista je lažna da testovi ne ovise o mreži."""

import unittest
from unittest import mock

from bankbot import fx, llm
from bankbot.agent import Conversation, reply

FAKE_RATES = {
    "USD": {"valuta": "USD", "drzava": "SAD", "kupovni": 1.14, "srednji": 1.1355, "prodajni": 1.13, "datum": "2026-09-30"},
    "CHF": {"valuta": "CHF", "drzava": "Švicarska", "kupovni": 0.95, "srednji": 0.9461, "prodajni": 0.94, "datum": "2026-09-30"},
}


def chat(*messages):
    state = Conversation()
    answers = [reply(m, state) for m in messages]
    return answers, state


@mock.patch.object(llm, "MODE", "simulated")
@mock.patch.object(fx, "get_rates", lambda day=None: FAKE_RATES)
class ConversationTest(unittest.TestCase):
    def test_cash_loan_flow(self):
        answers, state = chat("gotovinski kredit 15000 eura na 5 godina", "da")
        self.assertIn("Jeste li državljanin", answers[0])
        self.assertIn("292,02 EUR", answers[1])
        self.assertIn("6,29 %", answers[1])

    def test_asks_missing_slots_in_order(self):
        answers, _ = chat("želim kredit", "stambeni", "150000", "25 godina", "da")
        self.assertIn("gotovinskom ili stambenom", answers[0])
        self.assertIn("iznos", answers[1])
        self.assertIn("rok", answers[2])
        self.assertIn("državljanin", answers[3])
        self.assertIn("Mjesečna rata", answers[4])

    def test_non_citizen_housing_is_refused_politely(self):
        answers, state = chat("stambeni kredit 100000 eura na 20 godina", "nisam državljanin")
        self.assertIn("samo državljani Republike Hrvatske", answers[1])
        self.assertIn("gotovinski", answers[1])
        # Klijent prihvaća gotovinski; iznos je prevelik pa ga bot pita za novi.
        answers2 = [reply("da", state), reply("30000", state)]
        self.assertIn("od 1.000,00 EUR do 40.000,00 EUR", answers2[0])
        self.assertIn("rok od", answers2[1].lower())  # 20 godina je predugo za gotovinski

    def test_out_of_range_reported_immediately(self):
        answers, _ = chat("gotovinski 50000 eur")
        self.assertIn("nije moguć", answers[0])

    def test_foreign_currency_loan_offers_conversion(self):
        answers, state = chat("I need a cash loan of 10000 dollars for 4 years", "yes", "yes I am")
        self.assertIn("euros (EUR) only", answers[0])
        self.assertIn("8,806.69 EUR", answers[0])
        self.assertIn("Monthly payment", answers[2])
        self.assertEqual(state.last_result.amount, 8807)

    def test_details_and_schedule(self):
        answers, _ = chat("gotovinski 15000 eur na 5 godina", "da", "koliko ću ukupno platiti", "da")
        self.assertIn("17.521,09 EUR", answers[2])
        self.assertIn("Otplatni plan", answers[3])

    def test_details_after_step_by_step_calculation(self):
        # Razgovor koji je prije završio u pretrazi dokumentacije umjesto u kalkulatoru.
        answers, _ = chat("mjesecna rata", "gotovinski", "1200", "100 mjeseciiiiii", "da", "daj ukupan iznos otplate")
        self.assertIn("15,99 EUR", answers[4])
        self.assertIn("ukupno ćete otplatiti", answers[5])
        self.assertIn("1.200,00 EUR", answers[5])
        self.assertNotIn("dokumentaciji", answers[5])

    def test_yes_after_result_shows_details(self):
        answers, _ = chat("gotovinski 15000 eur na 5 godina", "da", "da", "da")
        self.assertIn("17.521,09 EUR", answers[2])
        self.assertIn("Otplatni plan", answers[3])

    def test_no_after_result(self):
        answers, _ = chat("gotovinski 15000 eur na 5 godina", "da", "ne hvala")
        self.assertIn("Nema na čemu", answers[2])

    def test_change_term_after_result(self):
        answers, state = chat("gotovinski 15000 eur na 5 godina", "da", "a na 3 godine?")
        self.assertIn("456,26 EUR", answers[2])

    def test_fx_rate_then_amount(self):
        answers, _ = chat("koji je tečaj franka", "250")
        self.assertIn("CHF", answers[0])
        self.assertIn("preračunam", answers[0])
        self.assertIn("264,24 EUR", answers[1])

    def test_fx_conversion(self):
        answers, _ = chat("koliko je 500 eura u dolarima")
        self.assertIn("567,75 USD", answers[0])

    def test_info_question(self):
        answers, _ = chat("kako mogu blokirati karticu?")
        self.assertIn("0800 1234", answers[0])
        self.assertIn("Izvor", answers[0])

    def test_out_of_scope(self):
        answers, _ = chat("koliko je sati u Tokiju?")
        self.assertIn("nemam informaciju", answers[0])

    def test_english(self):
        answers, state = chat("Hello", "What documents do I need for a housing loan?")
        self.assertEqual(state.lang, "en")
        self.assertIn("virtual assistant", answers[0])
        self.assertIn("Potrebna dokumentacija", answers[1])


if __name__ == "__main__":
    unittest.main()
