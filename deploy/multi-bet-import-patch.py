from pathlib import Path

path = Path('_site/index.html')
html = path.read_text(encoding='utf-8')

css = r'''
<style id="bt-multi-import-styles">
.bt-import-mode{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}
.bt-import-mode button{min-height:36px;border:1px solid var(--line);border-radius:8px;background:#071b2e;color:#8fa6bc;font-size:9px;font-weight:900;cursor:pointer}
.bt-import-mode button.active{background:rgba(46,103,240,.16);border-color:rgba(84,134,255,.5);color:#dce7ff}
.bt-multi-review{grid-column:1/-1;margin-top:14px;border:1px solid var(--line);border-radius:11px;background:#061827;overflow:hidden}
.bt-multi-review-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 13px;border-bottom:1px solid var(--line)}
.bt-multi-review-head strong{font-size:11px;color:#edf5fd}.bt-multi-review-head span{font-size:9px;color:var(--muted)}
.bt-multi-list{display:grid;gap:0;max-height:44vh;overflow:auto}
.bt-multi-bet{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;padding:11px 13px;border-bottom:1px solid rgba(139,174,209,.12)}
.bt-multi-bet:last-child{border-bottom:0}.bt-multi-bet input[type=checkbox]{margin-top:3px;accent-color:#2e67f0}
.bt-multi-bet-main{min-width:0}.bt-multi-bet-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px}
.bt-multi-bet-top strong{font-size:10px;color:#edf5fd}.bt-multi-bet-top span{font-size:9px;color:#8da6be}
.bt-multi-meta{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:7px}.bt-multi-meta i{font-style:normal;padding:4px 7px;border-radius:999px;background:rgba(255,255,255,.045);color:#aac0d4;font-size:8px;font-weight:800}
.bt-multi-lines{display:grid;gap:3px;color:#c8d7e6;font-size:8.5px;line-height:1.45}.bt-multi-lines b{color:#fff}.bt-multi-bet.bad{background:rgba(255,87,110,.045)}.bt-multi-bet.bad .bt-multi-bet-top strong{color:#ff9aaa}
.bt-multi-actions-note{margin-right:auto;align-self:center;color:#8da6be;font-size:9px}
@media(max-width:760px){.bt-multi-list{max-height:38vh}.bt-multi-bet{grid-template-columns:24px 1fr}.bt-multi-bet-top{align-items:flex-start;flex-direction:column}}
</style>
'''

script = r'''
<script id="bt-multi-bet-import">
(() => {
  "use strict";

  const $ = (root, sel) => root?.querySelector(sel);
  const $$ = (root, sel) => [...(root?.querySelectorAll(sel) || [])];
  const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const wait = ms => new Promise(r => setTimeout(r, ms));

  function setCtl(el, value) {
    if (!el || value == null || value === "") return;
    const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : el instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, String(value)); else el.value = String(value);
    el.dispatchEvent(new Event("input", {bubbles:true}));
    el.dispatchEvent(new Event("change", {bubbles:true}));
  }

  async function imageCanvas(input) {
    let bmp = null;
    if (typeof createImageBitmap === "function") {
      try { bmp = await createImageBitmap(input); } catch (_) {}
    }
    if (bmp) {
      const c = document.createElement("canvas"); c.width = bmp.width; c.height = bmp.height;
      c.getContext("2d", {willReadFrequently:true}).drawImage(bmp, 0, 0);
      try { bmp.close?.(); } catch (_) {}
      return c;
    }
    const url = typeof input === "string" ? input : URL.createObjectURL(input);
    try {
      const img = await new Promise((res, rej) => { const i = new Image(); i.onload=()=>res(i); i.onerror=rej; i.src=url; });
      const c = document.createElement("canvas"); c.width=img.naturalWidth||img.width; c.height=img.naturalHeight||img.height;
      c.getContext("2d", {willReadFrequently:true}).drawImage(img,0,0); return c;
    } finally { if (typeof input !== "string") URL.revokeObjectURL(url); }
  }

  function detectFooterBands(canvas) {
    const ctx = canvas.getContext("2d", {willReadFrequently:true});
    const w=canvas.width,h=canvas.height,{data}=ctx.getImageData(0,0,w,h);
    const x0=Math.floor(w*.02), x1=Math.ceil(w*.98), step=Math.max(2,Math.round(w/420));
    const rows=[];
    for (let y=0;y<h;y++) {
      let good=0,total=0;
      for (let x=x0;x<x1;x+=step) {
        const p=(y*w+x)*4,r=data[p],g=data[p+1],b=data[p+2],mx=Math.max(r,g,b),mn=Math.min(r,g,b);
        total++;
        if (r>=226&&r<=252&&g>=226&&g<=252&&b>=226&&b<=253&&mx-mn<=12) good++;
      }
      if (total && good/total >= .46) rows.push(y);
    }
    if (!rows.length) return [];
    const groups=[]; let s=rows[0],p=s;
    for (const y of rows.slice(1)) { if (y<=p+2) p=y; else { groups.push([s,p]); s=p=y; } }
    groups.push([s,p]);
    const minH=Math.max(8,Math.round(h*.0025)), maxH=Math.max(90,Math.round(h*.09));
    return groups
      .filter(g => g[1]-g[0]+1 >= minH && g[1]-g[0]+1 <= maxH)
      .map(g => ({top:g[0],bottom:g[1],height:g[1]-g[0]+1}))
      .filter((g,i,a) => i===0 || g.top-a[i-1].bottom > Math.max(55,Math.round(h*.012)));
  }

  function receiptSegments(canvas) {
    const bands=detectFooterBands(canvas);
    if (bands.length < 2) return [];
    const out=[]; let start=0;
    for (let i=0;i<bands.length;i++) {
      const b=bands[i];
      const end=Math.min(canvas.height,b.bottom+3);
      const height=end-start;
      if (height>=110) out.push({y0:start,y1:end,footer:b});
      start=Math.min(canvas.height,b.bottom+1);
    }
    return out.filter(s=>s.y1-s.y0>=110).slice(0,30);
  }

  function cropCanvas(base, seg) {
    const h=Math.max(1,seg.y1-seg.y0), c=document.createElement("canvas");
    c.width=base.width;c.height=h;
    const x=c.getContext("2d");x.fillStyle="#fff";x.fillRect(0,0,c.width,c.height);x.drawImage(base,0,seg.y0,base.width,h,0,0,base.width,h);
    return c;
  }

  function canvasBlob(canvas) { return new Promise((res,rej)=>canvas.toBlob(b=>b?res(b):rej(new Error("Could not create receipt crop")),"image/png")); }

  function isReady(p) {
    const stake=Number(p?.stake), ret=Number.isFinite(Number(p?.returnsPence))?Number(p.returnsPence)/100:Number(p?.returns);
    if (!p?.bookmaker || !p?.sport || !Number.isFinite(stake) || stake<=0 || !Number.isFinite(ret) || ret<0) return false;
    if ((p.betFormat==="Accumulator"||p.betFormat==="Bet Builder") && (!Array.isArray(p.legs)||!p.legs.length)) return false;
    return true;
  }

  function lineSummary(p) {
    const legs=Array.isArray(p?.legs)?p.legs:[];
    if (legs.length) return legs.slice(0,6).map((l,i)=>`<div><b>${i+1}.</b> ${esc(l.event||"")} · ${esc(l.market||"")} · <b>${esc(l.selection||"")}</b></div>`).join("") + (legs.length>6?`<div>+ ${legs.length-6} more selections</div>`:"");
    return `<div>${esc(p?.event||"")} · ${esc(p?.market||"")} · <b>${esc(p?.selection||"")}</b></div>`;
  }

  function renderMulti(modal, items) {
    modal.querySelector(".bt-multi-review")?.remove();
    modal.__btMultiResults=items;
    const good=items.filter(x=>isReady(x.parsed)).length;
    const box=document.createElement("section");box.className="bt-multi-review";
    box.innerHTML=`<div class="bt-multi-review-head"><strong>${items.length} bets separated</strong><span>${good} ready to import · ${items.length-good} need checking</span></div><div class="bt-multi-list">${items.map((x,i)=>{const p=x.parsed,ok=isReady(p),ret=Number.isFinite(Number(p?.returnsPence))?(Number(p.returnsPence)/100).toFixed(2):(Number.isFinite(Number(p?.returns))?Number(p.returns).toFixed(2):"—");return `<label class="bt-multi-bet ${ok?"":"bad"}"><input class="bt-multi-check" type="checkbox" data-i="${i}" ${ok?"checked":""} ${ok?"":"disabled"}><div class="bt-multi-bet-main"><div class="bt-multi-bet-top"><strong>Bet ${i+1}${ok?"":" · CHECK REQUIRED"}</strong><span>${esc(p?.date||"")}</span></div><div class="bt-multi-meta"><i>${esc(p?.bookmaker||"Bookmaker missing")}</i><i>${esc(p?.betFormat||"Single")}</i><i>${Array.isArray(p?.legs)&&p.legs.length?`${p.legs.length} legs`:esc(p?.result||"Pending")}</i><i>Stake ${Number.isFinite(Number(p?.stake))?`£${Number(p.stake).toFixed(2)}`:"—"}</i><i>Return ${ret==="—"?"—":`£${ret}`}</i></div><div class="bt-multi-lines">${lineSummary(p)}</div></div></label>`}).join("")}</div>`;
    const grid=$(modal,".bt-import-grid"); grid?.insertAdjacentElement("afterend",box);
    const normalFields=$(modal,".bt-import-fields"); if(normalFields)normalFields.style.display="none";
    modal.querySelector(".bt-import-leg-review")?.remove();
    const use=$(modal,".bt-use-import"); if(use){use.textContent=`Import selected (${good})`;use.classList.add("bt-multi-import");use.disabled=!good;}
    const actions=$(modal,".bt-import-actions");
    if(actions && !$(actions,".bt-multi-actions-note")){const n=document.createElement("span");n.className="bt-multi-actions-note";n.textContent="Untick any bet you do not want added.";actions.prepend(n)}
    $$(box,".bt-multi-check").forEach(cb=>cb.addEventListener("change",()=>{const n=$$(box,".bt-multi-check:checked").length;if(use){use.textContent=`Import selected (${n})`;use.disabled=!n}}));
  }

  async function scanMulti(modal) {
    const file=$(modal,'input[type="file"]')?.files?.[0],progress=$(modal,".bt-import-progress"),run=$(modal,".bt-run-ocr");
    if(!file){if(progress)progress.textContent="Choose one long screenshot first.";return}
    if(typeof window.__btOCRReceiptData!=="function"){if(progress)progress.textContent="Scanner is not ready yet.";return}
    if(run)run.disabled=true;
    try {
      if(progress)progress.textContent="Finding individual receipt boundaries…";
      const base=await imageCanvas(file),segments=receiptSegments(base);
      if(segments.length<2) throw new Error("I could not confidently find multiple Paddy Power receipt footers in this image. Make sure the screenshot contains the complete bottom Stake / Returns section for every bet.");
      const items=[];
      for(let i=0;i<segments.length;i++){
        if(progress)progress.textContent=`Scanning bet ${i+1} of ${segments.length}…`;
        const c=cropCanvas(base,segments[i]),blob=await canvasBlob(c);
        const parsed=await window.__btOCRReceiptData(blob,msg=>{if(progress)progress.textContent=`Bet ${i+1}/${segments.length} · ${msg}`});
        items.push({parsed,segment:segments[i]});
      }
      renderMulti(modal,items);
      if(progress)progress.textContent=`Multi scan complete · ${items.length} separate bets detected. Review the groups below before importing.`;
      return items;
    } catch(err) {
      console.error("Multi bet import",err); if(progress)progress.textContent=`Multi scan failed: ${err?.message||"Could not separate the receipts."}`; throw err;
    } finally {if(run)run.disabled=false}
  }

  async function openAddForm() {
    const add=[...document.querySelectorAll("button")].find(x=>x.textContent.trim()==="+ Add bet");
    if(!add) throw new Error("Open the Bet Tracker page before importing.");
    add.click();
    for(let i=0;i<75;i++){const f=document.querySelector(".modal-form");if(f)return f;await wait(40)}
    throw new Error("Add Bet form did not open.");
  }

  async function populateForm(form,p) {
    setCtl($(form,'[name="app"]'),p.bookmaker);setCtl($(form,'[name="sport"]'),p.sport||"Football");setCtl($(form,'[name="date"]'),p.date);
    setCtl($(form,'[name="source"]'),p.source||"Screenshot Import");setCtl($(form,'[name="competition"]'),p.competition||"");
    setCtl($(form,'[name="stake"]'),p.stake);setCtl($(form,'[name="potentialReturns"]'),Number.isFinite(Number(p.returnsPence))?(Number(p.returnsPence)/100).toFixed(2):p.returns);
    setCtl($(form,'[name="betFormat"]'),p.betFormat||"Single");setCtl($(form,'[name="result"]'),p.result||"Pending");
    await wait(120);
    if(Number(p.free)>0){const cb=$(form,'[name="isFreeBet"]');if(cb&&!cb.checked){cb.click();await wait(70)}setCtl($(form,'[name="freeBetAmount"]'),p.free)}
    const multi=(p.betFormat==="Accumulator"||p.betFormat==="Bet Builder")&&Array.isArray(p.legs)&&p.legs.length;
    if(multi){
      const target=p.legs.length;
      for(let guard=0;guard<45;guard++){
        const cards=$$(form,".bt-leg-card");if(cards.length===target)break;
        if(cards.length<target){$(form,".bt-add-leg")?.click();await wait(35)}
        else if(cards.length>target&&cards.length>1){cards.at(-1)?.querySelector(".bt-leg-head button")?.click();await wait(35)}
      }
      await wait(80);
      const cards=$$(form,".bt-leg-card");
      p.legs.forEach((leg,i)=>{const card=cards[i];if(!card)return;const sels=$$(card,"select"),ins=$$(card,"input");setCtl(sels[0],leg.sport||p.sport||"Football");setCtl(ins[0],leg.event||"");setCtl(ins[1],leg.market||"");setCtl(ins[2],leg.selection||"");if(leg.odds!=null&&leg.odds!=="")setCtl(ins[3],leg.odds);setCtl(sels[1],leg.result||p.result||"Pending")});
    } else {
      setCtl($(form,'[name="event"]'),p.event||"");setCtl($(form,'[name="market"]'),p.market||"");setCtl($(form,'[name="selection"]'),p.selection||"");
    }
    await wait(100);
  }

  async function importSelected(modal) {
    const items=modal.__btMultiResults||[],checks=$$(modal,".bt-multi-check:checked");
    const selected=checks.map(cb=>items[Number(cb.dataset.i)]).filter(Boolean);
    if(!selected.length)return;
    const use=$(modal,".bt-use-import");if(use)use.disabled=true;
    modal.closest(".bt-import-backdrop")?.remove();
    let added=0;
    try{
      for(let i=0;i<selected.length;i++){
        const p=selected[i].parsed;
        const form=await openAddForm();
        await populateForm(form,p);
        const submit=$(form,'button[type="submit"]');if(!submit)throw new Error(`Bet ${i+1}: Add Bet submit button missing.`);
        form.requestSubmit(submit);
        for(let t=0;t<75;t++){if(!form.isConnected)break;await wait(40)}
        if(form.isConnected)throw new Error(`Bet ${i+1}: the Add Bet form did not close after saving.`);
        added++;
        await wait(100);
      }
      window.alert(`${added} bet${added===1?"":"s"} imported from the long screenshot.`);
    }catch(err){console.error("Multi import save",err);window.alert(`${added} bet${added===1?"":"s"} imported before the process stopped. ${err?.message||"A bet could not be saved."}`)}
  }

  function setMode(modal, mode) {
    modal.dataset.btImportMode=mode;
    const multi=mode==="multi";
    $$(modal,".bt-import-mode button").forEach(b=>b.classList.toggle("active",b.dataset.mode===mode));
    const h=$(modal,".bt-import-head h2");if(h)h.textContent=multi?"Scan multiple bet receipts":"Scan a bet receipt";
    const fileLabel=$(modal,".bt-import-file");if(fileLabel){const input=$(fileLabel,"input");fileLabel.childNodes[0].textContent=multi?"Choose long screenshot":"Choose bet screenshot";if(input)fileLabel.appendChild(input)}
    const run=$(modal,".bt-run-ocr");if(run)run.textContent=multi?"Scan & split bets":"Scan screenshot";
    const fields=$(modal,".bt-import-fields");if(fields)fields.style.display=multi?"none":"";
    modal.querySelector(".bt-multi-review")?.remove();modal.__btMultiResults=null;
    const use=$(modal,".bt-use-import");if(use){use.classList.remove("bt-multi-import");use.textContent="Review in Add Bet";use.disabled=false}
    modal.querySelector(".bt-multi-actions-note")?.remove();
    const progress=$(modal,".bt-import-progress");if(progress)progress.textContent=multi?"Choose or paste one long screenshot containing complete receipts.":"Nothing scanned yet.";
  }

  function enhance(modal) {
    if(!modal || modal.dataset.btMultiReady)return;modal.dataset.btMultiReady="1";modal.dataset.btImportMode="single";
    const fileLabel=$(modal,".bt-import-file");if(!fileLabel)return;
    const modes=document.createElement("div");modes.className="bt-import-mode";modes.innerHTML='<button type="button" data-mode="single" class="active">Single Bet</button><button type="button" data-mode="multi">Multi Bet</button>';
    fileLabel.insertAdjacentElement("afterend",modes);
    modes.addEventListener("click",e=>{const b=e.target.closest("button[data-mode]");if(b)setMode(modal,b.dataset.mode)});
  }

  document.addEventListener("click", async e=>{
    const run=e.target.closest?.(".bt-run-ocr");
    if(run){const modal=run.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="multi"){e.preventDefault();e.stopImmediatePropagation();try{await scanMulti(modal)}catch(_){}return}}
    const use=e.target.closest?.(".bt-use-import");
    if(use){const modal=use.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="multi"){e.preventDefault();e.stopImmediatePropagation();await importSelected(modal);return}}
  },true);

  const mo=new MutationObserver(()=>document.querySelectorAll(".bt-import-modal").forEach(enhance));mo.observe(document.body,{childList:true,subtree:true});
  document.querySelectorAll(".bt-import-modal").forEach(enhance);
})();
</script>
'''

if 'id="bt-multi-bet-import"' in html:
    raise SystemExit('Multi Bet Import patch already present')
if '</head>' not in html or '</body>' not in html:
    raise SystemExit('HTML markers missing')
html = html.replace('</head>', css + '\n</head>', 1)
html = html.replace('</body>', script + '\n</body>', 1)
path.write_text(html, encoding='utf-8')
print('Applied Multi Bet Import patch')
