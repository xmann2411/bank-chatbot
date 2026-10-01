"""Web stranice -> markdown u data/knowledge/, pa ponovna izgradnja indeksa.

Popis stranica je u data/sources.json. Svaka stavka ima:
  "url"        http/https adresa ili lokalna .html datoteka relativno na korijen projekta
  "name"       prefiks za nazive .md datoteka
  "crawl"      (opcionalno) true = prati linkove na iste stranice i pokupi i podstranice
  "max_pages"  (opcionalno) najviše stranica po izvoru, zadano 30

    python -m scripts.scrape
"""

import json
import time
from collections import deque
from pathlib import PurePosixPath
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

from bankbot.config import ROOT, SOURCES_FILE
from bankbot.retrieval import build_index
from scripts.common import write_markdown

USER_AGENT = "BankaDemoChatbot/1.0 (interni scraper baze znanja)"
DELAY_SECONDS = 1.0

# Dijelovi stranice koji nisu sadržaj.
STRIP_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "form", "button", "svg"]
# CSS klase koje obično označavaju navigaciju i gumbe ("Saznajte više →"), a ne sadržaj.
STRIP_CLASSES = ("breadcrumb", "btn", "more", "cookie", "banner", "badge", "topbar")


def allowed_by_robots(url):
    parts = urlparse(url)
    rp = RobotFileParser()
    rp.set_url(urljoin(f"{parts.scheme}://{parts.netloc}", "/robots.txt"))
    try:
        rp.read()
    except OSError:
        return True  # nema robots.txt ili nije dostupan
    return rp.can_fetch(USER_AGENT, url)


def fetch(url):
    if url.startswith(("http://", "https://")):
        if not allowed_by_robots(url):
            raise PermissionError(f"robots.txt ne dopušta: {url}")
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        res.raise_for_status()
        res.encoding = res.apparent_encoding or res.encoding
        return res.text
    return (ROOT / url).read_text(encoding="utf-8")


def is_remote(url):
    return url.startswith(("http://", "https://"))


def internal_links(html, page_url):
    """Linkovi na druge stranice istog sitea (bez sidra, bez vanjskih adresa)."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if is_remote(page_url):
            target = urldefrag(urljoin(page_url, href))[0]
            if urlparse(target).netloc != urlparse(page_url).netloc:
                continue
        else:
            if is_remote(href):
                continue
            base = PurePosixPath(page_url).parent
            target = str(base / urldefrag(href)[0])
            if not target.endswith(".html"):
                continue
        links.append(target)
    return links


def page_name(url):
    path = urlparse(url).path if is_remote(url) else url
    stem = PurePosixPath(path).stem or "index"
    return stem


def crawl(start, max_pages):
    """Obilazi stranice u širinu počevši od start. Vraća [(url, html)]."""
    seen, queue, pages = {start}, deque([start]), []
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        try:
            html = fetch(url)
        except Exception as e:  # jedna loša stranica ne smije srušiti cijeli scrape
            print(f"  ! {url}: {e}")
            continue
        pages.append((url, html))
        for link in internal_links(html, url):
            if link not in seen:
                seen.add(link)
                queue.append(link)
        if is_remote(url) and queue:
            time.sleep(DELAY_SECONDS)
    return pages


def _flatten_short_blocks(root):
    """Kratke blokove sastavljene od nekoliko <span>/<div> spaja u jedan redak.

    Npr. <li><span>Valuta</span><span>EUR</span></li> bi inače postao "ValutaEUR",
    a kartica <div>12 mjeseci</div><div>2,00 %</div> tri odvojena retka.
    """
    for el in root.find_all(["li", "div"]):
        children = [c for c in el.children if getattr(c, "name", None)]
        loose_text = "".join(c for c in el.children if isinstance(c, str)).strip()
        if (
            2 <= len(children) <= 4
            and not loose_text
            and all(c.name in ("span", "div", "strong") and not c.find(["div", "ul", "table", "p", "h1", "h2", "h3"]) for c in children)
            and len(el.get_text(strip=True)) < 120
        ):
            parts = [c.get_text(" ", strip=True) for c in children]
            el.string = ": ".join(parts) if len(parts) == 2 else " ".join(parts)


def is_noindex(html):
    """Stranica s <meta name="robots" content="noindex"> ne ide u bazu znanja (linkove i dalje pratimo)."""
    meta = BeautifulSoup(html, "html.parser").find("meta", attrs={"name": "robots"})
    return bool(meta and "noindex" in meta.get("content", "").lower())


def html_to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(STRIP_TAGS):
        tag.decompose()
    for tag in soup.find_all(class_=lambda c: c and any(x in c for x in STRIP_CLASSES)):
        tag.decompose()
    content = soup.find("main") or soup.find("article") or soup.body or soup
    _flatten_short_blocks(content)
    md = markdownify(str(content), heading_style="ATX", bullets="-", strip=["a", "img"])
    return title, md


def main():
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    for src in sources:
        if src.get("crawl"):
            pages = crawl(src["url"], src.get("max_pages", 30))
        else:
            try:
                pages = [(src["url"], fetch(src["url"]))]
            except Exception as e:
                print(f"  ! {src['url']}: {e}")
                pages = []
        for url, html in pages:
            if is_noindex(html):
                print("  preskočeno (noindex):", url)
                continue
            title, md = html_to_markdown(html)
            path = write_markdown(f"web-{src['name']}-{page_name(url)}", title or src["name"], url, "web", md)
            print("  zapisano:", path.name)
    chunks = build_index()
    print(f"Indeks: {len(chunks)} chunkova.")


if __name__ == "__main__":
    main()
