from pathlib import Path
import re, shutil, subprocess, tempfile

html=Path('_site/index.html').read_text(encoding='utf-8')

required=[
    "review.className=use.className.replace(/\\bbt-use-import\\b/g,'').trim()+' bt-review-bet365-text';",
    'modal?.dataset.btImportMode==="bet365text"',
    'Check the scan first — bookmaker, stake and potential returns are required.'
]
for x in required:
    if x not in html:
        raise SystemExit(f'Bet365 review QA missing {x}')

scanner_m=re.search(r'<script id="bt-screenshot-scanner-v2">(.*?)</script>',html,re.S)
review_m=re.search(r'<script id="bt-paddy-review">(.*?)</script>',html,re.S)
b365_m=re.search(r'<script id="bt-bet365-text-import">(.*?)</script>',html,re.S)
style_m=re.search(r'<style id="bt-paddy-review-styles">(.*?)</style>',html,re.S)
if not all([scanner_m,review_m,b365_m,style_m]):
    raise SystemExit('Bet365 review QA could not extract final scanner/review/import scripts')

sample='''£10.00Four-FoldsRoss Smith , Nathan Aspinall +2.5 , Over 7.5 , Gian van Veen +2.5
Lost
Ross Smith4/9
Match Winner
Ryan Joyce
Ross Smith
Nathan Aspinall +2.52/11
Handicap 2-Way
Damon Heta
Nathan Aspinall
Over 7.51/9
Total Legs
James Wade
Danny Noppert
Gian van Veen +2.51/5
Handicap 2-Way
Gian van Veen
Chris Dobey
Stake£10.00
Return
£0.00
£0.00Returned'''

harness=f'''<!doctype html><html><head><meta charset="utf-8"><style>{style_m.group(1)}</style></head><body>
<div class="bt-import-modal">
  <div class="bt-import-head"><h2>Scan a bet receipt</h2></div>
  <div class="bt-import-mode"><button type="button" data-mode="single">Single</button></div>
  <div class="bt-import-file"></div><div class="bt-import-preview"></div>
  <div class="bt-import-grid"></div>
  <div class="bt-import-fields">
    <select name="bookmaker"><option value="">Select</option><option>Bet365</option></select>
    <select name="sport"><option value="">Select</option><option>Darts</option></select>
    <input name="date"><input name="stake"><input name="returns"><input name="competition"><input name="event"><input name="market"><input name="selection"><input name="free"><input name="source"><input name="betFormat"><input name="result"><textarea name="raw"></textarea>
  </div>
  <div class="bt-import-progress">Nothing scanned yet.</div>
  <div class="bt-import-actions"><button class="button primary bt-run-ocr" type="button">Scan screenshot</button><button class="button primary bt-use-import" type="button">Review in Add Bet</button></div>
</div>
<script>window.alert=()=>{{}};window.__btImportReviewedPaddy=async()=>({{added:0,total:0,error:null}});</script>
<script>{scanner_m.group(1)}</script>
<script>{review_m.group(1)}</script>
<script>{b365_m.group(1)}</script>
<script>
const errors=[];
setTimeout(()=>{{
  const modal=document.querySelector('.bt-import-modal');
  const mode=modal.querySelector('[data-mode="bet365text"]');
  if(!mode)errors.push('Bet365 mode missing'); else mode.click();
  setTimeout(()=>{{
    const ta=modal.querySelector('.bt-bet365-text');
    if(!ta)errors.push('Bet365 textarea missing'); else ta.value={sample!r};
    modal.querySelector('.bt-run-bet365-text')?.click();
    setTimeout(()=>{{
      const review=modal.querySelector('.bt-review-bet365-text');
      if(!review)errors.push('review button missing');
      if(review?.classList.contains('bt-use-import'))errors.push('review still has bt-use-import class');
      review?.click();
      setTimeout(()=>{{
        const overlay=document.querySelector('.bt-paddy-review-overlay');
        if(!overlay)errors.push('review overlay did not open');
        const title=overlay?.querySelector('.bt-pr-head h2')?.textContent.trim()||'';
        if(title!=='Review Bet365 Import')errors.push('wrong review title '+title);
        const progress=modal.querySelector('.bt-import-progress')?.textContent||'';
        if(progress.includes('Check the scan first'))errors.push('screenshot validation intercepted Bet365 review');
        const stake=overlay?.querySelector('[data-pkey="stake"]')?.value;
        const returns=overlay?.querySelector('[data-pkey="returns"]')?.value;
        const source=overlay?.querySelector('[data-pkey="source"]')?.value;
        if(stake!=='10')errors.push('review stake '+stake);
        if(!returns)errors.push('review returns missing');
        if(source!=='My Pick')errors.push('review source '+source);
        document.body.dataset.qa=errors.length?'fail':'pass';
        const out=document.createElement('div');out.id='qa-output';out.textContent=errors.length?'FAIL: '+errors.join(' | '):'PASS';document.body.appendChild(out);
      }},120);
    }},100);
  }},80);
}},80);
</script></body></html>'''

chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome:
    raise SystemExit('Bet365 review QA: Chrome/Chromium not available')
with tempfile.TemporaryDirectory() as td:
    f=Path(td)/'bet365-review-qa.html';f.write_text(harness,encoding='utf-8')
    r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1800','--dump-dom',f.as_uri()],capture_output=True,text=True,timeout=35)
    if r.returncode or 'data-qa="pass"' not in r.stdout:
        detail=re.search(r'<div id="qa-output">(.*?)</div>',r.stdout,re.S)
        raise SystemExit('Bet365 review browser QA failed: '+(detail.group(1) if detail else (r.stdout+r.stderr)[-2500:]))

print('Bet365 review browser QA passed: parsed Bet365 review bypasses screenshot validation and opens Review Bet365 Import with stake, returns and My Pick populated')
