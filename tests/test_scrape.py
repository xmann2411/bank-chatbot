import unittest

from scripts.scrape import crawl, html_to_markdown


class ScrapeTest(unittest.TestCase):
    def test_crawl_finds_all_subpages(self):
        pages = crawl("data/raw/web/index.html", max_pages=30)
        names = {url.rsplit("/", 1)[-1] for url, _ in pages}
        self.assertEqual(
            names,
            {"index.html", "krediti.html", "racuni.html", "kartice.html", "stednja.html",
             "digitalno-bankarstvo.html", "poslovnice.html", "o-nama.html", "asistent.html"},
        )

    def test_markdown_keeps_content_and_drops_noise(self):
        html = """<html><head><title>T</title><script>x()</script></head><body>
        <nav>Izbornik</nav><main><div class="breadcrumb">Početna / X</div>
        <h1>Naslov</h1><ul class="facts"><li><span>Valuta</span><span>EUR</span></li></ul>
        <a class="btn" href="#">Saznajte više</a></main><footer>Footer</footer></body></html>"""
        title, md = html_to_markdown(html)
        self.assertEqual(title, "T")
        self.assertIn("# Naslov", md)
        self.assertIn("Valuta: EUR", md)
        for noise in ("Izbornik", "Footer", "Početna /", "Saznajte", "x()"):
            self.assertNotIn(noise, md)


if __name__ == "__main__":
    unittest.main()
