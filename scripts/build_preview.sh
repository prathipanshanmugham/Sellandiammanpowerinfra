#!/usr/bin/env bash
# Builds the hosted preview: the real backend runs in memory with sample data, its answers are saved,
# then the frontend is built in preview mode and the data and PDFs are copied next to it.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 demo/export.py demo/build
rm -rf demo/build/site
(cd frontend && VITE_DEMO=true npx vite build --base=./ --outDir ../demo/build/site --emptyOutDir)
cp -r demo/build/data demo/build/pdf demo/build/site/
# page images, so the PDFs show inside the preview even where the browser can't display a PDF in a frame
python3 - <<'PY'
import json, subprocess, pathlib
site = pathlib.Path("demo/build/site")
pages = {}
for pdf in sorted((site / "pdf").glob("*.pdf")):
    subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", "quality=82", "-r", "96", str(pdf), str(site / "pdf" / pdf.stem)], check=True)
    pages[pdf.stem] = sorted(p.name for p in (site / "pdf").glob(f"{pdf.stem}-*.jpg"))
(site / "data" / "pdf_pages.json").write_text(json.dumps(pages))
print("pdf pages:", sum(len(v) for v in pages.values()))
PY
# artifact.html: the same page without the document wrapper, for hosts that add their own (the claude.ai preview)
python3 - <<'PY'
import re, pathlib
site = pathlib.Path("demo/build/site")
html = (site / "index.html").read_text()
head = re.search(r"<head>(.*)</head>", html, re.S).group(1)
keep = [l.strip() for l in head.splitlines() if l.strip() and "charset" not in l and 'name="viewport"' not in l and "apple-touch-icon" not in l]
keep = [re.sub(r"<title>.*</title>", "<title>Sellandiamman Power Infra</title>", l) for l in keep]
keep = [l.replace('rel="stylesheet" crossorigin', 'rel="stylesheet"') for l in keep]
(site / "artifact.html").write_text("\n".join(keep) + '\n<div id="root"></div>\n')
PY
echo "Preview ready in demo/build/site (open index.html through any static server)"
