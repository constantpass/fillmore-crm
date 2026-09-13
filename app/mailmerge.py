"""
Fills YOUR existing Word letter template with a property's name/address/date
-- nothing else. It never writes, rewrites, or rephrases a single word of
the letter itself. If the letter's wording needs to change, edit the .docx
template directly in Word; this module only ever substitutes placeholder
tokens.

Template requirements: your .docx should contain the literal tokens
{{name}}, {{address}}, and {{date}} wherever those values belong, e.g.

    Dear {{name}},
    ...
    Property: {{address}}
    {{date}}

This is the same token-filling logic validated in the earlier Quickshell
overlay build's fillmore-mailmerge.py CLI script, adapted here to be called
directly from Flask instead of run standalone against a JSON file.
"""

import re
from pathlib import Path

TOKEN_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def fill_paragraph_tokens(paragraph, values):
    """Replace {{token}} placeholders even when a token is split across
    multiple runs (common after anyone has ever edited the template text in
    Word). Concatenates the paragraph's run text, substitutes, then puts the
    whole result back in the first run and empties the rest."""
    full_text = "".join(run.text for run in paragraph.runs)
    if "{{" not in full_text:
        return

    def replace(match):
        key = match.group(1)
        return str(values.get(key, match.group(0)))

    new_text = TOKEN_PATTERN.sub(replace, full_text)
    if new_text == full_text:
        return

    if not paragraph.runs:
        return
    paragraph.runs[0].text = new_text
    for run in paragraph.runs[1:]:
        run.text = ""


def fill_template(template_path, values, out_path):
    import docx  # imported lazily so the rest of the app works without it installed

    document = docx.Document(str(template_path))
    for paragraph in document.paragraphs:
        fill_paragraph_tokens(paragraph, values)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    fill_paragraph_tokens(paragraph, values)
    document.save(str(out_path))


def safe_filename(name):
    return re.sub(r"[^\w\-]+", "_", name).strip("_") or "letter"


def render_letter_preview_text(template_path, values):
    """Plain-text rendering of the same merged fields, for the on-screen/
    print-preview view. Not a pixel-accurate docx-to-HTML conversion --
    just every paragraph's text (tokens filled) in reading order, which is
    sufficient for a quick reference/print without opening Word."""
    import docx

    document = docx.Document(str(template_path))
    lines = []
    for paragraph in document.paragraphs:
        text = "".join(run.text for run in paragraph.runs) or paragraph.text
        lines.append(TOKEN_PATTERN.sub(lambda m: str(values.get(m.group(1), m.group(0))), text))
    return "\n".join(lines)
