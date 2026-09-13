"""Seeds realistic sample data so the app is demonstrable on first run.
Safe to run multiple times -- it checks for existing data first and does
nothing if any project already exists (never clobbers real data)."""

import os
import sqlite3
import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("FILLMORE_DATA_DIR", Path.home() / ".local/share/fillmore-crm"))
DB_PATH = DATA_DIR / "db.sqlite3"


def iso_days_ago(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()


def seed():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA foreign_keys = ON")

    existing = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    if existing:
        print("Sample data skipped -- projects already exist.")
        db.close()
        return

    # --- SAMPLE DATA -- replace/delete this via the app UI once you're using it for real ---
    p1 = db.execute(
        "INSERT INTO projects (name, notes) VALUES (?, ?)",
        ("Palmetto Ave Assemblage", "Three adjacent parcels, trying to assemble for one buyer."),
    ).lastrowid

    p2 = db.execute(
        "INSERT INTO projects (name, notes) VALUES (?, ?)",
        ("Bayshore Corridor", "Single-owner opportunity, client wants operate-not-flip."),
    ).lastrowid

    props = [
        (p1, "111 Palmetto Ave", "Marcus Webb", "(813) 555-0142", "", "no_contact", 27.9506, -82.4572, ""),
        (p1, "115 Palmetto Ave", "Renee Ostrowski", "(813) 555-0198", "", "contact", 27.9508, -82.4570, "Spoke 9/8 -- open to offers, wants comps first."),
        (p1, "119 Palmetto Ave", "Dana Reyes", "(813) 555-0110", "", "no_contact", 27.9510, -82.4568, ""),
        (p2, "220 Bayshore Dr", "Harold Finch", "(727) 555-0177", "Finch Holdings LLC", "loi", 27.7676, -82.6404, "LOI sent 9/5, awaiting response. Holds title under Finch Holdings LLC -- check SunBiz."),
        (p2, "224 Bayshore Dr", None, None, "", "no_contact", None, None, ""),
    ]
    prop_ids = {}
    for project_id, address, owner_name, owner_contact, business_name, phase, lat, lng, notes in props:
        pid = db.execute(
            "INSERT INTO properties (project_id, address, owner_name, owner_contact, business_name, phase, lat, lng, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, address, owner_name or "", owner_contact or "", business_name or "", phase, lat, lng, notes),
        ).lastrowid
        prop_ids[address] = pid

    # Marcus Webb: 2 calls logged, due for call 3 of 3 today.
    db.execute("INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)", (prop_ids["111 Palmetto Ave"], iso_days_ago(2), "no_answer"))
    db.execute("INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)", (prop_ids["111 Palmetto Ave"], iso_days_ago(1), "no_answer"))

    # Dana Reyes: 3 calls logged, no letter yet -- due for a letter today.
    db.execute("INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)", (prop_ids["119 Palmetto Ave"], iso_days_ago(3), "no_answer"))
    db.execute("INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)", (prop_ids["119 Palmetto Ave"], iso_days_ago(2), "no_answer"))
    db.execute("INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)", (prop_ids["119 Palmetto Ave"], iso_days_ago(1), "voicemail"))

    # Renee Ostrowski: contact made, one call logged historically, cadence no longer applies.
    db.execute("INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)", (prop_ids["115 Palmetto Ave"], iso_days_ago(4), "answered"))

    db.commit()
    db.close()
    print("Sample data seeded: 2 projects, 5 properties.")


if __name__ == "__main__":
    seed()
