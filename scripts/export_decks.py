#!/usr/bin/env python3
"""Export a deck to PDF and PPTX, so a classroom PC can run it without a browser.

    python3 scripts/export_decks.py                 # every 115 interactive deck
    python3 scripts/export_decks.py beidou-jh-sdg2-zerohunger

Writes slides/<slug>/<slug>.pdf and slides/<slug>/<slug>.pptx.

Two things worth knowing:

* Click-to-reveal survives the export. A slide with a hidden answer is written
  out TWICE — once with the answer still hidden, once revealed — so advancing
  the PDF/PPTX reveals the answer exactly like tapping does on the web deck.
  The answer is never printed next to the question.
* The PPTX holds one full-bleed image per slide rather than editable text. That
  is deliberate: a school PC has no PingFang TC, and real text boxes would
  reflow and break the layout. Images look identical everywhere.

Needs Google Chrome (headless print), PyMuPDF and python-pptx.
"""
import os, re, sys, glob, time, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
CANVAS_W, CANVAS_H = 1200, 675


def slide_blocks(html):
    """Pull out each <div class="deck-slide">…</div> with brace-free depth counting."""
    out, i = [], 0
    while True:
        m = re.compile(r'<div class="deck-slide"[^>]*>').search(html, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth:
            nxt = re.compile(r'<div\b|</div>').search(html, j)
            if not nxt:
                return out
            depth += 1 if nxt.group(0) != '</div>' else -1
            j = nxt.end()
        out.append(html[m.end():j - len('</div>')])
        i = j


def reveal(block):
    """Same slide with every hidden answer shown."""
    b = re.sub(r'(<div class="[^"]*?)"([^>]*data-reveal-group)', r'\1 is-revealed"\2', block)
    b = re.sub(r'(class=")((?:[^"]*\s)?hs-tf)(["\s])', r'\1\2 is-revealed\3', b)
    b = re.sub(r'(class=")((?:[^"]*\s)?hs-hintbtn)(["\s])', r'\1\2 is-revealed\3', b)
    b = re.sub(r'(<[^>]*\bdata-reveal-group\b[^>]*class=")', r'\1is-revealed ', b)
    return b


def has_hidden_answer(block):
    return ('data-reveal-group' in block or 'hs-tf ' in block
            or 'hs-tf"' in block or 'hs-hintbtn' in block)


PRINT_PAGE = """<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="file://{css}">
<style>
  @page {{ size: {w}px {h}px; margin: 0; }}
  html, body {{ margin:0; padding:0; background:#fff; }}
  .pg {{ width:{w}px; height:{h}px; overflow:hidden; page-break-after:always;
         display:flex; align-items:center; justify-content:center; background:#000; }}
  .pg:last-child {{ page-break-after:auto; }}
  /* the canvas is scaled by deck.js on the web; in print it is 1:1 */
  .hs-canvas {{ --hs-scale:1; transform:none !important; }}
  .pg > img {{ width:100%; height:100%; object-fit:contain; }}
  /* no .deck.anim-ready here, so every entrance animation is already finished */
</style>
{pages}
"""


def build_print_html(slug, dest_dir):
    src = os.path.join(ROOT, 'slides', slug, 'index.html')
    html = open(src, encoding='utf-8').read()
    blocks = slide_blocks(html)
    if not blocks:
        raise SystemExit(f'{slug}: no slides found')

    pages, revealed_pages = [], 0
    for b in blocks:
        pages.append('<div class="pg">' + b + '</div>')
        if has_hidden_answer(b):
            pages.append('<div class="pg">' + reveal(b) + '</div>')
            revealed_pages += 1

    body = '\n'.join(pages)
    # /assets/... only resolves over http; make it absolute for file:// printing
    body = body.replace('src="/assets/', 'src="file://' + ROOT + '/assets/')
    body = body.replace('href="/assets/', 'href="file://' + ROOT + '/assets/')

    out = os.path.join(dest_dir, 'print.html')
    open(out, 'w', encoding='utf-8').write(PRINT_PAGE.format(
        css=os.path.join(ROOT, 'assets', 'css', 'deck.css'),
        w=CANVAS_W, h=CANVAS_H, pages=body))
    return out, len(blocks), revealed_pages


def to_pdf(print_html, pdf_path, timeout=180):
    """Headless Chrome writes the PDF and then often refuses to exit on macOS,
    so wait for the file to stop growing and stop the process ourselves."""
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with tempfile.TemporaryDirectory() as prof:
        proc = subprocess.Popen([
            CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
            '--user-data-dir=' + prof, '--allow-file-access-from-files',
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=20000', '--no-pdf-header-footer',
            '--print-to-pdf=' + pdf_path, 'file://' + print_html,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        last, steady, deadline = -1, 0, time.time() + timeout
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else -1
            steady = steady + 1 if size > 0 and size == last else 0
            if steady >= 3:                     # 1.5 s with no growth = done
                break
            last = size
            time.sleep(0.5)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 1024:
        raise SystemExit('Chrome produced no PDF for ' + pdf_path)


def to_pptx(pdf_path, pptx_path, scale=2.0):
    import fitz
    from pptx import Presentation
    from pptx.util import Inches

    doc = fitz.open(pdf_path)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    with tempfile.TemporaryDirectory() as tmp:
        for n, page in enumerate(doc):
            png = os.path.join(tmp, f'{n:03d}.png')
            page.get_pixmap(matrix=fitz.Matrix(scale, scale)).save(png)
            s = prs.slides.add_slide(blank)
            s.shapes.add_picture(png, 0, 0, prs.slide_width, prs.slide_height)
    prs.save(pptx_path)
    return len(doc)


def is_stale(slug):
    d = os.path.join(ROOT, 'slides', slug)
    src = os.path.join(d, 'index.html')
    outs = [os.path.join(d, slug + '.pdf'), os.path.join(d, slug + '.pptx')]
    if not all(os.path.exists(o) for o in outs):
        return True
    return any(os.path.getmtime(o) < os.path.getmtime(src) for o in outs)


def export(slug):
    out_dir = os.path.join(ROOT, 'slides', slug)
    pdf = os.path.join(out_dir, slug + '.pdf')
    pptx = os.path.join(out_dir, slug + '.pptx')
    with tempfile.TemporaryDirectory() as tmp:
        print_html, n_slides, n_revealed = build_print_html(slug, tmp)
        to_pdf(print_html, pdf)
        n_pages = to_pptx(pdf, pptx)
    print(f'  ✓ {slug}: {n_slides} slides (+{n_revealed} answer pages) '
          f'-> {n_pages}p  pdf {os.path.getsize(pdf)//1024}KB  '
          f'pptx {os.path.getsize(pptx)//1024}KB')
    return {'pdf': os.path.basename(pdf), 'pptx': os.path.basename(pptx), 'pages': n_pages}


def main():
    force = '--force' in sys.argv
    slugs = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not slugs:
        slugs = [os.path.basename(os.path.dirname(p))
                 for p in glob.glob(os.path.join(ROOT, 'slides', '*', 'index.html'))
                 if 'hs-canvas' in open(p, encoding='utf-8').read()]
    if not os.path.exists(CHROME):
        raise SystemExit('Google Chrome not found at ' + CHROME)
    todo = sorted(slugs if force else [s for s in slugs if is_stale(s)])
    skipped = len(slugs) - len(todo)
    print(f'exporting {len(todo)} deck(s)' + (f', {skipped} already current' if skipped else ''))
    for s in todo:
        export(s)


if __name__ == '__main__':
    main()
