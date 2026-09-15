from pathlib import Path

path = Path('_site/index.html')
html = path.read_text(encoding='utf-8')

script = r'''
<script id="bt-paddy-text-click-fix">
(() => {
  "use strict";
  const setup = modal => {
    if (!modal || modal.dataset.btTextClickFix) return;
    modal.dataset.btTextClickFix = "1";
    const actions = modal.querySelector('.bt-import-actions');
    const scan = modal.querySelector('.bt-run-ocr');
    if (!actions || !scan) return;
    const parse = document.createElement('button');
    parse.type = 'button';
    parse.className = scan.className.replace(/\bbt-run-ocr\b/g, '').trim() + ' bt-run-paddy-text';
    parse.textContent = 'Parse pasted bets';
    parse.style.display = 'none';
    scan.insertAdjacentElement('afterend', parse);

    const sync = () => {
      const textMode = modal.dataset.btImportMode === 'text';
      scan.style.display = textMode ? 'none' : '';
      parse.style.display = textMode ? '' : 'none';
    };

    modal.querySelector('.bt-import-mode')?.addEventListener('click', () => setTimeout(sync, 0));
    new MutationObserver(sync).observe(modal, {attributes:true, attributeFilter:['data-bt-import-mode']});

    parse.addEventListener('click', e => {
      e.preventDefault();
      e.stopPropagation();
      const progress = modal.querySelector('.bt-import-progress');
      const text = modal.querySelector('.bt-paddy-text')?.value || '';
      try {
        if (!text.trim()) throw new Error('Paste the Paddy Power text into the box first.');
        if (typeof window.__btParsePaddyText !== 'function') throw new Error('Paddy text parser is not ready.');
        if (progress) progress.textContent = 'Parsing copied Paddy Power text…';
        const items = window.__btParsePaddyText(text);
        // Reuse the text importer renderer by temporarily dispatching its own handler is unsafe because
        // the screenshot handler is registered first. Store the parse and render a dedicated review.
        modal.__btTextResults = items;
        const old = modal.querySelector('.bt-multi-review'); if (old) old.remove();
        const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        const ready = p => Array.isArray(p?._parseIssues) && p._parseIssues.length===0 && Array.isArray(p?.legs) && p.legs.length>0;
        const good = items.filter(x=>ready(x.parsed)).length;
        const box = document.createElement('section'); box.className='bt-multi-review';
        box.innerHTML = `<div class="bt-multi-review-head"><strong>${items.length} bets parsed from Paddy text</strong><span>${good} ready · ${items.length-good} need checking</span></div><div class="bt-multi-list">${items.map((x,i)=>{const p=x.parsed,ok=ready(p),issues=p._parseIssues||[],legs=p.legs||[];const lines=legs.slice(0,6).map((l,j)=>`<div><b>${j+1}.</b> ${esc(l.event)} · ${esc(l.market)} · <b>${esc(l.selection)}</b>${l._superSubReplacement?` <span style="color:#8299af">→ ${esc(l._superSubReplacement)}</span>`:''}</div>`).join('')+(legs.length>6?`<div>+ ${legs.length-6} more selections</div>`:'');return `<label class="bt-multi-bet ${ok?'':'bad'}"><input class="bt-multi-check" type="checkbox" data-i="${i}" ${ok?'checked':''} ${ok?'':'disabled'}><div class="bt-multi-bet-main"><div class="bt-multi-bet-top"><strong>Bet ${i+1}${ok?'':' · CHECK REQUIRED'}</strong><span>${esc(p._betId||p.date||'')}</span></div><div class="bt-multi-meta"><i>${esc(p.betFormat)}</i><i>${legs.length} legs</i><i>${esc(p.result)}</i><i>Stake £${Number(p.stake||0).toFixed(2)}</i><i>Potential £${Number(p.returns||0).toFixed(2)}</i>${p._receiptOdds?`<i>Price ${esc(p._receiptOdds)}</i>`:''}</div><div class="bt-multi-lines ${issues.length?'bt-text-warning':''}">${issues.length?issues.map(z=>`<div>${esc(z)}</div>`).join(''):lines}</div></div></label>`}).join('')}</div>`;
        modal.querySelector('.bt-import-grid')?.insertAdjacentElement('afterend',box);
        const use=modal.querySelector('.bt-use-import'); if(use){use.classList.add('bt-multi-import');use.textContent=`Import selected (${good})`;use.disabled=!good;}
        box.querySelectorAll('.bt-multi-check').forEach(cb=>cb.addEventListener('change',()=>{const n=box.querySelectorAll('.bt-multi-check:checked').length;if(use){use.textContent=`Import selected (${n})`;use.disabled=!n;}}));
        if (progress) progress.textContent=`Parsed ${items.length} bets · ${good} ready to import.`;
      } catch(err) {
        console.error('Paddy text parse',err);
        if(progress) progress.textContent=`Text import failed: ${err?.message||'Could not parse the pasted text.'}`;
      }
    }, true);
    sync();
  };
  const run=()=>document.querySelectorAll('.bt-import-modal').forEach(setup);
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true}); run();
})();
</script>
'''

if 'id="bt-paddy-text-click-fix"' in html:
    raise SystemExit('Paddy text click fix already present')
html = html.replace('</body>', script + '\n</body>', 1)
path.write_text(html, encoding='utf-8')
print('Applied Paddy text click fix')
