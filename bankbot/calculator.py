"""Izračun kredita. Čista matematika i pravila iz rates.json, bez LLM-a.

Svi krediti su u EUR, s fiksnom kamatnom stopom i jednakim mjesečnim anuitetima.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache

from .config import RATES_FILE

LOAN_TYPES = ("gotovinski", "stambeni")
CLIENT_TYPES = ("drzavljanin", "nedrzavljanin")


class LoanError(ValueError):
    """Zahtjev se ne može izračunati. `code` govori zašto, `details` nosi granice."""

    def __init__(self, code, **details):
        super().__init__(code)
        self.code = code
        self.details = details


@lru_cache(maxsize=1)
def load_rates():
    with open(RATES_FILE, encoding="utf-8") as f:
        return json.load(f)


def product(loan_type):
    return load_rates()["proizvodi"][loan_type]


def find_rate(loan_type, client_type, amount, months):
    """Vraća godišnju kamatnu stopu u % ili diže LoanError."""
    if loan_type not in LOAN_TYPES:
        raise LoanError("unknown_type")
    if client_type not in CLIENT_TYPES:
        raise LoanError("unknown_client")

    p = product(loan_type)
    if client_type not in p["dostupno_za"]:
        raise LoanError("not_available_for_client", loan_type=loan_type, client_type=client_type)
    if not p["min_iznos"] <= amount <= p["max_iznos"]:
        raise LoanError("amount_out_of_range", min=p["min_iznos"], max=p["max_iznos"])
    if not p["min_rok_mjeseci"] <= months <= p["max_rok_mjeseci"]:
        raise LoanError("term_out_of_range", min=p["min_rok_mjeseci"], max=p["max_rok_mjeseci"])

    # Retci su poredani od najkraćeg roka i najmanjeg iznosa; prvi koji pokriva zahtjev vrijedi.
    for row in p["stope"]:
        if row["klijent"] == client_type and months <= row["rok_do_mjeseci"] and amount <= row["iznos_do"]:
            return row["stopa"]
    raise LoanError("no_rate")


def annuity(principal, annual_rate_pct, months):
    """Mjesečni anuitet: A = P * r(1+r)^n / ((1+r)^n - 1)."""
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return principal / months
    f = (1 + r) ** months
    return principal * r * f / (f - 1)


@dataclass
class LoanResult:
    loan_type: str
    client_type: str
    amount: float
    months: int
    rate: float
    monthly_payment: float
    schedule: list = field(default_factory=list)

    @property
    def total_paid(self):
        return round(sum(row["rata"] for row in self.schedule), 2)

    @property
    def total_interest(self):
        return round(sum(row["kamata"] for row in self.schedule), 2)

    def yearly_summary(self):
        years = []
        for i in range(0, len(self.schedule), 12):
            chunk = self.schedule[i : i + 12]
            years.append(
                {
                    "godina": i // 12 + 1,
                    "uplaceno": round(sum(r["rata"] for r in chunk), 2),
                    "kamata": round(sum(r["kamata"] for r in chunk), 2),
                    "glavnica": round(sum(r["glavnica"] for r in chunk), 2),
                    "ostatak": chunk[-1]["ostatak"],
                }
            )
        return years


def amortization_schedule(principal, annual_rate_pct, months):
    """Otplatni plan po mjesecima. Zadnja rata poravnava razliku od zaokruživanja."""
    r = annual_rate_pct / 100 / 12
    payment = round(annuity(principal, annual_rate_pct, months), 2)
    balance = round(principal, 2)
    rows = []
    for m in range(1, months + 1):
        interest = round(balance * r, 2)
        principal_part = round(payment - interest, 2)
        if m == months:
            principal_part = balance
        balance = round(balance - principal_part, 2)
        rows.append(
            {
                "mjesec": m,
                "rata": round(interest + principal_part, 2),
                "kamata": interest,
                "glavnica": principal_part,
                "ostatak": balance,
            }
        )
    return rows


def calculate(loan_type, client_type, amount, months):
    rate = find_rate(loan_type, client_type, amount, months)
    return LoanResult(
        loan_type=loan_type,
        client_type=client_type,
        amount=float(amount),
        months=int(months),
        rate=rate,
        monthly_payment=round(annuity(amount, rate, months), 2),
        schedule=amortization_schedule(amount, rate, months),
    )
