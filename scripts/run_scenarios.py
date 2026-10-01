"""Pušta testne razgovore kroz bota i ispisuje cijeli razgovor + provjere.

    python -m scripts.run_scenarios                      # svi razgovori
    python -m scripts.run_scenarios --group kredit       # samo jedna grupa
    python -m scripts.run_scenarios --only-failed        # ispiši samo razgovore s greškom
    python -m scripts.run_scenarios --out izvjestaj.md   # spremi i u markdown datoteku

Grupe: kredit, valuta, tecaj, banka, engleski, izvan_teme, tipfeleri, pojasnjenja, ostalo.

Svaki razgovor počinje od nule (novi Conversation). Uz poruku se može navesti
što odgovor mora sadržavati; ako ne sadrži, razgovor je označen kao FAIL.
Radi u modu koji je trenutno aktivan (simulirani, ili pravi model ako je u .env ključ).
Tečaj se dohvaća uživo s HNB-a, pa se iznosi preračuna mijenjaju iz dana u dan.
"""

import argparse
import sys
import time
from datetime import datetime

from bankbot import llm
from bankbot.agent import Conversation, reply
from bankbot.config import MODEL

# Poruka je ili tekst, ili (tekst, [što odgovor mora sadržavati]).
# Provjera ne razlikuje velika i mala slova.
SCENARIOS = [
    # ------------------------------------------------------------------ kredit
    ("kredit", "Gotovinski, sve u jednoj poruci pa detalji i plan", [
        ("koliko bi mi bila rata za gotovinski kredit od 15000 eura na 5 godina?", ["državljanin"]),
        ("da", ["292,02 EUR", "6,29 %"]),
        ("koliko ću ukupno platiti?", ["17.521,09 EUR"]),
        ("da", ["Otplatni plan"]),
        ("a na 3 godine?", ["456,26 EUR"]),
    ]),
    ("kredit", "Bot pita redom što nedostaje", [
        ("želim kredit", ["gotovinskom ili stambenom"]),
        ("stambeni", ["iznos"]),
        ("150000", ["rok"]),
        ("25 godina", ["državljanin"]),
        ("da", ["Mjesečna rata"]),
    ]),
    ("kredit", "Nedržavljanin traži stambeni, prihvati gotovinski, iznos prevelik", [
        ("Želim stambeni kredit", ["iznos"]),
        ("150 tisuća", ["rok"]),
        ("25 godina", ["državljanin"]),
        ("ne", ["samo državljani Republike Hrvatske", "gotovinski"]),
        ("da", ["nije moguć", "40.000,00 EUR"]),
    ]),
    ("kredit", "Nedržavljanin: stambeni odbijen, gotovinski predug rok", [
        ("stambeni kredit 100000 eura na 20 godina", ["državljanin"]),
        ("nisam državljanin", ["samo državljani"]),
        ("da", ["od 1.000,00 EUR do 40.000,00 EUR"]),
        ("30000", ["rok od"]),
    ]),
    ("kredit", "Stranac pita za stambeni", [
        ("mogu li kao stranac dobiti stambeni kredit", ["samo državljani", "gotovinski"]),
    ]),
    ("kredit", "Iznos izvan granica javlja se odmah", [
        ("gotovinski 50000 eur na 5 godina", ["nije moguć"]),
        ("30000", ["državljanin"]),
        ("da", ["584,04 EUR"]),
    ]),
    ("kredit", "Rok izvan granica, pa ukupno", [
        ("stambeni kredit na 40 godina", ["nije moguć"]),
        ("20 godina", ["iznos"]),
        ("200000", ["državljanin"]),
        ("da", ["1.179,54 EUR"]),
        ("koliko ukupno", ["283.089,88 EUR"]),
    ]),
    ("kredit", "Korak po korak pa 'daj ukupan iznos otplate' (prije išlo u pretragu)", [
        ("mjesecna rata", ["gotovinskom ili stambenom"]),
        ("gotovinski", ["iznos"]),
        ("1200", ["rok"]),
        ("100 mjeseciiiiii", ["državljanin"]),
        ("da", ["15,99 EUR"]),
        ("daj ukupan iznos otplate", ["ukupno ćete otplatiti", "1.200,00 EUR"]),
    ]),
    ("kredit", "Kratki 'da' na ponude detalja i plana", [
        ("gotovinski 15000 eur na 5 godina", ["državljanin"]),
        ("da", ["292,02 EUR"]),
        ("da", ["17.521,09 EUR"]),
        ("da", ["Otplatni plan"]),
    ]),
    ("kredit", "'ne hvala' nakon izračuna", [
        ("gotovinski 15000 eur na 5 godina", ["državljanin"]),
        ("da", ["292,02 EUR"]),
        ("ne hvala", ["Nema na čemu"]),
    ]),
    ("kredit", "Sve u jednoj poruci, uključujući državljanstvo", [
        ("gotovinski kredit 10000 eur na 3 godine, državljanin sam", ["306,44 EUR", "6,49 %"]),
    ]),
    ("kredit", "Kratka poruka s vrstom kredita", [
        ("gotovinski 5000 eur na 2 godine", ["državljanin"]),
    ]),
    ("kredit", "Vrsta kredita nije navedena", [
        ("koliko bi bila rata kredita od 5000 eura na 2 godine", ["gotovinskom ili stambenom"]),
    ]),
    # ------------------------------------------------------------------ valuta
    ("valuta", "Kredit u dolarima: samo EUR + ponuda preračuna", [
        ("I'd like a loan of 10000 dollars for 4 years", ["euros (EUR) only", "USD"]),
        ("yes", ["cash loan or a housing loan"]),
        ("cash", ["Croatian citizen"]),
        ("yes I am", ["Monthly payment"]),
    ]),
    # ------------------------------------------------------------------ tecaj
    ("tecaj", "Tečaj franka pa samo iznos", [
        ("koji je tečaj švicarskog franka", ["CHF", "preračunam"]),
        ("250", ["CHF =", "EUR"]),
    ]),
    ("tecaj", "EUR u USD", [("koliko je 500 eura u dolarima", ["EUR =", "USD"])]),
    ("tecaj", "USD u EUR", [("koliko je 100 dolara u eurima", ["USD =", "EUR"])]),
    ("tecaj", "Tečaj dolara", [("koji je tečaj dolara", ["USD", "srednji"])]),
    ("tecaj", "Tečajna lista", [("tečajna lista", ["srednji tečaj"])]),
    # ------------------------------------------------------------------ banka
    ("banka", "Radno vrijeme Split", [("koje je radno vrijeme poslovnice u Splitu?", ["Split", "8:00"])]),
    ("banka", "Poslovnica Zadar", [("imate li poslovnicu u Zadru", ["Zadar"])]),
    ("banka", "Poslovnica Pula", [("imate li poslovnicu u Puli", ["Pula", "Giardini"])]),
    ("banka", "Poslovnica Rijeka", [("gdje je poslovnica u Rijeci", ["Rijeka", "Korzo"])]),
    ("banka", "Blokada kartice", [("kako mogu blokirati karticu?", ["0800 1234"])]),
    ("banka", "Izgubljena kartica", [("kako blokirati izgubljenu karticu", ["0800 1234"])]),
    ("banka", "Naknada na tuđim bankomatima", [("koja je naknada za podizanje gotovine na tuđim bankomatima", ["1,50 EUR"])]),
    ("banka", "Kreditna kartica", [("koliko košta kreditna kartica", ["25,00 EUR"])]),
    ("banka", "Dnevni limit", [("koliki je dnevni limit za podizanje gotovine debitnom karticom", ["1.000 EUR"])]),
    ("banka", "Vođenje računa", [("kolika je naknada za vođenje tekućeg računa", ["2,00 EUR"])]),
    ("banka", "Oročena štednja", [("koja je kamata na oročenu štednju", ["2,00 %"])]),
    ("banka", "Štednja na 3 godine", [("koja je kamata na štednju na 3 godine", ["2,50 %"])]),
    ("banka", "Minimalno oročenje", [("koliko je najmanje za oročenje", ["500,00 EUR"])]),
    ("banka", "Dječja štednja", [("koja je dječja štednja", ["Demo Junior"])]),
    ("banka", "Dokumentacija za stambeni", [("koja dokumentacija treba za stambeni kredit", ["zemljišne knjige"])]),
    ("banka", "Što treba za stambeni (razgovorno)", [("sto mi treba za stambeni kredit", [])]),
    ("banka", "Prijevremena otplata", [("naknada za prijevremenu otplatu gotovinskog kredita", ["prijevremen"])]),
    ("banka", "Ranija otplata (razgovorno)", [("da li mogu otplatiti kredit ranije", ["prijevremen"])]),
    ("banka", "Osiguranje kredita", [("je li osiguranje kredita obavezno", ["osiguranj"])]),
    ("banka", "Trajanje odobravanja", [("koliko traje odobravanje kredita", ["radni dan"])]),
    ("banka", "Kredit za umirovljenike", [("jel mogu dobit kredit ako sam u mirovini", ["mirovin"])]),
    ("banka", "Kredit za umirovljenike (razgovorno 'ak')", [("jel mogu dobit kredit ak sam u mirovini", ["mirovin"])]),
    ("banka", "Umirovljenik i gotovinski", [("mogu li kao umirovljenik dobiti gotovinski kredit", ["mirovin", "gotovinsk"])]),
    ("banka", "Penzioner (razgovorno)", [("dal penzioner moze dobit kredit", ["mirovin"])]),
    ("banka", "Račun za strance", [("mogu li kao stranac otvoriti račun", ["putovnic"])]),
    ("banka", "Prekoračenje", [("mogu li dobiti prekoračenje", ["3.000 EUR"])]),
    ("banka", "Mobilno bankarstvo", [("kako se prijaviti u mobilno bankarstvo", ["aktivacijski kod"])]),
    ("banka", "Kontakt centar", [("koji je broj kontakt centra", ["0800 1234"])]),
    ("banka", "Sjedište", [("gdje se nalazi sjediste banke", ["Ilica 100"])]),
    ("banka", "OIB", [("koji je OIB banke", ["12345678901"])]),
    ("banka", "Slanje novca u inozemstvo", [("koliko košta slanje novca u inozemstvo", ["SEPA"])]),
    # ------------------------------------------------------------------ engleski
    ("engleski", "Pozdrav i dokumenti za stambeni", [
        ("Hello", ["virtual assistant"]),
        ("What documents do I need for a housing loan?", ["dokumentacija"]),
    ]),
    ("engleski", "Blokada kartice", [("how can I block my card", ["0800 1234"])]),
    ("engleski", "Radno vrijeme", [("What are your opening hours?", ["8:00"])]),
    ("engleski", "Radno vrijeme poslovnica", [("what are the branch opening hours", ["8:00"])]),
    # ------------------------------------------------------------------ izvan teme
    ("izvan_teme", "Vrijeme u Tokiju", [("koliko je vrijeme u Tokiju", ["nemam informaciju"])]),
    ("izvan_teme", "Sati u Tokiju", [("koliko je sati u Tokiju?", ["nemam informaciju"])]),
    ("izvan_teme", "Predsjednik", [("tko je predsjednik države", ["nemam informaciju"])]),
    ("izvan_teme", "Svjetsko prvenstvo", [("tko je osvojio svjetsko prvenstvo", ["nemam informaciju"])]),
    ("izvan_teme", "Vremenska prognoza", [("kakvo je vrijeme sutra", ["nemam informaciju"])]),
    ("izvan_teme", "Recept", [("recept za palačinke", ["nemam informaciju"])]),
    # ------------------------------------------------------------------ tipfeleri
    ("tipfeleri", "Blokada kartice s tipfelerima", [("kako blokirat kartcu", ["0800 1234"])]),
    ("tipfeleri", "Kredit s tipfelerima", [
        ("gotovniski kredt 5000 eur na 3 godne", ["državljanin"]),
        ("da", ["153,22 EUR"]),
    ]),
    ("tipfeleri", "Zamijenjena slova u 'tečaj'", [("koji je tecja dolara", ["USD", "srednji"])]),
    ("tipfeleri", "Radno vrijeme s tipfelerom", [("radno vrjeme poslovnice u splitu", ["Split", "8:00"])]),
    ("tipfeleri", "Državljanstvo s tipfelerom", [("drzavljain sam, gotovinski 10000 na 5 god", ["197,02 EUR"])]),
    ("tipfeleri", "Engleski s tipfelerom", [("what are your openning hours", ["8:00"])]),
    ("tipfeleri", "Kreditna kartica nije kredit", [("koliko kosta kreditan kartica", ["25,00 EUR"])]),
    ("tipfeleri", "Podizanje novca", [("gdje mogu podignuti novac", ["bankomat"])]),
    # ------------------------------------------------------------------ pojasnjenja
    ("pojasnjenja", "Nesiguran ispravak: bot pita, klijent potvrdi", [
        ("oročnje štednje", ["Jeste li mislili", "oročenja"]),
        ("da", ["2,00 %"]),
    ]),
    ("pojasnjenja", "Nesiguran ispravak: klijent kaže ne", [
        ("oročnje štednje", ["Jeste li mislili"]),
        ("ne", ["drugačije"]),
    ]),
    ("pojasnjenja", "Samo 'kredit': izračun ili uvjeti?", [
        ("kredit", ["Izračun mjesečne rate", "Uvjeti i kamatne stope"]),
        ("izračun mjesečne rate", ["gotovinskom ili stambenom"]),
    ]),
    ("pojasnjenja", "'stambeni kredit' pa odabir broja 2", [
        ("stambeni kredit", ["Jeste li mislili na"]),
        ("2", ["kamatne stope", "3,49 %"]),
    ]),
    ("pojasnjenja", "Kredit za stan pa odabir broja 1", [
        ("kakav je kredit za stan", ["Jeste li mislili na"]),
        ("1", ["iznos", "20.000,00 EUR"]),
    ]),
    ("pojasnjenja", "Nakon pitanja klijent postavi drugo pitanje", [
        ("kredit", ["Jeste li mislili na"]),
        ("koji je tečaj dolara", ["USD"]),
    ]),
    # ------------------------------------------------------------------ ostalo
    ("ostalo", "Pozdrav i zahvala", [
        ("Bok", ["virtualni asistent"]),
        ("hvala", ["Nema na čemu"]),
    ]),
]


def run_scenario(turns):
    state = Conversation()
    transcript, failures = [], []
    for turn in turns:
        message, expected = (turn, []) if isinstance(turn, str) else turn
        answer = reply(message, state)
        missing = [e for e in expected if e.lower() not in answer.lower()]
        transcript.append((message, answer, missing))
        if missing:
            failures.append((message, missing))
    return transcript, failures


def format_scenario(i, group, name, transcript, failures):
    status = "FAIL" if failures else "OK"
    lines = [f"## {i}. [{status}] {name}  ({group})", ""]
    for message, answer, missing in transcript:
        lines.append(f"**Vi:** {message}")
        lines.append("")
        lines.append("**Bot:** " + answer.replace("\n", "\n> ").replace("\n> \n> ", "\n>\n> "))
        if missing:
            lines.append("")
            lines.append(f"> ✗ nedostaje u odgovoru: {', '.join(repr(m) for m in missing)}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Pušta testne razgovore kroz bota.")
    parser.add_argument("--group", help="samo jedna grupa (kredit, valuta, tecaj, banka, engleski, izvan_teme, ostalo)")
    parser.add_argument("--only-failed", action="store_true", help="ispiši samo razgovore s greškom")
    parser.add_argument("--out", help="spremi izvještaj u markdown datoteku")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    scenarios = [s for s in SCENARIOS if not args.group or s[0] == args.group]
    if not scenarios:
        sys.exit(f"Nema grupe '{args.group}'.")

    mode = f"pravi model ({MODEL})" if llm.MODE == "real" else "simulirani mod"
    header = f"# Testni razgovori – {datetime.now():%Y-%m-%d %H:%M} – {mode}\n"
    blocks, summary = [], []
    start = time.time()

    for i, (group, name, turns) in enumerate(scenarios, 1):
        transcript, failures = run_scenario(turns)
        summary.append((i, group, name, failures))
        if failures or not args.only_failed:
            block = format_scenario(i, group, name, transcript, failures)
            blocks.append(block)
            print(block)
            print("-" * 70)

    failed = [s for s in summary if s[3]]
    total_turns = sum(len(s[2]) for s in scenarios)
    result = [
        "",
        f"## Rezultat: {len(scenarios) - len(failed)}/{len(scenarios)} razgovora OK "
        f"({total_turns} poruka, {time.time() - start:.1f} s)",
    ]
    for i, group, name, failures in failed:
        for message, missing in failures:
            result.append(f"- ✗ {i}. {name}: na \"{message}\" nedostaje {', '.join(repr(m) for m in missing)}")
    print("\n".join(result))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(header + "\n" + "\n\n".join(blocks) + "\n" + "\n".join(result) + "\n")
        print(f"\nIzvještaj spremljen: {args.out}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
