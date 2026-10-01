"""Tekstovi odgovora na hrvatskom i engleskom + formatiranje iznosa."""

from .calculator import product


def money(value, lang, currency="EUR"):
    s = f"{value:,.2f}"
    if lang == "hr":
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {currency}"


def pct(value, lang):
    s = f"{value:.2f}"
    return (s.replace(".", ",") if lang == "hr" else s) + " %"


def _hr_plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def term(months, lang):
    years, rest = divmod(months, 12)
    if lang == "en":
        if rest == 0:
            return f"{years} year{'s' if years != 1 else ''} ({months} months)"
        return f"{months} months"
    m = f"{months} {_hr_plural(months, 'mjesec', 'mjeseca', 'mjeseci')}"
    if rest == 0:
        return f"{years} {_hr_plural(years, 'godina', 'godine', 'godina')} ({m})"
    return m


def term_range(min_months, max_months, lang):
    """Raspon roka, npr. 'od 12 do 120 mjeseci (od 1 do 10 godina)'."""
    y1, y2 = min_months // 12, max_months // 12
    if lang == "en":
        return f"from {min_months} to {max_months} months ({y1} to {y2} years)"
    return f"od {min_months} do {max_months} mjeseci (od {y1} do {y2} godina)"


def loan_name(loan_type, lang):
    return product(loan_type)["naziv"][lang]


def client_name(client_type, lang):
    return {
        ("drzavljanin", "hr"): "državljanin RH",
        ("nedrzavljanin", "hr"): "nije državljanin RH",
        ("drzavljanin", "en"): "Croatian citizen",
        ("nedrzavljanin", "en"): "not a Croatian citizen",
    }[(client_type, lang)]


T = {
    "greeting": {
        "hr": "Pozdrav! Ja sam virtualni asistent Banke Demo. Mogu odgovoriti na pitanja o banci i njenim uslugama, "
              "izračunati mjesečnu ratu gotovinskog ili stambenog kredita te pokazati tečajnu listu HNB-a i preračunati iznos. Kako vam mogu pomoći?",
        "en": "Hello! I'm Banka Demo's virtual assistant. I can answer questions about the bank and its services, "
              "calculate the monthly payment for a cash or housing loan, and show the HNB exchange rate list or convert an amount. How can I help?",
    },
    "thanks": {
        "hr": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
        "en": "You're welcome! Let me know if there's anything else.",
    },
    "no_info": {
        "hr": "Nažalost, o tome nemam informaciju u dokumentaciji banke. Mogu pomoći s pitanjima o proizvodima i uslugama Banke Demo, "
              "izračunom rate kredita i tečajnom listom. Za ostalo se možete obratiti Kontakt centru na 0800 1234.",
        "en": "Sorry, I couldn't find that in the bank's documentation. I can help with questions about Banka Demo's products and services, "
              "loan payment calculations and exchange rates. For anything else, please contact our Contact Centre at 0800 1234.",
    },
    "rag_intro": {
        "hr": "Prema dokumentaciji banke:",
        "en": "Here's what I found in the bank's documentation (the source text is in Croatian):",
    },
    "source": {"hr": "Izvor", "en": "Source"},
    # --- kalkulator ---
    "ask_loan_type": {
        "hr": "Rado ću izračunati mjesečnu ratu. Radi li se o gotovinskom ili stambenom kreditu?",
        "en": "I'd be happy to calculate the monthly payment. Is it a cash loan or a housing loan?",
    },
    "ask_amount": {
        "hr": "Koliki iznos kredita želite? Za {name} iznos može biti od {min} do {max}.",
        "en": "How much would you like to borrow? For a {name}, the amount can be from {min} to {max}.",
    },
    "ask_months": {
        "hr": "Na koji rok otplate? Za {name} rok može biti {range}.",
        "en": "What repayment term would you like? For a {name}, the term can be {range}.",
    },
    "ask_client_type": {
        "hr": "Jeste li državljanin Republike Hrvatske? Kamatna stopa ovisi i o tome.",
        "en": "Are you a Croatian citizen? The interest rate also depends on that.",
    },
    "amount_out_of_range": {
        "hr": "Iznos od {value} nije moguć za {name}. Iznos mora biti od {min} do {max}. Koji iznos želite?",
        "en": "An amount of {value} isn't possible for a {name}. The amount must be between {min} and {max}. What amount would you like?",
    },
    "term_out_of_range": {
        "hr": "Rok od {value} nije moguć za {name}. Rok mora biti {range}. Na koji rok želite?",
        "en": "A term of {value} isn't possible for a {name}. The term must be {range}. What term would you like?",
    },
    "housing_not_for_foreigners": {
        "hr": "Nažalost, stambeni kredit u našoj banci mogu ugovoriti samo državljani Republike Hrvatske. "
              "Ispričavamo se zbog toga. Možete ugovoriti gotovinski nenamjenski kredit (od {min} do {max}, na rok do {max_term} mjeseci). "
              "Želite li da izračunam ratu za gotovinski kredit?",
        "en": "Unfortunately, our housing loans are available only to Croatian citizens, and we're sorry about that. "
              "You can apply for a cash loan (from {min} to {max}, with a term of up to {max_term} months). "
              "Would you like me to calculate the payment for a cash loan?",
    },
    "foreign_currency_loan": {
        "hr": "Naši krediti odobravaju se isključivo u eurima (EUR). {amount} po srednjem tečaju HNB-a na dan {date} iznosi {eur}. "
              "Želite li izračun za kredit od {eur_round}?",
        "en": "Our loans are granted in euros (EUR) only. {amount} at the HNB middle rate on {date} is {eur}. "
              "Would you like a calculation for a loan of {eur_round}?",
    },
    "foreign_currency_no_fx": {
        "hr": "Naši krediti odobravaju se isključivo u eurima (EUR), a tečajnu listu trenutno ne mogu dohvatiti. Molim upišite iznos u eurima.",
        "en": "Our loans are granted in euros (EUR) only, and I can't reach the exchange rate list right now. Please enter the amount in euros.",
    },
    "ask_amount_eur": {
        "hr": "U redu. Koji iznos u eurima želite?",
        "en": "Okay. What amount in euros would you like?",
    },
    "loan_cancelled": {
        "hr": "U redu, prekidam izračun. Ako trebate još nešto, tu sam.",
        "en": "Okay, I've stopped the calculation. Let me know if you need anything else.",
    },
    "result": {
        "hr": "Informativni izračun za {name}:\n"
              "  • iznos kredita: {amount}\n"
              "  • rok otplate: {term}\n"
              "  • klijent: {client}\n"
              "  • fiksna kamatna stopa: {rate}\n\n"
              "Mjesečna rata: {payment}\n\n"
              "Ako želite, mogu prikazati i ukupan iznos otplate, ukupnu kamatu i otplatni plan.\n"
              "Napomena: izračun je informativan i ne predstavlja ponudu banke.",
        "en": "Indicative calculation for a {name}:\n"
              "  • loan amount: {amount}\n"
              "  • repayment term: {term}\n"
              "  • client: {client}\n"
              "  • fixed interest rate: {rate}\n\n"
              "Monthly payment: {payment}\n\n"
              "If you'd like, I can also show the total amount repaid, total interest and a repayment schedule.\n"
              "Note: this calculation is for information only and is not an offer from the bank.",
    },
    "totals": {
        "hr": "Izračun za {name}, iznos {amount}, rok {term}, kamatna stopa {rate}:\n"
              "  • mjesečna rata: {payment}\n"
              "  • ukupno ćete otplatiti: {total}\n"
              "  • od toga kamata: {interest}",
        "en": "Calculation for a {name}, amount {amount}, term {term}, interest rate {rate}:\n"
              "  • monthly payment: {payment}\n"
              "  • total repaid: {total}\n"
              "  • of which interest: {interest}",
    },
    "offer_schedule": {
        "hr": "Želite li i otplatni plan po godinama?",
        "en": "Would you like the repayment schedule by year as well?",
    },
    "schedule_header": {
        "hr": "Otplatni plan po godinama:",
        "en": "Repayment schedule by year:",
    },
    "schedule_cols": {
        "hr": ("God.", "Uplaćeno", "Kamata", "Glavnica", "Ostatak duga"),
        "en": ("Year", "Paid", "Interest", "Principal", "Remaining"),
    },
    "schedule_csv": {
        "hr": "Plan po mjesecima spremljen je u datoteku: {path}",
        "en": "The monthly schedule has been saved to: {path}",
    },
    "schedule_csv_web": {
        "hr": "Cijeli plan po mjesecima možete preuzeti ovdje: [otplatni plan (CSV)]({url})",
        "en": "You can download the full monthly schedule here: [repayment schedule (CSV)]({url})",
    },
    # --- pojašnjenja ---
    "yes": {"hr": "Da", "en": "Yes"},
    "no": {"hr": "Ne", "en": "No"},
    "did_you_mean_one": {
        "hr": "Nisam siguran jesam li vas dobro razumio. Jeste li mislili: „{text}“?",
        "en": "I'm not sure I understood you correctly. Did you mean: \"{text}\"?",
    },
    "did_you_mean_many": {
        "hr": "Nisam siguran što vas točno zanima. Jeste li mislili na:",
        "en": "I'm not sure what exactly you're asking about. Did you mean:",
    },
    "pick_option": {
        "hr": "Odgovorite brojem ili napišite pitanje drugim riječima.",
        "en": "Reply with a number or rephrase your question.",
    },
    "rephrase": {
        "hr": "U redu. Možete li pitanje napisati malo drugačije? Pokušat ću ponovno.",
        "en": "Okay. Could you phrase your question a bit differently? I'll try again.",
    },
    "loan_type_cash": {"hr": "Gotovinski", "en": "Cash loan"},
    "loan_type_housing": {"hr": "Stambeni", "en": "Housing loan"},
    "qr_totals": {"hr": "Ukupan iznos i kamata", "en": "Total and interest"},
    "qr_schedule": {"hr": "Otplatni plan", "en": "Repayment schedule"},
    "no_result_yet": {
        "hr": "Još nemam izračun kredita. Recite mi vrstu kredita, iznos i rok pa ću izračunati ratu.",
        "en": "I don't have a loan calculation yet. Tell me the loan type, amount and term and I'll calculate the payment.",
    },
    # --- tečaj ---
    "fx_rate": {
        "hr": "Tečaj HNB-a za {cur} ({country}) na dan {date}, za 1 EUR:\n"
              "  • kupovni: {buy}\n  • srednji: {mid}\n  • prodajni: {sell}\n\n"
              "Želite li da vam preračunam neki iznos? Upišite npr. \"250 {cur} u EUR\" ili samo iznos u {cur}.",
        "en": "HNB exchange rate for {cur} ({country}) on {date}, per 1 EUR:\n"
              "  • buying: {buy}\n  • middle: {mid}\n  • selling: {sell}\n\n"
              "Would you like me to convert an amount? Type e.g. \"250 {cur} to EUR\" or just an amount in {cur}.",
    },
    "fx_list": {
        "hr": "Srednji tečaj HNB-a na dan {date} (jedinica strane valute za 1 EUR):\n{rows}\n\n"
              "Mogu preračunati bilo koji iznos, npr. \"100 USD u EUR\" ili \"koliko je 500 eura u francima\".",
        "en": "HNB middle rates on {date} (foreign currency units per 1 EUR):\n{rows}\n\n"
              "I can convert any amount, e.g. \"100 USD to EUR\" or \"how much is 500 euros in pounds\".",
    },
    "fx_converted": {
        "hr": "{src} = {dst} (srednji tečaj HNB-a na dan {date}).\n"
              "Napomena: banka pri stvarnoj kupoprodaji valute primjenjuje svoju tečajnu listu.",
        "en": "{src} = {dst} (HNB middle rate on {date}).\n"
              "Note: for actual currency exchange the bank applies its own exchange rate list.",
    },
    "fx_unavailable": {
        "hr": "Trenutno ne mogu dohvatiti tečajnu listu HNB-a. Pokušajte malo kasnije.",
        "en": "I can't reach the HNB exchange rate list right now. Please try again a bit later.",
    },
    "fx_unknown_currency": {
        "hr": "Valuta {cur} nije na tečajnoj listi HNB-a.",
        "en": "The currency {cur} isn't on the HNB exchange rate list.",
    },
}


def t(key, lang, **kw):
    return T[key][lang].format(**kw) if kw else T[key][lang]
