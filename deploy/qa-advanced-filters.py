from pathlib import Path
import json,re,shutil,subprocess,tempfile,time

html=Path('_site/index.html').read_text(encoding='utf-8')
required=[
    'id="bt-advanced-filter-styles"','children:"Bookmaker"','children:"Sport"','children:"Source"','children:"Result"',
    'className:"bt-tracker-advanced-panel"','btMulti("Year"','btMulti("Month"','Custom date range',
    'btMulti("Risk Level"','btMulti("Bet Type"','btMulti("Competition"','Multi-competition','Competition(s)',
    'btCompetitionMeta','btAdvancedMatch'
]
for x in required:
    if x not in html: raise SystemExit(f'Advanced v2 QA missing {x}')
for x in ['btAdvFields','btAddRule','Enter filter value','children:"Condition"','children:"+ Add filter"']:
    if x in html: raise SystemExit(f'Advanced v2 QA found removed generic builder token {x}')
if html.count('Competition(s)')<2:
    raise SystemExit('Advanced v2 QA expected Competition(s) in Add/Edit and Paddy review')

main_m=re.search(r'<script>"use strict";\(\(\)=>\{.*?</script>',html,re.S)
if not main_m: raise SystemExit('Advanced v2 QA: main script missing')
main_js=main_m.group(0)[8:-9]
styles=''.join(re.findall(r'<style\b[^>]*>.*?</style>',html,re.S))
if 'bt-advanced-filter-styles' not in styles: raise SystemExit('Advanced v2 QA: deployed styles missing')
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(main_js); fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True)
Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Advanced v2 QA syntax failed: '+r.stderr)

chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome: raise SystemExit('Advanced v2 QA: no Chrome')

tracker={'version':1,'startingBalance':100,'transactions':[],'bets':[
 {'id':'b1','date':'2026-09-05','app':'Bet365','sport':'Football','type':'Medium Risk (Evs - 10/1)','source':'A','betFormat':'Bet Builder','competition':'Premier League','odds':4,'stake':5,'potentialReturns':20,'result':'Win','event':'Prem only','market':'x','selection':'x','legs':[],'createdAt':1},
 {'id':'b2','date':'2026-09-06','app':'Paddy Power','sport':'Football','type':'Medium Risk (Evs - 10/1)','source':'B','betFormat':'Accumulator','competition':'Championship','odds':4,'stake':5,'potentialReturns':20,'result':'Win','event':'Champ only','market':'x','selection':'x','legs':[],'createdAt':2},
 {'id':'b3','date':'2026-09-07','app':'Betfred','sport':'Football','type':'Medium Risk (Evs - 10/1)','source':'C','betFormat':'Bet Builder','competition':'Premier League, Championship','odds':4,'stake':5,'potentialReturns':20,'result':'Win','event':'Prem champ','market':'x','selection':'x','legs':[],'createdAt':3},
 {'id':'b4','date':'2026-09-08','app':'Ladbrokes','sport':'Football','type':'Medium Risk (Evs - 10/1)','source':'D','betFormat':'Bet Builder','competition':'Premier League, Championship, PDC European Tour','odds':4,'stake':5,'potentialReturns':20,'result':'Win','event':'Prem champ pdc','market':'x','selection':'x','legs':[],'createdAt':4},
 {'id':'b5','date':'2025-10-12','app':'William Hill','sport':'Football','type':'High Risk (10/1+)','source':'E','betFormat':'Single','competition':'Europa League','odds':12,'stake':5,'potentialReturns':60,'result':'Win','event':'Europa','market':'x','selection':'x','legs':[],'createdAt':5},
 {'id':'b6','date':'2026-09-09','app':'Sky Bet','sport':'Football','type':'Low Risk (Around Evs)','source':'F','betFormat':'Accumulator','competition':'Multiple competitions','odds':2,'stake':5,'potentialReturns':10,'result':'Win','event':'Unknown multi','market':'x','selection':'x','legs':[],'createdAt':6},
 {'id':'b7','date':'2026-09-10','app':'Bet365','sport':'Football','type':'Low Risk (Around Evs)','source':'G','betFormat':'Single','competition':'','odds':2,'stake':5,'potentialReturns':10,'result':'Win','event':'Unclassified','market':'x','selection':'x','legs':[],'createdAt':7}
],'ladder':{'startStake':10,'targetReturn':100,'days':7,'results':['Pending']*7}}

page=f'''<!doctype html><html><head>{styles}</head><body><div id="bet-tracker-root"></div><script>localStorage.setItem('bet-tracker-user-v1',JSON.stringify({json.dumps(tracker)}));</script><script>{main_js}</script><script>
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const rows=()=>document.querySelectorAll('table.bet-table tbody tr').length;
const directLabel=(el)=>el?.querySelector(':scope > span')?.textContent.trim();
const filterBox=name=>[...document.querySelectorAll('.bt-adv-filter')].find(x=>directLabel(x)===name);
async function tick(name,opt){{
 const box=filterBox(name); if(!box)throw new Error('Missing filter '+name);
 if(!box.querySelector('.bt-adv-menu')){{box.querySelector('.bt-adv-picker')?.click();await wait(70)}}
 const lab=[...box.querySelectorAll('.bt-adv-checks label')].find(x=>x.textContent.trim()===opt);
 if(!lab)throw new Error('Missing option '+name+' / '+opt);
 lab.querySelector('input')?.click(); await wait(100);
}}
async function clearAll(){{document.querySelector('.bt-adv-clear-all')?.click();await wait(110)}}
const nativeSet=(el,val)=>{{const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(el,val);el.dispatchEvent(new Event('input',{{bubbles:true}}));el.dispatchEvent(new Event('change',{{bubbles:true}}));}};
(async()=>{{
 await wait(100);[...document.querySelectorAll('aside nav button')].find(b=>b.textContent.includes('Bet Tracker'))?.click();await wait(140);
 const normal=[...document.querySelectorAll('.bt-filter-control>span')].map(x=>x.textContent.trim());
 const adv=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Advanced'); if(!adv)throw new Error('Advanced button missing');adv.click();await wait(120);
 const labels=[...document.querySelectorAll('.bt-adv-filter>span')].map(x=>x.textContent.trim());
 const panel=document.querySelector('.bt-tracker-advanced-panel'),pr=panel?.getBoundingClientRect();
 const checks=[];
 checks.push(['normal-labels',normal.join('|')==='Bookmaker|Sport|Source|Result',normal.join('|')]);
 checks.push(['open',adv.textContent.trim()==='Hide Advanced'&&adv.getAttribute('aria-expanded')==='true'&&pr&&pr.width>400&&pr.height>100&&labels.join('|')==='Year|Month|Custom date range|Risk Level|Bet Type|Competition',rows()]);
 await tick('Year','2026');checks.push(['year',rows()===6,rows()]);
 await tick('Month','September');checks.push(['month',rows()===6,rows()]);
 await tick('Risk Level','Medium Risk');checks.push(['risk',rows()===4,rows()]);
 await tick('Bet Type','Bet Builder');checks.push(['bet-type',rows()===3,rows()]);
 await tick('Competition','Premier League');await tick('Competition','Championship');checks.push(['competition-subset',rows()===2,rows()]);
 await clearAll();checks.push(['clear-all',rows()===7,rows()]);
 await tick('Competition','Multi-competition');checks.push(['multi-competition',rows()===3,rows()]);
 await clearAll();
 const from=document.querySelector('[aria-label="Advanced from date"]'),to=document.querySelector('[aria-label="Advanced to date"]');nativeSet(from,'2025-10-01');nativeSet(to,'2025-10-31');await wait(130);checks.push(['date-range',rows()===1,rows()]);
 await clearAll();
 [...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='+ Add bet')?.click();await wait(100);
 const comp=document.querySelector('input[name="competition"]');checks.push(['competition-entry',!!comp&&comp.parentElement.textContent.includes('Competition(s)')&&comp.placeholder.includes('Premier League, Championship'),comp?.placeholder||'missing']);
 const ok=checks.every(x=>x[1]);document.body.dataset.qa=ok?'pass':'fail';document.body.dataset.detail=JSON.stringify(checks);
}})().catch(e=>{{document.body.dataset.qa='fail';document.body.dataset.detail=String(e.stack||e)}});
</script></body></html>'''

with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'index.html').write_text(page,encoding='utf-8')
    srv=subprocess.Popen(['python3','-m','http.server','8766','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.25)
        r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking','--virtual-time-budget=6000','--dump-dom','http://127.0.0.1:8766/index.html'],capture_output=True,text=True,timeout=35)
        if r.returncode or 'data-qa="pass"' not in r.stdout:
            b=re.search(r'<body([^>]*)>',r.stdout,re.S)
            raise SystemExit('Advanced v2 browser QA failed: '+(b.group(1) if b else (r.stdout+r.stderr)[-4000:]))
    finally:
        srv.terminate()
        try:srv.wait(timeout=2)
        except: srv.kill()
print('Advanced v2 browser QA passed: Year/Month/date/risk/bet-type multi-selects work; competition uses whole-bet subset semantics and Multi-competition override')
