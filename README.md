# Banka Demo – chatbot

[![Testovi](https://github.com/xmann2411/bank-chatbot/actions/workflows/tests.yml/badge.svg)](https://github.com/xmann2411/bank-chatbot/actions/workflows/tests.yml)

Chatbot za izmišljenu banku "Banka Demo d.d.". Zna tri stvari:

1. **odgovoriti na pitanja o banci** iz dokumentacije (PDF, Word, web stranice)
2. **izračunati mjesečnu ratu** gotovinskog ili stambenog kredita (samo u EUR)
3. **pokazati tečajnu listu HNB-a** i preračunati iznos između valuta

Radi na hrvatskom i engleskom, u terminalu ili kao chat na web stranici banke. Za rad **ne treba API ključ**: bez ključa radi po pravilima (simulirani mod), a s ključem koristi Claude.

## Što treba

- **Python 3.12 ili noviji** (testirano na 3.12 i 3.14). Provjera: `python --version`
- **Git**
- **Internet** za instalaciju paketa i tečajnu listu HNB-a
- Opcionalno: **Docker Desktop** za spremanje razgovora u Redis, i **Anthropic API ključ** za pravi model

## Brzi početak

**1. Preuzmite projekt**

```bash
git clone https://github.com/xmann2411/bank-chatbot.git
cd bank-chatbot
```

**2. Napravite virtualno okruženje i uključite ga**

```bash
python -m venv .venv
```

Zatim, ovisno o terminalu:

| Terminal | Naredba |
|---|---|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows Command Prompt (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux / Git Bash | `source .venv/bin/activate` (Git Bash: `source .venv/Scripts/activate`) |

Kad je okruženje uključeno, na početku retka u terminalu piše `(.venv)`. Ako PowerShell javi *"running scripts is disabled on this system"*, pogledajte [Česti problemi](#česti-problemi).

**3. Instalirajte pakete** (traje nekoliko minuta)

```bash
pip install -r requirements.txt
```

**4. Pokrenite chat u terminalu**

```bash
python chat.py
```

Probajte npr.:

- `gotovinski kredit 10000 eur na 3 godine`
- `koji je tečaj dolara`
- `kako blokirati karticu`
- `koje je radno vrijeme poslovnice u Splitu`

Za izlaz upišite `izlaz`.

Baza znanja je već napunjena (`data/knowledge/`), pa ništa ne treba pripremati.

## Web chat

```bash
python -m web.app
```

Otvorite **http://localhost:5000/**. Dobit ćete web stranicu Banke Demo s gumbom za chat u donjem desnom kutu na svakoj stranici. Na stranici **Virtualni asistent** (`/asistent.html`) chat je preko cijele stranice. Server se gasi s `Ctrl+C`.

Ako je port 5000 zauzet (na macOS-u ga koristi AirPlay), pokrenite server na drugom portu:

```bash
PORT=5001 python -m web.app          # macOS / Linux / Git Bash
$env:PORT=5001; python -m web.app    # Windows PowerShell
```

Što chat radi:

- Prije odgovora se kratko prikazuju točkice, kao da bot tipka.
- Razgovor ostaje kad klijent prelazi s jedne stranice na drugu ili osvježi stranicu. Nakon 30 minuta neaktivnosti počinje novi razgovor.
- Nudi prijedloge pitanja i gumbe za brze odgovore (npr. Gotovinski / Stambeni, Da / Ne).
- Tablice (otplatni plan, naknade) prikazuju se kao tablice, a otplatni plan po mjesecima može se preuzeti kao CSV.
- Gumbi "Izračunajte ratu" na stranici otvaraju chat i odmah pošalju pitanje (atribut `data-bankbot` na linku).
- Na mobitelu se otvara preko cijelog zaslona.
- Oznaka "demo način" u zaglavlju chata znači da bot radi bez API ključa.

Server se sam restarta kad promijenite Python kod. Isključuje se s `RELOAD=0`.

### API

| | |
|---|---|
| `POST /api/session` | novi razgovor → `{session_id, greeting, mode}` |
| `POST /api/chat` | `{session_id, message}` → `{reply, quick_replies}` |
| `GET /api/schedule/<session_id>.csv` | otplatni plan zadnjeg izračuna |
| `GET /api/health` | način rada i gdje se spremaju razgovori (`redis` / `memory`) |

## Postavke (`.env`)

Sve postavke su opcionalne; bez njih sve radi. Za postavke napravite `.env` iz predloška:

```bash
cp .env.example .env          # macOS / Linux / Git Bash
copy .env.example .env        # Windows (PowerShell ili cmd)
```

| Varijabla | Čemu služi |
|---|---|
| `ANTHROPIC_API_KEY` | ključ za Claude; bez njega bot radi u simuliranom modu |
| `ANTHROPIC_MODEL` | koji model (zadano `claude-opus-5-5`; jeftinije `claude-sonnet-5-5`, `claude-haiku-4-5`) |
| `REDIS_URL` | gdje spremati razgovore web chata, npr. `redis://localhost:6379/0` |

`.env` je u `.gitignore`, pa ključ nikad ne završi u gitu. Nakon izmjene `.env` restartajte server.

### Spremanje razgovora u Redis

Bez Redisa web server drži razgovore u memoriji, pa ih restart servera izbriše. S Redisom razgovor preživi restart, a isti Redis može koristiti i više servera.

1. Pokrenite Docker Desktop i pričekajte da piše *Engine running*.
2. Pokrenite Redis (`docker-compose.yml` je u projektu):
   ```bash
   docker compose up -d
   ```
3. U `.env` postavite `REDIS_URL=redis://localhost:6379/0`.
4. Pokrenite web server. Pri pokretanju mora pisati `Sesije: Redis (redis://localhost:6379/0)`, a http://localhost:5000/api/health vraća `"sessions": "redis"`.

Redis se gasi s `docker compose down`. Razgovori ostaju spremljeni na disku i vrate se kod sljedećeg `docker compose up -d`.

Detalji:

- Svaki razgovor je jedan JSON pod ključem `bankbot:session:<id>`, s rokom od 30 minuta koji se produži kod svake poruke.
- Sprema se zadnjih 40 poruka. Otplatni plan se ne sprema; kod učitavanja se ponovno izračuna iz iznosa, roka i stope.
- Dvije poruke istog razgovora ne obrađuju se istovremeno (Redis lock).
- Ako je `REDIS_URL` postavljen, a Redis ne radi, server ispiše upozorenje i drži razgovore u memoriji.

### Pravi model (API ključ)

Ključ se dobiva na [console.anthropic.com](https://console.anthropic.com) (API Keys). Plaća se prema potrošnji, odvojeno od Claude pretplate. Upišite ga u `.env` kao `ANTHROPIC_API_KEY=...` i restartajte chat ili server. U zaglavlju web chata nestane oznaka "demo način".

## Kako bot radi

Svaka poruka prolazi iste korake (`bankbot/agent.py`):

1. **Otvoreno pitanje**: ako je bot upravo nešto pitao ("Jeste li državljanin?"), kratki odgovor ("da") ide tom pitanju.
2. **Tipfeleri** se ispravljaju (samo u simuliranom modu).
3. **Namjera**: pitanje o banci, izračun kredita, detalji izračuna, tečaj, pozdrav ili zahvala.
4. **Jasnoća**: ako bot nije siguran što je klijent mislio, pita "Jeste li mislili…?" i ponudi opcije.
5. **Subagent** odgovara: kalkulator, pretraga dokumentacije ili tečaj.

### Simulirani i pravi mod

Svaki korak koji može raditi model (`bankbot/llm.py`) ima i verziju po pravilima:

| Korak | Bez API ključa | S API ključem |
|---|---|---|
| tipfeleri | rječnik + sličnost slova (`spelling.py`) | model |
| namjera | pravila (`nlu.py`) | model, uz kontekst razgovora |
| podaci za kredit | pravila (iznos, rok, vrsta, državljanstvo) | model vrati JSON |
| upit za pretragu | sinonimi + mali englesko-hrvatski rječnik | model preformulira |
| pretraga | BM25, 3 najbolja dijela dokumentacije | isto |
| odgovor o banci | citat iz dokumentacije | model piše odgovor iz ta 3 dijela |
| izračun kredita i tečaj | kod | kod |

Ako model ne odgovori (mreža, limit, neispravan ključ), bot se za taj korak vrati na pravila, pa uvijek nešto odgovori.

**Brojeve nikad ne računa model.** Kamatna stopa dolazi iz `data/rates.json`, a rata iz formule u `calculator.py`.

### Tipfeleri i pitanja "Jeste li mislili...?"

- **Tipfeleri** (`spelling.py`): svaka riječ se uspoređuje s rječnikom riječi iz baze znanja i ključnih riječi bota.
  - Kad je ispravak siguran ("kartcu" → "karticu", "kerdit" → "kredit", "mjeseciiii" → "mjeseci"), bot ga primijeni bez pitanja.
  - Kad nije siguran, a ispravak bi promijenio odgovor, pita: *"Jeste li mislili: „oročenja štednje“?"*
  - Padeži poznatih riječi ("Splitu", "kreditna") ne smatraju se tipfelerima.
- **Nejasna pitanja** (`clarify.py`):
  - "kredit" ili "stambeni kredit" bez ičeg drugog: bot pita želi li klijent izračun rate ili uvjete i kamatne stope.
  - Ako pretraga nađe nešto samo djelomično slično, bot ponudi pronađene teme umjesto da odgovori nešto krivo.
- Na pitanje se odgovara brojem ("2"), riječju ("prvo"), s "da"/"ne", tekstom opcije ili klikom na gumb. Ako klijent umjesto toga postavi novo pitanje, bot odgovori na njega.

### Kalkulator

Skuplja četiri podatka i pita za one koji nedostaju: vrstu kredita, iznos, rok i je li klijent državljanin RH. Pravila su u `data/rates.json`:

| | Gotovinski | Stambeni |
|---|---|---|
| Iznos | 1.000 – 40.000 EUR | 20.000 – 400.000 EUR |
| Rok | 12 – 120 mjeseci | 60 – 360 mjeseci |
| Državljani RH | 5,99 – 7,19 % | 3,49 – 4,09 % |
| Nedržavljani | 7,19 – 8,39 % | nije dostupno |

Stopa je uvijek fiksna. Ovisi o vrsti kredita, državljanstvu, roku i iznosu, a ne ovisi o tome gdje klijent prima plaću.

- Na početku daje samo mjesečnu ratu. Ukupan iznos otplate, ukupnu kamatu i otplatni plan daje ako klijent pita. Otplatni plan po mjesecima u terminalu se sprema u `exports/`, a u web chatu se preuzima kao CSV.
- Kad nedržavljanin traži stambeni kredit, pristojno upozori da to nije moguće i ponudi izračun za gotovinski.
- Ako klijent traži kredit u stranoj valuti, objasni da su krediti samo u EUR, preračuna iznos po tečaju HNB-a i ponudi izračun s tim iznosom.
- Iznos ili rok izvan granica javi odmah, uz dopuštene granice.

### Tečajna lista

Koristi se javni API HNB-a (`https://api.hnb.hr/tecajn-eur/v3`), bez ključa. Tečaj se sprema u dnevni cache (`data/cache/`), a preračun ide po srednjem tečaju. Nakon prikaza tečaja bot nudi preračun, a klijent može upisati samo iznos.

## Baza znanja

Bot ne čita PDF-ove i Word dokumente izravno. Svi izvori se jednom pretvore u markdown i izrežu na dijelove (chunkove), a bot pretražuje samo njih.

```
data/raw/pdf/*.pdf     ─┐
data/raw/docx/*.docx   ─┼─ python -m scripts.ingest ─┐
                        │                             ├─> data/knowledge/*.md ─> data/index.json (chunkovi)
data/sources.json (URL) ─── python -m scripts.scrape ─┘
```

- **`scripts/ingest.py`** pretvara PDF i Word dokumente u markdown. Naslovi ostaju naslovi, a tablice ostaju tablice.
- **`scripts/scrape.py`** je posebna skripta za web. Kreće od adrese iz `data/sources.json` i, uz `"crawl": true`, sama prati linkove na podstranice istog sitea. Miče izbornik, footer, breadcrumb, gumbe i skripte, a stranice označene s `noindex` preskače. Poštuje `robots.txt` i čeka sekundu između stranica.
- Obje skripte na kraju ponovno izgrade `data/index.json`.

Na pitanje klijenta bot pretraži chunkove (BM25, pretraga po ključnim riječima) i uzme **3 najbolje ocijenjena**. Ako nijedan nije dovoljno relevantan, kaže da tu informaciju nema.

- **Novi dokument:** stavite ga u `data/raw/pdf/` ili `data/raw/docx/` i pokrenite `python -m scripts.ingest`.
- **Nova web stranica:** dodajte je u `data/sources.json` i pokrenite `python -m scripts.scrape`.

Svaki `.md` u zaglavlju ima datum obrade, pa nakon ingesta git pokazuje izmjene u svim datotekama baze znanja, i kad se sadržaj nije promijenio. Restartajte chat ili server da učitaju novi indeks.

## Testni podaci

Banka i svi njeni dokumenti su izmišljeni. Brojke na web stranici i u dokumentima usklađene su s `data/rates.json`. Generirani dokumenti su već u repozitoriju, pa ove skripte ne treba pokretati:

- `python -m scripts.build_demo_site` gradi web stranicu banke u `data/raw/web/` (8 stranica + stranica virtualnog asistenta).
- `python -m scripts.generate_demo_docs` generira testne PDF i Word dokumente. Treba TTF font s hrvatskim slovima: na Windowsima i macOS-u to je Arial, a na Linuxu paket `fonts-dejavu-core`.

## Testovi

```bash
python -m unittest
```

Pokreću se iz korijena projekta. Četiri testa za pravi Redis preskaču se, osim ako postavite `REDIS_TEST_URL` (baza 15 je odvojena od pravih razgovora):

```bash
REDIS_TEST_URL=redis://localhost:6379/15 python -m unittest                 # macOS / Linux / Git Bash
$env:REDIS_TEST_URL="redis://localhost:6379/15"; python -m unittest         # Windows PowerShell
```

### Testni razgovori

`scripts/run_scenarios.py` pušta 75 razgovora kroz bota (kredit, preračun valute, tečaj, pitanja o banci, engleski, pitanja izvan teme, tipfeleri, pojašnjenja). Ispisuje cijeli razgovor i provjerava sadrži li svaki odgovor ono što mora, npr. "292,02 EUR".

```bash
python -m scripts.run_scenarios                        # svi razgovori
python -m scripts.run_scenarios --group kredit         # samo jedna grupa
python -m scripts.run_scenarios --only-failed          # samo oni s greškom
python -m scripts.run_scenarios --out razgovori.md     # izvještaj u datoteku
```

Skripta radi u trenutno aktivnom modu, pa se s API ključem tako može usporediti pravi model sa simuliranim. Grupa `tecaj` dohvaća pravu tečajnu listu, pa treba internet. Novi razgovor dodaje se u listu `SCENARIOS` na vrhu skripte. Isti razgovori vrte se i u `python -m unittest`, s lažnom tečajnom listom.

### GitHub Actions

Na svaki push i pull request [workflow](.github/workflows/tests.yml) pokrene sve testove na Ubuntu s Pythonom 3.12 i 3.14, uz pravi Redis. Rezultati su u kartici **Actions** na GitHubu, a run se može pokrenuti i ručno (**Run workflow**).

## Struktura

```
chat.py                       chat u terminalu
web/app.py                    web server: stranica banke + chat API
web/sessions.py               spremanje razgovora: Redis ili memorija
web/static/                   chat prozor (chat-widget.js, chat-widget.css)
bankbot/agent.py              glavni agent: koraci 1–5 iz "Kako bot radi"
bankbot/calculator_agent.py   kalkulator: skupljanje podataka, detalji, otplatni plan
bankbot/calculator.py         izračun: stopa iz rates.json, anuitet, otplatni plan
bankbot/info_agent.py         pitanja o banci (pretraga + odgovor)
bankbot/retrieval.py          chunking i BM25 pretraga
bankbot/fx_agent.py, fx.py    tečaj i preračun, HNB API
bankbot/llm.py                poziv modela + povratak na pravila
bankbot/nlu.py                pravila: namjera, iznosi, rokovi, jezik
bankbot/spelling.py           ispravljanje tipfelera
bankbot/clarify.py            pitanja "Jeste li mislili...?"
bankbot/texts.py              tekstovi odgovora (hr/en)
bankbot/config.py             putanje i postavke iz .env
bankbot/audit.py              audit log (logs/audit.jsonl)
scripts/                      ingest, scrape, testni razgovori, testni podaci
data/rates.json               kamatne stope i granice kredita
data/raw/                     izvorni dokumenti (PDF, Word, web stranica banke)
data/knowledge/, index.json   baza znanja (markdown i chunkovi)
tests/                        testovi
docker-compose.yml            Redis za razgovore
.github/workflows/tests.yml   GitHub Actions
```

## Česti problemi

**PowerShell: "running scripts is disabled on this system" kod uključivanja `.venv`**
Windows po zadanom ne dopušta pokretanje skripti. Jednom pokrenite:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Ili koristite Command Prompt (`.venv\Scripts\activate.bat`). Može i bez uključivanja okruženja, pozivom Pythona izravno: `.venv\Scripts\python chat.py`.

**`python` nije pronađen**
Na macOS-u i Linuxu naredba je često `python3` (`python3 -m venv .venv`). Kad je okruženje uključeno, radi i `python`. Na Windowsima probajte `py`.

**"Address already in use" / port 5000 zauzet**
Pokrenite server na drugom portu (`PORT=5001`, vidi [Web chat](#web-chat)). Na macOS-u port 5000 zauzima AirPlay Receiver.

**Server ispiše "UPOZORENJE: Redis … nije dostupan"**
Redis ne radi. Provjerite je li Docker Desktop pokrenut i je li pokrenut `docker compose up -d`. Bez Redisa sve radi, samo razgovori nestaju kod restarta servera.

**Chat na stranici kaže "Server nije dostupan"**
Web server nije pokrenut ili je stranica otvorena kao datoteka. Stranicu otvarajte preko http://localhost:5000/, a ne dvoklikom na HTML datoteku.

**Tečaj: "Trenutno ne mogu dohvatiti tečajnu listu HNB-a"**
Nema interneta ili HNB API trenutno ne odgovara. Ostatak bota radi normalno.

## Ograničenja simuliranog moda

Bez API ključa bot uspoređuje riječi, a ne značenje. Pitanja postavljena posve drugim riječima ponekad promaši; za najčešće slučajeve u `retrieval.py` postoje popisi sinonima i englesko-hrvatskih pojmova. Na engleska pitanja o banci vraća dijelove dokumentacije na hrvatskom, jer nema tko prevesti. S pravim modelom oba problema nestaju.
