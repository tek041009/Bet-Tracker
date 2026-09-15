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
   use.textContent=`Review ${results.length} parsed bets`;
   use.disabled=!ready;
   use.classList.add('bt-review-paddy-button');
 }
}
document.addEventListener('click',e=>{
 const parse=e.target.closest?.('.bt-run-paddy-text');
 if(parse){const modal=parse.closest('.bt-import-modal');setTimeout(()=>sync(modal),0);setTimeout(()=>sync(modal),50);return}
 const use=e.target.closest?.('.bt-use-import');
 const modal=use?.closest?.('.bt-import-modal');
 if(!use||!modal||modal.dataset.btImportMode!=="text"||!modal.__btTextResults?.length)return;
 e.preventDefault();e.stopImmediatePropagation();
 if(typeof window.__btOpenPaddyReview==='function')window.__btOpenPaddyReview(modal);
},true);
const mo=new MutationObserver(()=>document.querySelectorAll('.bt-import-modal[data-bt-import-mode="text"]').forEach(sync));mo.observe(document.body,{childList:true,subtree:true});
})();
</script>
'''
if 'id="bt-paddy-review-button-fix"' in h: raise SystemExit('already applied')
h=h.replace('</body>',script+'\n</body>',1)
p.write_text(h,encoding='utf-8')
print('Applied explicit Paddy review button fix')
