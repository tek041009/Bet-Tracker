from pathlib import Path
import json, re, shutil, subprocess, tempfile, time

html=Path('_site/index.html').read_text(encoding='utf-8')

# Static wiring checks for the React Bet Tracker bulk-selection flow.
required=[
    'onBulkDelete:q',
    'className:"bt-row-select"',
    'aria-label":"Select all filtered bets"',
    'Delete selected (${B.size})',
    'Delete ${r.length} selected bet${r.length===1?"":"s"}? This cannot be undone.',
    'onBulkDelete:B',
    'id="bt-bulk-delete-styles"',
    'id="bt-import-progress-styles"',
    'window.__btPaddyImportProgress?.({added,total})',
    'Adding your bets to Bet Tracker',
    'Import complete. Opening Bet Tracker…',
    'goToBetTracker();await sleep(650);screen.remove()',
]
for token in required:
    if token not in html:
        raise SystemExit(f'Bulk/import QA failed: missing {token}')

# Syntax-check the final bundled React app and the two Paddy scripts that own import progress.
main_m=re.search(r'<script>"use strict";\(\(\)=>\{.*?</script>',html,re.S)
if not main_m:
    raise SystemExit('Bulk/import QA failed: main React app script not found')
script_checks=[('main-app',main_m.group(0)[8:-9])]
for sid in ['bt-paddy-text-import','bt-paddy-review']:
    m=re.search(rf'<script id="{sid}">(.*?)</script>',html,re.S)
    if not m:
        raise SystemExit(f'Bulk/import QA failed: {sid} not found')
    script_checks.append((sid,m.group(1)))
for name,js in script_checks:
    with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
        f.write(js); fn=f.name
    r=subprocess.run(['node','--check',fn],capture_output=True,text=True)
    Path(fn).unlink(missing_ok=True)
    if r.returncode:
        raise SystemExit(f'Bulk/import QA failed: JS syntax error in {name}: {r.stderr}')

chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome:
    raise SystemExit('Bulk/import QA failed: Chrome/Chromium not available')

# Browser QA 1: real React Bet Tracker UI -> select two rows -> one confirmation -> both removed.
main_js=main_m.group(0)[8:-9]
tracker={
  'version':1,'startingBalance':100,'transactions':[],
  'bets':[
    {'id':'b1','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Win','profitLoss':5,'balanceAfter':105,'event':'A v B','market':'Match Odds','selection':'A','legs':[],'createdAt':1},
    {'id':'b2','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Loss','profitLoss':-5,'balanceAfter':100,'event':'C v D','market':'Match Odds','selection':'C','legs':[],'createdAt':2},
    {'id':'b3','date':'2026-09-15','app':'Bet365','sport':'Darts','type':'Medium Risk (Evs - 10/1)','source':'My Pick','betFormat':'Single','odds':3,'stake':5,'potentialReturns':15,'bankrollRisk':.05,'result':'Pending','profitLoss':None,'balanceAfter':100,'event':'E v F','market':'Match Betting','selection':'E','legs':[],'createdAt':3},
  ],
  'ladder':{'startStake':10,'targetReturn':100,'days':7,'results':['Pending']*7}
}
bulk_page=f'''<!doctype html><html><body><div id="bet-tracker-root"></div>
<script>localStorage.setItem('bet-tracker-user-v1',JSON.stringify({json.dumps(tracker)}));window.confirm=()=>true;</script>
<script>{main_js}</script>
<script>
setTimeout(()=>{{
 const nav=[...document.querySelectorAll('aside nav button')].find(b=>b.textContent.includes('Bet Tracker'));nav?.click();
 setTimeout(()=>{{
  const before=document.querySelectorAll('table.bet-table tbody tr').length;
  const boxes=[...document.querySelectorAll('.bt-row-select')];boxes[0]?.click();boxes[1]?.click();
  setTimeout(()=>{{
   const del=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Delete selected (2)');del?.click();
   setTimeout(()=>{{
    const after=document.querySelectorAll('table.bet-table tbody tr').length;
    let stored=-1;try{{stored=JSON.parse(localStorage.getItem('bet-tracker-user-v1')||'null')?.bets?.length??-1}}catch(e){{}}
    document.body.dataset.before=before;document.body.dataset.boxes=boxes.length;document.body.dataset.after=after;document.body.dataset.stored=stored;document.body.dataset.qa=(before===3&&boxes.length===3&&!!del&&after===1&&stored===1)?'pass':'fail';
   }},180);
  }},80);
 }},100);
}},80);
</script></body></html>'''

# Browser QA 2: real Paddy review + real Paddy sequential importer against a mock Add Bet form.
review_css=re.search(r'<style id="bt-paddy-review-styles">(.*?)</style>',html,re.S)
progress_css=re.search(r'<style id="bt-import-progress-styles">(.*?)</style>',html,re.S)
text_js=re.search(r'<script id="bt-paddy-text-import">(.*?)</script>',html,re.S).group(1)
review_js=re.search(r'<script id="bt-paddy-review">(.*?)</script>',html,re.S).group(1)
if not review_css or not progress_css:
    raise SystemExit('Bulk/import QA failed: review/progress CSS missing')
import_page=f'''<!doctype html><html><head><style>{review_css.group(1)}\n{progress_css.group(1)}</style></head><body>
<aside><nav><button id="bets-nav">Bet Tracker</button></nav></aside><button id="add">+ Add bet</button>
<div class="bt-import-backdrop"><div class="bt-import-modal" data-bt-import-mode="text"><div class="bt-import-mode"></div><label class="bt-import-file"><input></label><div class="bt-import-grid"></div><div class="bt-import-actions"><button class="bt-use-import">Review</button></div><input class="bt-multi-check" data-i="0" type="checkbox" checked><input class="bt-multi-check" data-i="1" type="checkbox" checked></div></div>
<script>
document.getElementById('bets-nav').onclick=()=>document.body.dataset.nav=String(Number(document.body.dataset.nav||0)+1);
document.getElementById('add').onclick=()=>{{const f=document.createElement('form');f.className='modal-form';f.innerHTML=`<select name="app"><option>Paddy Power</option></select><select name="sport"><option>Football</option></select><input name="date"><select name="type"><option>Low Risk (Around Evs)</option></select><input name="source"><input name="competition"><input name="notes"><input name="stake"><input name="potentialReturns"><select name="betFormat"><option>Bet Builder</option></select><select name="result"><option>Win</option><option>Loss</option><option>Pending</option></select><input name="isFreeBet" type="checkbox"><input name="freeBetAmount"><div class="bt-leg-card"><select><option>Football</option></select><input><input><input><input><select><option>Win</option><option>Loss</option><option>Pending</option></select></div><button type="button" class="bt-add-leg">Add</button><button type="submit">Add bet</button>`;f.onsubmit=e=>{{e.preventDefault();f.remove()}};document.body.appendChild(f)}};
</script><script>{text_js}</script><script>{review_js}</script><script>
const modal=document.querySelector('.bt-import-modal');const parsed=id=>({{_betId:id,date:'2026-09-15',betFormat:'Bet Builder',result:'Win',stake:5,returns:10,free:'',_receiptOdds:2,notes:'',source:'My Pick',bookmaker:'Paddy Power',sport:'Football',competition:'',_riskType:'Low Risk (Around Evs)',_parseIssues:[],legs:[{{sport:'Football',event:'A v B',market:'Match Odds',selection:'A',odds:null,result:'Win',_superSubReplacement:''}}]}});modal.__btTextResults=[{{raw:'',parsed:parsed('1')}},{{raw:'',parsed:parsed('2')}}];window.__btOpenPaddyReview(modal);setTimeout(()=>document.querySelector('.bt-pr-import')?.click(),30);
setTimeout(()=>{{const o=document.querySelector('.bt-importing-overlay');document.body.dataset.midCount=o?.querySelector('.bt-importing-count')?.textContent.trim()||'';document.body.dataset.midStatus=o?.querySelector('.bt-importing-status')?.textContent.trim()||'';document.body.dataset.midForms=document.querySelectorAll('.modal-form').length;document.body.dataset.midNav=document.body.dataset.nav||'0'}},1050);
setTimeout(()=>{{const done=!document.querySelector('.bt-importing-overlay');document.body.dataset.done=done?'1':'0';document.body.dataset.finalNav=document.body.dataset.nav||'0';document.body.dataset.qa=(document.body.dataset.midCount==='2 / 2'&&document.body.dataset.midStatus==='Import complete. Opening Bet Tracker…'&&document.body.dataset.midForms==='0'&&Number(document.body.dataset.midNav)>=1&&done&&Number(document.body.dataset.finalNav)>=2)?'pass':'fail'}},1700);
</script></body></html>'''

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    (td/'bulk.html').write_text(bulk_page,encoding='utf-8')
    (td/'import.html').write_text(import_page,encoding='utf-8')
    server=subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.35)
        for name,budget in [('bulk.html',1800),('import.html',2400)]:
            r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking','--virtual-time-budget='+str(budget),'--dump-dom','http://127.0.0.1:8765/'+name],capture_output=True,text=True,timeout=35)
            if r.returncode!=0 or 'data-qa="pass"' not in r.stdout:
                body=re.search(r'<body([^>]*)>',r.stdout,re.S)
                detail=body.group(1) if body else (r.stdout+r.stderr)[-2500:]
                raise SystemExit(f'Bulk/import browser QA failed for {name}: {detail}')
    finally:
        server.terminate()
        try: server.wait(timeout=2)
        except subprocess.TimeoutExpired: server.kill()

print('Bulk/import QA passed: real tracker multi-select deletes selected bets in one action; real reviewed Paddy import shows live count, saves all bets, closes import UI and returns to Bet Tracker')
