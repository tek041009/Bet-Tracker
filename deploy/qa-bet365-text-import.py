from pathlib import Path
import json,re,subprocess,tempfile

html=Path('_site/index.html').read_text(encoding='utf-8')
required=[
    'id="bt-bet365-text-import"','Paste Bet365 Text','window.__btParseBet365Text=parseAll',
    'source:"My Pick"','bookmaker:"Bet365"','every selection was Void','Review ${esc(src[0]?.parsed?.bookmaker||"Paddy Power")} Import'
]
for x in required:
    if x not in html: raise SystemExit(f'Bet365 QA missing {x}')

m=re.search(r'<script id="bt-bet365-text-import">(.*?)</script>',html,re.S)
if not m: raise SystemExit('Bet365 QA parser script missing')
js=m.group(1)
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(js); fn=f.name
r=subprocess.run(['node','--check',fn],capture_output=True,text=True);Path(fn).unlink(missing_ok=True)
if r.returncode: raise SystemExit('Bet365 QA syntax failed: '+r.stderr)

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

£16.00Five-FoldsGerwyn Price , James Wade , Gian van Veen , Stephen Bunting , Wessel Nijman
Gerwyn Price3/10
Match Winner
Gerwyn Price
Bradley Brooks
James Wade1/5
Match Winner
James Wade
Jim Long
Gian van Veen4/9
Match Winner
Gian van Veen
Gabriel Clemens
Stephen Bunting2/5
Match Winner
Stephen Bunting
Brendan Dolan
Wessel Nijman2/5
Match Winner
Wessel Nijman
Sebastian Bialecki
Stake£16.00
Return
£70.67
✓£70.67Returned
Won

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
William O'Connor1/12
Match Winner
William O'Connor
Kevin Lankhuizen
Stake£14.00
Return
£28.16
✓£28.16Returned
Won

£16.00Five-FoldsOver 7.5 , Josh Rock +2.5 , Luke Humphries , Wessel Nijman +2.5 , Luke Littler
Over 7.51/10
Total Legs
Gian van Veen
Ross Smith
Josh Rock +2.52/11
Handicap 2-Way
Josh Rock
William O'Connor
Luke Humphries1/4
Match Winner
Luke Humphries
Andrew Gilding
Wessel Nijman +2.51/5
Handicap 2-Way
Michael van Gerwen
Wessel Nijman
Luke Littler1/6
Match Winner
Luke Littler
Krzysztof Ratajski
Stake£16.00
Return
£36.40
✓£36.40Returned
Won

£10.00DoublesRoss Smith , Luke Littler
Ross Smith1/4Void
Match Winner
Ross Smith
Stephen Burton
Luke Littler1/8Void
Match Winner
Luke Littler
Niko Springer
Stake£10.00
Return
£10.00
£10.00Cashed Out

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

node='global.window=global;global.localStorage={getItem:()=>null};global.document={querySelectorAll:()=>[],body:{}};global.MutationObserver=class{observe(){}};\n'+js+'\nconst items=window.__btParseBet365Text('+json.dumps(sample)+');console.log(JSON.stringify({found:items._found,removed:items._removed,kept:items.length,dates:items.map(x=>x.parsed.date),sources:[...new Set(items.map(x=>x.parsed.source))],books:[...new Set(items.map(x=>x.parsed.bookmaker))],issues:items.flatMap(x=>x.parsed._parseIssues),results:items.map(x=>x.parsed.result),legs:items.map(x=>x.parsed.legs.length),winPotential:items[1].parsed.returns,winPrice:items[1].parsed._receiptOdds}));'
r=subprocess.run(['node','-e',node],capture_output=True,text=True,timeout=30)
if r.returncode: raise SystemExit('Bet365 QA parser execution failed: '+r.stderr)
try:data=json.loads(r.stdout.strip())
except Exception as e: raise SystemExit('Bet365 QA invalid parser output: '+r.stdout) from e
expected_dates=['2026-09-13','2026-09-12','2026-09-11','2026-09-06','2026-09-04']
checks={
    'found':data['found']==6,'removed_all_void':data['removed']==1,'kept':data['kept']==5,
    'dates':data['dates']==expected_dates,'source':data['sources']==['My Pick'],'bookmaker':data['books']==['Bet365'],
    'issues':data['issues']==[],'results':data['results']==['Loss','Win','Win','Win','Void'],
    'legs':data['legs']==[4,5,4,5,2],'winning_return':data['winPotential']=='70.67'
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit(f'Bet365 QA failed {bad}: {data}')
print('Bet365 text QA passed: plain copied text parses, dates infer across Sep 4/6/11/12/13, My Pick is default, all-Void stake=return is excluded, real equal-stake cash-out is kept')
