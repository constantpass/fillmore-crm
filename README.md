# Fillmore CRM

A private, local property/deal tracker built around how you actually work:
projects, properties inside them, the 6-stage pipeline, and the same
call-then-letter cadence you already run by hand -- now tracked instead of
held in your head.

**This only runs on your own computer.** Nobody else can reach it, not
even on your home network -- it only listens on `127.0.0.1`, which is a
fancy way of saying "this machine, and only this machine." Your client
data never leaves your PC.

## Quick start (Mac, Windows, or Linux)

You need Python 3 installed (Mac and Linux already have it; on Windows,
get it from [python.org](https://www.python.org/downloads/) -- check "Add
Python to PATH" during install).

1. Download this repo (green **Code** button -> **Download ZIP**, then
   unzip it -- or `git clone` if you use git) and open a terminal/folder
   there.
2. **Mac or Linux:** run `./run.sh`
   **Windows:** double-click `run.bat`
3. First run takes ~30 seconds (it's setting up its own private Python
   environment right next to this folder -- doesn't touch anything else
   on your system). Your browser opens automatically to
   **http://127.0.0.1:8850/**.
4. Leave that terminal window open while you're using it -- closing it
   stops the app. Run the same command again any time to start it back up
   (fast after the first time).

Your data (`db.sqlite3`, photos) is stored outside this folder, so
re-downloading or moving this repo never touches your real records.

## Always-on background service (Linux/Arch only, optional)

If you're on this same Omarchy/Arch setup and want it running permanently
in the background instead of in a terminal window, use `./install.sh`
instead of `run.sh` -- it installs a systemd user service. Stop it with
`systemctl --user stop fillmore-crm.service`, start it again with
`systemctl --user start fillmore-crm.service`.

## What's in it right now

Sample data -- two fake projects with a few fake properties -- so you can
see how it works immediately. Delete/replace it with your real deals
whenever you're ready; nothing about the sample data is required to keep.

## Your letter template

To use the "Preview" and "Download filled .docx" buttons, copy your real
Word letter template to:

```
~/.local/share/fillmore-crm/letter_template.docx
```

Open it in Word and make sure it has these exact tokens wherever those
values belong:

```
{{name}}
{{address}}
{{date}}
```

For example:

```
Dear {{name}},

...

Property: {{address}}
{{date}}
```

Nothing else about your letter changes. This never rewrites your wording
-- it only fills in those three fields and leaves everything else exactly
as you wrote it.

## Back up your data

Click **"Download full backup (.zip)"** on the dashboard any time. It
bundles your whole database and every photo into one file you can save
anywhere (a USB drive, cloud storage, wherever). Do this regularly --
everything lives on this one computer, so this is your safety net.

## If you want to build on this yourself

The whole thing is a plain Flask app -- one Python file (`app/app.py`),
a SQLite database, and regular HTML templates. No build step, no
frameworks beyond Flask itself. If you ever want to add something (an
automated EarthPlat capture, a new view, anything), point your own coding
agent at the `app/` folder -- it's built to be read and extended, not just
used as-is.

## Uninstall

```
systemctl --user disable --now fillmore-crm.service
rm -rf ~/.local/share/fillmore-crm ~/.config/systemd/user/fillmore-crm.service
```

Your data is in `~/.local/share/fillmore-crm/` -- back it up first if you
want to keep it.
