import unittest

from bankbot import spelling
from bankbot.clarify import pick_option


class SpellingTest(unittest.TestCase):
    def test_sure_corrections(self):
        cases = {
            "kako blokirat kartcu": "karticu",
            "stamebni kerdit": "stambeni kredit",  # zamijenjena susjedna slova
            "koji je tecja dolara": "tecaj",
            "gotovniski kredt na 5 godna": "gotovinski kredit na 5 godina",
            "100 mjeseciiiiii": "100 mjeseci",
            "hvla": "hvala",
        }
        for text, expected in cases.items():
            sure, _, _ = spelling.correct(text)
            self.assertIn(expected, sure, text)

    def test_leaves_valid_words_alone(self):
        for text in ["radno vrijeme poslovnice u Splitu", "koliko je sati u Tokiju", "tko je predsjednik države",
                     "recept za palačinke", "koliko kosta kreditna kartica"]:
            sure, unsure, changes = spelling.correct(text)
            self.assertEqual(sure, text, changes)
            self.assertIsNone(unsure, text)

    def test_unsure_correction_is_only_suggested(self):
        sure, unsure, _ = spelling.correct("oročnje štednje")
        self.assertEqual(sure, "oročnje štednje")
        self.assertEqual(unsure, "oročenja štednje")


class PickOptionTest(unittest.TestCase):
    OPTIONS = [{"label": "Izračun mjesečne rate", "message": "a"}, {"label": "Uvjeti i kamatne stope", "message": "b"}]

    def test_by_number_word_and_label(self):
        self.assertEqual(pick_option("2", self.OPTIONS)["message"], "b")
        self.assertEqual(pick_option("prvo", self.OPTIONS)["message"], "a")
        self.assertEqual(pick_option("Uvjeti i kamatne stope", self.OPTIONS)["message"], "b")
        self.assertEqual(pick_option("izracun mjesecne rate", self.OPTIONS)["message"], "a")

    def test_yes_only_for_single_option(self):
        self.assertIsNone(pick_option("da", self.OPTIONS))
        self.assertEqual(pick_option("da", self.OPTIONS[:1])["message"], "a")

    def test_unrelated_message(self):
        self.assertIsNone(pick_option("koji je tečaj dolara", self.OPTIONS))


if __name__ == "__main__":
    unittest.main()
