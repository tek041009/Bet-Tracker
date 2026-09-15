from pathlib import Path
import json,re,shutil,subprocess,tempfile,time

html=Path('_site/index.html').read_text(encoding='utf-8')
for x in ['id="bt-advanced-filter-styles"','children:"Bookmaker"','children:"Sport"','children:"Source"','children:"Result"','children:advOpen?"Hide Advanced":"Advanced"','Advanced filters','btAdvancedMatch(o,r)']:
    if x not in html: raise SystemExit(f'Advanced filter QA missing {x}')
main_m=re.search(r'<script>"use strict";\(\(\)=>\{.*?</script>',html,re.S)
if not main_m: raise SystemExit('Advanced filter QA: main script missing')
main_js=main_m.group(0)[8:-9]
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:f.write(main_js);fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True);Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Advanced filter QA syntax failed: '+r.stderr)
chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome: raise SystemExit('Advanced filter QA: no Chrome')
tracker={'version':1,'startingBalance':100,'transactions':[],'bets':[
 {'id':'b1','date':'2026-09-14','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Win','profitLoss':5,'balanceAfter':105,'event':'Leeds v Newcastle','market':'Player To Have 1 Or More Shots','selection':'Harvey Barnes','legs':[],'createdAt':1},
 {'id':'b2','date':'2026-09-14','app':'Bet365','sport':'Football','type':'Medium Risk (Evs - 10/1)','source':'Model Pick','betFormat':'Bet Builder','odds':4,'stake':5,'potentialReturns':20,'bankrollRisk':.05,'result':'Loss','profitLoss':-5,'balanceAfter':100,'event':'West Ham v Arsenal','market':'Match Odds','selection':'West Ham','legs':[],'createdAt':2}
],'ladder':{'startStake':10,'targetReturn':100,'days':7,'results':['Pending']*7}}
page=f'''<!doctype html><html><body><div id="bet-tracker-root"></div><script>localStorage.setItem('bet-tracker-user-v1',JSON.stringify({json.dumps(tracker)}));</script><script>{main_js}</script><script>
const setNative=(el,val)=>{{const proto=el instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype;const setter=Object.getOwnPropertyDescriptor(proto,'value').set;setter.call(el,val);el.dispatchEvent(new Event(el instanceof HTMLSelectElement?'change':'input',{{bubbles:true}}));}};
setTimeout(()=>{{[...document.querySelectorAll('aside nav button')].find(b=>b.textContent.includes('Bet Tracker'))?.click();setTimeout(()=>{{
 const labels=[...document.querySelectorAll('.bt-filter-control>span')].map(x=>x.textContent.trim());
 const adv=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Advanced');adv?.click();
 setTimeout(()=>{{
  const add=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='+ Add filter');add?.click();
  setTimeout(()=>{{
   const rule=document.querySelector('.bt-advanced-rule');const sels=rule?.querySelectorAll('select');const inp=rule?.querySelector('input');
   if(sels?.[0])setNative(sels[0],'market');
   setTimeout(()=>{{if(inp)setNative(inp,'Match Odds');}},50);
   setTimeout(()=>{{const rows=document.querySelectorAll('table.bet-table tbody tr');document.body.dataset.qa=(JSON.stringify(labels)===JSON.stringify(['Bookmaker','Sport','Source','Result'])&&!!document.querySelector('.bt-advanced-panel')&&rows.length===1&&rows[0].textContent.includes('West Ham'))?'pass':'fail';document.body.dataset.detail=labels.join('|')+' / '+rows.length+' / '+(rows[0]?.textContent||'');}},350);
  }},120);
 }},120);
}},120)}},100);
</script></body></html>'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'index.html').write_text(page,encoding='utf-8');srv=subprocess.Popen(['python3','-m','http.server','8766','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.25);r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking','--virtual-time-budget=2500','--dump-dom','http://127.0.0.1:8766/index.html'],capture_output=True,text=True,timeout=35)
        if r.returncode or 'data-qa="pass"' not in r.stdout:
            b=re.search(r'<body([^>]*)>',r.stdout,re.S);raise SystemExit('Advanced filter browser QA failed: '+(b.group(1) if b else (r.stdout+r.stderr)[-2000:]))
    finally:
        srv.terminate();
        try:srv.wait(timeout=2)
        except: srv.kill()
print('Advanced filter browser QA passed: category labels visible, Advanced opens, market rule filters tracker rows')
