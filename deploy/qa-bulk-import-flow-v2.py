from pathlib import Path
import json,re,shutil,subprocess,tempfile,time

html=Path('_site/index.html').read_text(encoding='utf-8')
required=[
 'onBulkDelete:q','className:"bt-row-select"','aria-label":"Select all filtered bets"',
 'Delete selected (${B.size})','onBulkDelete:B','id="bt-bulk-delete-styles"',
 'id="bt-import-progress-styles"','Adding your bets to Bet Tracker',
 'window.__btPaddyImportProgress?.({added,total})',
 'return await importSelected(modal);',
 'Import complete. Opening Bet Tracker…','goToBetTracker();await sleep(650);screen.remove()'
]
for x in required:
    if x not in html: raise SystemExit(f'QA v2 failed: missing {x}')

main_m=re.search(r'<script>"use strict";\(\(\)=>\{.*?</script>',html,re.S)
text_m=re.search(r'<script id="bt-paddy-text-import">(.*?)</script>',html,re.S)
review_m=re.search(r'<script id="bt-paddy-review">(.*?)</script>',html,re.S)
review_css=re.search(r'<style id="bt-paddy-review-styles">(.*?)</style>',html,re.S)
progress_css=re.search(r'<style id="bt-import-progress-styles">(.*?)</style>',html,re.S)
if not all([main_m,text_m,review_m,review_css,progress_css]): raise SystemExit('QA v2 failed: built scripts/styles missing')
main_js=main_m.group(0)[8:-9]; text_js=text_m.group(1); review_js=review_m.group(1)
for name,js in [('main',main_js),('text',text_js),('review',review_js)]:
    with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f: f.write(js); fn=f.name
    r=subprocess.run(['node','--check',fn],capture_output=True,text=True); Path(fn).unlink(missing_ok=True)
    if r.returncode: raise SystemExit(f'QA v2 syntax failed {name}: {r.stderr}')

chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome: raise SystemExit('QA v2 failed: no Chrome')

tracker={'version':1,'startingBalance':100,'transactions':[],'bets':[
 {'id':'b1','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Win','profitLoss':5,'balanceAfter':105,'event':'A v B','market':'Match Odds','selection':'A','legs':[],'createdAt':1},
 {'id':'b2','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Loss','profitLoss':-5,'balanceAfter':100,'event':'C v D','market':'Match Odds','selection':'C','legs':[],'createdAt':2},
 {'id':'b3','date':'2026-09-15','app':'Bet365','sport':'Darts','type':'Medium Risk (Evs - 10/1)','source':'My Pick','betFormat':'Single','odds':3,'stake':5,'potentialReturns':15,'bankrollRisk':.05,'result':'Pending','profitLoss':None,'balanceAfter':100,'event':'E v F','market':'Match Betting','selection':'E','legs':[],'createdAt':3}],
 'ladder':{'startStake':10,'targetReturn':100,'days':7,'results':['Pending']*7}}

bulk=f'''<!doctype html><html><body><div id="bet-tracker-root"></div><script>localStorage.setItem('bet-tracker-user-v1',JSON.stringify({json.dumps(tracker)}));window.confirm=()=>true;</script><script>{main_js}</script><script>
setTimeout(()=>{{const nav=[...document.querySelectorAll('aside nav button')].find(b=>b.textContent.includes('Bet Tracker'));nav?.click();setTimeout(()=>{{const before=document.querySelectorAll('table.bet-table tbody tr').length;const boxes=[...document.querySelectorAll('.bt-row-select')];boxes[0]?.click();boxes[1]?.click();setTimeout(()=>{{const del=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Delete selected (2)');del?.click();setTimeout(()=>{{const after=document.querySelectorAll('table.bet-table tbody tr').length;let stored=-1;try{{stored=JSON.parse(localStorage.getItem('bet-tracker-user-v1')||'null')?.bets?.length??-1}}catch(e){{}}document.body.dataset.qa=(before===3&&boxes.length===3&&!!del&&after===1&&stored===1)?'pass':'fail';document.body.dataset.detail=`${{before}}/${{boxes.length}}/${{after}}/${{stored}}/${{!!del}}`; }},220)}},80)}},100)}},80);
</script></body></html>'''

imp=f'''<!doctype html><html><head><style>{review_css.group(1)}\n{progress_css.group(1)}</style></head><body><aside><nav><button id="bets-nav">Bet Tracker</button></nav></aside><button id="add">+ Add bet</button>
<script>document.getElementById('bets-nav').onclick=()=>document.body.dataset.nav=String(Number(document.body.dataset.nav||0)+1);document.getElementById('add').onclick=()=>{{const f=document.createElement('form');f.className='modal-form';f.innerHTML=`<select name="app"><option>Paddy Power</option></select><select name="sport"><option>Football</option></select><input name="date"><select name="type"><option>Low Risk (Around Evs)</option></select><input name="source"><input name="competition"><input name="notes"><input name="stake"><input name="potentialReturns"><select name="betFormat"><option>Bet Builder</option></select><select name="result"><option>Win</option><option>Loss</option><option>Pending</option></select><input name="isFreeBet" type="checkbox"><input name="freeBetAmount"><div class="bt-leg-card"><select><option>Football</option></select><input><input><input><input><select><option>Win</option><option>Loss</option><option>Pending</option></select></div><button type="button" class="bt-add-leg">Add</button><button type="submit">Add bet</button>`;f.onsubmit=e=>{{e.preventDefault();f.remove()}};document.body.appendChild(f)}};</script>
<script>{text_js}</script><script>{review_js}</script><script>
const wrap=document.createElement('div');wrap.className='bt-import-backdrop';wrap.innerHTML=`<div class="bt-import-modal" data-bt-import-mode="text"><div class="bt-import-mode"></div><label class="bt-import-file"><input></label><div class="bt-import-grid"></div><div class="bt-import-actions"><button class="bt-use-import">Review</button></div><input class="bt-multi-check" data-i="0" type="checkbox" checked><input class="bt-multi-check" data-i="1" type="checkbox" checked></div>`;document.body.appendChild(wrap);
const modal=wrap.querySelector('.bt-import-modal');const parsed=id=>({{_betId:id,date:'2026-09-15',betFormat:'Bet Builder',result:'Win',stake:5,returns:10,free:'',_receiptOdds:2,notes:'',source:'My Pick',bookmaker:'Paddy Power',sport:'Football',competition:'',_riskType:'Low Risk (Around Evs)',_parseIssues:[],legs:[{{sport:'Football',event:'A v B',market:'Match Odds',selection:'A',odds:null,result:'Win',_superSubReplacement:''}}]}});
document.body.dataset.hook=typeof window.__btImportReviewedPaddy;modal.__btTextResults=[{{raw:'',parsed:parsed('1')}},{{raw:'',parsed:parsed('2')}}];window.__btOpenPaddyReview(modal);setTimeout(()=>document.querySelector('.bt-pr-import')?.click(),50);
setTimeout(()=>{{const o=document.querySelector('.bt-importing-overlay');document.body.dataset.mid=o?.querySelector('.bt-importing-count')?.textContent.trim()||'';document.body.dataset.status=o?.querySelector('.bt-importing-status')?.textContent.trim()||'';document.body.dataset.forms=String(document.querySelectorAll('.modal-form').length);}},1100);
setTimeout(()=>{{const done=!document.querySelector('.bt-importing-overlay');const ok=document.body.dataset.hook==='function'&&document.body.dataset.mid==='2 / 2'&&document.body.dataset.status==='Import complete. Opening Bet Tracker…'&&document.body.dataset.forms==='0'&&done&&Number(document.body.dataset.nav||0)>=2;document.body.dataset.qa=ok?'pass':'fail';}},1900);
</script></body></html>'''

with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'bulk.html').write_text(bulk,encoding='utf-8');(td/'import.html').write_text(imp,encoding='utf-8')
    server=subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.3)
        for name,budget in [('bulk.html',2000),('import.html',2800)]:
            r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking',f'--virtual-time-budget={budget}','--dump-dom','http://127.0.0.1:8765/'+name],capture_output=True,text=True,timeout=35)
            if r.returncode or 'data-qa="pass"' not in r.stdout:
                b=re.search(r'<body([^>]*)>',r.stdout,re.S);detail=b.group(1) if b else (r.stdout+r.stderr)[-3000:]
                raise SystemExit(f'QA v2 browser failed {name}:{detail}')
    finally:
        server.terminate();
        try: server.wait(timeout=2)
        except subprocess.TimeoutExpired: server.kill()
print('QA v2 passed: bulk multi-delete works in real tracker; reviewed batch import reports progress, imports all bets and lands on Bet Tracker')
