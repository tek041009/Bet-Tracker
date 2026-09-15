from pathlib import Path
import json,re,shutil,subprocess,tempfile,time

html=Path('_site/index.html').read_text(encoding='utf-8')
for x in ['r1.__btLastSelectedId','e.shiftKey','Shift-click to select a range','Delete selected (${B.size})']:
    if x not in html: raise SystemExit(f'Shift-select QA missing {x}')
main_m=re.search(r'<script>"use strict";\(\(\)=>\{.*?</script>',html,re.S)
if not main_m: raise SystemExit('Shift-select QA: main script missing')
main_js=main_m.group(0)[8:-9]
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(main_js); fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True); Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Shift-select QA syntax failed: '+r.stderr)
chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not chrome: raise SystemExit('Shift-select QA: no Chrome')

def bet(i):
    return {'id':f'b{i}','date':'2026-09-15','app':'Paddy Power','sport':'Football','type':'Low Risk (Around Evs)','source':'My Pick','betFormat':'Single','odds':2,'stake':5,'potentialReturns':10,'bankrollRisk':.05,'result':'Win','profitLoss':5,'balanceAfter':100+i,'event':f'Match {i}','market':'Match Odds','selection':f'Team {i}','legs':[],'createdAt':i}
tracker={'version':1,'startingBalance':100,'transactions':[],'bets':[bet(i) for i in range(1,6)],'ladder':{'startStake':10,'targetReturn':100,'days':7,'results':['Pending']*7}}
page=f'''<!doctype html><html><body><div id="bet-tracker-root"></div><script>localStorage.setItem('bet-tracker-user-v1',JSON.stringify({json.dumps(tracker)}));window.confirm=()=>true;</script><script>{main_js}</script><script>
setTimeout(()=>{{
  [...document.querySelectorAll('aside nav button')].find(b=>b.textContent.includes('Bet Tracker'))?.click();
  setTimeout(()=>{{
    let boxes=[...document.querySelectorAll('.bt-row-select')];
    const before=document.querySelectorAll('table.bet-table tbody tr').length;
    boxes[0]?.click();
    setTimeout(()=>{{
      boxes=[...document.querySelectorAll('.bt-row-select')];
      boxes[3]?.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true,shiftKey:true}}));
      setTimeout(()=>{{
        boxes=[...document.querySelectorAll('.bt-row-select')];
        const pattern=boxes.map(x=>x.checked?'1':'0').join('');
        const del=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Delete selected (4)');
        del?.click();
        setTimeout(()=>{{
          const after=document.querySelectorAll('table.bet-table tbody tr').length;
          let stored=-1;try{{stored=JSON.parse(localStorage.getItem('bet-tracker-user-v1')||'null')?.bets?.length??-1}}catch(e){{}}
          const ok=before===5&&boxes.length===5&&pattern==='11110'&&!!del&&after===1&&stored===1;
          document.body.dataset.qa=ok?'pass':'fail';
          document.body.dataset.detail=`before=${{before}} boxes=${{boxes.length}} pattern=${{pattern}} delete=${{!!del}} after=${{after}} stored=${{stored}}`;
        }},220);
      }},120);
    }},100);
  }},120);
}},100);
</script></body></html>'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td); (td/'index.html').write_text(page,encoding='utf-8')
    server=subprocess.Popen(['python3','-m','http.server','8767','--bind','127.0.0.1'],cwd=td,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(.3)
        r=subprocess.run([chrome,'--headless','--disable-gpu','--no-sandbox','--disable-background-networking','--virtual-time-budget=2400','--dump-dom','http://127.0.0.1:8767/index.html'],capture_output=True,text=True,timeout=35)
        if r.returncode or 'data-qa="pass"' not in r.stdout:
            b=re.search(r'<body([^>]*)>',r.stdout,re.S)
            raise SystemExit('Shift-select browser QA failed: '+(b.group(1) if b else (r.stdout+r.stderr)[-2500:]))
    finally:
        server.terminate()
        try: server.wait(timeout=2)
        except subprocess.TimeoutExpired: server.kill()
print('Shift-select browser QA passed: first checkbox + Shift-click fourth selects exactly the contiguous four-bet range and bulk delete removes those four')
