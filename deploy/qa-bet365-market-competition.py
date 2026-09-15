from pathlib import Path
import json,re,subprocess,tempfile

html=Path('_site/index.html').read_text(encoding='utf-8')
for token in [
    'PDC European Tour · Czech Darts Open',
    'PDC European Tour · Flanders Darts Trophy',
    'function canonMarket(s)',
    'return "Match Result"',
    'return "Legs Handicap"',
    'return "Total Legs"',
    'return "Player 180s"',
    'cashed&&Number.isFinite(settled)?settled'
]:
    if token not in html:
        raise SystemExit(f'Bet365 market/competition QA missing {token}')

m=re.search(r'<script id="bt-bet365-text-import">(.*?)</script>',html,re.S)
if not m: raise SystemExit('Bet365 market/competition QA parser missing')
js=m.group(1)
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(js); fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True);Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Bet365 normalized parser syntax failed: '+r.stderr)

sample='''£10.00Four-FoldsRoss Smith , Nathan Aspinall +2.5 , Over 7.5 , Gian van Veen +2.5
Lost
Ross Smith4/9
Match Winner
Ryan Joyce
Ross Smith
Nathan Aspinall +2.52/11
Handicap 2-Way
Damon Heta
Nathan Aspinall
Over 7.51/9
Total Legs
James Wade
Danny Noppert
Gian van Veen +2.51/5
Handicap 2-Way
Gian van Veen
Chris Dobey
Stake£10.00
Return
£0.00
£0.00Returned

£14.00Bet Builder +Over 7.5 , Damon Heta vs Beau Greaves, William O'Connor
Over 7.51/10
Total Legs
Sebastian Bialecki
Kim Huybrechts
1/5
Over 7.5 Legs
Total Legs
Match Handicap: Beau Greaves +3.5 Legs
Handicap 2-Way
Damon Heta
Beau Greaves
Damon Heta - Over 0.5 180s
Player 180s
Damon Heta
Beau Greaves
William O'Connor1/12
Match Winner
William O'Connor
Kevin Lankhuizen
Stake£14.00
Return
£28.16
✓£28.16Returned
Won

£10.00DoublesBeau Greaves , Rob Cross
Beau Greaves8/13
Match Winner
Daryl Gurney
Beau Greaves
Rob Cross2/5
Match Winner
Rob Cross
Keane Barry
Stake£10.00
Return
£10.00
£10.00Cashed Out'''

node='global.window=global;global.localStorage={getItem:()=>null};global.document={querySelectorAll:()=>[],body:{}};global.MutationObserver=class{observe(){}};\n'+js+'\nconst items=window.__btParseBet365Text('+json.dumps(sample)+');console.log(JSON.stringify({competitions:[...new Set(items.map(x=>x.parsed.competition))],markets:[...new Set(items.flatMap(x=>x.parsed.legs.map(l=>l.market)))],sports:[...new Set(items.map(x=>x.parsed.sport))],cashoutReturn:items[2].parsed.returns,issues:items.flatMap(x=>x.parsed._parseIssues)}));'
r=subprocess.run(['node','-e',node],capture_output=True,text=True,timeout=30)
if r.returncode: raise SystemExit('Bet365 normalized parser execution failed: '+r.stderr)
try:data=json.loads(r.stdout.strip())
except Exception as e: raise SystemExit('Bet365 normalized parser output invalid: '+r.stdout) from e

expected_comp=['PDC European Tour · Flanders Darts Trophy','PDC European Tour · Czech Darts Open']
if data['competitions']!=expected_comp:
    raise SystemExit(f'Competition normalization failed: {data}')
for market in ['Match Result','Legs Handicap','Total Legs','Player 180s']:
    if market not in data['markets']:
        raise SystemExit(f'Market normalization missing {market}: {data}')
for raw in ['Match Winner','Handicap 2-Way']:
    if raw in data['markets']:
        raise SystemExit(f'Raw Bet365 market leaked through: {raw}: {data}')
if data['sports']!=['Darts']:
    raise SystemExit(f'Canonical market names broke Darts inference: {data}')
if data['cashoutReturn']!='10.00':
    raise SystemExit(f'Actual cash-out return not preserved: {data}')
# Historical-result verification has its own dedicated QA. This synthetic market fixture
# deliberately includes props that are not in the verified historical-result lookup, so
# only fail this normalization QA for non-historical parser issues.
unexpected=[x for x in data['issues'] if 'historical leg result' not in x]
if unexpected:
    raise SystemExit(f'Unexpected normalized parser issues: {data}')
print('Bet365 market/competition QA passed: European Tour event labels, canonical per-leg markets, Darts inference and cash-out returns are correct')
