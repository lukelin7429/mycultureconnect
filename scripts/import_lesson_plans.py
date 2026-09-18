#!/usr/bin/env python3
"""
Import Dom Jones's 46-week curriculum PDF into data/lesson-plans.json.

    python3 scripts/import_lesson_plans.py <curriculum.pdf> [--weeks 1,2,3 | --weeks all]

Every run refreshes the unit list and the title, unit and date of all 46 weeks.
The full lesson body (target, vocabulary, the five timed blocks, media,
homework, CEFR, next-week routine) is imported only for --weeks (default: 1),
so a week can be checked on the site before the whole year goes live.

Anything already in the JSON that is not units/weeks — the page copy, the
author block — is kept as is. The PDF itself is never published: each week's
calendar date and class logistics stay in the JSON as metadata, the pages show
the lesson only. Requires PyMuPDF (fitz): it is the extractor that keeps → and
• intact.
"""
import json
import os
import re
import sys

import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "lesson-plans.json")

# The PDF sets unit names in caps; these are the same names in title case.
UNITS = {
    1: "English Reset & Power Vocabulary",
    2: "The World of Time",
    3: "Say It Better",
    4: "English in the Real World",
    5: "Storytellers",
    6: "How English Really Works",
    7: "English Through Media",
    8: "The English Challenge",
}

BLOCKS = [("0–10 min", "Homework review"), ("10–20 min", "Vocabulary"),
          ("20–35 min", "New learning"), ("35–50 min", "Fun / application"),
          ("50–57 min", "Challenge / exit ticket")]

HEAD_RE = re.compile(r"^WEEK (\d+) • (.+)$")
UNIT_RE = re.compile(r"^UNIT (\d+) • ")


def squash(s):
    return re.sub(r"\s+", " ", s or "").strip()


def read_pdf(path):
    """One flat, ordered list of items across all pages: ('text', y, str) for
    every text block and ('table', y, rows) for every ruled table, so a week
    that runs over a page break is still one contiguous run."""
    doc = fitz.open(path)
    items = []
    for pno, page in enumerate(doc):
        for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
            items.append(("text", (pno, y0), text))
        for t in page.find_tables().tables:
            items.append(("table", (pno, t.bbox[1]), t.extract()))
    items.sort(key=lambda it: it[1])
    return items


def split_weeks(items):
    """Cut the item stream at every WEEK heading; remember the unit in force."""
    weeks, unit, cur = [], None, None
    for kind, _, payload in items:
        if kind == "text":
            for line in payload.splitlines():
                m = UNIT_RE.match(line.strip())
                if m:
                    unit = int(m.group(1))
                m = HEAD_RE.match(line.strip())
                if m:
                    cur = {"n": int(m.group(1)), "unit": unit, "title": m.group(2).strip(),
                           "items": []}
                    weeks.append(cur)
        if cur is not None:
            cur["items"].append((kind, payload))
    return weeks


def week_text(w):
    return "\n".join(p for k, p in w["items"] if k == "text")


def week_tables(w):
    """Tables in order, with a page-split table (header on one page, body on
    the next) stitched back together."""
    out = []
    for k, rows in w["items"]:
        if k != "table":
            continue
        first = squash(rows[0][0] or "")
        is_header = bool(re.match(r"(LANGUAGE TARGET|\d+–\d+ MIN|. ?OPTIONAL VIDEO|NEXT-WEEK ROUTINE|CEFR)", first))
        if not is_header and out and len(out[-1]) == 1:
            out[-1] = out[-1] + rows
        else:
            out.append(rows)
    return out


def between(text, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.S)
    return squash(m.group(1)) if m else ""


DATE_RE = re.compile(r"WEEK \d+ • .+?\s+([A-Z][a-z]+day, [A-Z][a-z]+ \d+, \d{4})")


def week_date(w):
    m = DATE_RE.search(week_text(w))
    return m.group(1) if m else ""


def week_body(w):
    text = week_text(w)
    tables = week_tables(w)
    by = {}
    for rows in tables:
        first = squash(rows[0][0] or "")
        if first.startswith("LANGUAGE TARGET"):
            by["target"] = rows
        elif first.startswith("0–10 MIN"):
            by["blocks1"] = rows
        elif first.startswith("35–50 MIN"):
            by["blocks2"] = rows
        elif "OPTIONAL VIDEO" in first:
            by["media"] = rows
        elif first.startswith("NEXT-WEEK"):
            by["next"] = rows
    missing = [k for k in ("target", "blocks1", "blocks2", "media", "next")
               if k not in by or len(by[k]) < 2]
    if missing:
        raise ValueError(f"week {w['n']}: could not read {', '.join(missing)}")

    cell = lambda k, c: squash(by[k][1][c])
    vocab = [v.strip() for v in cell("target", 1).split(",") if v.strip()]
    return {
        "language_target": cell("target", 0),
        "vocabulary": vocab,
        "taiwan_connection": between(text, "SEASONAL / TAIWAN CONNECTION", "0–10 MIN"),
        "blocks": [{"time": t, "label": l, "text": txt} for (t, l), txt in zip(
            BLOCKS, [cell("blocks1", 0), cell("blocks1", 1), cell("blocks1", 2),
                     cell("blocks2", 0), cell("blocks2", 1)])],
        "media": cell("media", 0),
        "homework": cell("media", 1),
        "cefr": between(text, "SAME LESSON, DIFFERENT OUTPUT", "NEXT-WEEK ROUTINE"),
        "next_week": cell("next", 0),
    }


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pdf = sys.argv[1]
    want = "1"
    if "--weeks" in sys.argv:
        want = sys.argv[sys.argv.index("--weeks") + 1]
    weeks = split_weeks(read_pdf(pdf))
    if len(weeks) != 46:
        sys.exit(f"expected 46 week headings, found {len(weeks)}")
    wanted = set(range(1, 47)) if want == "all" else {int(x) for x in want.split(",")}

    data = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    old = {w["n"]: w for w in data.get("weeks", [])}
    out_weeks = []
    for w in weeks:
        rec = {"n": w["n"], "unit": w["unit"], "title": w["title"], "date": week_date(w)}
        if w["n"] in wanted:
            rec.update(week_body(w))
            print(f"  ✓ week {w['n']:02d}  {w['title']}  ({len(rec['vocabulary'])} words)")
        elif old.get(w["n"], {}).get("blocks"):
            rec = old[w["n"]]  # keep a body imported on an earlier run
        out_weeks.append(rec)

    data["units"] = [{"n": n, "title": t} for n, t in sorted(UNITS.items())]
    data["weeks"] = out_weeks
    data["total_weeks"] = 46
    live = sum(1 for w in out_weeks if w.get("blocks"))
    data["status"] = "complete" if live == 46 else "preparing"
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  → {os.path.relpath(OUT, ROOT)}: 46 titles, {live} full lesson(s)")


if __name__ == "__main__":
    main()
