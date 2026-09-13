#!/usr/bin/env bash
# Fillmore CRM -- portable runner (Mac/Linux). No install, no sudo, no
# system packages: everything lives in a local venv folder next to this
# script, and your data lives in ~/.local/share/fillmore-crm (Linux/Mac)
# so re-cloning or moving this folder never touches your real records.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV_DIR=".venv"
DATA_DIR="${FILLMORE_DATA_DIR:-$HOME/.local/share/fillmore-crm}"

if [ ! -d "$VENV_DIR" ]; then
    echo "== First run: setting up (one-time, ~30s) =="
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -q -r requirements.txt

mkdir -p "$DATA_DIR/photos"
export FILLMORE_DATA_DIR="$DATA_DIR"

"$VENV_DIR/bin/python" -c "
import sys; sys.path.insert(0, 'app')
import app as fillmore_app
fillmore_app.init_db()
fillmore_app.migrate_db()
"
"$VENV_DIR/bin/python" app/seed.py

echo "== Starting Fillmore CRM =="
echo "Opening http://127.0.0.1:${FILLMORE_PORT:-8850}/ in a moment..."
( sleep 1.5
  URL="http://127.0.0.1:${FILLMORE_PORT:-8850}/"
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  fi
) &

cd app
exec "../$VENV_DIR/bin/python" app.py
