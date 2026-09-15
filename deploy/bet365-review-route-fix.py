from pathlib import Path

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

old_class="review.className=use.className+' bt-review-bet365-text';"
new_class="review.className=use.className.replace(/\\bbt-use-import\\b/g,'').trim()+' bt-review-bet365-text';"
if h.count(old_class)!=1:
    raise SystemExit(f'Expected one Bet365 review class assignment, found {h.count(old_class)}')
h=h.replace(old_class,new_class,1)

old_route='if(modal?.dataset.btImportMode==="text"&&typeof window.__btOpenPaddyReview==="function"){window.__btOpenPaddyReview(modal);return}if(modal)await useImportV6(modal);return'
new_route='if((modal?.dataset.btImportMode==="text"||modal?.dataset.btImportMode==="bet365text")&&typeof window.__btOpenPaddyReview==="function"){window.__btOpenPaddyReview(modal);return}if(modal)await useImportV6(modal);return'
if h.count(old_route)!=1:
    raise SystemExit(f'Expected one scanner review route, found {h.count(old_route)}')
h=h.replace(old_route,new_route,1)

p.write_text(h,encoding='utf-8')
print('Fixed Bet365 review button so screenshot validation cannot intercept it; bet365text now explicitly routes to reviewed-import flow')
