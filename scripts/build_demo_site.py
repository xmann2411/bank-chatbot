"""Gradi testnu web stranicu izmišljene Banke Demo d.d. u data/raw/web/.

Zaglavlje, izbornik i footer su isti na svim stranicama, pa se slažu iz jednog
predloška. Brojke su usklađene s data/rates.json i dokumentima u data/raw/.

    python -m scripts.build_demo_site

Stranicu s chatom pokrenite preko web servera:

    python -m web.app
    -> http://localhost:5000/

Chat prozor (/widget/chat-widget.js) radi samo preko tog servera jer treba API.
"""

from bankbot.config import RAW_DIR

WEB_DIR = RAW_DIR / "web"

NAV = [
    ("index.html", "Početna"),
    ("krediti.html", "Krediti"),
    ("racuni.html", "Računi"),
    ("kartice.html", "Kartice"),
    ("stednja.html", "Štednja"),
    ("digitalno-bankarstvo.html", "Demo mBank"),
    ("poslovnice.html", "Poslovnice"),
    ("o-nama.html", "O nama"),
]

LOGO = """<svg viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="10" fill="#0b2e4f"/>
<path d="M8 17 20 9l12 8v2H8z" fill="#f2b134"/><rect x="11" y="21" width="3" height="9" fill="#fff"/>
<rect x="18.5" y="21" width="3" height="9" fill="#fff"/><rect x="26" y="21" width="3" height="9" fill="#fff"/>
<rect x="8" y="31" width="24" height="2.5" fill="#fff"/></svg>"""

ICONS = {
    "loan": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h.01M18 12h.01"/></svg>',
    "house": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg>',
    "account": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 10 12 4l9 6"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/></svg>',
    "card": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/></svg>',
    "savings": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12a8 6 0 1 0 16 0 8 6 0 1 0-16 0"/><path d="M12 9v6M9.5 10.5h4a1.5 1.5 0 0 1 0 3h-3"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
}

TEMPLATE = """<!doctype html>
<html lang="hr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Banka Demo d.d.</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="css/style.css">
<link rel="stylesheet" href="/widget/chat-widget.css">{extra_head}
<script>/* analitika - scraper ovo izbacuje */ window.dataLayer = window.dataLayer || [];</script>
</head>
<body>
<div class="topbar"><div class="container">
  <span>Kontakt centar <a href="tel:08001234">0800 1234</a> · Blokada kartica 0-24 · <a href="asistent.html">Virtualni asistent</a></span>
  <span class="lang">Građani · Poslovni subjekti <a class="active" href="#">HR</a><a href="#">EN</a></span>
</div></div>
<header class="site"><div class="container">
  <a class="logo" href="index.html">{logo}<span>Banka Demo<small>d.d. · od 1995.</small></span></a>
  <nav class="main">{nav}</nav>
  <a class="btn btn-primary" href="digitalno-bankarstvo.html">Prijava</a>
</div></header>
<main>
{hero}
{body}
</main>
<footer class="site">
  <div class="container">
    <div class="cols">
      <div>
        <a class="logo" href="index.html" style="color:#fff">{logo}<span>Banka Demo</span></a>
        <p>Ilica 100, 10000 Zagreb<br>Kontakt centar: 0800 1234<br>info@bankademo.example</p>
      </div>
      <div><h4>Proizvodi</h4><ul>
        <li><a href="krediti.html">Krediti</a></li><li><a href="racuni.html">Tekući računi</a></li>
        <li><a href="kartice.html">Kartice</a></li><li><a href="stednja.html">Štednja</a></li></ul></div>
      <div><h4>Usluge</h4><ul>
        <li><a href="digitalno-bankarstvo.html">Demo mBank</a></li><li><a href="poslovnice.html">Poslovnice i bankomati</a></li>
        <li><a href="poslovnice.html#kontakt">Kontakt</a></li><li><a href="asistent.html">Virtualni asistent</a></li></ul></div>
      <div><h4>Banka</h4><ul>
        <li><a href="o-nama.html">O nama</a></li><li><a href="#">Kolačići</a></li>
        <li><a href="#">Zaštita osobnih podataka</a></li><li><a href="#">Uvjeti korištenja</a></li></ul></div>
    </div>
    <div class="legal">
      <span>© 2026 Banka Demo d.d. Sva prava pridržana.</span>
      <span>Banka Demo d.d. je izmišljena banka napravljena za demonstraciju chatbota.</span>
    </div>
  </div>
</footer>
<script src="/widget/chat-widget.js" defer></script>
</body>
</html>
"""


def page_hero(title, lead, crumb):
    return f"""<div class="page-hero"><div class="container">
  <div class="breadcrumb"><a href="index.html">Početna</a> / {crumb}</div>
  <h1>{title}</h1>
  <p>{lead}</p>
</div></div>"""


# ---------------------------------------------------------------------------
# Stranice
# ---------------------------------------------------------------------------

PAGES = {}

PAGES["index.html"] = dict(
    title="Početna",
    description="Banka Demo - krediti, računi, kartice i štednja za građane.",
    hero=f"""<div class="hero"><div class="container">
  <div>
    <span class="badge">Novo</span>
    <h1>Gotovinski kredit do 40.000 EUR uz fiksnu kamatnu stopu</h1>
    <p class="lead">Rata se ne mijenja do kraja otplate. Odluka isti ili idući radni dan, a postojeći klijenti kredit do 15.000 EUR mogu zatražiti izravno u aplikaciji Demo mBank.</p>
    <div class="actions">
      <a class="btn btn-gold" href="krediti.html#gotovinski">Saznajte više</a>
      <a class="btn btn-outline" href="asistent.html" data-bankbot="Želim izračunati ratu gotovinskog kredita">Izračunajte ratu</a>
    </div>
  </div>
  <div class="hero-card">
    <div>fiksna kamatna stopa već od</div>
    <div class="big">5,99 %</div>
    <ul>
      <li>iznos od 1.000 do 40.000 EUR</li>
      <li>rok otplate od 1 do 10 godina</li>
      <li>stopa ne ovisi o tome gdje primate plaću</li>
    </ul>
  </div>
</div></div>""",
    body=f"""<section><div class="container">
  <h2>Sve što trebate na jednom mjestu</h2>
  <p class="section-intro">Banka Demo je tu za građane od 1995. godine. Više od 250.000 klijenata koristi naše račune, kartice, kredite i štednju.</p>
  <div class="grid grid-4">
    <div class="card"><div class="icon">{ICONS['loan']}</div><h3>Krediti</h3><p>Gotovinski i stambeni krediti u eurima, uvijek s fiksnom kamatnom stopom.</p><a class="more" href="krediti.html">Krediti →</a></div>
    <div class="card"><div class="icon">{ICONS['account']}</div><h3>Tekući računi</h3><p>Paketi Osnovni i Plus. Za mlade do 27 godina i umirovljenike vođenje računa je besplatno.</p><a class="more" href="racuni.html">Računi →</a></div>
    <div class="card"><div class="icon">{ICONS['card']}</div><h3>Kartice</h3><p>Debitna kartica uz svaki račun i kreditna kartica Demo Classic.</p><a class="more" href="kartice.html">Kartice →</a></div>
    <div class="card"><div class="icon">{ICONS['savings']}</div><h3>Štednja</h3><p>Oročena štednja do 2,50 % godišnje i dječja štednja Demo Junior.</p><a class="more" href="stednja.html">Štednja →</a></div>
  </div>
</div></section>

<section class="alt"><div class="container">
  <div class="grid grid-4">
    <div class="stat"><div class="num">250.000+</div><div class="lbl">klijenata</div></div>
    <div class="stat"><div class="num">18</div><div class="lbl">poslovnica u Hrvatskoj</div></div>
    <div class="stat"><div class="num">140+</div><div class="lbl">bankomata</div></div>
    <div class="stat"><div class="num">0-24</div><div class="lbl">blokada kartica</div></div>
  </div>
</div></section>

<section><div class="container">
  <h2>Novosti</h2>
  <div class="grid grid-3">
    <div class="card"><div class="news-date">15. rujna 2026.</div><h3>Nova verzija aplikacije Demo mBank</h3><p>Kredit do 15.000 EUR sada možete zatražiti izravno u aplikaciji, ako plaću primate u Banci Demo.</p></div>
    <div class="card"><div class="news-date">1. rujna 2026.</div><h3>Nove kamatne stope na kredite</h3><p>Od 1. rujna 2026. vrijede nove fiksne kamatne stope za gotovinske i stambene kredite.</p><a class="more" href="krediti.html#kamatne-stope">Pogledajte stope →</a></div>
    <div class="card"><div class="news-date">20. kolovoza 2026.</div><h3>Poslovnica Split radi i subotom</h3><p>Poslovnica Split na Rivi otvorena je subotom od 8 do 12 sati.</p></div>
  </div>
</div></section>

<section><div class="container">
  <div class="cta">
    <div><h2>Trebate pomoć?</h2><p>Pitajte virtualnog asistenta, dostupan je 0-24. Kontakt centar 0800 1234 radi radnim danom od 8 do 20 sati, subotom od 8 do 14 sati.</p></div>
    <a class="btn btn-gold" href="asistent.html" data-bankbot="">Pitajte asistenta</a>
  </div>
</div></section>""",
)

PAGES["krediti.html"] = dict(
    title="Krediti",
    description="Gotovinski nenamjenski i stambeni krediti Banke Demo u eurima s fiksnom kamatnom stopom.",
    hero=page_hero("Krediti", "Gotovinski i stambeni krediti isključivo u eurima (EUR), s fiksnom kamatnom stopom i jednakim mjesečnim ratama.", "Krediti"),
    body=f"""<section id="gotovinski"><div class="container product">
  <div>
    <div class="icon" style="width:44px;height:44px;border-radius:12px;background:var(--teal-light);color:var(--teal);display:grid;place-items:center;margin-bottom:14px">{ICONS['loan']}</div>
    <h2>Gotovinski nenamjenski kredit</h2>
    <p>Sredstva koristite za što god trebate: kupnju automobila, putovanje, obrazovanje ili zatvaranje drugih obveza. Novac se isplaćuje na vaš tekući račun najkasnije dva radna dana nakon potpisa ugovora.</p>
    <ul class="check">
      <li>fiksna kamatna stopa za cijelo vrijeme otplate</li>
      <li>odluka isti ili idući radni dan uz potpunu dokumentaciju</li>
      <li>za kredite do 15.000 EUR dovoljna je zadužnica, bez jamca</li>
      <li>kredit mogu ugovoriti i osobe koje nisu državljani RH, uz dozvolu boravka i stalna primanja u RH</li>
      <li>datum dospijeća rate birate sami: 1., 10. ili 20. u mjesecu</li>
    </ul>
    <div class="notice">Za osobe koje nisu državljani Republike Hrvatske kamatna stopa je viša. Pogledajte tablicu kamatnih stopa niže.</div>
  </div>
  <div class="card">
    <ul class="facts">
      <li><span>Valuta</span><span>isključivo EUR</span></li>
      <li><span>Iznos</span><span>1.000 - 40.000 EUR</span></li>
      <li><span>Rok otplate</span><span>12 - 120 mjeseci</span></li>
      <li><span>Kamatna stopa</span><span>fiksna, od 5,99 %</span></li>
      <li><span>Naknada za obradu</span><span>1 %, min. 50 / maks. 300 EUR</span></li>
      <li><span>Dob klijenta</span><span>18 - 75 godina na kraju otplate</span></li>
    </ul>
  </div>
</div></section>

<section class="alt" id="stambeni"><div class="container product">
  <div>
    <div class="icon" style="width:44px;height:44px;border-radius:12px;background:#fff;color:var(--teal);display:grid;place-items:center;margin-bottom:14px">{ICONS['house']}</div>
    <h2>Stambeni kredit</h2>
    <p>Za kupnju, izgradnju, dogradnju ili adaptaciju stambene nekretnine u Hrvatskoj te za refinanciranje stambenog kredita u drugoj banci. Banka financira do 85 % procijenjene vrijednosti nekretnine.</p>
    <ul class="check">
      <li>fiksna kamatna stopa od 3,49 % za cijelo vrijeme otplate</li>
      <li>bez naknade za obradu kredita</li>
      <li>prijevremena otplata bez naknade</li>
      <li>odluka u roku od 5 radnih dana od predaje potpune dokumentacije</li>
    </ul>
    <div class="notice">Stambeni kredit mogu ugovoriti isključivo državljani Republike Hrvatske. Osobe koje nisu državljani RH mogu ugovoriti gotovinski nenamjenski kredit do 40.000 EUR.</div>
  </div>
  <div class="card">
    <ul class="facts">
      <li><span>Valuta</span><span>isključivo EUR</span></li>
      <li><span>Iznos</span><span>20.000 - 400.000 EUR</span></li>
      <li><span>Rok otplate</span><span>5 - 30 godina</span></li>
      <li><span>Kamatna stopa</span><span>fiksna, od 3,49 %</span></li>
      <li><span>Učešće</span><span>najmanje 15 %</span></li>
      <li><span>Osiguranje</span><span>hipoteka, polica osiguranja nekretnine, zadužnica</span></li>
    </ul>
  </div>
</div></section>

<section id="kamatne-stope"><div class="container">
  <h2>Kamatne stope</h2>
  <p class="section-intro">Sve kamatne stope su fiksne, nominalne i godišnje. Stopa ovisi o vrsti kredita, roku otplate, iznosu kredita i o tome je li klijent državljanin RH. Ne ovisi o tome u kojoj banci primate plaću. Vrijede od 1. rujna 2026.</p>

  <h3>Gotovinski nenamjenski kredit</h3>
  <div class="table-wrap"><table class="data">
    <tr><th>Rok otplate</th><th>Iznos</th><th>Državljani RH</th><th>Osobe koje nisu državljani RH</th></tr>
    <tr><td>do 36 mjeseci</td><td>do 10.000 EUR</td><td>6,49 %</td><td>7,69 %</td></tr>
    <tr><td>do 36 mjeseci</td><td>10.000,01 - 40.000 EUR</td><td>5,99 %</td><td>7,19 %</td></tr>
    <tr><td>37 - 84 mjeseca</td><td>do 10.000 EUR</td><td>6,79 %</td><td>7,99 %</td></tr>
    <tr><td>37 - 84 mjeseca</td><td>10.000,01 - 40.000 EUR</td><td>6,29 %</td><td>7,49 %</td></tr>
    <tr><td>85 - 120 mjeseci</td><td>do 10.000 EUR</td><td>7,19 %</td><td>8,39 %</td></tr>
    <tr><td>85 - 120 mjeseci</td><td>10.000,01 - 40.000 EUR</td><td>6,69 %</td><td>7,89 %</td></tr>
  </table></div>

  <h3 style="margin-top:32px">Stambeni kredit (samo državljani RH)</h3>
  <div class="table-wrap"><table class="data">
    <tr><th>Rok otplate</th><th>Iznos do 100.000 EUR</th><th>Iznos iznad 100.000 EUR</th></tr>
    <tr><td>60 - 180 mjeseci (5 - 15 godina)</td><td>3,69 %</td><td>3,49 %</td></tr>
    <tr><td>181 - 300 mjeseci (do 25 godina)</td><td>3,89 %</td><td>3,69 %</td></tr>
    <tr><td>301 - 360 mjeseci (do 30 godina)</td><td>4,09 %</td><td>3,89 %</td></tr>
  </table></div>
</div></section>

<section class="alt"><div class="container">
  <h2>Reprezentativni primjeri</h2>
  <div class="grid grid-2">
    <div class="example">
      <h3>Gotovinski kredit</h3>
      <ul class="facts">
        <li><span>Iznos kredita</span><span>15.000,00 EUR</span></li>
        <li><span>Rok otplate</span><span>60 mjeseci</span></li>
        <li><span>Fiksna kamatna stopa</span><span>6,29 %</span></li>
        <li><span>Mjesečna rata</span><span>292,02 EUR</span></li>
        <li><span>Ukupan iznos otplate</span><span>17.521,09 EUR</span></li>
        <li><span>Ukupna kamata</span><span>2.521,09 EUR</span></li>
      </ul>
      <small>Primjer za državljanina RH. Ukupni iznos ne uključuje naknadu za obradu.</small>
    </div>
    <div class="example">
      <h3>Stambeni kredit</h3>
      <ul class="facts">
        <li><span>Iznos kredita</span><span>120.000,00 EUR</span></li>
        <li><span>Rok otplate</span><span>240 mjeseci</span></li>
        <li><span>Fiksna kamatna stopa</span><span>3,69 %</span></li>
        <li><span>Mjesečna rata</span><span>707,72 EUR</span></li>
        <li><span>Ukupan iznos otplate</span><span>169.854,43 EUR</span></li>
        <li><span>Ukupna kamata</span><span>49.854,43 EUR</span></li>
      </ul>
      <small>Ukupni iznos ne uključuje troškove procjene nekretnine, javnog bilježnika i upisa hipoteke.</small>
    </div>
  </div>
</div></section>

<section><div class="container">
  <h2>Kako do kredita</h2>
  <div class="grid grid-4">
    <div class="card"><h3>1. Izračun</h3><p>Izračunajte ratu uz pomoć virtualnog asistenta ili u poslovnici.</p><a class="btn btn-primary" href="asistent.html" data-bankbot="Želim izračunati ratu kredita">Izračunajte ratu</a></div>
    <div class="card"><h3>2. Zahtjev</h3><p>Zahtjev predajte u poslovnici ili u aplikaciji Demo mBank.</p></div>
    <div class="card"><h3>3. Dokumentacija</h3><p>Osobna iskaznica, potvrda poslodavca o primanjima i, ako plaću ne primate kod nas, izvadak s računa za 3 mjeseca.</p></div>
    <div class="card"><h3>4. Isplata</h3><p>Gotovinski kredit isplaćujemo najkasnije 2 radna dana nakon potpisa ugovora.</p></div>
  </div>
  <div class="notice info">Banka Demo odobrava kredite isključivo u eurima, bez valutne klauzule. Kredit se ne odobrava s počekom otplate.</div>
</div></section>""",
)

PAGES["racuni.html"] = dict(
    title="Tekući računi",
    description="Tekući računi Banke Demo - paketi Osnovni i Plus, besplatno za mlade i umirovljenike.",
    hero=page_hero("Tekući računi", "Odaberite paket koji vam odgovara. Otvaranje računa je bez naknade, a račun možete otvoriti i ako niste državljanin Republike Hrvatske.", "Računi"),
    body="""<section><div class="container">
  <h2>Paketi tekućeg računa</h2>
  <div class="grid grid-3">
    <div class="card">
      <h3>Osnovni</h3>
      <p style="font-size:32px;font-weight:800;color:var(--navy);margin:8px 0">2,00 EUR<span style="font-size:15px;font-weight:500;color:var(--muted)"> / mj.</span></p>
      <ul class="check">
        <li>tekući račun u eurima</li>
        <li>internet i mobilno bankarstvo Demo mBank</li>
        <li>uplate u korist računa u Banci Demo bez naknade</li>
      </ul>
    </div>
    <div class="card" style="border:2px solid var(--teal)">
      <span class="badge">Najpopularnije</span>
      <h3>Plus</h3>
      <p style="font-size:32px;font-weight:800;color:var(--navy);margin:8px 0">4,50 EUR<span style="font-size:15px;font-weight:500;color:var(--muted)"> / mj.</span></p>
      <ul class="check">
        <li>sve iz paketa Osnovni</li>
        <li>debitna kartica bez godišnje članarine</li>
        <li>neograničene interne uplate</li>
      </ul>
    </div>
    <div class="card">
      <h3>Mladi i umirovljenici</h3>
      <p style="font-size:32px;font-weight:800;color:var(--navy);margin:8px 0">0,00 EUR<span style="font-size:15px;font-weight:500;color:var(--muted)"> / mj.</span></p>
      <ul class="check">
        <li>za mlade do 27 godina</li>
        <li>za umirovljenike koji primaju mirovinu u Banci Demo</li>
        <li>vođenje računa bez naknade</li>
      </ul>
    </div>
  </div>
</div></section>

<section class="alt"><div class="container">
  <h2>Kako otvoriti račun</h2>
  <p class="section-intro">Račun otvarate u bilo kojoj poslovnici. Potrebni su vam važeća osobna iskaznica ili putovnica i OIB.</p>
  <div class="notice info">Osobe koje nisu državljani Republike Hrvatske mogu otvoriti tekući račun uz važeću putovnicu ili osobnu iskaznicu i OIB.</div>
  <h3 style="margin-top:28px">Naknade u platnom prometu</h3>
  <div class="table-wrap"><table class="data">
    <tr><th>Usluga</th><th>Demo mBank</th><th>Poslovnica</th></tr>
    <tr><td>Uplata u korist računa u Banci Demo</td><td>bez naknade</td><td>1,00 EUR</td></tr>
    <tr><td>Uplata u korist računa u drugoj banci (nacionalna i SEPA)</td><td>0,20 EUR</td><td>2,00 EUR</td></tr>
    <tr><td>Trenutno plaćanje (instant)</td><td>0,20 EUR</td><td>2,00 EUR</td></tr>
    <tr><td>Plaćanje u stranoj valuti izvan SEPA područja</td><td>0,3 %, min. 10,00 EUR</td><td>0,5 %, min. 15,00 EUR</td></tr>
  </table></div>
  <p style="margin-top:16px;color:var(--muted)">Zatvaranje računa je bez naknade. Potvrda o stanju računa: 5,00 EUR.</p>
</div></section>

<section><div class="container">
  <h2>Prekoračenje po tekućem računu</h2>
  <p class="section-intro">Dozvoljeno prekoračenje može se odobriti do visine jedne neto plaće, najviše 3.000 EUR, klijentima koji plaću ili mirovinu primaju na račun u Banci Demo najmanje 3 mjeseca. Prekoračenje se ugovara na godinu dana uz automatsko produljenje.</p>
</div></section>""",
)

PAGES["kartice.html"] = dict(
    title="Kartice",
    description="Debitne i kreditne kartice Banke Demo, naknade, blokada kartice.",
    hero=page_hero("Kartice", "Plaćajte beskontaktno u trgovinama, na internetu i u inozemstvu. Karticu u svakom trenutku možete blokirati u aplikaciji.", "Kartice"),
    body=f"""<section><div class="container">
  <div class="grid grid-2">
    <div class="card">
      <div class="icon">{ICONS['card']}</div>
      <h3>Debitna kartica</h3>
      <p>Uz svaki tekući račun. Beskontaktno plaćanje, plaćanje na internetu i podizanje gotovine.</p>
      <ul class="facts">
        <li><span>Godišnja članarina</span><span>bez naknade uz paket Plus, inače 10,00 EUR</span></li>
        <li><span>Dnevni limit podizanja gotovine</span><span>1.000 EUR</span></li>
        <li><span>Dnevni limit plaćanja</span><span>3.000 EUR</span></li>
      </ul>
    </div>
    <div class="card">
      <div class="icon">{ICONS['card']}</div>
      <h3>Kreditna kartica Demo Classic</h3>
      <p>Plaćanje na rate bez kamata u partnerskim trgovinama i odgoda plaćanja do 45 dana.</p>
      <ul class="facts">
        <li><span>Godišnja članarina</span><span>25,00 EUR</span></li>
        <li><span>Okvir potrošnje</span><span>od 500 do 5.000 EUR</span></li>
        <li><span>Plaćanje na rate</span><span>2 - 24 rate bez kamata kod partnera</span></li>
      </ul>
    </div>
  </div>
</div></section>

<section class="alt"><div class="container">
  <h2>Naknade za kartice</h2>
  <div class="table-wrap"><table class="data">
    <tr><th>Usluga</th><th>Naknada</th></tr>
    <tr><td>Podizanje gotovine na bankomatima Banke Demo</td><td>bez naknade</td></tr>
    <tr><td>Podizanje gotovine na bankomatima drugih banaka u RH</td><td>1,50 EUR</td></tr>
    <tr><td>Podizanje gotovine u inozemstvu</td><td>2 %, min. 3,00 EUR</td></tr>
    <tr><td>Izrada nove kartice zbog gubitka ili krađe</td><td>7,00 EUR</td></tr>
    <tr><td>Promjena PIN-a na bankomatu Banke Demo</td><td>bez naknade</td></tr>
  </table></div>
</div></section>

<section><div class="container">
  <h2>Izgubljena ili ukradena kartica</h2>
  <div class="notice">Karticu odmah blokirajte u aplikaciji Demo mBank (Kartice &gt; Blokiraj karticu) ili pozivom na <strong>0800 1234</strong>, dostupno 0-24, svaki dan. Iz inozemstva nazovite <strong>+385 1 4000 123</strong>. Nova kartica izrađuje se u roku od 5 radnih dana.</div>
</div></section>""",
)

PAGES["stednja.html"] = dict(
    title="Štednja",
    description="Oročena štednja i dječja štednja Demo Junior u Banci Demo.",
    hero=page_hero("Štednja", "Oročena štednja u eurima s fiksnom kamatnom stopom. Depoziti su osigurani do 100.000 EUR po deponentu.", "Štednja"),
    body=f"""<section><div class="container">
  <h2>Oročena štednja</h2>
  <p class="section-intro">Kamatna stopa je fiksna za cijelo razdoblje oročenja. Minimalni iznos oročenja je 500,00 EUR, a kamata se isplaćuje na kraju oročenja.</p>
  <div class="grid grid-3">
    <div class="card stat"><div class="lbl">12 mjeseci</div><div class="num">2,00 %</div><div class="lbl">godišnje</div></div>
    <div class="card stat"><div class="lbl">24 mjeseca</div><div class="num">2,30 %</div><div class="lbl">godišnje</div></div>
    <div class="card stat"><div class="lbl">36 mjeseci</div><div class="num">2,50 %</div><div class="lbl">godišnje</div></div>
  </div>
  <div class="notice">Prijevremeni raskid oročenja: kamata se obračunava po stopi za sredstva na vidjelo (0,01 %).</div>
</div></section>

<section class="alt"><div class="container product">
  <div>
    <h2>Dječja štednja Demo Junior</h2>
    <p>Štedite za budućnost svog djeteta od rođenja do 18. godine.</p>
    <ul class="check">
      <li>kamatna stopa 2,50 % godišnje</li>
      <li>bez minimalnog iznosa uplate</li>
      <li>uplate u bilo kojem trenutku, i trajnim nalogom</li>
    </ul>
  </div>
  <div class="card">
    <div class="icon">{ICONS['shield']}</div>
    <h3>Vaš novac je siguran</h3>
    <p>Depoziti u Banci Demo osigurani su kod Hrvatske agencije za osiguranje depozita (HAOD) do 100.000,00 EUR po deponentu.</p>
  </div>
</div></section>""",
)

PAGES["digitalno-bankarstvo.html"] = dict(
    title="Digitalno bankarstvo",
    description="Mobilno i internet bankarstvo Demo mBank.",
    hero=page_hero("Demo mBank", "Mobilno i internet bankarstvo za sve klijente s tekućim računom, bez naknade.", "Digitalno bankarstvo"),
    body=f"""<section><div class="container">
  <div class="grid grid-3">
    <div class="card"><div class="icon">{ICONS['phone']}</div><h3>Plaćanja</h3><p>Plaćanje računa skeniranjem barkoda, trenutna plaćanja i trajni nalozi.</p></div>
    <div class="card"><div class="icon">{ICONS['card']}</div><h3>Upravljanje karticama</h3><p>Blokada i deblokada kartice, promjena limita i pregled PIN-a.</p></div>
    <div class="card"><div class="icon">{ICONS['loan']}</div><h3>Kredit u aplikaciji</h3><p>Klijenti koji primaju plaću u Banci Demo mogu zatražiti gotovinski kredit do 15.000 EUR izravno u aplikaciji.</p></div>
  </div>
</div></section>

<section class="alt"><div class="container">
  <h2>Kako aktivirati Demo mBank</h2>
  <div class="grid grid-3">
    <div class="card"><h3>1. Preuzmite aplikaciju</h3><p>Aplikaciju Demo mBank preuzmite s Google Play ili App Store trgovine.</p></div>
    <div class="card"><h3>2. Aktivacijski kod</h3><p>Aktivacijski kod dobivate u poslovnici ili putem internet bankarstva.</p></div>
    <div class="card"><h3>3. Postavite PIN</h3><p>Postavite PIN za aplikaciju i po želji prijavu otiskom prsta ili licem.</p></div>
  </div>
  <div class="notice info">Banka Demo nikad neće tražiti vaš PIN, lozinku ili aktivacijski kod putem e-maila, SMS-a ili telefona.</div>
</div></section>""",
)

PAGES["poslovnice.html"] = dict(
    title="Poslovnice i kontakt",
    description="Popis poslovnica Banke Demo, radno vrijeme, bankomati i kontakt.",
    hero=page_hero("Poslovnice i kontakt", "18 poslovnica diljem Hrvatske i više od 140 bankomata dostupnih 0-24.", "Poslovnice i kontakt"),
    body=f"""<section><div class="container">
  <h2>Poslovnice i radno vrijeme</h2>
  <div class="table-wrap"><table class="data">
    <tr><th>Poslovnica</th><th>Adresa</th><th>Radno vrijeme</th></tr>
    <tr><td>Zagreb - Centar</td><td>Ilica 100, Zagreb</td><td>pon-pet 8:00-19:00, sub 8:00-12:00</td></tr>
    <tr><td>Zagreb - Novi Zagreb</td><td>Avenija Dubrovnik 15, Zagreb</td><td>pon-pet 8:00-19:00</td></tr>
    <tr><td>Zagreb - Dubrava</td><td>Avenija Dubrava 40, Zagreb</td><td>pon-pet 8:00-16:00</td></tr>
    <tr><td>Split</td><td>Riva 5, Split</td><td>pon-pet 8:00-19:00, sub 8:00-12:00</td></tr>
    <tr><td>Rijeka</td><td>Korzo 20, Rijeka</td><td>pon-pet 8:00-16:00</td></tr>
    <tr><td>Osijek</td><td>Europska avenija 8, Osijek</td><td>pon-pet 8:00-16:00</td></tr>
    <tr><td>Zadar</td><td>Široka ulica 3, Zadar</td><td>pon-pet 8:00-16:00</td></tr>
    <tr><td>Pula</td><td>Giardini 2, Pula</td><td>pon-pet 8:00-16:00</td></tr>
    <tr><td>Varaždin</td><td>Trg kralja Tomislava 6, Varaždin</td><td>pon-pet 8:00-16:00</td></tr>
    <tr><td>Dubrovnik</td><td>Ulica Vukovarska 11, Dubrovnik</td><td>pon-pet 8:00-16:00</td></tr>
  </table></div>
  <p style="margin-top:16px;color:var(--muted)">Na blagdane i neradne dane poslovnice ne rade. Bankomati Banke Demo dostupni su 0-24 na svim lokacijama poslovnica te na više od 120 drugih lokacija.</p>
</div></section>

<section class="alt" id="kontakt"><div class="container">
  <h2>Kontakt</h2>
  <div class="grid grid-3">
    <div class="card"><div class="icon">{ICONS['phone']}</div><h3>Kontakt centar</h3><p><strong>0800 1234</strong> (besplatan poziv)<br>radnim danom od 8 do 20 sati<br>subotom od 8 do 14 sati</p></div>
    <div class="card"><div class="icon">{ICONS['shield']}</div><h3>Blokada kartica</h3><p><strong>0800 1234</strong>, dostupno 0-24<br>iz inozemstva: <strong>+385 1 4000 123</strong></p></div>
    <div class="card"><div class="icon">{ICONS['pin']}</div><h3>Sjedište</h3><p>Ilica 100, 10000 Zagreb<br>info@bankademo.example</p></div>
  </div>
</div></section>""",
)

PAGES["o-nama.html"] = dict(
    title="O nama",
    description="O Banci Demo d.d. - povijest, podaci o banci i nadzor.",
    hero=page_hero("O nama", "Banka Demo d.d. osnovana je 1995. godine u Zagrebu kao banka usmjerena na građane.", "O nama"),
    body="""<section><div class="container product">
  <div>
    <h2>Naša priča</h2>
    <p>Banka Demo d.d. osnovana je 1995. godine u Zagrebu. Danas ima više od 250.000 klijenata i 18 poslovnica diljem Hrvatske. Usmjereni smo na građane: tekuće račune, kartice, kredite i štednju.</p>
    <p>Svi naši krediti odobravaju se isključivo u eurima, s fiksnom kamatnom stopom, jer vjerujemo da klijent od prvog dana treba znati koliko će plaćati do kraja otplate.</p>
    <p>Banka je pod nadzorom Hrvatske narodne banke. Depoziti su osigurani kod Hrvatske agencije za osiguranje depozita (HAOD) do 100.000,00 EUR po deponentu.</p>
  </div>
  <div class="card">
    <h3>Podaci o banci</h3>
    <ul class="facts">
      <li><span>Naziv</span><span>Banka Demo d.d.</span></li>
      <li><span>Sjedište</span><span>Ilica 100, 10000 Zagreb</span></li>
      <li><span>OIB</span><span>12345678901</span></li>
      <li><span>SWIFT/BIC</span><span>DEMOHR2X</span></li>
      <li><span>Nadzorno tijelo</span><span>Hrvatska narodna banka</span></li>
    </ul>
  </div>
</div></section>""",
)


PAGES["asistent.html"] = dict(
    title="Virtualni asistent",
    description="Virtualni asistent Banke Demo: pitanja o banci, izračun rate kredita i tečajna lista.",
    # Stranica nema sadržaja za bazu znanja, pa je scraper preskače.
    extra_head='\n<meta name="robots" content="noindex, follow">',
    hero=page_hero("Virtualni asistent", "Pitajte nas o računima, karticama i štednji, izračunajte mjesečnu ratu kredita ili provjerite tečaj. Dostupno 0-24.", "Virtualni asistent"),
    body="""<section class="alt"><div class="container"><div id="bankbot-page"></div></div></section>""",
)


def build():
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    for filename, page in PAGES.items():
        nav = "".join(
            f'<a href="{href}"{" class=\"active\"" if href == filename else ""}>{label}</a>' for href, label in NAV
        )
        html = TEMPLATE.format(
            title=page["title"], description=page["description"], logo=LOGO, nav=nav, hero=page["hero"], body=page["body"],
            extra_head=page.get("extra_head", ""),
        )
        (WEB_DIR / filename).write_text(html, encoding="utf-8", newline="\n")
        print("  zapisano:", filename)


if __name__ == "__main__":
    build()
