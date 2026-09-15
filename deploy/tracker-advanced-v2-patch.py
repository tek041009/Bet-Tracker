from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

# Replace the generic Field / Condition / Value rule-builder state with the
# tracker-level filters the user actually wants.
old_state='''[advOpen,setAdvOpen]=(0,W.useState)(false),[advRules,setAdvRules]=(0,W.useState)(()=>[{field:"any",op:"contains",value:""}]);'''
new_state='''[advOpen,setAdvOpen]=(0,W.useState)(false),[advMenu,setAdvMenu]=(0,W.useState)(null),[advYears,setAdvYears]=(0,W.useState)([]),[advMonths,setAdvMonths]=(0,W.useState)([]),[advFrom,setAdvFrom]=(0,W.useState)(""),[advTo,setAdvTo]=(0,W.useState)(""),[advRisks,setAdvRisks]=(0,W.useState)([]),[advFormats,setAdvFormats]=(0,W.useState)([]),[advComps,setAdvComps]=(0,W.useState)([]);'''
if h.count(old_state)!=1:
    raise SystemExit(f'Advanced v2 expected old state once, found {h.count(old_state)}')
h=h.replace(old_state,new_state,1)

start=h.find('''  let P=[...new Set(t.bets.map(o=>o.source||"My Pick").filter(Boolean))].sort(),''')
end=h.find('''  (0,W.useEffect)(()=>{C(x=>{let z=new Set([...x].filter(id=>t.bets.some(p=>p.id===id)));''',start)
if start<0 or end<0:
    raise SystemExit('Advanced v2 could not locate tracker filter/helper block')
new_logic='''  function btCompetitionMeta(o){
    const legacy=String(o?.competition||"").trim(),unknown=/^(?:multiple competitions|multi-competition)$/i.test(legacy),raw=[];
    if(Array.isArray(o?.competitions))raw.push(...o.competitions);
    if(legacy&&!unknown)raw.push(...legacy.split(/\\s*(?:,|;|\\|)\\s*/));
    const items=[...new Set(raw.map(x=>String(x||"").trim()).filter(Boolean).filter(x=>!/^(?:multiple competitions|multi-competition)$/i.test(x)))];
    return {items,multi:unknown||items.length>1,unknown};
  }
  function btAdvancedMatch(o){
    const date=String(o?.date||""),year=date.slice(0,4),month=date.slice(5,7);
    if(advYears.length&&!advYears.includes(year))return false;
    if(advMonths.length&&!advMonths.includes(month))return false;
    if(advFrom&&(!date||date<advFrom))return false;
    if(advTo&&(!date||date>advTo))return false;
    if(advRisks.length&&!advRisks.includes(String(o?.type||"")))return false;
    if(advFormats.length&&!advFormats.includes(String(o?.betFormat||"")))return false;
    if(advComps.length){
      const meta=btCompetitionMeta(o),wantMulti=advComps.includes("__MULTI__"),named=advComps.filter(x=>x!=="__MULTI__");
      const viaMulti=wantMulti&&meta.multi;
      const viaNamed=meta.items.length>0&&named.length>0&&meta.items.every(x=>named.includes(x));
      if(!viaMulti&&!viaNamed)return false;
    }
    return true;
  }
  const btRiskLabel=x=>/^Low Risk/i.test(x)?"Low Risk":/^Medium Risk/i.test(x)?"Medium Risk":/^High Risk/i.test(x)?"High Risk":/^Longshot/i.test(x)?"Longshot":x;
  const btToggle=(vals,setter,value)=>setter(vals.includes(value)?vals.filter(x=>x!==value):[...vals,value]);
  const btSummary=(vals,opts)=>{if(!vals.length)return "All";if(vals.length===1)return opts.find(x=>x[0]===vals[0])?.[1]||vals[0];return `${vals.length} selected`};
  const btMulti=(label,key,vals,opts,setter)=>(0,c.jsxs)("div",{className:"bt-adv-filter",children:[
    (0,c.jsx)("span",{children:label}),
    (0,c.jsxs)("button",{type:"button",className:`bt-adv-picker${vals.length?" has-value":""}`,onClick:()=>setAdvMenu(m=>m===key?null:key),"aria-expanded":advMenu===key,children:[(0,c.jsx)("b",{children:btSummary(vals,opts)}),(0,c.jsx)("i",{children:"⌄"})]}),
    advMenu===key&&(0,c.jsxs)("div",{className:"bt-adv-menu",children:[
      (0,c.jsxs)("div",{className:"bt-adv-menu-actions",children:[(0,c.jsx)("button",{type:"button",onClick:()=>setter(opts.map(x=>x[0])),children:"Select all"}),(0,c.jsx)("button",{type:"button",onClick:()=>setter([]),children:"Clear"})]}),
      (0,c.jsx)("div",{className:"bt-adv-checks",children:opts.map(([value,text])=>(0,c.jsxs)("label",{children:[(0,c.jsx)("input",{type:"checkbox",checked:vals.includes(value),onChange:()=>btToggle(vals,setter,value)}),(0,c.jsx)("span",{children:text})]},value))})
    ]})
  ]});
  let P=[...new Set(t.bets.map(o=>o.source||"My Pick").filter(Boolean))].sort(),
      btYears=[...new Set(t.bets.map(o=>String(o.date||"").slice(0,4)).filter(x=>/^\\d{4}$/.test(x)))].sort((a,b)=>b.localeCompare(a)).map(x=>[x,x]),
      btMonths=[["01","January"],["02","February"],["03","March"],["04","April"],["05","May"],["06","June"],["07","July"],["08","August"],["09","September"],["10","October"],["11","November"],["12","December"]],
      btRisks=[...new Set(t.bets.map(o=>o.type).filter(Boolean))].sort().map(x=>[x,btRiskLabel(x)]),
      btFormats=[...new Set(t.bets.map(o=>o.betFormat).filter(Boolean))].sort().map(x=>[x,x]),
      btCommonComps=["Premier League","Champions League","Europa League","Conference League","Championship","League One","League Two","FA Cup","EFL Cup","World Cup","European Championship","PDC World Championship","PDC European Tour","NBA"],
      btSeenComps=[...new Set(t.bets.flatMap(o=>btCompetitionMeta(o).items))],
      btCompNames=[...new Set([...btCommonComps,...btSeenComps])].sort((a,b)=>a.localeCompare(b)),
      btCompOptions=[["__MULTI__","Multi-competition"],...btCompNames.map(x=>[x,x])],
      v=[...(0,W.useMemo)(()=>lm(t),[t])].reverse().filter(o=>i==="All"||o.app===i).filter(o=>s==="All"||o.sport===s).filter(o=>b==="All"||o.result===b).filter(o=>d==="All"||(o.source||"My Pick")===d).filter(o=>`${o.description||""} ${o.app||""} ${o.sport||""} ${o.competition||""} ${o.event||""} ${o.market||""} ${o.selection||""} ${o.source||""} ${o.betFormat||""}`.toLowerCase().includes(n.toLowerCase())).filter(btAdvancedMatch),
      T=v.reduce((o,r)=>o+_n(r),0),E=v.reduce((o,r)=>o+(r.profitLoss??0),0),S=v.filter(o=>o.result==="Win").length,y=v.filter(o=>o.result==="Loss").length;
'''
h=h[:start]+new_logic+h[end:]

panel_start=h.find('''      advOpen&&(0,c.jsxs)("div",{className:"bt-tracker-advanced-panel",children:''')
panel_end=h.find('''      (0,c.jsx)("div",{className:"table-wrap bet-table-wrap"''',panel_start)
if panel_start<0 or panel_end<0:
    raise SystemExit('Advanced v2 could not locate generic Advanced panel')
new_panel='''      advOpen&&(0,c.jsxs)("div",{className:"bt-tracker-advanced-panel",children:[
        (0,c.jsxs)("div",{className:"bt-advanced-head",children:[(0,c.jsx)("strong",{children:"Advanced filters"}),(0,c.jsx)("button",{type:"button",className:"button secondary bt-adv-clear-all",onClick:()=>{setAdvYears([]);setAdvMonths([]);setAdvFrom("");setAdvTo("");setAdvRisks([]);setAdvFormats([]);setAdvComps([]);setAdvMenu(null)},children:"Clear all"})]}),
        (0,c.jsxs)("div",{className:"bt-advanced-grid",children:[
          btMulti("Year","year",advYears,btYears,setAdvYears),
          btMulti("Month","month",advMonths,btMonths,setAdvMonths),
          (0,c.jsxs)("div",{className:"bt-adv-filter bt-adv-date-range",children:[(0,c.jsx)("span",{children:"Custom date range"}),(0,c.jsxs)("div",{children:[(0,c.jsx)("input",{type:"date",value:advFrom,onChange:o=>setAdvFrom(o.target.value),"aria-label":"Advanced from date"}),(0,c.jsx)("em",{children:"to"}),(0,c.jsx)("input",{type:"date",value:advTo,onChange:o=>setAdvTo(o.target.value),"aria-label":"Advanced to date"})]})]}),
          btMulti("Risk Level","risk",advRisks,btRisks,setAdvRisks),
          btMulti("Bet Type","format",advFormats,btFormats,setAdvFormats),
          btMulti("Competition","competition",advComps,btCompOptions,setAdvComps)
        ]})
      ]}),
'''
h=h[:panel_start]+new_panel+h[panel_end:]

# Make the existing whole-bet Competition field explicit about comma-separated
# multi-competition tagging. Existing data shape stays backwards-compatible.
old_comp='''(0,c.jsxs)("label",{children:["Competition",(0,c.jsx)("input",{name:"competition",defaultValue:t?.competition??"",placeholder:"e.g. Premier League"})]}),'''
new_comp='''(0,c.jsxs)("label",{children:["Competition(s)",(0,c.jsx)("input",{name:"competition",defaultValue:t?.competition??"",placeholder:"e.g. Premier League, Championship"})]}),'''
if h.count(old_comp)!=1:
    raise SystemExit(f'Advanced v2 expected one Add/Edit competition field, found {h.count(old_comp)}')
h=h.replace(old_comp,new_comp,1)

# Also expose the same whole-bet competition field in the Paddy review screen,
# so imported bets can be tagged before they are added to the tracker.
old_review='''${field('Notes','notes',p.notes||'','text',true)}${field('Source','source',p.source||'','text',true)}</div>'''
new_review='''${field('Notes','notes',p.notes||'','text',true)}${field('Source','source',p.source||'','text',true)}${field('Competition(s)','competition',p.competition||'','text',true)}</div>'''
if h.count(old_review)!=1:
    raise SystemExit(f'Advanced v2 expected one Paddy review metadata row, found {h.count(old_review)}')
h=h.replace(old_review,new_review,1)

style_start=h.find('<style id="bt-advanced-filter-styles">')
style_end=h.find('</style>',style_start)
if style_start<0 or style_end<0:
    raise SystemExit('Advanced v2 could not locate old advanced styles')
style_end+=len('</style>')
new_style='''<style id="bt-advanced-filter-styles">
.bt-filter-control{display:grid;gap:4px;min-width:118px}.bt-filter-control>span{font-size:9px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:#8298aa}.bt-filter-control select{width:100%}.bt-advanced-toggle{white-space:nowrap;align-self:end}.bt-advanced-toggle.is-active{border-color:rgba(84,134,255,.65)!important;background:rgba(46,103,240,.16)!important}.bt-tracker-advanced-panel{display:block;margin:12px 0 14px;padding:14px;border:1px solid rgba(84,134,255,.34);border-radius:12px;background:#081925;box-shadow:0 12px 28px rgba(0,0,0,.22);overflow:visible}.bt-advanced-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:11px}.bt-advanced-head strong{font-size:13px}.bt-adv-clear-all{min-height:30px!important;padding:6px 10px!important}.bt-advanced-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.bt-adv-filter{position:relative;display:grid;gap:5px;min-width:0}.bt-adv-filter>span{font-size:8px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#8298aa}.bt-adv-picker{height:36px;width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;border:1px solid rgba(120,157,190,.2);border-radius:8px;background:#06131f;color:#eaf3fb;padding:0 10px;cursor:pointer;text-align:left}.bt-adv-picker b{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px}.bt-adv-picker i{font-style:normal;color:#8298aa}.bt-adv-picker.has-value{border-color:rgba(84,134,255,.55);background:rgba(46,103,240,.08)}.bt-adv-menu{position:absolute;z-index:1200;top:calc(100% + 5px);left:0;width:min(310px,82vw);padding:8px;border:1px solid rgba(120,157,190,.24);border-radius:10px;background:#071725;box-shadow:0 18px 42px rgba(0,0,0,.48)}.bt-adv-menu-actions{display:flex;justify-content:flex-end;gap:6px;padding:0 0 7px;border-bottom:1px solid rgba(120,157,190,.12)}.bt-adv-menu-actions button{border:0;background:transparent;color:#8fb3ff;font-size:9px;font-weight:800;cursor:pointer}.bt-adv-checks{max-height:235px;overflow:auto;padding-top:6px}.bt-adv-checks label{display:flex;align-items:center;gap:8px;padding:6px 5px;border-radius:6px;color:#dce7f3;font-size:10px;cursor:pointer}.bt-adv-checks label:hover{background:rgba(255,255,255,.04)}.bt-adv-checks input{width:14px;height:14px;accent-color:#2e67f0}.bt-adv-date-range{grid-column:span 1}.bt-adv-date-range>div{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);align-items:center;gap:6px}.bt-adv-date-range input{min-width:0;width:100%;height:36px;border:1px solid rgba(120,157,190,.2);border-radius:8px;background:#06131f;color:#eaf3fb;padding:0 8px}.bt-adv-date-range em{font-size:9px;font-style:normal;color:#728aa0}@media(max-width:980px){.bt-advanced-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.filter-bar .bt-filter-control{min-width:140px}}@media(max-width:620px){.bt-advanced-grid{grid-template-columns:1fr}.bt-adv-date-range{grid-column:auto}.bt-tracker-advanced-panel{padding:11px}.bt-adv-menu{width:min(330px,calc(100vw - 48px))}}
</style>'''
h=h[:style_start]+new_style+h[style_end:]

# Guard against accidentally leaving the generic builder behind.
for bad in ['btAdvFields','btAddRule','Enter filter value','children:"Condition"','children:"+ Add filter"']:
    if bad in h:
        raise SystemExit(f'Advanced v2 still contains generic builder token: {bad}')
for good in ['btMulti("Year"','btMulti("Month"','Custom date range','btMulti("Risk Level"','btMulti("Bet Type"','btMulti("Competition"','Multi-competition','Competition(s)']:
    if good not in h:
        raise SystemExit(f'Advanced v2 missing expected token: {good}')

p.write_text(h,encoding='utf-8')
print('Rebuilt Bet Tracker Advanced filters as Excel-style Year / Month / Date / Risk / Bet Type / Competition multi-select filters')
