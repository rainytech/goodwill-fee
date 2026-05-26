"""
Goodwill Tuition Centre — Fee logic layer (ported from fee_tracker_gui.py)
Pure Python, no GUI. Shared brain for the Kivy Android app.
Data model and all calculations match the PC version exactly.
"""

import os
import json
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────
# DATA FILE  (path is set by the app at runtime — Android sandbox)
# ──────────────────────────────────────────────────────────────

SEED = {
    "bank_balance": 50000.00,
    "students": [
        {
            "roll_no": "G001", "name": "Arun Kumar", "class": "Accountancy",
            "phone": "9876543210", "term": "LT",
            "join_date": "01/04/26", "end_date": "31/03/27",
            "fee_due": 15000, "fee_received": 15000,
            "last_payment_date": "05/04/26",
            "next_due_date": "", "next_due_amount": 0,
            "cycle": "one-time", "cycle_fee": 15000,
        },
        {
            "roll_no": "G002", "name": "Bhavya Nair", "class": "Income Tax",
            "phone": "9876501234", "term": "ST",
            "join_date": "01/05/26", "end_date": "31/07/26",
            "fee_due": 5000, "fee_received": 2000,
            "last_payment_date": "01/05/26",
            "next_due_date": "05/06/26", "next_due_amount": 1500,
            "cycle": "monthly", "cycle_fee": 1500,
        },
        {
            "roll_no": "G003", "name": "Cyril Joseph", "class": "Accountancy",
            "phone": "9123456789", "term": "LT",
            "join_date": "15/03/26", "end_date": "28/02/27",
            "fee_due": 15000, "fee_received": 0,
            "last_payment_date": "",
            "next_due_date": "05/06/26", "next_due_amount": 1500,
            "cycle": "monthly", "cycle_fee": 1500,
        },
    ],
}


def load_data(data_file):
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            d = json.load(f)
        for s in d.get("students", []):
            s.setdefault("next_due_date", "")
            s.setdefault("next_due_amount", 0)
            s.setdefault("cycle", "monthly")
            s.setdefault("cycle_fee", 0)
        return d
    save_data(data_file, SEED)
    return json.loads(json.dumps(SEED))


def save_data(data_file, d):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def parse_date(s):
    parts = s.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Date must be DD/MM/YY: got {s!r}")
    d, m, y = (int(p) for p in parts)
    if y < 100:
        y += 2000
    return date(y, m, d)


def fmt_date(s):
    return parse_date(s).strftime("%d/%m/%y")


def advance_date(d, cycle):
    if cycle == "weekly":
        return d + timedelta(days=7)
    if cycle == "monthly":
        today = date.today()
        y, m = today.year, today.month + 1
        if m > 12:
            m = 1
            y += 1
        return date(y, m, 5)
    return None


def next_fifth():
    today = date.today()
    if today.day <= 5:
        return date(today.year, today.month, 5)
    y, m = today.year, today.month + 1
    if m > 12:
        m = 1
        y += 1
    return date(y, m, 5)


def fifth_after(d):
    y, m = d.year, d.month + 1
    if m > 12:
        m = 1
        y += 1
    return date(y, m, 5)


def status_of(s):
    next_amt = s.get("next_due_amount", 0) or 0
    next_dt = s.get("next_due_date", "") or ""
    if next_amt <= 0 or not next_dt:
        return "PAID"
    try:
        if parse_date(next_dt) < date.today():
            return "OVERDUE"
    except ValueError:
        pass
    return "DUE"


def expected_receipts(students, target):
    total = 0
    for s in students:
        cyc = s.get("cycle", "monthly")
        fee = s.get("cycle_fee", 0) or 0
        ndd = s.get("next_due_date", "") or ""
        if cyc == "monthly" and ndd:
            try:
                if parse_date(ndd) <= target:
                    total += fee
            except ValueError:
                pass
        elif cyc == "weekly" and ndd:
            try:
                d = parse_date(ndd)
            except ValueError:
                continue
            while d <= target:
                total += fee
                d += timedelta(days=7)
    return total


def window_receipts(students, start, end):
    total = 0
    for s in students:
        cyc = s.get("cycle", "monthly")
        fee = s.get("cycle_fee", 0) or 0
        ndd = s.get("next_due_date", "") or ""
        if not ndd:
            continue
        try:
            d = parse_date(ndd)
        except ValueError:
            continue
        if cyc == "monthly":
            if (start is None or d > start) and d <= end:
                total += fee
        elif cyc == "weekly":
            while d <= end:
                if start is None or d > start:
                    total += fee
                d += timedelta(days=7)
    return total


def apply_receipt(s, amt):
    """Mutates student s for a received amount. Returns a message string.
    Same logic as the PC record_receipt (minus bank update, done by caller)."""
    s["fee_received"] = (s.get("fee_received", 0) or 0) + amt
    s["last_payment_date"] = date.today().strftime("%d/%m/%y")

    cycle = s.get("cycle", "monthly")
    cycle_fee = s.get("cycle_fee", 0) or 0
    current_due = s.get("next_due_amount", 0) or 0
    remaining = current_due - amt

    if cycle == "one-time":
        s["next_due_amount"] = max(remaining, 0)
        if s["next_due_amount"] == 0:
            s["next_due_date"] = ""
        return f"Rs {amt:,.2f} received from {s['name']}."

    if remaining > 0:
        s["next_due_amount"] = remaining
        return (f"Rs {amt:,.2f} received from {s['name']}.\n"
                f"Remaining this cycle: Rs {remaining:,.2f}")

    overpaid = -remaining
    try:
        base_dt = parse_date(s["next_due_date"]) if s.get("next_due_date") else date.today()
    except ValueError:
        base_dt = date.today()
    new_dt = advance_date(base_dt, cycle)
    s["next_due_date"] = new_dt.strftime("%d/%m/%y") if new_dt else ""
    s["next_due_amount"] = max(cycle_fee - overpaid, 0)
    return (f"Rs {amt:,.2f} received from {s['name']}.\n"
            f"Cycle paid. Next due: {s['next_due_date']} - Rs {s['next_due_amount']:,.2f}")
