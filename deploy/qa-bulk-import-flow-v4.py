from pathlib import Path
import json,re,shutil,subprocess,tempfile,time

html=Path('_site/index.html').read_text(encoding='utf-8')
required=[
    'onBulkDelete:q','className:"bt-row-select"','aria-label":"Select all filtered bets"',
    'Delete selected (${B.size})','onBulkDelete:B','id="bt-bulk-delete-styles"',
    'id="bt-import-progress-styles"','Adding your bets to Bet Tracker',
    'window.__btPaddyImportProgress?.({added,total,skipped})',
    'return await importSelected(modal);','Import complete. Opening Bet Tracker…',
    'Safe to retry — bets already saved will be skipped.',
    'goToBetTracker();await sleep(650);screen.remove()'
]
for x in required:
    if x not in html: raise SystemExit(f'QA v4 failed: missing {x}')

main_m=re.search(r'<script>"use strict";\(\(\)=>\{.*?</script>',html,re.S)
text_m=re.search(r'<script id="bt-paddy-text-import">(.*?)</script>',html,re.S)
review_m=re.search(r'<script id="bt-paddy-review">(.*?)</script>',html,re.S)
review_css=re.search(r'<style id="bt-paddy-review-styles">(.*?)</style>',html,re.S)
progress_css=re.search(r'<style id="bt-import-progress-styles">(.*?)</style>',html,re.S)
if not all([main_m,text_m,review_m,review_css,progress_css]):
    raise SystemExit('QA v4 failed: scripts/styles missing')
main_js=main_m.group(0)[8:-9];text_js=text_m.group(1);review_js=review_m.group(1)

actual_wrapper='window.__btImportReviewedPaddy=async (modal,items)=>{ modal.__btTextResults=items; const old=modal.querySelectorAll(".bt-multi-check"); old.forEach((c,i)=>c.checked=i<items.length); return await importSelected(modal); };'
if actual_wrapper not in text_js:
    raise SystemExit('QA v4 failed: real reviewed importer does not return import result')
if text_js.count('window.__btPaddyImportProgress?.({added,total,skipped})')<2:
    raise SystemExit('QA v4 failed: real importer does not publish retry-safe start/per-bet progress')
if 'storedHasBetId(betId)' not in text_js or 'skipped++' not in text_js:
    raise SystemExit('QA v4 failed: duplicate-safe retry logic missing')

for name,js in [('main',main_js),('text',text_js),('review',review_js)]:
    with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
        f.write(js);fn=f.name
    r=subprocess.run(['node','--check',fn],capture_output=True,text=True)
    Path(fn).unlink(missing_ok=True)
    if r.returncode: raise SystemExit(f'QA v4 syntax failed {name}: {r.stderr}')

chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome: raise SystemExit('QA v4 failed: no Chrome')

tracker={'version':1,'startingBalance':100,'transactions':[],'bets':[
 {'id':'b1','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Win','profitLoss':5,'balanceAfter':105,'event':'A v B','market':'Match Odds','selection':'A','legs':[],'createdAt':1},
 {'id':'b2','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Loss','profitLoss':-5,'balanceAfter':100,'event':'C v D','market':'Match Odds','selection':'C','legs':[],'createdAt':2},
 {'id':'b3','date':'2026-09-15','app':'Bet365','sport':'Darts','type':'Medium Risk (Evs - 10/1)','source':'My Pick','betFormat':'Single','odds':3,'stake':5,'potentialReturns':15,'bankrollRisk':.05,'result':'Pending','profitLoss':None,'balanceAfter':100,'event':'E v F','market':'Match Betting','selection':'E','legs':[],'createdAt':3}
],'ladder':{'startStake':10,'targetReturn':100,'days':7,'results':['Pending']*7}}

bulk=f'''<!doctype html><html><body><div id="bet-tracker-root"></div><script>localStorage.setItem('bet-tracker-user-v1',JSON.stringify({json.dumps(tracker)}));window.confirm=()=>true;</script><script>{main_js}</script><script>setTimeout(()=>{{[...document.querySelectorAll('aside nav button')].find(b=>b.textContent.includes('Bet Tracker'))?.click();setTimeout(()=>{{const before=document.querySelectorAll('table.bet-table tbody tr').length,boxes=[...document.querySelectorAll('.bt-row-select')];boxes[0]?.click();boxes[1]?.click();setTimeout(()=>{{const del=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Delete selected (2)');del?.click();setTimeout(()=>{{const after=document.querySelectorAll('table.bet-table tbody tr').length;let stored=-1;try{{stored=JSON.parse(localStorage.getItem('bet-tracker-user-v1')||'null')?.bets?.length??-1}}catch(e){{}}document.body.dataset.qa=(before===3&&boxes.length===3&&!!del&&after===1&&stored===1)?'pass':'fail';document.body.dataset.detail=`${{before}}/${{boxes.length}}/${{after}}/${{stored}}`; }},220)}},80)}},100)}},80);</script></body></html>'''

imp=f'''<!doctype html><html><head><style>{review_css.group(1)}\n{progress_css.group(1)}</style></head><body><aside><nav><button id="bets-nav">Bet Tracker</button></nav></aside><script>document.getElementById('bets-nav').onclick=()=>document.body.dataset.nav=String(Number(document.body.dataset.nav||0)+1);</script><script>{review_js}</script><script>
const wrap=document.createElement('div');wrap.className='bt-import-backdrop';wrap.innerHTML=`<div class="bt-import-modal" data-bt-import-mode="text"><div class="bt-import-actions"><button class="bt-use-import">Review</button></div><input class="bt-multi-check" data-i="0" type="checkbox" checked><input class="bt-multi-check" data-i="1" type="checkbox" checked></div>`;document.body.appendChild(wrap);const modal=wrap.querySelector('.bt-import-modal');const parsed=id=>({{_betId:id,date:'2026-09-15',betFormat:'Bet Builder',result:'Win',stake:5,returns:10,free:'',_receiptOdds:2,notes:'',source:'My Pick',_parseIssues:[],legs:[{{sport:'Football',event:'A v B',market:'Match Odds',selection:'A',odds:null,result:'Win',_superSubReplacement:''}}]}});modal.__btTextResults=[{{raw:'',parsed:parsed('1')}},{{raw:'',parsed:parsed('2')}}];window.__btImportReviewedPaddy=async(m,items)=>{{const total=items.length;window.__btPaddyImportProgress?.({{added:0,total,skipped:0}});await new Promise(r=>setTimeout(r,120));window.__btPaddyImportProgress?.({{added:1,total,skipped:1}});await new Promise(r=>setTimeout(r,120));window.__btPaddyImportProgress?.({{added:2,total,skipped:1}});return {{added:2,total,error:null,skipped:1}}}};window.__btOpenPaddyReview(modal);setTimeout(()=>document.querySelector('.bt-pr-import')?.click(),30);setTimeout(()=>{{const o=document.querySelector('.bt-importing-overlay');document.body.dataset.mid=o?.querySelector('.bt-importing-count')?.textContent.trim()||'';document.body.dataset.status=o?.querySelector('.bt-importing-status')?.textContent.trim()||'';}},500);setTimeout(()=>{{const done=!document.querySelector('.bt-importing-overlay');document.body.dataset.qa=(document.body.dataset.mid==='2 / 2'&&document.body.dataset.status.includes('1 already-saved bet was skipped')&&done&&Number(document.body.dataset.nav||0)>=2)?'pass':'fail';}},1200);
</script></body></html>'''

with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'bulk.html').write_text(bulk,encoding='utf-8');(td/'import.html').write_text(imp,encoding='utf-8')
    server=subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.3)
        for name,budget in [('bulk.html',2000),('import.html',1800)]:
            r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking',f'--virtual-time-budget={budget}','--dump-dom','http://127.0.0.1:8765/'+name],capture_output=True,text=True,timeout=35)
            if r.returncode or 'data-qa="pass"' not in r.stdout:
                b=re.search(r'<body([^>]*)>',r.stdout,re.S)
                raise SystemExit(f'QA v4 browser failed {name}: '+(b.group(1) if b else (r.stdout+r.stderr)[-2500:]))
    finally:
        server.terminate()
        try:server.wait(timeout=2)
        except subprocess.TimeoutExpired:server.kill()

print('QA v4 passed: bulk delete works; reviewed import progress supports skipped existing bets and completes back to Bet Tracker')
