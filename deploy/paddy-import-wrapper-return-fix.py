from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')
old='''window.__btImportReviewedPaddy=async (modal,items)=>{ modal.__btTextResults=items; const old=modal.querySelectorAll(".bt-multi-check"); old.forEach((c,i)=>c.checked=i<items.length); await importSelected(modal); };'''
new='''window.__btImportReviewedPaddy=async (modal,items)=>{ modal.__btTextResults=items; const old=modal.querySelectorAll(".bt-multi-check"); old.forEach((c,i)=>c.checked=i<items.length); return await importSelected(modal); };'''
if h.count(old)!=1:
    raise SystemExit(f'Expected one reviewed Paddy import wrapper, found {h.count(old)}')
h=h.replace(old,new,1)
p.write_text(h,encoding='utf-8')
print('Fixed reviewed Paddy importer to return {added,total,error} to loading screen')
