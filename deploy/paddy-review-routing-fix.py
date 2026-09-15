from pathlib import Path

p = Path('_site/index.html')
h = p.read_text(encoding='utf-8')

old = '''    const use=e.target.closest?.(".bt-use-import");if(use){const modal=use.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="text"){e.preventDefault();e.stopImmediatePropagation();await importSelected(modal);return}}'''
new = '''    const use=e.target.closest?.(".bt-use-import");if(use){const modal=use.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="text"){e.preventDefault();e.stopImmediatePropagation();if(typeof window.__btOpenPaddyReview==="function")window.__btOpenPaddyReview(modal);return}}'''

count = h.count(old)
if count != 1:
    raise SystemExit(f'Expected exactly 1 Paddy direct-import click handler, found {count}')

h = h.replace(old, new, 1)
p.write_text(h, encoding='utf-8')
print('Routed Paddy text action through review stage')
