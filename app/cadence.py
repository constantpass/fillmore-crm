"""
Pure cadence math -- no automation lives here, this only ever computes what
a human should look at today. It never places a call or sends a letter.

Cadence rule (from the source interview): call a lead 2x/day for 3 days.
If still no answer, a letter goes out (the day of the 3rd unanswered call),
or same/next day "priority" mail for urgent properties. A property only
re-enters the cadence after a follow-up letter is logged. Once a property's
phase moves past "no_contact" (contact was actually made), the automated
cadence stops -- a live conversation isn't a scheduling problem anymore.

This mirrors the logic already validated in the earlier Quickshell overlay
build's CadenceLogic.js -- kept in exact lockstep on purpose so the rule
means the same thing everywhere it's used.
"""

import datetime

PHASES = ["no_contact", "contact", "loi", "contract", "deal", "closing"]
PHASE_LABELS = {
    "no_contact": "No Contact",
    "contact": "Contact",
    "loi": "LOI",
    "contract": "Contract",
    "deal": "Deal",
    "closing": "Closing",
}


def today_str():
    return datetime.date.today().isoformat()


def calls_since_last_letter(call_dates, letter_dates):
    if not letter_dates:
        return len(call_dates)
    last_letter = letter_dates[-1]
    return len([c for c in call_dates if c > last_letter])


def status(phase, call_dates, letter_dates, today=None):
    """call_dates and letter_dates are sorted lists of ISO date strings.
    Returns dict with due (bool), action ("call"|"letter"|None), label."""
    today = today or today_str()
    if phase != "no_contact":
        return {"due": False, "action": None, "label": ""}

    n = calls_since_last_letter(call_dates, letter_dates)
    called_today = today in call_dates

    if n >= 3:
        last_letter = letter_dates[-1] if letter_dates else None
        last_call = call_dates[-1] if call_dates else None
        already_sent_for_these_calls = (
            last_letter and last_call and last_letter >= last_call
        )
        if not already_sent_for_these_calls:
            return {"due": True, "action": "letter", "label": "Send letter"}
        return {"due": False, "action": None, "label": ""}

    if not called_today:
        return {
            "due": True,
            "action": "call",
            "label": f"Call ({n + 1} of 3)",
        }
    return {"due": False, "action": None, "label": ""}
