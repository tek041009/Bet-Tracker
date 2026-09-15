from pathlib import Path
import re, subprocess, tempfile

html = Path('_site/index.html').read_text(encoding='utf-8')

required = [
    'id="bt-paddy-text-import"',
    'id="bt-paddy-text-click-fix"',
    'id="bt-paddy-review"',
    'id="bt-paddy-review-button-fix"',
    'Review ${results.length} parsed bets',
    'Review ${esc(src[0]?.parsed?.bookmaker||"Paddy Power")} Import',
    'Import Approved Bets',
]
for token in required:
    if token not in html:
        raise SystemExit(f'QA failed: missing {token}')

# 1) Verify the *earliest/base* .bt-use-import capture handler routes both reviewed
# text modes to review before the generic screenshot importer can swallow the click.
core_route = 'if((modal?.dataset.btImportMode==="text"||modal?.dataset.btImportMode==="bet365text")&&typeof window.__btOpenPaddyReview==="function"){window.__btOpenPaddyReview(modal);return}if(modal)await useImportV6(modal);return'
if html.count(core_route) != 1:
    raise SystemExit(f'QA failed: live/base import handler is not routed through reviewed text import exactly once (found {html.count(core_route)})')

# 2) Verify the Paddy text importer itself does not bypass review.
text_match = re.search(r'<script id="bt-paddy-text-import">(.*?)</script>', html, re.S)
if not text_match:
    raise SystemExit('QA failed: Paddy text importer script missing')
text_js = text_match.group(1)
bad = 'e.preventDefault();e.stopImmediatePropagation();await importSelected(modal);return'
if bad in text_js:
    raise SystemExit('QA failed: Paddy text importer still directly imports from the review button')

# 3) Verify the review renderer helper matches how the review code actually calls it.
review_match = re.search(r'<script id="bt-paddy-review">(.*?)</script>', html, re.S)
if not review_match:
    raise SystemExit('QA failed: Paddy review script missing')
review_js = review_match.group(1)
correct_helper = 'const $=(s,r=document)=>r?.querySelector(s), $$=(r,s)=>[...(r?.querySelectorAll(s)||[])], esc=s=>'
broken_helper = 'const $=(r,s)=>r?.querySelector(s), $$=(r,s)=>[...(r?.querySelectorAll(s)||[])], esc=s=>'
if correct_helper not in review_js or broken_helper in review_js:
    raise SystemExit('QA failed: Paddy review selector helper is still incompatible with selector-first render calls')
if "$('.bt-pr-count',o)" not in review_js or "$('.bt-pr-close',overlay)" not in review_js:
    raise SystemExit('QA failed: expected review render/navigation bindings are missing')

# 4) Syntax-check every Paddy patch script in the final built artifact.
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

print('Paddy review QA passed: earliest live click route -> reviewed text import, renderer bindings valid, direct import blocked, scripts syntax-valid')
