from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

old='''onClick:()=>setAdvOpen(x=>!x),children:advOpen?"Hide Advanced":"Advanced"'''
new='''onClick:()=>{if(!advOpen&&advRules.length===0)btAddRule();setAdvOpen(x=>!x)},"aria-expanded":advOpen,children:advOpen?"Hide Advanced":"Advanced"'''
if h.count(old)!=1:
    raise SystemExit(f'Expected one Advanced toggle handler, found {h.count(old)}')
h=h.replace(old,new,1)

# Do NOT reuse .bt-advanced-panel: the base app already uses that class for the
# Profit / Loss Analysis advanced panel and its CSS deliberately starts hidden.
# Give the Bet Tracker panel its own class so the two features cannot conflict.
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
print('Tracker Advanced panel now uses its own visible class, isolated from legacy Analysis advanced CSS')
