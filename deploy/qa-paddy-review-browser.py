from pathlib import Path
import re, shutil, subprocess, tempfile

html = Path('_site/index.html').read_text(encoding='utf-8')
style_m = re.search(r'<style id="bt-paddy-review-styles">(.*?)</style>', html, re.S)
parser_m = re.search(r'<script id="bt-paddy-text-import">(.*?)</script>', html, re.S)
review_m = re.search(r'<script id="bt-paddy-review">(.*?)</script>', html, re.S)
if not style_m or not parser_m or not review_m:
    raise SystemExit('Browser QA failed: Paddy parser/review style/script not found')

harness = f'''<!doctype html><html><head><meta charset="utf-8"><style>{style_m.group(1)}</style></head><body>
<div class="bt-import-modal" data-bt-import-mode="text"><div class="bt-import-actions"><button class="bt-use-import">Review parsed bets</button></div></div>
<script>{parser_m.group(1)}</script>
<script>{review_m.group(1)}</script>
<script>
const errors=[];
const raw=`Bet Builder (12 legs)
4.2
5.01
Leeds v Newcastle
20:00 14 September 2026
W
Yes
Both Teams To Score
W
Yoane Wissa
Player To Have 1 Or More Shots
Super Sub
W
Dominic Calvert-Lewin
Lukas Nmecha
Player To Have 1 Or More Shots
Super Sub
W
Harvey Barnes
Player To Have 1 Or More Shots
Super Sub
W
Jacob Murphy
Bazoumana Toure
Player To Have 1 Or More Shots
Super Sub
W
Anton Stach
Sean Longstaff
Player To Have 1 Or More Shots
Super Sub
W
Noah Okafor
Harry Wilson
Player To Have 1 Or More Shots
Super Sub
W
Nico Gonzalez
Sean Steur
Player To Commit 1 Or More Fouls
Super Sub
W
Dominic Calvert-Lewin
Lukas Nmecha
Player To Commit 1 Or More Fouls
Super Sub
W
Anton Stach
Sean Longstaff
Player To Commit 1 Or More Fouls
Super Sub
L
Yoane Wissa
Player To Be Fouled 1 Or More Times
Super Sub
W
Harvey Barnes
Player To Be Fouled 1 Or More Times
Super Sub
Stake
£7.00
Returns
£0.00`;
const parsed=window.__btParsePaddyText(raw)[0].parsed;
const expected=[
 ['Yes','Both Teams To Score','', 'Win'],
 ['Yoane Wissa','Player To Have 1 Or More Shots','', 'Win'],
 ['Dominic Calvert-Lewin','Player To Have 1 Or More Shots','Lukas Nmecha','Win'],
 ['Harvey Barnes','Player To Have 1 Or More Shots','', 'Win'],
 ['Jacob Murphy','Player To Have 1 Or More Shots','Bazoumana Toure','Win'],
 ['Anton Stach','Player To Have 1 Or More Shots','Sean Longstaff','Win'],
 ['Noah Okafor','Player To Have 1 Or More Shots','Harry Wilson','Win'],
 ['Nico Gonzalez','Player To Commit 1 Or More Fouls','Sean Steur','Win'],
 ['Dominic Calvert-Lewin','Player To Commit 1 Or More Fouls','Lukas Nmecha','Win'],
 ['Anton Stach','Player To Commit 1 Or More Fouls','Sean Longstaff','Win'],
 ['Yoane Wissa','Player To Be Fouled 1 Or More Times','', 'Loss'],
 ['Harvey Barnes','Player To Be Fouled 1 Or More Times','', 'Win']
];
if(parsed.legs.length!==12) errors.push('leg count '+parsed.legs.length);
expected.forEach((x,i)=>{{const l=parsed.legs[i]||{{}};if(l.selection!==x[0])errors.push(`leg ${{i+1}} selection ${{l.selection}}`);if(l.market!==x[1])errors.push(`leg ${{i+1}} market ${{l.market}}`);if((l._superSubReplacement||'')!==x[2])errors.push(`leg ${{i+1}} super ${{l._superSubReplacement||''}}`);if(l.result!==x[3])errors.push(`leg ${{i+1}} result ${{l.result}}`);}});
if(parsed.date!=='2026-09-14') errors.push('date '+parsed.date);

const modal=document.querySelector('.bt-import-modal');
modal.__btTextResults=[{{raw,parsed}}];
window.__btOpenPaddyReview(modal);
setTimeout(()=>{{
 const overlay=document.querySelector('.bt-paddy-review-overlay');
 if(!overlay) errors.push('overlay missing');
 const heads=[...document.querySelectorAll('.bt-pr-leg-table-head span')].map(x=>x.textContent.trim());
 if(JSON.stringify(heads)!==JSON.stringify(['Leg','Market','Selection','Super Sub','Result'])) errors.push('headers '+JSON.stringify(heads));
 const rows=[...document.querySelectorAll('.bt-pr-leg-row')];
 if(rows.length!==12) errors.push('review row count '+rows.length);
 expected.forEach((x,i)=>{{const row=rows[i];if(row?.querySelector('[data-lkey="market"]')?.value!==x[1])errors.push(`review ${{i+1}} market`);if(row?.querySelector('[data-lkey="selection"]')?.value!==x[0])errors.push(`review ${{i+1}} selection`);if((row?.querySelector('[data-lkey="_superSubReplacement"]')?.value||'')!==x[2])errors.push(`review ${{i+1}} super`);if(row?.querySelector('[data-lkey="result"]')?.value!==x[3])errors.push(`review ${{i+1}} result`);}});
 const out=document.createElement('div');out.id='qa-output';out.textContent=errors.length?'FAIL: '+errors.join(' | '):'PASS: exact Leeds v Newcastle 12-leg paste';document.body.appendChild(out);
 document.body.dataset.qa=errors.length?'fail':'pass';
}},100);
</script></body></html>'''

chrome = shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome:
    raise SystemExit('Browser QA failed: Chrome/Chromium not available on runner')

with tempfile.TemporaryDirectory() as td:
    f = Path(td)/'paddy-review-qa.html'
    f.write_text(harness, encoding='utf-8')
    r = subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1500','--dump-dom',f.as_uri()], text=True, capture_output=True, timeout=30)
    out = r.stdout + '\n' + r.stderr
    if r.returncode != 0 or 'data-qa="pass"' not in r.stdout:
        detail = re.search(r'<div id="qa-output">(.*?)</div>', r.stdout, re.S)
        raise SystemExit('Browser QA failed: '+(detail.group(1) if detail else out[-2500:]))

print('Browser QA passed: exact Leeds v Newcastle pasted builder parses all 12 legs and carries each Super Sub through to review')
