from pathlib import Path
import re

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

m=re.search(r'(<script id="bt-bet365-text-import">)(.*?)(</script>)',h,re.S)
if not m:
    raise SystemExit('Bet365 normalization: importer script missing')
js=m.group(2)

if 'function canonMarket(' in js:
    raise SystemExit('Bet365 normalization already applied')

if js.count('"Czech Darts Open"') != 3:
    raise SystemExit(f'Expected 3 Czech Darts Open schedule labels, found {js.count(chr(34)+"Czech Darts Open"+chr(34))}')
if js.count('"Flanders Darts Trophy"') != 3:
    raise SystemExit(f'Expected 3 Flanders Darts Trophy schedule labels, found {js.count(chr(34)+"Flanders Darts Trophy"+chr(34))}')
js=js.replace('"Czech Darts Open"','"PDC European Tour · Czech Darts Open"')
js=js.replace('"Flanders Darts Trophy"','"PDC European Tour · Flanders Darts Trophy"')

old='function sportFor(legs){return legs.some(l=>/legs|180s|match winner|handicap 2-way/i.test(l.market||""))?"Darts":"Football"}'
new='function canonMarket(s){const x=clean(s);if(/^Match Winner$/i.test(x))return "Match Result";if(/^Handicap 2-Way$/i.test(x))return "Legs Handicap";if(/^Total Legs$/i.test(x))return "Total Legs";if(/^Player 180s$/i.test(x))return "Player 180s";return x}\nfunction sportFor(legs){return legs.some(l=>/legs|180s|match winner|handicap 2-way|match result|legs handicap/i.test(l.market||""))?"Darts":"Football"}'
if js.count(old)!=1:
    raise SystemExit(f'Expected one Bet365 sportFor helper, found {js.count(old)}')
js=js.replace(old,new,1)

old='const market=data[i+1],a=data[i+2],b=data[i+3];'
new='const market=canonMarket(data[i+1]),a=data[i+2],b=data[i+3];'
if js.count(old)!=1:
    raise SystemExit(f'Expected one standard Bet365 market assignment, found {js.count(old)}')
js=js.replace(old,new,1)

old='const selection=seg[k],market=seg[k+1];'
new='const selection=seg[k],market=canonMarket(seg[k+1]);'
if js.count(old)!=1:
    raise SystemExit(f'Expected one Bet Builder market assignment, found {js.count(old)}')
js=js.replace(old,new,1)

old='let potential=Number.isFinite(settled)&&result==="Win"?settled:(Number.isFinite(price)?round2(hd.stake*price):(Number.isFinite(settled)?settled:NaN));'
new='let potential=cashed&&Number.isFinite(settled)?settled:(Number.isFinite(settled)&&result==="Win"?settled:(Number.isFinite(price)?round2(hd.stake*price):(Number.isFinite(settled)?settled:NaN)));'
if js.count(old)!=1:
    raise SystemExit(f'Expected one Bet365 return calculation, found {js.count(old)}')
js=js.replace(old,new,1)

h=h[:m.start(2)]+js+h[m.end(2):]
p.write_text(h,encoding='utf-8')
print('Normalized Bet365 markets, labelled all supplied events as PDC European Tour, and preserved actual cash-out returns')
