from pathlib import Path
p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')
script=r'''
<script id="bt-paddy-review-button-fix">
(()=>{"use strict";
function sync(modal){
 if(!modal||modal.dataset.btImportMode!=="text")return;
 const use=modal.querySelector('.bt-use-import');
 if(!use)return;
 const results=modal.__btTextResults||[];
 if(results.length){
   const ready=results.filter(x=>Array.isArray(x?.parsed?.legs)&&x.parsed.legs.length>0).length;
   const label=`Review ${results.length} parsed bets`;
   if(use.textContent!==label) use.textContent=label;
   const disabled=!ready;
   if(use.disabled!==disabled) use.disabled=disabled;
   if(!use.classList.contains('bt-review-paddy-button')) use.classList.add('bt-review-paddy-button');
 }
}
document.addEventListener('click',e=>{
 const parse=e.target.closest?.('.bt-run-paddy-text');
 if(parse){const modal=parse.closest('.bt-import-modal');setTimeout(()=>sync(modal),0);setTimeout(()=>sync(modal),60);return}
 const use=e.target.closest?.('.bt-use-import');
 const modal=use?.closest?.('.bt-import-modal');
 if(!use||!modal||modal.dataset.btImportMode!=="text"||!modal.__btTextResults?.length)return;
 e.preventDefault();e.stopImmediatePropagation();
 if(typeof window.__btOpenPaddyReview==='function')window.__btOpenPaddyReview(modal);
},true);
// Deliberately no subtree MutationObserver here: the previous observer watched the whole document
// while sync() changed button text, causing a self-triggering mutation loop and UI freeze.
})();
</script>
'''
if 'id="bt-paddy-review-button-fix"' in h: raise SystemExit('already applied')
h=h.replace('</body>',script+'\n</body>',1)
p.write_text(h,encoding='utf-8')
print('Applied non-looping explicit Paddy review button fix')
