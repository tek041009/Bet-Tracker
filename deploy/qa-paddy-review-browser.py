from pathlib import Path
import re, shutil, subprocess, tempfile

html = Path('_site/index.html').read_text(encoding='utf-8')
style_m = re.search(r'<style id="bt-paddy-review-styles">(.*?)</style>', html, re.S)
script_m = re.search(r'<script id="bt-paddy-review">(.*?)</script>', html, re.S)
if not style_m or not script_m:
    raise SystemExit('Browser QA failed: Paddy review style/script not found')

harness = f'''<!doctype html><html><head><meta charset="utf-8"><style>{style_m.group(1)}</style></head><body>
<div class="bt-import-modal" data-bt-import-mode="text"><button class="bt-use-import">Review parsed bets</button></div>
<script>{script_m.group(1)}</script>
<script>
const modal=document.querySelector('.bt-import-modal');
modal.__btTextResults=[{{raw:'',parsed:{{_betId:'O/1/2',date:'2026-09-15',betFormat:'Bet Builder',result:'Win',stake:5,returns:10,free:'',_receiptOdds:2,notes:'',source:'Paddy Power Text Import',_parseIssues:[],legs:[
{{sport:'Football',event:'Man Utd v Test',market:'Player To Have 2 Or More Shots',selection:'Bryan Mbeumo',odds:null,result:'Win',_superSubReplacement:'Shea Lacey'}},
{{sport:'Football',event:'Man Utd v Test',market:'Match Odds',selection:'Man Utd',odds:null,result:'Loss',_superSubReplacement:''}}
]}}}}];
window.__btOpenPaddyReview(modal);
setTimeout(()=>{{
 const errors=[];
 const overlay=document.querySelector('.bt-paddy-review-overlay');
 if(!overlay) errors.push('overlay missing');
 const heads=[...document.querySelectorAll('.bt-pr-leg-table-head span')].map(x=>x.textContent.trim());
 if(JSON.stringify(heads)!==JSON.stringify(['Leg','Market','Selection','Super Sub','Result'])) errors.push('headers '+JSON.stringify(heads));
 const rows=[...document.querySelectorAll('.bt-pr-leg-row')];
 if(rows.length!==2) errors.push('row count '+rows.length);
 const first=rows[0]; const second=rows[1];
 if(first?.querySelector('[data-lkey="market"]')?.value!=='Player To Have 2 Or More Shots') errors.push('market');
 if(first?.querySelector('[data-lkey="selection"]')?.value!=='Bryan Mbeumo') errors.push('selection');
 if(first?.querySelector('[data-lkey="_superSubReplacement"]')?.value!=='Shea Lacey') errors.push('super sub value');
 if(second?.querySelector('[data-lkey="_superSubReplacement"]')?.value!=='') errors.push('blank super sub');
 if(first?.querySelector('[data-lkey="result"]')?.value!=='Win') errors.push('result');
 if(document.querySelector('[data-lkey="event"]')) errors.push('fixture still shown');
 if(document.querySelector('[data-lkey="odds"]')) errors.push('odds still shown');
 const out=document.createElement('div');out.id='qa-output';out.textContent=errors.length?'FAIL: '+errors.join(' | '):'PASS: Leg | Market | Selection | Super Sub | Result';document.body.appendChild(out);
 document.body.dataset.qa=errors.length?'fail':'pass';
}},50);
</script></body></html>'''

chrome = shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome:
    raise SystemExit('Browser QA failed: Chrome/Chromium not available on runner')

with tempfile.TemporaryDirectory() as td:
    f = Path(td)/'paddy-review-qa.html'
    f.write_text(harness, encoding='utf-8')
    r = subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1000','--dump-dom',f.as_uri()], text=True, capture_output=True, timeout=30)
    out = r.stdout + '\n' + r.stderr
    if r.returncode != 0 or 'data-qa="pass"' not in r.stdout:
        detail = re.search(r'<div id="qa-output">(.*?)</div>', r.stdout, re.S)
        raise SystemExit('Browser QA failed: '+(detail.group(1) if detail else out[-1500:]))

print('Browser QA passed: review renders exact leg columns and Super Sub is a dedicated editable field')
