from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

old='''onClick:()=>setAdvOpen(x=>!x),children:advOpen?"Hide Advanced":"Advanced"'''
new='''onClick:()=>{if(!advOpen&&advRules.length===0)btAddRule();setAdvOpen(x=>!x)},"aria-expanded":advOpen,children:advOpen?"Hide Advanced":"Advanced"'''
if h.count(old)!=1:
    raise SystemExit(f'Expected one Advanced toggle handler, found {h.count(old)}')
h=h.replace(old,new,1)

# The base app already has an older .bt-advanced-panel { display:none } rule.
# Our conditional React panel reused the same class, so it existed in the DOM but was still hidden.
old_panel='''advOpen&&(0,c.jsxs)("div",{className:"bt-advanced-panel",children:'''
new_panel='''advOpen&&(0,c.jsxs)("div",{className:"bt-advanced-panel open",children:'''
if h.count(old_panel)!=1:
    raise SystemExit(f'Expected one Advanced panel render, found {h.count(old_panel)}')
h=h.replace(old_panel,new_panel,1)

old_css='''.bt-advanced-panel{margin:12px 0 14px;padding:14px;border:1px solid rgba(120,157,190,.18);border-radius:12px;background:#081925}'''
new_css='''.bt-advanced-panel{display:block!important;margin:12px 0 14px;padding:16px;border:1px solid rgba(84,134,255,.48);border-radius:12px;background:#081925;box-shadow:0 12px 28px rgba(0,0,0,.28);max-height:42vh;overflow:auto}'''
if h.count(old_css)!=1:
    raise SystemExit(f'Expected one Advanced panel style, found {h.count(old_css)}')
h=h.replace(old_css,new_css,1)

p.write_text(h,encoding='utf-8')
print('Fixed Advanced panel visibility conflict with legacy display:none CSS')
