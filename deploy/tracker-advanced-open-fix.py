from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

blank='{field:"any",op:"contains",value:""}'

# Start with one real rule already present. This avoids relying on two batched
# React state updates (add-rule + open) from the same click.
old_state='''[advRules,setAdvRules]=(0,W.useState)([]);'''
new_state=f'''[advRules,setAdvRules]=(0,W.useState)(()=>[{blank}]);'''
if h.count(old_state)!=1:
    raise SystemExit(f'Expected one Advanced rules state initializer, found {h.count(old_state)}')
h=h.replace(old_state,new_state,1)

old='''onClick:()=>setAdvOpen(x=>!x),children:advOpen?"Hide Advanced":"Advanced"'''
new='''onClick:()=>setAdvOpen(x=>!x),"aria-expanded":advOpen,children:advOpen?"Hide Advanced":"Advanced"'''
if h.count(old)!=1:
    raise SystemExit(f'Expected one Advanced toggle handler, found {h.count(old)}')
h=h.replace(old,new,1)

# Clearing should leave one blank usable row rather than an empty panel.
old_clear='''onClick:()=>setAdvRules([]),children:"Clear"'''
new_clear=f'''onClick:()=>setAdvRules([{blank}]),children:"Clear"'''
if h.count(old_clear)!=1:
    raise SystemExit(f'Expected one Advanced clear handler, found {h.count(old_clear)}')
h=h.replace(old_clear,new_clear,1)

# Do NOT reuse .bt-advanced-panel: the base app already uses that class for the
# Profit / Loss Analysis advanced panel and its CSS deliberately starts hidden.
old_panel='''advOpen&&(0,c.jsxs)("div",{className:"bt-advanced-panel",children:'''
new_panel='''advOpen&&(0,c.jsxs)("div",{className:"bt-tracker-advanced-panel",children:'''
if h.count(old_panel)!=1:
    raise SystemExit(f'Expected one tracker Advanced panel render, found {h.count(old_panel)}')
h=h.replace(old_panel,new_panel,1)

old_css='''.bt-advanced-panel{margin:12px 0 14px;padding:14px;border:1px solid rgba(120,157,190,.18);border-radius:12px;background:#081925}'''
new_css='''.bt-tracker-advanced-panel{display:block;margin:12px 0 14px;padding:16px;border:1px solid rgba(84,134,255,.48);border-radius:12px;background:#081925;box-shadow:0 12px 28px rgba(0,0,0,.28);max-height:42vh;overflow:auto}'''
if h.count(old_css)!=1:
    raise SystemExit(f'Expected one tracker Advanced panel style, found {h.count(old_css)}')
h=h.replace(old_css,new_css,1)

p.write_text(h,encoding='utf-8')
print('Tracker Advanced now opens with a real visible rule and uses its own isolated panel class')
