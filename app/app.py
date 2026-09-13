"""
Fillmore CRM -- a local, single-user property/deal tracker for Zach
(Fillmore Real Estate Group). Flask + SQLite, bound to 127.0.0.1 ONLY.

WHY 127.0.0.1 ONLY: this holds real client names, addresses, and deal
details. Do not change host="0.0.0.0" anywhere below without also adding
real authentication -- this app has none today, and it is never supposed
to be reachable from another machine on the network or the internet.

Data lives in ~/.local/share/fillmore-crm/ (db.sqlite3, photos/,
letter_template.docx you provide yourself). See README.md.

Kept deliberately simple (plain sqlite3, no ORM, no build step) so this is
easy for a future coding agent -- including Zach's own -- to read in one
sitting and extend.
"""

import datetime
import io
import os
import re
import sqlite3
import zipfile
from pathlib import Path

from flask import (
    Flask,
    abort,
    g,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

import cadence
import links
import mailmerge

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("FILLMORE_DATA_DIR", Path.home() / ".local/share/fillmore-crm"))
PHOTOS_DIR = DATA_DIR / "photos"
DB_PATH = DATA_DIR / "db.sqlite3"
TEMPLATE_PATH = DATA_DIR / "letter_template.docx"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB, generous for a few photos at once


@app.context_processor
def inject_tools():
    return {"tools": links.STATIC_TOOLS}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(str(DB_PATH))
    with open(APP_DIR / "schema.sql", "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()
    db.close()


def migrate_db():
    """Idempotent ALTER TABLE additions for columns added after the initial
    schema -- schema.sql's CREATE TABLE IF NOT EXISTS can't add a column to
    an existing table, so anything beyond a brand-new table goes here.
    Always safe to call against a fresh DB too (columns just won't be missing)."""
    db = sqlite3.connect(str(DB_PATH))
    cols = [r[1] for r in db.execute("PRAGMA table_info(properties)").fetchall()]
    if "business_name" not in cols:
        db.execute("ALTER TABLE properties ADD COLUMN business_name TEXT DEFAULT ''")
    db.commit()
    db.close()


# ---------- helpers ----------

def log_activity(db, property_id, kind, detail=""):
    db.execute(
        "INSERT INTO activity (property_id, kind, detail) VALUES (?, ?, ?)",
        (property_id, kind, detail),
    )


def merged_history(db, property_id):
    """Calls + letters + general activity, one chronological list, newest
    first. Each entry is a dict with at least {kind, label, at}."""
    rows = []
    for r in db.execute("SELECT * FROM calls WHERE property_id=?", (property_id,)):
        rows.append({"kind": "call", "label": f"Call — {r['outcome'].replace('_', ' ')}", "at": r["called_on"]})
    for r in db.execute("SELECT * FROM letters WHERE property_id=?", (property_id,)):
        label = "Letter sent" + (" (priority)" if r["priority"] else "")
        rows.append({"kind": "letter", "label": label, "at": r["sent_on"]})
    for r in db.execute("SELECT * FROM activity WHERE property_id=?", (property_id,)):
        rows.append({"kind": r["kind"], "label": _activity_label(r), "at": r["at"]})
    rows.sort(key=lambda x: x["at"], reverse=True)
    return rows


_ACTIVITY_VERBS = {
    "created": "Property added",
    "phase": "Phase changed",
    "notes": "Notes saved",
    "location": "Map pin set",
    "photo": "Photo added",
    "details": "Details updated",
}


def _activity_label(row):
    verb = _ACTIVITY_VERBS.get(row["kind"], row["kind"].replace("_", " ").title())
    return f"{verb} — {row['detail']}" if row["detail"] else verb


def property_with_cadence(row, today=None):
    db = get_db()
    calls = [
        r["called_on"]
        for r in db.execute(
            "SELECT called_on FROM calls WHERE property_id=? ORDER BY called_on", (row["id"],)
        )
    ]
    letters = [
        r["sent_on"]
        for r in db.execute(
            "SELECT sent_on FROM letters WHERE property_id=? ORDER BY sent_on", (row["id"],)
        )
    ]
    status = cadence.status(row["phase"], calls, letters, today)
    d = dict(row)
    d["calls"] = calls
    d["letters"] = letters
    d["cadence"] = status
    return d


def all_properties_with_cadence(today=None):
    db = get_db()
    rows = db.execute(
        "SELECT properties.*, projects.name AS project_name FROM properties "
        "JOIN projects ON projects.id = properties.project_id ORDER BY properties.id"
    ).fetchall()
    return [property_with_cadence(r, today) for r in rows]


# ---------- routes: dashboard ----------

@app.route("/")
def index():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY name").fetchall()
    props = all_properties_with_cadence()

    phase_counts = {p: 0 for p in cadence.PHASES}
    for p in props:
        if p["phase"] in phase_counts:
            phase_counts[p["phase"]] += 1

    today_items = [p for p in props if p["cadence"]["due"]]

    projects_view = []
    for proj in projects:
        proj_props = [p for p in props if p["project_id"] == proj["id"]]
        projects_view.append({"project": dict(proj), "properties": proj_props})

    return render_template(
        "index.html",
        projects_view=projects_view,
        phase_counts=phase_counts,
        phase_labels=cadence.PHASE_LABELS,
        phases=cadence.PHASES,
        today_items=today_items,
        today=cadence.today_str(),
    )


@app.route("/project/new", methods=["POST"])
def project_new():
    db = get_db()
    name = request.form.get("name", "").strip()
    if not name:
        abort(400, "Project name is required.")
    db.execute("INSERT INTO projects (name, notes) VALUES (?, ?)", (name, request.form.get("notes", "")))
    db.commit()
    return redirect(url_for("index"))


# ---------- routes: property ----------

@app.route("/property/new", methods=["POST"])
def property_new():
    db = get_db()
    project_id = request.form.get("project_id")
    address = request.form.get("address", "").strip()
    if not project_id or not address:
        abort(400, "Project and address are required.")
    db.execute(
        "INSERT INTO properties (project_id, address, owner_name, owner_contact, business_name, earthplat_url, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            project_id,
            address,
            request.form.get("owner_name", ""),
            request.form.get("owner_contact", ""),
            request.form.get("business_name", ""),
            request.form.get("earthplat_url", ""),
            request.form.get("notes", ""),
        ),
    )
    new_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    log_activity(db, new_id, "created", address)
    db.commit()
    next_page = request.form.get("next", "detail")
    if next_page == "sheet":
        return redirect(url_for("sheet_view"))
    return redirect(url_for("property_detail", property_id=new_id))


@app.route("/property/<int:property_id>/delete", methods=["POST"])
def property_delete(property_id):
    db = get_db()
    row = db.execute("SELECT id FROM properties WHERE id=?", (property_id,)).fetchone()
    if row is None:
        abort(404)
    for photo in db.execute("SELECT filename FROM photos WHERE property_id=?", (property_id,)):
        photo_path = PHOTOS_DIR / photo["filename"]
        if photo_path.exists():
            photo_path.unlink()
    db.execute("DELETE FROM properties WHERE id=?", (property_id,))
    db.commit()
    next_page = request.form.get("next", "sheet")
    if next_page == "index":
        return redirect(url_for("index"))
    return redirect(url_for("sheet_view"))


@app.route("/property/<int:property_id>")
def property_detail(property_id):
    db = get_db()
    row = db.execute(
        "SELECT properties.*, projects.name AS project_name FROM properties "
        "JOIN projects ON projects.id = properties.project_id WHERE properties.id=?",
        (property_id,),
    ).fetchone()
    if row is None:
        abort(404)
    prop = property_with_cadence(row)

    siblings = db.execute(
        "SELECT * FROM properties WHERE project_id=? AND id!=? ORDER BY address",
        (row["project_id"], property_id),
    ).fetchall()

    photos = db.execute(
        "SELECT * FROM photos WHERE property_id=? ORDER BY uploaded_at", (property_id,)
    ).fetchall()

    history = merged_history(db, property_id)

    return render_template(
        "property.html",
        prop=prop,
        siblings=siblings,
        photos=photos,
        history=history,
        deep_links=links.property_deep_links(prop),
        phases=cadence.PHASES,
        phase_labels=cadence.PHASE_LABELS,
        today=cadence.today_str(),
        has_template=TEMPLATE_PATH.exists(),
    )


# ---------- routes: sheet (flat, searchable, cross-project) ----------

@app.route("/sheet")
def sheet_view():
    db = get_db()
    rows = db.execute(
        "SELECT properties.*, projects.name AS project_name FROM properties "
        "JOIN projects ON projects.id = properties.project_id ORDER BY projects.name, properties.address"
    ).fetchall()
    projects = db.execute("SELECT * FROM projects ORDER BY name").fetchall()
    return render_template(
        "sheet.html",
        rows=rows,
        projects=projects,
        phases=cadence.PHASES,
        phase_labels=cadence.PHASE_LABELS,
    )


@app.route("/property/<int:property_id>/phase", methods=["POST"])
def property_set_phase(property_id):
    db = get_db()
    phase = request.form.get("phase")
    if phase not in cadence.PHASES:
        abort(400, "Unknown phase.")
    db.execute("UPDATE properties SET phase=? WHERE id=?", (phase, property_id))
    log_activity(db, property_id, "phase", cadence.PHASE_LABELS.get(phase, phase))
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/property/<int:property_id>/notes", methods=["POST"])
def property_set_notes(property_id):
    db = get_db()
    db.execute("UPDATE properties SET notes=? WHERE id=?", (request.form.get("notes", ""), property_id))
    log_activity(db, property_id, "notes")
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/property/<int:property_id>/location", methods=["POST"])
def property_set_location(property_id):
    db = get_db()
    try:
        lat = float(request.form.get("lat"))
        lng = float(request.form.get("lng"))
    except (TypeError, ValueError):
        abort(400, "lat/lng must be numbers.")
    db.execute("UPDATE properties SET lat=?, lng=? WHERE id=?", (lat, lng, property_id))
    log_activity(db, property_id, "location", f"{lat:.4f}, {lng:.4f}")
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/property/<int:property_id>/details", methods=["POST"])
def property_set_details(property_id):
    db = get_db()
    row = db.execute("SELECT * FROM properties WHERE id=?", (property_id,)).fetchone()
    if row is None:
        abort(404)
    owner_name = request.form.get("owner_name", "").strip()
    owner_contact = request.form.get("owner_contact", "").strip()
    business_name = request.form.get("business_name", "").strip()

    changed = []
    if owner_name != (row["owner_name"] or ""):
        changed.append("owner name")
    if owner_contact != (row["owner_contact"] or ""):
        changed.append("owner contact")
    if business_name != (row["business_name"] or ""):
        changed.append("business name")

    db.execute(
        "UPDATE properties SET owner_name=?, owner_contact=?, business_name=? WHERE id=?",
        (owner_name, owner_contact, business_name, property_id),
    )
    if changed:
        log_activity(db, property_id, "details", ", ".join(changed))
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/property/<int:property_id>/call", methods=["POST"])
def property_log_call(property_id):
    db = get_db()
    outcome = request.form.get("outcome", "no_answer")
    db.execute(
        "INSERT INTO calls (property_id, called_on, outcome) VALUES (?, ?, ?)",
        (property_id, cadence.today_str(), outcome),
    )
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/property/<int:property_id>/letter/log", methods=["POST"])
def property_log_letter(property_id):
    db = get_db()
    priority = 1 if request.form.get("priority") == "1" else 0
    db.execute(
        "INSERT INTO letters (property_id, sent_on, priority) VALUES (?, ?, ?)",
        (property_id, cadence.today_str(), priority),
    )
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/property/<int:property_id>/photo", methods=["POST"])
def property_add_photo(property_id):
    db = get_db()
    file = request.files.get("photo")
    if not file or not file.filename:
        return redirect(url_for("property_detail", property_id=property_id))
    filename = secure_filename(f"{property_id}_{int(datetime.datetime.now().timestamp())}_{file.filename}")
    file.save(str(PHOTOS_DIR / filename))
    caption = request.form.get("caption", "")
    db.execute(
        "INSERT INTO photos (property_id, filename, caption) VALUES (?, ?, ?)",
        (property_id, filename, caption),
    )
    log_activity(db, property_id, "photo", caption or file.filename)
    db.commit()
    return redirect(url_for("property_detail", property_id=property_id))


@app.route("/photos/<path:filename>")
def serve_photo(filename):
    return send_from_directory(str(PHOTOS_DIR), filename)


# ---------- letters: preview + docx download ----------

def merge_values(prop_row):
    return {
        "name": prop_row["owner_name"] or "",
        "address": prop_row["address"] or "",
        "date": datetime.date.today().strftime("%B %-d, %Y"),
    }


@app.route("/property/<int:property_id>/letter/preview")
def property_letter_preview(property_id):
    db = get_db()
    row = db.execute("SELECT * FROM properties WHERE id=?", (property_id,)).fetchone()
    if row is None:
        abort(404)
    if not TEMPLATE_PATH.exists():
        return render_template("letter_preview.html", prop=row, text=None, no_template=True)
    text = mailmerge.render_letter_preview_text(TEMPLATE_PATH, merge_values(row))
    return render_template("letter_preview.html", prop=row, text=text, no_template=False)


@app.route("/property/<int:property_id>/letter/download")
def property_letter_download(property_id):
    db = get_db()
    row = db.execute("SELECT * FROM properties WHERE id=?", (property_id,)).fetchone()
    if row is None:
        abort(404)
    if not TEMPLATE_PATH.exists():
        abort(400, f"No letter template found at {TEMPLATE_PATH}. Drop your .docx there first (see README).")
    buf = io.BytesIO()
    tmp_path = DATA_DIR / f".tmp_letter_{property_id}.docx"
    mailmerge.fill_template(TEMPLATE_PATH, merge_values(row), tmp_path)
    with open(tmp_path, "rb") as f:
        buf.write(f.read())
    tmp_path.unlink(missing_ok=True)
    buf.seek(0)
    safe_name = mailmerge.safe_filename(row["owner_name"] or row["address"])
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"letter_{safe_name}.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ---------- backup / export ----------

@app.route("/export")
def export_backup():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, arcname="db.sqlite3")
        for photo in PHOTOS_DIR.glob("*"):
            zf.write(photo, arcname=f"photos/{photo.name}")
    buf.seek(0)
    stamp = datetime.date.today().isoformat()
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"fillmore-crm-backup-{stamp}.zip",
        mimetype="application/zip",
    )


if __name__ == "__main__":
    # schema.sql is CREATE TABLE IF NOT EXISTS only -- safe to run every
    # startup so a new table (e.g. activity) gets added to an existing
    # database without touching what's already there. migrate_db() handles
    # ALTER TABLE additions to tables that already existed before this.
    init_db()
    migrate_db()
    app.run(host="127.0.0.1", port=int(os.environ.get("FILLMORE_PORT", 8850)), debug=False)
