from pathlib import Path
import re,subprocess,tempfile

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
    'storedHasBetId(betId)',
    'return {added,total,error:null,skipped}',
    'window.__btPaddyImportProgress?.({added,total,skipped})',
]
for x in required:
    if x not in html: raise SystemExit(f'Batch reliability QA missing {x}')

if 'goToBetTracker();await sleep(120);window.__btPaddyImportProgress' in html:
    raise SystemExit('Batch reliability QA: fixed 120 ms tracker wait still present')

m=re.search(r'<script id="bt-paddy-text-import">(.*?)</script>',html,re.S)
if not m: raise SystemExit('Batch reliability QA: Paddy importer missing')
js=m.group(1)
if 'for(let t=0;t<75;t++){if(!form.isConnected)break;await wait(40)}' in js:
    raise SystemExit('Batch reliability QA: reviewed importer still uses old 3 second save timeout')

with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(js); fn=f.name
r=subprocess.run(['node','--check',fn],text=True,capture_output=True)
Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Batch reliability QA syntax failed: '+r.stderr)

if 'function updateImportScreen(x,added,total,error="",skipped=0)' not in html:
    raise SystemExit('Batch reliability QA: progress UI does not accept skipped count')
if 'result?.skipped||0' not in html:
    raise SystemExit('Batch reliability QA: final progress update drops skipped count')

print('Batch reliability QA passed: no fixed 120ms navigation race, reviewed tracker/add-form waits are 8s, saves are validation-aware, and retries skip already-saved Bet365 IDs')
