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
const rawBuilder=`Bet Builder (3 legs)\n5.0\nMan Utd v Test\n20:00 15 September 2026\nW\nSuper Sub\nBryan MbeumosvgShea Lacey\nPlayer To Have 2 Or More Shots\nL\nSuper SubWin More\nDominic Calvert-Lewin\nsvg\nLukas Nmecha\nPlayer To Have 2 Or More Shots\nW\nBruno Fernandes\nPlayer To Have 1 Or More Shots\nStake\n£5.00\nReturns\n£25.00\nBet ID: O/1/2`;
const parsed=window.__btParsePaddyText(rawBuilder)[0].parsed;
if(parsed.legs.length!==3) errors.push('builder leg count '+parsed.legs.length);
if(parsed.legs[0]?.selection!=='Bryan Mbeumo') errors.push('combined selection '+parsed.legs[0]?.selection);
if(parsed.legs[0]?._superSubReplacement!=='Shea Lacey') errors.push('combined super '+parsed.legs[0]?._superSubReplacement);
if(parsed.legs[1]?.selection!=='Dominic Calvert-Lewin') errors.push('split selection '+parsed.legs[1]?.selection);
if(parsed.legs[1]?._superSubReplacement!=='Lukas Nmecha') errors.push('split super '+parsed.legs[1]?._superSubReplacement);
if(parsed.legs[2]?._superSubReplacement!=='') errors.push('normal super not blank');

const rawAccumulator=`Accumulator (1 leg)\n2.0\nW\nSuper Sub\nJacob Murphy\nsvgBazoumana Toure\n1.50\nPlayer To Have 1 Or More Shots - Newcastle v Test\n15:00 15 September 2026\nStake\n£5.00\nReturns\n£10.00\nBet ID: O/1/3`;
const acc=window.__btParsePaddyText(rawAccumulator)[0].parsed;
if(acc.legs[0]?.selection!=='Jacob Murphy') errors.push('acc selection '+acc.legs[0]?.selection);
if(acc.legs[0]?._superSubReplacement!=='Bazoumana Toure') errors.push('acc super '+acc.legs[0]?._superSubReplacement);

const modal=document.querySelector('.bt-import-modal');
modal.__btTextResults=[{{raw:rawBuilder,parsed}}];
window.__btOpenPaddyReview(modal);
setTimeout(()=>{{
 const overlay=document.querySelector('.bt-paddy-review-overlay');
 if(!overlay) errors.push('overlay missing');
 const heads=[...document.querySelectorAll('.bt-pr-leg-table-head span')].map(x=>x.textContent.trim());
 if(JSON.stringify(heads)!==JSON.stringify(['Leg','Market','Selection','Super Sub','Result'])) errors.push('headers '+JSON.stringify(heads));
 const rows=[...document.querySelectorAll('.bt-pr-leg-row')];
 if(rows.length!==3) errors.push('row count '+rows.length);
 if(rows[0]?.querySelector('[data-lkey="_superSubReplacement"]')?.value!=='Shea Lacey') errors.push('review combined super');
 if(rows[1]?.querySelector('[data-lkey="_superSubReplacement"]')?.value!=='Lukas Nmecha') errors.push('review split super');
 if(rows[2]?.querySelector('[data-lkey="_superSubReplacement"]')?.value!=='') errors.push('review blank super');
 if(rows[0]?.querySelector('[data-lkey="market"]')?.value!=='Player To Have 2 Or More Shots') errors.push('market');
 if(rows[0]?.querySelector('[data-lkey="selection"]')?.value!=='Bryan Mbeumo') errors.push('selection');
 if(rows[0]?.querySelector('[data-lkey="result"]')?.value!=='Win') errors.push('result');
 if(document.querySelector('[data-lkey="event"]')) errors.push('fixture still shown');
 if(document.querySelector('[data-lkey="odds"]')) errors.push('odds still shown');
 const out=document.createElement('div');out.id='qa-output';out.textContent=errors.length?'FAIL: '+errors.join(' | '):'PASS: parser -> review Super Sub values';document.body.appendChild(out);
 document.body.dataset.qa=errors.length?'fail':'pass';
}},80);
</script></body></html>'''

chrome = shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome:
    raise SystemExit('Browser QA failed: Chrome/Chromium not available on runner')

with tempfile.TemporaryDirectory() as td:
    f = Path(td)/'paddy-review-qa.html'
    f.write_text(harness, encoding='utf-8')
    r = subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1200','--dump-dom',f.as_uri()], text=True, capture_output=True, timeout=30)
    out = r.stdout + '\n' + r.stderr
    if r.returncode != 0 or 'data-qa="pass"' not in r.stdout:
        detail = re.search(r'<div id="qa-output">(.*?)</div>', r.stdout, re.S)
        raise SystemExit('Browser QA failed: '+(detail.group(1) if detail else out[-2000:]))

print('Browser QA passed: actual Paddy parser carries combined/split Super Subs through to review; normal Super Sub cells stay blank')
