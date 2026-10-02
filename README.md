# Banka Demo – chatbot

[![Testovi](https://github.com/xmann2411/bank-chatbot/actions/workflows/tests.yml/badge.svg)](https://github.com/xmann2411/bank-chatbot/actions/workflows/tests.yml)

Chatbot za izmišljenu banku "Banka Demo d.d.". Zna tri stvari:

1. **odgovoriti na pitanja o banci** – iz dokumentacije (PDF, Word, web stranice)
2. **izračunati mjesečnu ratu** gotovinskog ili stambenog kredita (samo EUR)
3. **tečajnu listu HNB-a** i preračun iznosa između valuta

Radi na hrvatskom i engleskom.

## Pokretanje

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (na Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python chat.py
```

Baza znanja je već napunjena (`data/knowledge/`), pa chat radi odmah.

## Web sučelje

```bash
python -m web.app
```

Otvorite http://localhost:5000/. Dobit ćete web stranicu Banke Demo s chat prozorom u donjem desnom kutu na svakoj stranici. Na stranici **Virtualni asistent** (`/asistent.html`) chat je preko cijele stranice.

- Razgovor ostaje kad klijent prelazi s jedne stranice na drugu (pamti se u `sessionStorage` preglednika).
- Na početku razgovora nude se prijedlozi pitanja. Gumbi "Izračunajte ratu" na stranici otvaraju chat i odmah pošalju pitanje; to je atribut `data-bankbot` na linku.
- Tablice (otplatni plan, naknade) prikazuju se kao prave tablice. Otplatni plan po mjesecima može se preuzeti kao CSV.
- Na mobitelu se chat otvara preko cijelog zaslona.
- Oznaka "demo način" u zaglavlju chata znači da nema API ključa.

API (`web/app.py`):

| | |
|---|---|
| `POST /api/session` | novi razgovor → `{session_id, greeting, mode}` |
| `POST /api/chat` | `{session_id, message}` → `{reply}` |
| `GET /api/schedule/<session_id>.csv` | otplatni plan zadnjeg izračuna |
| `GET /api/health` | gdje se spremaju sesije (`redis` / `memory`) |

Nakon 30 minuta neaktivnosti razgovor se briše i na serveru i u pregledniku, pa klijent dobiva novi razgovor s napomenom da je prethodni završen. Unutar tih 30 minuta razgovor ostaje i nakon osvježavanja stranice i prelaska na druge stranice.

### Spremanje razgovora u Redis

Stanje razgovora sprema se u Redis ako je u `.env` postavljen `REDIS_URL`. To uključuje skupljene podatke za kredit, zadnji izračun, otvoreno pitanje bota i povijest poruka. Takav razgovor preživi restart web servera, a isti Redis može koristiti i više procesa ili servera.

```bash
docker compose up -d                       # Redis u Dockeru (docker-compose.yml)
```

Zatim u `.env` postavite `REDIS_URL=redis://localhost:6379/0` i pokrenite server. `GET /api/health` pokazuje gdje se sesije spremaju (`redis` ili `memory`).

- Svaki razgovor je jedan JSON pod ključem `bankbot:session:<id>`, s rokom od 30 minuta koji se produži kod svake poruke.
- Otplatni plan se ne sprema; kod učitavanja se ponovno izračuna iz iznosa, roka i stope. Sprema se zadnjih 40 poruka.
- Dvije poruke istog razgovora ne obrađuju se istovremeno (Redis lock).
- Bez `REDIS_URL`, ili ako Redis nije dostupan kod pokretanja, sesije se drže u memoriji servera i server to ispiše kao upozorenje.

Za produkciju bi još trebao pravi WSGI server (npr. `waitress`) umjesto Flaskovog razvojnog servera.

## Simulirani i pravi mod

Kao u recovery agentu, `bankbot/llm.py` ima dva moda:

- **bez API ključa (simulirani mod)**:
  - namjera i parametri se prepoznaju pravilima (`nlu.py`);
  - odgovori o banci slažu se iz dohvaćenih dijelova dokumentacije;
  - tekstovi kalkulatora i tečaja su predlošci (`texts.py`).
- **s ključem**: kopirajte `.env.example` u `.env` i upišite `ANTHROPIC_API_KEY=...`. LLM onda:
  - prepoznaje namjeru;
  - izvlači parametre kredita iz slobodnog teksta;
  - preformulira pitanje za pretragu;
  - piše odgovor iz 3 dohvaćena chunka.

Model se bira u `.env` (`ANTHROPIC_MODEL`, zadano `claude-opus-5-5`).

Ako model ne odgovori (mreža, limit, neispravan ključ), bot se za taj korak vrati na simulirani mod, pa uvijek nešto odgovori.

**Brojeve nikad ne računa LLM.** Kamatna stopa dolazi iz `data/rates.json`, a rata iz formule u `calculator.py`. LLM samo izvlači iznos, rok, vrstu kredita i državljanstvo iz poruke.

## Kako se puni baza znanja

Bot ne čita PDF-ove i Word dokumente izravno. Prvo se svi izvori pretvore u markdown, a bot poslije pretražuje samo taj markdown.

```
data/raw/pdf/*.pdf     ─┐
data/raw/docx/*.docx   ─┼─ python -m scripts.ingest ─┐
                        │                             ├─> data/knowledge/*.md ─> data/index.json (chunkovi)
data/sources.json (URL) ─── python -m scripts.scrape ─┘
```

- **`scripts/ingest.py`** čita PDF i Word dokumente i sprema ih kao `.md`. Naslovi ostaju naslovi, a tablice ostaju tablice.
- **`scripts/scrape.py`** je posebna skripta za web. Kreće od adrese iz `data/sources.json` i, ako je uključen `"crawl": true`, sama prati linkove na podstranice istog sitea. S njih miče izbornik, footer, breadcrumb, gumbe i skripte, a sadržaj sprema kao `.md`. Poštuje `robots.txt` i čeka sekundu između stranica.
- Obje skripte na kraju ponovno izgrade indeks: markdown se reže na chunkove po naslovima i sprema u `data/index.json`.

Na pitanje klijenta bot pretraži chunkove (BM25, pretraga po ključnim riječima) i uzme **3 najbolje ocijenjena**. Ako nijedan nije dovoljno relevantan, kaže da tu informaciju nema.

**Dodavanje novog dokumenta:** stavite ga u `data/raw/pdf/` ili `data/raw/docx/` i pokrenite `python -m scripts.ingest`.
**Nova web stranica:** dodajte je u `data/sources.json` i pokrenite `python -m scripts.scrape`.

## Testna web stranica banke

U `data/raw/web/` je web stranica izmišljene Banke Demo s 8 stranica: početna, krediti, računi, kartice, štednja, Demo mBank, poslovnice i o nama. Stranicu gradi `python -m scripts.build_demo_site`, jer su zaglavlje i footer zajednički pa se ne ponavljaju ručno.

Pregled u pregledniku: pokrenite web server (`python -m web.app`) i otvorite http://localhost:5000/. Stranica asistenta ima `noindex`, pa je scraper ne sprema u bazu.

PDF i Word dokumenti generirani su skriptom `scripts/generate_demo_docs.py`. Brojke na stranici i u dokumentima usklađene su s `data/rates.json`.

## Tipfeleri i pitanja "Jeste li mislili...?"

Bot pokušava shvatiti što je klijent mislio i kad poruka nije savršeno napisana:

- **Tipfeleri** (`spelling.py`, samo u simuliranom modu): svaka riječ se uspoređuje s rječnikom riječi iz baze znanja i ključnih riječi bota.
  - Kad je ispravak siguran ("kartcu" → "karticu", "kerdit" → "kredit", "mjeseciiii" → "mjeseci"), bot ga primijeni bez pitanja.
  - Kad nije siguran, a ispravak bi promijenio odgovor, bot pita: *"Jeste li mislili: „oročenja štednje“?"*
  - Padeži poznatih riječi ("Splitu", "kreditna") ne smatraju se tipfelerima.
- **Nejasna pitanja** (`clarify.py`):
  - "kredit" ili "stambeni kredit" bez ičeg drugog: bot pita želi li klijent izračun rate ili uvjete i kamatne stope.
  - Ako pretraga nađe nešto samo djelomično slično, bot ponudi teme koje je pronašao umjesto da odgovori nešto krivo.
- **Odgovor na pitanje**: klijent može odgovoriti brojem ("2"), riječju ("prvo"), s "da"/"ne", tekstom opcije ili klikom na gumb u web chatu. Ako umjesto toga postavi novo pitanje, bot odgovori na njega.
- **Brzi odgovori**: kalkulator i pitanja za pojašnjenje nude gumbe (Gotovinski / Stambeni, Da / Ne, Ukupan iznos i kamata / Otplatni plan). U terminalu se ispisuju u uglatim zagradama.

S API ključem tipfelere i nejasna pitanja rješava model: router može vratiti namjeru `clarify` s pitanjem i opcijama, a odgovor iz dokumentacije smije pitati "Jeste li mislili na...".

## Kalkulator (subagent)

Skuplja četiri podatka i pita za one koji nedostaju:

- vrsta kredita
- iznos
- rok
- je li klijent državljanin RH

Pravila su u `data/rates.json`:

| | Gotovinski | Stambeni |
|---|---|---|
| Iznos | 1.000 – 40.000 EUR | 20.000 – 400.000 EUR |
| Rok | 12 – 120 mjeseci | 60 – 360 mjeseci |
| Državljani RH | 5,99 – 7,19 % | 3,49 – 4,09 % |
| Nedržavljani | 7,19 – 8,39 % | nije dostupno |

Stopa je uvijek fiksna. Ovisi o vrsti kredita, državljanstvu, roku i iznosu, a ne ovisi o tome gdje klijent prima plaću.

Ponašanje kalkulatora:

- Na početku daje samo mjesečnu ratu. Ukupan iznos otplate, ukupnu kamatu i otplatni plan po godinama daje ako klijent pita. Plan po mjesecima sprema i u CSV u `exports/`.
- Kad nedržavljanin traži stambeni kredit, pristojno upozori da to nije moguće i ponudi izračun za gotovinski.
- Ako klijent traži kredit u stranoj valuti, objasni da su krediti samo u EUR, preračuna iznos po tečaju HNB-a i ponudi izračun s tim iznosom.
- Iznos ili rok izvan granica javi odmah, uz dopuštene granice.

## Tečajna lista

Koristi se javni API HNB-a (`https://api.hnb.hr/tecajn-eur/v3`), bez ključa. Tečaj se sprema u dnevni cache (`data/cache/`). Preračun ide po srednjem tečaju.

Nakon prikaza tečaja bot nudi preračun, a klijent može upisati samo iznos.

## Struktura

```
chat.py                    chat u terminalu
web/app.py                 web server: stranica banke + chat API
web/sessions.py            spremanje razgovora: Redis ili memorija
docker-compose.yml         Redis za razgovore
web/static/                chat prozor (chat-widget.js, chat-widget.css)
bankbot/agent.py           glavni agent: prepozna namjeru i proslijedi subagentu
bankbot/calculator_agent.py  subagent za kredite (skupljanje podataka, detalji, otplatni plan)
bankbot/calculator.py      izračun: stopa iz rates.json, anuitet, otplatni plan
bankbot/info_agent.py      pitanja o banci (RAG)
bankbot/retrieval.py       chunking + BM25 pretraga
bankbot/fx_agent.py        tečaj i preračun
bankbot/fx.py              HNB API
bankbot/llm.py             poziv modela + simulirani mod
bankbot/nlu.py             pravila za simulirani mod (namjera, iznosi, rokovi, jezik)
bankbot/spelling.py        ispravljanje tipfelera (simulirani mod)
bankbot/clarify.py         pitanja "Jeste li mislili...?" i odabir ponuđene opcije
bankbot/texts.py           tekstovi odgovora (hr/en)
bankbot/audit.py           audit log (logs/audit.jsonl)
scripts/                   ingest, scrape, generiranje testnih dokumenata
data/rates.json            kamatne stope i granice kredita
tests/                     testovi
```

## Testovi

```bash
python -m unittest
```

### GitHub Actions

Na svaki push i pull request [workflow](.github/workflows/tests.yml) pokrene sve testove na Ubuntu s Pythonom 3.12 i 3.14. Uz testove se diže i pravi Redis, pa se spremanje sesija testira i protiv njega (`RealRedisStoreTest`), a ne samo protiv fakeredisa. Lokalno se to uključuje s `REDIS_TEST_URL=redis://localhost:6379/15`; baza 15 je odvojena od pravih razgovora. Rezultati su u kartici **Actions** na GitHubu, a run se može pokrenuti i ručno (**Run workflow**).

### Testni razgovori

`scripts/run_scenarios.py` pušta ~75 razgovora kroz bota (kredit, preračun valute, tečaj, pitanja o banci, engleski, pitanja izvan teme, tipfeleri, pojašnjenja). Ispisuje cijeli razgovor i provjerava sadrži li svaki odgovor ono što mora, npr. "292,02 EUR".

```bash
python -m scripts.run_scenarios                        # svi razgovori
python -m scripts.run_scenarios --group kredit         # samo jedna grupa
python -m scripts.run_scenarios --only-failed          # samo oni s greškom
python -m scripts.run_scenarios --out razgovori.md     # izvještaj u datoteku
```

Radi u trenutno aktivnom modu, pa se s API ključem tako može usporediti pravi model sa simuliranim. Novi razgovor dodaje se u listu `SCENARIOS` na vrhu skripte. Isti razgovori vrte se i u `python -m unittest`, s lažnom tečajnom listom.

## Ograničenja simuliranog moda

Pretraga po ključnim riječima ne razumije sinonime ni parafraze. Za to u `retrieval.py` postoje mali popisi sinonima i englesko-hrvatskih pojmova.

Na engleska pitanja o banci bot u simuliranom modu vraća dijelove dokumentacije na hrvatskom, jer nema tko prevesti. S pravim modelom te stvari rade puno bolje.

