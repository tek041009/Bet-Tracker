from pathlib import Path
import re

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

m=re.search(r'(<script id="bt-paddy-text-import">)(.*?)(</script>)',h,re.S)
if not m:
    raise SystemExit('Leg odds precision patch: Paddy importer script missing')
js=m.group(2)
old='''if(leg.odds!=null&&leg.odds!=="")setCtl(ins[3],leg.odds);'''
new='''if(leg.odds!=null&&leg.odds!==""){const o=Number(leg.odds),v=Number.isFinite(o)?Math.round(o*1000)/1000:leg.odds;setCtl(ins[3],v)}'''
if js.count(old)!=1:
    raise SystemExit(f'Leg odds precision patch: expected one leg-odds setter, found {js.count(old)}')
js=js.replace(old,new,1)
h=h[:m.start(2)]+js+h[m.end(2):]
p.write_text(h,encoding='utf-8')
print('Normalized imported leg odds to the Add Bet form step of 0.001 before validation')
