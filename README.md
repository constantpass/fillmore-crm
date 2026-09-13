# Fillmore CRM

A private, local property/deal tracker built around how you actually work:
projects, properties inside them, the 6-stage pipeline, and the same
call-then-letter cadence you already run by hand -- now tracked instead of
held in your head.

**This only runs on your own computer.** Nobody else can reach it, not
even on your home network -- it only listens on `127.0.0.1`, which is a
fancy way of saying "this machine, and only this machine." Your client
data never leaves your PC.

## Install (one time)

1. Open a terminal in this folder (the one with `install.sh` in it).
2. Run:
   ```
   ./install.sh
   ```
3. It'll ask for your password once (to install two small pieces of
   software it needs -- Flask and python-docx, both just tools, nothing
   that touches your data).
4. When it finishes, open **http://127.0.0.1:8850/** in your browser.

That's it. It keeps running quietly in the background from now on --
closing the browser tab does NOT turn it off, so it's always ready. If you
ever want to fully stop it: `systemctl --user stop fillmore-crm.service`.
To start it again: `systemctl --user start fillmore-crm.service`.

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
