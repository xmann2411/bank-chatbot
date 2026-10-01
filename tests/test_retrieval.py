import unittest

from bankbot import retrieval


def top_section(query):
    hits = retrieval.search(query)
    return hits[0].chunk["section"].split(" > ")[-1] if hits else None


class RetrievalTest(unittest.TestCase):
    def test_top_hit(self):
        cases = {
            "koje je radno vrijeme poslovnice u Splitu": "Poslovnice i radno vrijeme",
            "kako blokirati izgubljenu karticu": "Kako mogu blokirati izgubljenu ili ukradenu karticu?",
            "koja je kamata na oročenu štednju": "Oročena štednja",
            "koja dokumentacija treba za stambeni kredit": "Potrebna dokumentacija",
            "kolika je naknada za vođenje tekućeg računa": "Tekući račun",
        }
        for query, section in cases.items():
            self.assertEqual(top_section(query), section, query)

    def test_relevant_chunk_among_top3(self):
        hits = retrieval.search("naknada za prijevremenu otplatu gotovinskog kredita")
        self.assertIn("Naknade", [h.chunk["section"].split(" > ")[-1] for h in hits])

    def test_english_query(self):
        q = retrieval.translate_query("What are the branch opening hours?")
        self.assertEqual(top_section(q), "Poslovnice i radno vrijeme")

    def test_returns_at_most_three(self):
        self.assertLessEqual(len(retrieval.search("kredit naknada kartica račun")), 3)

    def test_out_of_scope(self):
        self.assertEqual(retrieval.search("koliko je sati u Tokiju"), [])
        self.assertEqual(retrieval.search("tko je osvojio svjetsko prvenstvo"), [])

    def test_chunking_keeps_headings(self):
        md = "---\nnaslov: Test\nizvor: test.pdf\n---\n# Naslov\n\nuvod\n\n## Sekcija A\n\ntekst a\n\n## Sekcija B\n\ntekst b"
        chunks = retrieval.chunk_markdown(md, "test.md")
        self.assertEqual([c["section"] for c in chunks], ["Naslov", "Naslov > Sekcija A", "Naslov > Sekcija B"])
        self.assertTrue(all(c["source"] == "test.pdf" for c in chunks))


if __name__ == "__main__":
    unittest.main()
