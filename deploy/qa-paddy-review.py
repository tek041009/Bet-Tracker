from pathlib import Path
import re, subprocess, tempfile

html = Path('_site/index.html').read_text(encoding='utf-8')

required = [
    'id="bt-paddy-text-import"',
    'id="bt-paddy-text-click-fix"',
    'id="bt-paddy-review"',
    'id="bt-paddy-review-button-fix"',
    'window.__btOpenPaddyReview(modal)',
    'Review ${results.length} parsed bets',
    'Review Paddy Power Import',
    'Import Approved Bets',
]
for token in required:
    if token not in html:
        raise SystemExit(f'QA failed: missing {token}')

text_match = re.search(r'<script id="bt-paddy-text-import">(.*?)</script>', html, re.S)
if not text_match:
    raise SystemExit('QA failed: Paddy text importer script missing')
text_js = text_match.group(1)

bad = 'e.preventDefault();e.stopImmediatePropagation();await importSelected(modal);return'
if bad in text_js:
    raise SystemExit('QA failed: Paddy text importer still directly imports from the review button')

route = 'e.preventDefault();e.stopImmediatePropagation();if(typeof window.__btOpenPaddyReview==="function")window.__btOpenPaddyReview(modal);return'
if text_js.count(route) != 1:
    raise SystemExit(f'QA failed: expected one explicit Paddy review route in text importer, found {text_js.count(route)}')

# Syntax-check every Paddy patch script in the built artifact, not just source patch files.
ids = [
    'bt-paddy-text-import',
    'bt-paddy-text-click-fix',
    'bt-paddy-review',
    'bt-paddy-review-button-fix',
]
for sid in ids:
    m = re.search(rf'<script id="{re.escape(sid)}">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit(f'QA failed: script {sid} not found')
    with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as f:
        f.write(m.group(1))
        name = f.name
    r = subprocess.run(['node', '--check', name], text=True, capture_output=True)
    Path(name).unlink(missing_ok=True)
    if r.returncode:
        raise SystemExit(f'QA failed: JS syntax error in {sid}: {r.stderr}')

print('Paddy review QA passed: review button routes to review, direct text import blocked, scripts syntax-valid')
