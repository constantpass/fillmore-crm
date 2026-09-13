-- Fillmore CRM schema. Single-user, single-machine, local-only.
-- Phase is a plain text column (not a SQL enum) constrained in Python --
-- keep this file simple enough for a future coding agent to read in one pass.

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    owner_name TEXT DEFAULT '',
    owner_contact TEXT DEFAULT '',
    phase TEXT NOT NULL DEFAULT 'no_contact',
    lat REAL,
    lng REAL,
    earthplat_url TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    caption TEXT DEFAULT '',
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    called_on TEXT NOT NULL,   -- date, YYYY-MM-DD
    outcome TEXT DEFAULT 'no_answer'  -- no_answer | answered | voicemail
);

CREATE TABLE IF NOT EXISTS letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    sent_on TEXT NOT NULL,   -- date, YYYY-MM-DD
    priority INTEGER NOT NULL DEFAULT 0  -- 0/1 boolean
);

-- General activity log -- every save/edit on a property gets a row here,
-- distinct from calls/letters (which are the cadence-specific log). The
-- property detail page merges all three into one chronological History.
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,      -- created | phase | notes | location | photo | details
    detail TEXT DEFAULT '',
    at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_properties_project ON properties(project_id);
CREATE INDEX IF NOT EXISTS idx_photos_property ON photos(property_id);
CREATE INDEX IF NOT EXISTS idx_calls_property ON calls(property_id);
CREATE INDEX IF NOT EXISTS idx_letters_property ON letters(property_id);
CREATE INDEX IF NOT EXISTS idx_activity_property ON activity(property_id);
