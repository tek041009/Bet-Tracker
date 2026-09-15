from pathlib import Path
import json,re,subprocess,tempfile

html=Path('_site/index.html').read_text(encoding='utf-8')
for token in ['function bt365SettleHistoricalLegs(','BT365_HIST_SCORES','BT365_HIST_180','_historicalLegResultsChecked','prefix.endsWith(".")&&digits.length>=2']:
    if token not in html: raise SystemExit(f'Bet365 leg-result QA missing {token}')

m=re.search(r'<script id="bt-bet365-text-import">(.*?)</script>',html,re.S)
if not m: raise SystemExit('Bet365 leg-result QA parser script missing')
js=m.group(1)
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(js); fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True);Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Bet365 leg-result QA syntax failed: '+r.stderr)

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

£2.00Bet Builder +Ross Smith, Luke Humphries, Michael van Gerwen, Jonny Clayton, Danny Noppert
Lost
2/13
Ross Smith - Over 1.5 180s
Player 180s
Gerwyn Price
Ross Smith
1/4
Luke Humphries - Over 1.5 180s
Player 180s
William O'Connor
Luke Humphries
1/5
Michael van Gerwen - Over 1.5 180s
Player 180s
Jonny Clayton
Michael van Gerwen
1/2
Jonny Clayton - Over 1.5 180s
Player 180s
Jonny Clayton
Michael van Gerwen
1/2
Danny Noppert - Over 0.5 180s
Player 180s
Danny Noppert
Luke Littler
Stake£2.00
Return
£0.00
£0.00Returned'''

node='''global.window=global;global.localStorage={getItem:()=>null};global.document={querySelectorAll:()=>[],addEventListener:()=>{},body:{}};global.MutationObserver=class{observe(){}};\n'''+js+'\nconst items=window.__btParseBet365Text('+json.dumps(sample)+');console.log(JSON.stringify(items.map(x=>({date:x.parsed.date,competition:x.parsed.competition,checked:x.parsed._historicalLegResultsChecked,issues:x.parsed._parseIssues,legs:x.parsed.legs.map(l=>({selection:l.selection,market:l.market,result:l.result,odds:l.odds}))}))));'
r=subprocess.run(['node','-e',node],capture_output=True,text=True,timeout=30)
if r.returncode: raise SystemExit('Bet365 leg-result QA execution failed: '+r.stderr)
try:data=json.loads(r.stdout.strip())
except Exception as e: raise SystemExit('Bet365 leg-result QA invalid output: '+r.stdout) from e
if len(data)!=2: raise SystemExit(f'Expected 2 test bets, got {len(data)}')
first,second=data
expected_first=[
    ('Ross Smith','Match Result','Win'),
    ('Nathan Aspinall +2.5','Legs Handicap','Win'),
    ('Over 7.5','Total Legs','Loss'),
    ('Gian van Veen +2.5','Legs Handicap','Win'),
]
actual_first=[(x['selection'],x['market'],x['result']) for x in first['legs']]
if actual_first!=expected_first: raise SystemExit(f'Decimal/parser or result settlement mismatch: {actual_first}')
if first['date']!='2026-09-13' or not first['competition'].startswith('PDC European Tour') or not first['checked'] or first['issues']:
    raise SystemExit(f'Flanders historical settlement metadata failed: {first}')
expected_second=['Win','Win','Win','Loss','Loss']
if [x['result'] for x in second['legs']]!=expected_second:
    raise SystemExit(f'180 settlement mismatch: {second["legs"]}')
if second['date']!='2026-09-06' or not second['checked'] or second['issues']:
    raise SystemExit(f'Czech historical settlement metadata failed: {second}')
print('Bet365 historical leg-result QA passed: decimal handicap/total selections stay intact and Match Result / Legs Handicap / Total Legs / Player 180s settle to verified Win/Loss values')
