import unittest

from bankbot import nlu


class AmountTest(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(nlu.extract_amount("trebam 10.000 eura"), (10000, "EUR"))
        self.assertEqual(nlu.extract_amount("15k eur"), (15000, "EUR"))
        self.assertEqual(nlu.extract_amount("150 tisuća"), (150000, None))
        self.assertEqual(nlu.extract_amount("10,000 USD"), (10000, "USD"))
        self.assertEqual(nlu.extract_amount("€ 2500"), (2500, "EUR"))
        self.assertEqual(nlu.extract_amount("5000 dolara"), (5000, "USD"))

    def test_term_is_not_amount(self):
        p = nlu.extract_loan_params("gotovinski 20000 eur na 5 godina")
        self.assertEqual(p["amount"], 20000)
        self.assertEqual(p["months"], 60)
        self.assertEqual(p["loan_type"], "gotovinski")


class SlotAnswerTest(unittest.TestCase):
    def test_short_answers_use_awaiting(self):
        self.assertEqual(nlu.extract_loan_params("da", "client_type")["client_type"], "drzavljanin")
        self.assertEqual(nlu.extract_loan_params("ne", "client_type")["client_type"], "nedrzavljanin")
        self.assertEqual(nlu.extract_loan_params("5", "months")["months"], 60)
        self.assertEqual(nlu.extract_loan_params("84", "months")["months"], 84)
        self.assertEqual(nlu.extract_loan_params("20000", "amount")["amount"], 20000)

    def test_client_type(self):
        self.assertEqual(nlu.extract_client_type("nisam hrvatski državljanin"), "nedrzavljanin")
        self.assertEqual(nlu.extract_client_type("ja sam stranac"), "nedrzavljanin")
        self.assertEqual(nlu.extract_client_type("I'm not a Croatian citizen"), "nedrzavljanin")
        self.assertEqual(nlu.extract_client_type("jesam, državljanin sam"), "drzavljanin")


class IntentTest(unittest.TestCase):
    def test_intents(self):
        cases = {
            "bok": "greeting",
            "koliko bi bila rata za kredit od 10000 eura": "loan_calc",
            "gotovinski 5000 eur na 2 godine": "loan_calc",
            "koji je tečaj dolara": "fx",
            "koliko je 100 USD u eurima": "fx",
            "koje je radno vrijeme poslovnica": "info",
            "koji su uvjeti za stambeni kredit": "info",
            "how much is the monthly payment for a 20000 EUR loan": "loan_calc",
        }
        for text, intent in cases.items():
            self.assertEqual(nlu.classify_intent(text), intent, text)

    def test_details_only_after_result(self):
        self.assertEqual(nlu.classify_intent("koliko ću ukupno platiti", {"has_result": True}), "loan_details")

    def test_language(self):
        self.assertEqual(nlu.detect_language("Koliko je rata?"), "hr")
        self.assertEqual(nlu.detect_language("What is the monthly payment?"), "en")
        self.assertEqual(nlu.detect_language("5", default="en"), "en")


if __name__ == "__main__":
    unittest.main()
