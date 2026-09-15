from pathlib import Path
import re, subprocess, tempfile

html=Path('_site/index.html').read_text(encoding='utf-8')
needle='''if(leg.odds!=null&&leg.odds!==""){const o=Number(leg.odds),v=Number.isFinite(o)?Math.round(o*1000)/1000:leg.odds;setCtl(ins[3],v)}'''
if needle not in html:
    raise SystemExit('Leg odds QA: importer does not normalize repeating decimal odds to 0.001 precision')
if 'step:"0.001"' not in html:
    raise SystemExit('Leg odds QA: Add Bet leg odds field no longer uses step 0.001')

# Reproduce the exact fractional prices shown in the user's failed Bet365 import.
vals=[1+4/9,1+2/11,1+1/9]
rounded=[round(v*1000)/1000 for v in vals]
expected=[1.444,1.182,1.111]
if rounded!=expected:
    raise SystemExit(f'Leg odds QA: unexpected normalization {rounded}')
for v in rounded:
    if abs(v*1000-round(v*1000))>1e-9:
        raise SystemExit(f'Leg odds QA: {v} is not valid for step 0.001')

m=re.search(r'<script id="bt-paddy-text-import">(.*?)</script>',html,re.S)
if not m: raise SystemExit('Leg odds QA: reviewed importer script missing')
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(m.group(1)); fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True)
Path(fn).unlink(missing_ok=True)
if r.returncode:
    raise SystemExit('Leg odds QA syntax failed: '+r.stderr)

print('Leg odds QA passed: 1.444444…, 1.181818… and 1.111111… normalize to valid 0.001-step values before Add Bet validation')
