from pathlib import Path

p = Path('_site/index.html')
h = p.read_text(encoding='utf-8')

# The base screenshot importer owns an earlier document-level capture listener for .bt-use-import.
# It was swallowing the Paddy review click before any later Paddy listener could see it.
old_core = '''const use=e.target.closest?.(".bt-use-import");if(use){e.preventDefault();e.stopImmediatePropagation();const modal=use.closest(".bt-import-modal");if(modal)await useImportV6(modal);return}'''
new_core = '''const use=e.target.closest?.(".bt-use-import");if(use){e.preventDefault();e.stopImmediatePropagation();const modal=use.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="text"&&typeof window.__btOpenPaddyReview==="function"){window.__btOpenPaddyReview(modal);return}if(modal)await useImportV6(modal);return}'''
if h.count(old_core) != 1:
    raise SystemExit(f'Expected exactly one base import capture route, found {h.count(old_core)}')
h = h.replace(old_core, new_core, 1)

# The review script used selector-first calls like $(".bt-pr-count", overlay),
# but the helper had accidentally been declared root-first. That made render() throw.
old_helper = '''const $=(r,s)=>r?.querySelector(s), $$=(r,s)=>[...(r?.querySelectorAll(s)||[])], esc=s=>'''
new_helper = '''const $=(s,r=document)=>r?.querySelector(s), $$=(r,s)=>[...(r?.querySelectorAll(s)||[])], esc=s=>'''
if h.count(old_helper) != 1:
    raise SystemExit(f'Expected exactly one broken Paddy review selector helper, found {h.count(old_helper)}')
h = h.replace(old_helper, new_helper, 1)

p.write_text(h, encoding='utf-8')
print('Applied Paddy review runtime fix: base click interceptor rerouted + review renderer helper corrected')
