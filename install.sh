#!/usr/bin/env bash
# Fillmore CRM installer. Safe to re-run -- never overwrites your real data
# (db.sqlite3, photos, or your letter template) once they exist.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

APP_DEST="$HOME/.local/share/fillmore-crm/app"
DATA_DIR="$HOME/.local/share/fillmore-crm"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "== Fillmore CRM installer =="

echo "-- Checking for python-flask and python-docx..."
if ! python3 -c "import flask" >/dev/null 2>&1 || ! python3 -c "import docx" >/dev/null 2>&1; then
    echo "   Installing via pacman (you may be asked for your password)..."
    if command -v omarchy >/dev/null 2>&1; then
        omarchy pkg add python-flask python-docx || sudo pacman -S --noconfirm python-flask python-docx
    else
        sudo pacman -S --noconfirm python-flask python-docx
    fi
else
    echo "   Already installed."
fi

echo "-- Installing app code to $APP_DEST"
mkdir -p "$APP_DEST"
cp -r app/. "$APP_DEST/"

mkdir -p "$DATA_DIR/photos"

echo "-- Initializing database (safe if it already exists)"
python3 -c "
import sys
sys.path.insert(0, '$APP_DEST')
import os
os.environ['FILLMORE_DATA_DIR'] = '$DATA_DIR'
import app as fillmore_app
fillmore_app.init_db()
fillmore_app.migrate_db()
"

echo "-- Seeding sample data (skipped automatically if you already have real data)"
FILLMORE_DATA_DIR="$DATA_DIR" python3 "$APP_DEST/seed.py"

if [ ! -f "$DATA_DIR/letter_template.docx" ]; then
    echo ""
    echo "   NOTE: no letter template found yet."
    echo "   Copy your real Word letter template to:"
    echo "     $DATA_DIR/letter_template.docx"
    echo "   Make sure it contains the tokens {{name}}, {{address}}, {{date}}"
    echo "   wherever those values belong. The letter buttons won't work until you do this."
fi

echo "-- Installing the background service"
mkdir -p "$SYSTEMD_DIR"
cp systemd/fillmore-crm.service "$SYSTEMD_DIR/fillmore-crm.service"
systemctl --user daemon-reload
systemctl --user enable --now fillmore-crm.service

sleep 2
echo ""
echo "== Done =="
echo "Open this in your browser:  http://127.0.0.1:8850/"
echo "It'll keep running in the background -- closing the browser tab is fine,"
echo "the app stays ready. To stop it entirely: systemctl --user stop fillmore-crm.service"
