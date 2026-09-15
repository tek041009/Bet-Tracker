from pathlib import Path
import re

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

m=re.search(r'(<script id="bt-bet365-text-import">)(.*?)(</script>)',h,re.S)
if not m:
    raise SystemExit('Bet365 historical results: importer script missing')
js=m.group(2)

if 'function bt365SettleHistoricalLegs(' in js:
    raise SystemExit('Bet365 historical leg results already applied')

old=r'''const selOdds=s=>{const x=clean(s);if(oddsOnly(x))return null;const m=x.match(/^(.+?)(\d+\s*\/\s*\d+)(Void)?$/i);return m?{selection:m[1].trim(),fraction:m[2],void:!!m[3]}:null};'''
new=r'''const selOdds=s=>{let x=clean(s),v=/Void$/i.test(x);if(v)x=x.replace(/Void$/i,"").trim();if(oddsOnly(x))return null;const slash=x.lastIndexOf("/");if(slash<1)return null;const den=x.slice(slash+1).trim();if(!/^\d+$/.test(den))return null;let j=slash-1;while(j>=0&&/\d/.test(x[j]))j--;const digits=x.slice(j+1,slash);if(!digits)return null;let prefix=x.slice(0,j+1),num=digits,selection=prefix.trim();if(prefix.endsWith(".")&&digits.length>=2){selection=(prefix+digits[0]).trim();num=digits.slice(1)}if(!selection||!num)return null;return {selection,fraction:`${num}/${den}`,void:v}};'''
if js.count(old)!=1:
    raise SystemExit(f'Expected one Bet365 selection/odds parser, found {js.count(old)}')
js=js.replace(old,new,1)

sport='''function sportFor(legs){return legs.some(l=>/legs|180s|match winner|handicap 2-way|match result|legs handicap/i.test(l.market||""))?"Darts":"Football"}'''
if js.count(sport)!=1:
    raise SystemExit(f'Expected normalized Bet365 sport helper once, found {js.count(sport)}')

helpers=r'''
function bt365HistNorm(s){return clean(s).normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[’‘]/g,"'").toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}
function bt365HistKey(date,a,b){return `${date}|${[bt365HistNorm(a),bt365HistNorm(b)].sort().join("||")}`}
const BT365_HIST_SCORES=new Map([
["2026-09-04","Krzysztof Ratajski",6,"Adam Gawlas",2],["2026-09-04","Daryl Gurney",4,"Beau Greaves",6],["2026-09-04","Luke Woodhouse",6,"Connor Scutt",4],["2026-09-04","Dirk van Duijvenbode",2,"Mario Vandenbogaerde",6],["2026-09-04","Niels Zonneveld",3,"Jeffrey de Graaf",6],["2026-09-04","Rob Cross",4,"Keane Barry",6],["2026-09-04","Martin Schindler",6,"Rob Owen",4],["2026-09-05","Nathan Aspinall",2,"Andrew Gilding",6],["2026-09-05","Luke Humphries",6,"Beau Greaves",2],["2026-09-05","Gerwyn Price",6,"Callan Rydz",2],["2026-09-05","Gary Anderson",3,"Cameron Menzies",6],["2026-09-05","Chris Dobey",4,"Keane Barry",6],["2026-09-05","Jonny Clayton",6,"Damon Heta",2],["2026-09-05","Josh Rock",6,"Ryan Joyce",3],["2026-09-05","Luke Littler",6,"Niko Springer",4],["2026-09-05","Michael van Gerwen",6,"Mario Vandenbogaerde",4],["2026-09-05","Wessel Nijman",6,"Martin Schindler",5],["2026-09-05","Ross Smith",6,"Stephen Burton",1],["2026-09-05","Ryan Searle",4,"William O'Connor",6],["2026-09-06","Luke Humphries",6,"Andrew Gilding",3],["2026-09-06","Gerwyn Price",6,"Cameron Menzies",1],["2026-09-06","Danny Noppert",0,"Luke Littler",6],["2026-09-06","Luke Woodhouse",5,"Danny Noppert",6],["2026-09-06","Gerwyn Price",6,"Ross Smith",4],["2026-09-06","Gian van Veen",3,"Ross Smith",6],["2026-09-06","Jonny Clayton",6,"Keane Barry",4],["2026-09-06","Jonny Clayton",3,"Michael van Gerwen",6],["2026-09-06","Josh Rock",5,"William O'Connor",6],["2026-09-06","Luke Littler",6,"Krzysztof Ratajski",3],["2026-09-06","William O'Connor",3,"Luke Humphries",6],["2026-09-06","Michael van Gerwen",6,"Wessel Nijman",4],["2026-09-11","Andrew Gilding",5,"Chris Landman",6],["2026-09-11","Joe Cullen",3,"Andy Baetens",6],["2026-09-11","Damon Heta",6,"Beau Greaves",5],["2026-09-11","Mickey Mansell",4,"Bradley Brooks",6],["2026-09-11","Dirk van Duijvenbode",3,"Brendan Dolan",6],["2026-09-11","Cameron Menzies",4,"Gabriel Clemens",6],["2026-09-11","Rob Cross",6,"Cristo Reyes",3],["2026-09-11","Niko Springer",6,"Jaimy Jacobs",1],["2026-09-11","Kevin Doets",6,"James Hurrell",1],["2026-09-11","Jeffrey de Graaf",6,"Jeroen Caron",5],["2026-09-11","Raymond van Barneveld",2,"Jim Long",6],["2026-09-11","Karel Sedlacek",6,"Michael Hansen",2],["2026-09-11","William O'Connor",6,"Kevin Lankhuizen",2],["2026-09-11","Sebastian Bialecki",6,"Kim Huybrechts",5],["2026-09-11","Niels Zonneveld",6,"Petr Tous",3],["2026-09-11","Ryan Joyce",6,"Stephen Burton",5],["2026-09-12","Ryan Searle",6,"Andy Baetens",2],["2026-09-12","Gerwyn Price",6,"Bradley Brooks",3],["2026-09-12","Stephen Bunting",6,"Brendan Dolan",5],["2026-09-12","Chris Dobey",6,"Niels Zonneveld",1],["2026-09-12","Danny Noppert",6,"Chris Landman",2],["2026-09-12","Michael van Gerwen",5,"Damon Heta",6],["2026-09-12","Gian van Veen",6,"Gabriel Clemens",3],["2026-09-12","James Wade",6,"Jim Long",2],["2026-09-12","Ross Smith",6,"Jeffrey de Graaf",2],["2026-09-12","Jermaine Wattimena",6,"Karel Sedlacek",3],["2026-09-12","Josh Rock",3,"Ryan Joyce",6],["2026-09-12","Krzysztof Ratajski",5,"Kevin Doets",6],["2026-09-12","Luke Woodhouse",6,"William O'Connor",3],["2026-09-12","Martin Schindler",4,"Rob Cross",6],["2026-09-12","Nathan Aspinall",6,"Niko Springer",1],["2026-09-12","Wessel Nijman",6,"Sebastian Bialecki",4],["2026-09-13","Gian van Veen",6,"Chris Dobey",3],["2026-09-13","Ryan Searle",5,"Chris Dobey",6],["2026-09-13","Damon Heta",6,"Luke Woodhouse",3],["2026-09-13","Damon Heta",6,"Nathan Aspinall",5],["2026-09-13","James Wade",6,"Danny Noppert",0],["2026-09-13","Danny Noppert",6,"Wessel Nijman",4],["2026-09-13","Gerwyn Price",5,"Ross Smith",6],["2026-09-13","Gian van Veen",6,"Kevin Doets",5],["2026-09-13","James Wade",6,"Rob Cross",5],["2026-09-13","Ryan Joyce",6,"Jermaine Wattimena",5],["2026-09-13","Stephen Bunting",4,"Nathan Aspinall",6],["2026-09-13","Ryan Joyce",5,"Ross Smith",6]
].map(x=>[bt365HistKey(x[0],x[1],x[3]),{a:x[1],sa:x[2],b:x[3],sb:x[4]}]));
const BT365_HIST_DATES=new Set(["2026-09-04","2026-09-05","2026-09-06","2026-09-11","2026-09-12","2026-09-13"]);
const BT365_HIST_180=new Map([
["2026-09-13|gerwyn price||ross smith|ross smith over 0 5 180s","Win"],["2026-09-13|gerwyn price||ross smith|gerwyn price over 0 5 180s","Win"],
["2026-09-13|chris dobey||ryan searle|chris dobey over 0 5 180s","Win"],["2026-09-13|gian van veen||kevin doets|kevin doets over 0 5 180s","Win"],
["2026-09-06|gerwyn price||ross smith|ross smith over 1 5 180s","Win"],
["2026-09-06|luke humphries||william o connor|luke humphries over 0 5 180s","Win"],["2026-09-06|luke humphries||william o connor|luke humphries over 1 5 180s","Win"],
["2026-09-06|jonny clayton||michael van gerwen|michael van gerwen over 0 5 180s","Win"],["2026-09-06|jonny clayton||michael van gerwen|jonny clayton over 0 5 180s","Win"],
["2026-09-06|jonny clayton||michael van gerwen|michael van gerwen over 1 5 180s","Win"],["2026-09-06|jonny clayton||michael van gerwen|jonny clayton over 1 5 180s","Loss"],
["2026-09-06|danny noppert||luke littler|danny noppert over 0 5 180s","Loss"],["2026-09-06|danny noppert||luke littler|danny noppert over 1 5 180s","Loss"]
]);
function bt365HistScore(sc,player){const n=bt365HistNorm(player);if(n===bt365HistNorm(sc.a))return sc.sa;if(n===bt365HistNorm(sc.b))return sc.sb;return null}
function bt365SettleHistoricalLegs(p){if(!p||p.bookmaker!=="Bet365"||!Array.isArray(p.legs)||!BT365_HIST_DATES.has(p.date))return p;let checked=0,unresolved=0;for(const l of p.legs){if(l.result==="Void"){checked++;continue}const mm=String(l.event||"").match(/^(.*?)\s+v\s+(.*?)$/i);if(!mm){unresolved++;continue}const key=bt365HistKey(p.date,mm[1],mm[2]),sc=BT365_HIST_SCORES.get(key);let result="";if(l.market==="Player 180s"){result=BT365_HIST_180.get(`${key}|${bt365HistNorm(l.selection)}`)||""}else if(sc&&l.market==="Match Result"){const who=String(l.selection||"").replace(/^Match Result:\s*/i,"").trim(),mine=bt365HistScore(sc,who),other=bt365HistNorm(who)===bt365HistNorm(mm[1])?bt365HistScore(sc,mm[2]):bt365HistScore(sc,mm[1]);if(mine!=null&&other!=null)result=mine>other?"Win":"Loss"}else if(sc&&l.market==="Total Legs"){const tm=String(l.selection||"").match(/\b(Over|Under)\s+([0-9]+(?:\.[0-9]+)?)/i);if(tm){const total=sc.sa+sc.sb,line=Number(tm[2]);result=tm[1].toLowerCase()==="over"?(total>line?"Win":"Loss"):(total<line?"Win":"Loss")}}else if(sc&&l.market==="Legs Handicap"){const raw=String(l.selection||"").replace(/^Match Handicap:\s*/i,"").replace(/\s+Legs$/i,"").trim(),hm=raw.match(/^(.*?)\s+([+-]\d+(?:\.\d+)?)$/);if(hm){const who=hm[1].trim(),mine=bt365HistScore(sc,who),other=bt365HistNorm(who)===bt365HistNorm(mm[1])?bt365HistScore(sc,mm[2]):bt365HistScore(sc,mm[1]);if(mine!=null&&other!=null)result=mine+Number(hm[2])>other?"Win":"Loss"}}if(result){l.result=result;l._historicalResultChecked=true;checked++}else unresolved++}if(checked===p.legs.length&&p.legs.length){p._historicalLegResultsChecked=true;p.notes=[p.notes,"All leg results checked from historical PDC results/match stats"].filter(Boolean).join(" · ")}else if(unresolved){p._parseIssues=p._parseIssues||[];p._parseIssues.push(`${unresolved} historical leg result${unresolved===1?"":"s"} could not be verified`)}return p}
'''
js=js.replace(sport,sport+helpers,1)

old_push='''if(x.exclude)removed++;else items.push({raw:chunk,parsed:x.parsed})'''
new_push='''if(x.exclude)removed++;else{bt365SettleHistoricalLegs(x.parsed);items.push({raw:chunk,parsed:x.parsed})}'''
if js.count(old_push)!=1:
    raise SystemExit(f'Expected one Bet365 parseAll push, found {js.count(old_push)}')
js=js.replace(old_push,new_push,1)

h=h[:m.start(2)]+js+h[m.end(2):]
p.write_text(h,encoding='utf-8')
print('Applied verified historical Win/Loss/Void to every Bet365 leg for the Sep 4-13 European Tour batch and fixed decimal selection/odds splitting')
