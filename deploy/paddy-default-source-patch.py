from pathlib import Path

p = Path('_site/index.html')
h = p.read_text(encoding='utf-8')
old = 'source:"Paddy Power Text Import"'
new = 'source:"My Pick"'
count = h.count(old)
if count != 1:
    raise SystemExit(f'Expected exactly one Paddy source default, found {count}')
h = h.replace(old, new, 1)
p.write_text(h, encoding='utf-8')
print('Set Paddy imported bet source default to My Pick')
