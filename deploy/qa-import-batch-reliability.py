from pathlib import Path
import json,re,shutil,subprocess,tempfile,time

html=Path('_site/index.html').read_text(encoding='utf-8')
required=[
    'function storedHasBetId(id)',
    'async function waitForAddButton()',
    'for(let i=0;i<200;i++)',
    'Bet Tracker did not finish opening. Please retry the import.',
    'save did not complete after 8 seconds',
    'Safe to retry — bets already saved will be skipped.',
    'skipped++',
    'form.checkValidity()',
]
for x in required:
    if x not in html: raise SystemExit(f'Batch reliability QA missing {x}')
if 'goToBetTracker();await sleep(120);window.__btPaddyImportProgress' in html:
    raise SystemExit('Batch reliability QA: fixed 120 ms tracker wait still present')

m=re.search(r'<script id="bt-paddy-text-import">(.*?)</script>',html,re.S)
if not m: raise SystemExit('Batch reliability QA: Paddy importer missing')
js=m.group(1)
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(js); fn=f.name
r=subprocess.run(['node','--check',fn],text=True,capture_output=True)
Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Batch reliability QA syntax failed: '+r.stderr)

chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome: raise SystemExit('Batch reliability QA: no Chrome')

harness=f'''<!doctype html><html><body>
<script>
localStorage.setItem('bet-tracker-user-v1',JSON.stringify({{version:1,bets:[{{id:'old',notes:'Bet365 Paste ID: B365-OLD00001'}}],transactions:[]}}));
</script>
<script>{js}</script>
<script>
function makeForm(){{
 const f=document.createElement('form');f.className='modal-form';f.innerHTML=`
  <select name="app"><option>Bet365</option></select><select name="sport"><option>Darts</option></select>
  <input name="date" required type="date"><select name="type"><option>Low Risk (Around Evs)</option></select>
  <input name="source"><input name="competition"><input name="notes"><input name="stake" required type="number" min="0.01" step="0.01"><input name="potentialReturns" required type="number" min="0" step="0.01">
  <select name="betFormat"><option>Accumulator</option></select><select name="result"><option>Win</option><option>Loss</option><option>Void</option><option>Pending</option></select>
  <div class="bt-leg-card"><select><option>Darts</option></select><select><option>Win</option><option>Loss</option><option>Void</option><option>Pending</option></select><input><input><input><input type="number"></div>
  <button type="button" class="bt-add-leg">Add leg</button><button type="submit">Save</button>`;
 f.addEventListener('submit',e=>{{e.preventDefault();let d=JSON.parse(localStorage.getItem('bet-tracker-user-v1'));d.bets.push({{id:'new',notes:'Bet365 Paste ID: B365-NEW00002'}});localStorage.setItem('bet-tracker-user-v1',JSON.stringify(d));f.remove();}});
 document.body.appendChild(f);return f;
}}
setTimeout(()=>{{const b=document.createElement('button');b.textContent='+ Add bet';b.onclick=makeForm;document.body.appendChild(b)}},650);
const modal=document.createElement('div');modal.className='bt-import-modal';
const parsed=(id)=>({{_betId:id,bookmaker:'Bet365',sport:'Darts',date:'2026-09-13',_riskType:'Low Risk (Around Evs)',source:'My Pick',competition:'PDC European Tour · Flanders Darts Trophy',notes:'Bet365 Paste ID: '+id,stake:5,returns:'10.00',betFormat:'Accumulator',result:'Win',free:'',legs:[{{sport:'Darts',event:'A v B',market:'Match Result',selection:'A',odds:null,result:'Win'}}]}});
const items=[{{parsed:parsed('B365-OLD00001')}},{{parsed:parsed('B365-NEW00002')}}];modal.__btTextResults=items;items.forEach((_,i)=>{{const c=document.createElement('input');c.type='checkbox';c.checked=true;c.className='bt-multi-check';c.dataset.i=String(i);modal.appendChild(c)}});document.body.appendChild(modal);
window.__btPaddyImportProgress=x=>document.body.dataset.progress=JSON.stringify(x);
(async()=>{{const t=performance.now();const r=await window.__btImportReviewedPaddy(modal,items);const elapsed=performance.now()-t;const data=JSON.parse(localStorage.getItem('bet-tracker-user-v1'));document.body.dataset.result=JSON.stringify(r);document.body.dataset.elapsed=String(Math.round(elapsed));document.body.dataset.qa=(r?.added===2&&r?.skipped===1&&!r?.error&&data.bets.length===2&&elapsed>=500)?'pass':'fail';}})();
</script></body></html>'''

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'qa.html';p.write_text(harness,encoding='utf-8')
    server=subprocess.Popen(['python3','-m','http.server','8767','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.25)
        r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking','--virtual-time-budget=4000','--dump-dom','http://127.0.0.1:8767/qa.html'],capture_output=True,text=True,timeout=30)
        if r.returncode or 'data-qa="pass"' not in r.stdout:
            body=re.search(r'<body([^>]*)>',r.stdout,re.S)
            raise SystemExit('Batch reliability browser QA failed: '+(body.group(1) if body else (r.stdout+r.stderr)[-2200:]))
    finally:
        server.terminate()
        try:server.wait(timeout=2)
        except subprocess.TimeoutExpired:server.kill()

print('Batch reliability QA passed: importer waits for delayed Bet Tracker readiness, skips an already-saved Bet365 ID, and saves the remaining bet without duplication')
