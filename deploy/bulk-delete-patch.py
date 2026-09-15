from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

repls=[
('function r1({data:t,onAdd:l,onEdit:a,onDelete:e}){\n  let[n,u]=(0,W.useState)(""),[i,f]=(0,W.useState)("All"),[s,m]=(0,W.useState)("All"),[b,h]=(0,W.useState)("All"),[d,k]=(0,W.useState)("All");',
 'function r1({data:t,onAdd:l,onEdit:a,onDelete:e,onBulkDelete:q}){\n  let[n,u]=(0,W.useState)(""),[i,f]=(0,W.useState)("All"),[s,m]=(0,W.useState)("All"),[b,h]=(0,W.useState)("All"),[d,k]=(0,W.useState)("All"),[B,C]=(0,W.useState)(()=>new Set);'),
('      T=v.reduce((o,r)=>o+_n(r),0),E=v.reduce((o,r)=>o+(r.profitLoss??0),0),S=v.filter(o=>o.result==="Win").length,y=v.filter(o=>o.result==="Loss").length;\n  return(0,c.jsxs)',
 '      T=v.reduce((o,r)=>o+_n(r),0),E=v.reduce((o,r)=>o+(r.profitLoss??0),0),S=v.filter(o=>o.result==="Win").length,y=v.filter(o=>o.result==="Loss").length;\n  (0,W.useEffect)(()=>{C(x=>{let z=new Set([...x].filter(id=>t.bets.some(p=>p.id===id)));return z.size===x.size?x:z})},[t.bets]);\n  let A=v.length>0&&v.every(o=>B.has(o.id)),D=(id,checked,shift)=>{C(x=>{let z=new Set(x),anchor=r1.__btLastSelectedId;if(shift&&anchor){let a=v.findIndex(o=>o.id===anchor),b=v.findIndex(o=>o.id===id);if(a>=0&&b>=0){let lo=Math.min(a,b),hi=Math.max(a,b);v.slice(lo,hi+1).forEach(o=>checked?z.add(o.id):z.delete(o.id))}else checked?z.add(id):z.delete(id)}else checked?z.add(id):z.delete(id);return z});r1.__btLastSelectedId=id},H=()=>{r1.__btLastSelectedId=null;C(x=>{let z=new Set(x);if(A)v.forEach(o=>z.delete(o.id));else v.forEach(o=>z.add(o.id));return z})},R=()=>{if(B.size&&q?.([...B])){C(new Set);r1.__btLastSelectedId=null}};\n  return(0,c.jsxs)'),
('    (0,c.jsx)(Ul,{eyebrow:"Detailed bet tracking",title:"Bet Tracker",description:"",actions:(0,c.jsx)("button",{className:"button primary",onClick:l,children:"+ Add bet"})}),',
 '    (0,c.jsx)(Ul,{eyebrow:"Detailed bet tracking",title:"Bet Tracker",description:"",actions:(0,c.jsxs)(c.Fragment,{children:[B.size>0&&(0,c.jsx)("button",{className:"button secondary bt-bulk-delete",onClick:R,children:`Delete selected (${B.size})`}),(0,c.jsx)("button",{className:"button primary",onClick:l,children:"+ Add bet"})]})}),'),
('(0,c.jsx)("th",{children:"Balance"}),(0,c.jsx)("th",{})]})}),',
 '(0,c.jsx)("th",{children:"Balance"}),(0,c.jsx)("th",{className:"bt-select-col",children:(0,c.jsx)("input",{type:"checkbox",checked:A,onChange:H,disabled:!v.length,"aria-label":"Select all filtered bets",title:"Select all filtered bets"})})]})}),'),
('(0,c.jsx)("tbody",{children:v.map(o=>(0,c.jsx)(m1,{item:o,onEdit:()=>a(o),onDelete:()=>e(o.id)},o.id))})',
 '(0,c.jsx)("tbody",{children:v.map(o=>(0,c.jsx)(m1,{item:o,onEdit:()=>a(o),onDelete:()=>e(o.id),isSelected:B.has(o.id),onSelect:(checked,shift)=>D(o.id,checked,shift)},o.id))})'),
('function m1({item:t,onEdit:l,onDelete:a}){',
 'function m1({item:t,onEdit:l,onDelete:a,isSelected:o,onSelect:r}){'),
('(0,c.jsx)("td",{children:(0,c.jsxs)("div",{className:"row-actions",children:[t.receiptImage&&',
 '(0,c.jsx)("td",{children:(0,c.jsxs)("div",{className:"row-actions",children:[(0,c.jsx)("input",{type:"checkbox",className:"bt-row-select",checked:o,onClick:e=>r(e.currentTarget.checked,e.shiftKey),onChange:()=>{},"aria-label":`Select ${e}`,title:"Select bet · Shift-click to select a range"}),t.receiptImage&&'),
('},v=r=>{h(p=>({...p,bets:p.bets.some(A=>A.id===r.id)?p.bets.map(A=>A.id===r.id?r:A):[...p.bets,r]})),s(null)},T=r=>{window.confirm("Delete this bet?")&&h(p=>({...p,bets:p.bets.filter(A=>A.id!==r)}))},E=r=>{',
 '},v=r=>{h(p=>({...p,bets:p.bets.some(A=>A.id===r.id)?p.bets.map(A=>A.id===r.id?r:A):[...p.bets,r]})),s(null)},T=r=>{window.confirm("Delete this bet?")&&h(p=>({...p,bets:p.bets.filter(A=>A.id!==r)}))},B=r=>{if(!r?.length)return!1;if(!window.confirm(`Delete ${r.length} selected bet${r.length===1?"":"s"}? This cannot be undone.`))return!1;let z=new Set(r);h(p=>({...p,bets:p.bets.filter(A=>!z.has(A.id))}));return!0},E=r=>{'),
('u==="bets"&&(0,c.jsx)(r1,{data:l,onAdd:()=>s({type:"bet"}),onEdit:r=>s({type:"bet",bet:r}),onDelete:T}),',
 'u==="bets"&&(0,c.jsx)(r1,{data:l,onAdd:()=>s({type:"bet"}),onEdit:r=>s({type:"bet",bet:r}),onDelete:T,onBulkDelete:B}),')
]

for old,new in repls:
    count=h.count(old)
    if count!=1:
        raise SystemExit(f'Bulk-delete patch expected one match, found {count}: {old[:90]}')
    h=h.replace(old,new,1)

css='''\n<style id="bt-bulk-delete-styles">\n.bt-select-col{width:54px;text-align:center}.bt-select-col input,.bt-row-select{width:16px;height:16px;accent-color:#2e67f0;cursor:pointer}.row-actions .bt-row-select{margin:0 4px 0 0;flex:0 0 auto}.bt-bulk-delete{border-color:rgba(255,105,120,.35)!important;color:#ffb4bd!important;background:rgba(120,25,38,.16)!important}\n</style>\n'''
if 'id="bt-bulk-delete-styles"' in h:
    raise SystemExit('Bulk-delete patch already applied')
h=h.replace('</head>',css+'</head>',1)
p.write_text(h,encoding='utf-8')
print('Applied Bet Tracker row selection, Shift-click range selection, select-all-filtered and single-confirm bulk delete')
