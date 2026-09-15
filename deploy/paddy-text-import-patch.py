from pathlib import Path

path = Path('_site/index.html')
html = path.read_text(encoding='utf-8')

css = r'''
<style id="bt-paddy-text-import-styles">
.bt-import-mode{grid-template-columns:repeat(3,minmax(0,1fr))!important}
.bt-text-import-panel{display:none;margin-top:9px}
.bt-text-import-panel textarea{width:100%;min-height:340px;max-height:52vh;resize:vertical;border:1px solid var(--line);border-radius:10px;background:#061827;color:#e8f1fa;padding:12px 13px;font:500 11px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;outline:none}
.bt-text-import-panel textarea:focus{border-color:rgba(84,134,255,.65);box-shadow:0 0 0 2px rgba(46,103,240,.12)}
.bt-text-import-help{margin:7px 2px 0;color:#8da6be;font-size:9px;line-height:1.45}
.bt-text-import-help b{color:#dce7ff}
.bt-text-warning{color:#ffb0ba!important}
@media(max-width:760px){.bt-import-mode{grid-template-columns:1fr!important}.bt-text-import-panel textarea{min-height:260px}}
</style>
'''

script = r'''
<script id="bt-paddy-text-import">
(() => {
  "use strict";

  const $=(r,s)=>r?.querySelector(s), $$=(r,s)=>[...(r?.querySelectorAll(s)||[])];
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const MONTHS={january:"01",february:"02",march:"03",april:"04",may:"05",june:"06",july:"07",august:"08",september:"09",october:"10",november:"11",december:"12"};

  function cleanLine(s){
    return String(s||"").replace(/\u00a0/g," ").replace(/\*\*/g,"").replace(/^\s*[-•·]\s*/,"").replace(/\s+/g," ").trim();
  }
  function parseDateLine(s){
    const m=cleanLine(s).match(/^(\d{1,2}):(\d{2})\s+(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})$/i);
    if(!m)return "";return `${m[5]}-${MONTHS[m[4].toLowerCase()]}-${String(Number(m[3])).padStart(2,"0")}`;
  }
  function resultCode(s){s=cleanLine(s).toUpperCase();return s==="W"?"Win":s==="L"?"Loss":s==="V"?"Void":""}
  function overallResult(legs){if(!legs.length)return "Pending";if(legs.some(x=>x.result==="Loss"))return "Loss";if(legs.every(x=>x.result==="Void"))return "Void";if(legs.every(x=>x.result==="Win"||x.result==="Void")&&legs.some(x=>x.result==="Win"))return "Win";return "Pending"}
  function round2(n){return Math.round((Number(n)||0)*100)/100}
  function currencyAfter(lines,label){
    for(let i=0;i<lines.length;i++)if(new RegExp(`^${label}$`,"i").test(lines[i]))for(let j=i+1;j<Math.min(lines.length,i+4);j++){const m=lines[j].match(/^£\s*([0-9]+(?:\.[0-9]{1,2})?)$/);if(m)return Number(m[1])}
    return NaN;
  }
  function splitSuperSub(raw){
    const s=cleanLine(raw);let m=s.match(/^(.+?)svg(.+)$/i);
    if(m&&/[A-Za-zÀ-ÿ]/.test(m[1])&&/[A-Za-zÀ-ÿ]/.test(m[2]))return {selection:cleanLine(m[1]),replacement:cleanLine(m[2])};
    m=s.match(/^(.+?)\s*(?:↔|→|->|=>|⇄|⇆)\s*(.+)$/);
    return m?{selection:cleanLine(m[1]),replacement:cleanLine(m[2])}:{selection:s,replacement:""};
  }
  function inferSport(market){return /^Match Betting$/i.test(cleanLine(market))?"Darts":"Football"}
  function existingBetIds(){
    try{const d=JSON.parse(localStorage.getItem("bet-tracker-user-v1")||"null"),set=new Set();for(const b of (d?.bets||[])){const s=JSON.stringify(b);const ms=s.match(/O\/\d+\/\d+/g)||[];ms.forEach(x=>set.add(x))}return set}catch(_){return new Set()}
  }

  function parseBuilder(lines){
    let currentEvent="",firstDate="";const legs=[];
    for(let i=1;i<lines.length;){
      if(/^Stake$/i.test(lines[i]))break;
      const d=parseDateLine(lines[i+1]||"");
      if(d&&!resultCode(lines[i])){currentEvent=cleanLine(lines[i]);if(!firstDate)firstDate=d;i+=2;continue}
      const rr=resultCode(lines[i]);
      if(rr){
        let j=i+1;while(j<lines.length&&/^(?:Super Sub|Win More|Super SubWin More)$/i.test(lines[j]))j++;
        const rawSel=lines[j++]||"";while(j<lines.length&&/^(?:Super Sub|Win More|Super SubWin More)$/i.test(lines[j]))j++;
        const market=cleanLine(lines[j++]||"");const ss=splitSuperSub(rawSel);
        legs.push({sport:"Football",event:currentEvent,market,selection:ss.selection,odds:null,result:rr,_superSubReplacement:ss.replacement});
        while(j<lines.length&&/^(?:Super Sub|Win More|Super SubWin More)$/i.test(lines[j]))j++;i=j;continue;
      }
      i++;
    }
    return {legs,date:firstDate};
  }

  function parseAccumulator(lines){
    let firstDate="";const legs=[];
    for(let i=1;i<lines.length;){
      if(/^Stake$/i.test(lines[i]))break;
      const rr=resultCode(lines[i]);if(!rr){i++;continue}
      const rawSel=lines[++i]||"";let legOdds=null;
      if(/^\d+(?:\.\d+)?$/.test(lines[i+1]||""))legOdds=Number(lines[++i]);
      const me=cleanLine(lines[++i]||"");let market="",event="";const k=me.indexOf(" - ");
      if(k>=0){market=me.slice(0,k).trim();event=me.slice(k+3).trim()}
      const d=parseDateLine(lines[i+1]||"");if(d){if(!firstDate)firstDate=d;i++}
      const ss=splitSuperSub(rawSel);legs.push({sport:inferSport(market),event,market,selection:ss.selection,odds:legOdds,result:rr,_superSubReplacement:ss.replacement});i++;
    }
    return {legs,date:firstDate};
  }

  function riskType(price){const n=Number(price);if(!Number.isFinite(n))return "Low Risk (Around Evs)";if(n>=101)return "Longshot (100/1+)";if(n>=11)return "High Risk (10/1+)";if(n>2.2)return "Medium Risk (Evs - 10/1)";return "Low Risk (Around Evs)"}

  function parseChunk(raw,knownIds){
    const lines=String(raw).replace(/\r/g,"").split(/\n+/).map(cleanLine).filter(Boolean),head=lines[0]||"";
    const betFormat=/^Accumulator\b/i.test(head)||/^Treble\b/i.test(head)?"Accumulator":/^Bet Builder\b/i.test(head)?"Bet Builder":"Single";
    const lm=head.match(/(?:-\s*)?(\d+)\s+legs?\)?$/i),declaredLegs=lm?Number(lm[1]):null;
    const em=head.match(/\((\d+)\s+events?\s*-\s*\d+\s+legs?\)/i),declaredEvents=em?Number(em[1]):null;
    let firstStructure=lines.length;
    for(let i=1;i<lines.length;i++)if(resultCode(lines[i])||parseDateLine(lines[i+1]||"")||/^Stake$/i.test(lines[i])){firstStructure=i;break}
    const prices=lines.slice(1,firstStructure).filter(x=>/^\d+(?:\.\d+)?$/.test(x)).map(Number).filter(x=>x>=1&&x<=1000);
    const receiptOdds=prices.length?prices.at(-1):null,originalOdds=prices.length>1?prices[0]:receiptOdds;
    const parsed=betFormat==="Accumulator"?parseAccumulator(lines):parseBuilder(lines);
    const stake=currencyAfter(lines,"Stake"),settled=currencyAfter(lines,"Returns"),joined=lines.join(" ");
    const fm=joined.match(/Inc\.?\s*£\s*([0-9]+(?:\.[0-9]{1,2})?)\s*Free\s*Bet/i),free=fm?Number(fm[1]):0;
    const betId=(joined.match(/Bet ID:\s*(O\/\d+\/\d+)/i)||[])[1]||"";
    const boosted=(joined.match(/Boosted\s*£\s*([0-9]+(?:\.[0-9]{1,2})?)/i)||[])[1]||"";
    const powerUp=/\bPower up\b/i.test(joined),result=overallResult(parsed.legs);
    let potential=settled;
    if((result==="Loss"||result==="Void"||result==="Pending")&&Number.isFinite(stake)&&stake>0&&receiptOdds)potential=round2(stake*receiptOdds-free);
    if(result==="Win"&&(!Number.isFinite(potential)||potential<=0)&&Number.isFinite(stake)&&stake>0&&receiptOdds)potential=round2(stake*receiptOdds-free);
    const events=[...new Set(parsed.legs.map(x=>x.event).filter(Boolean))],sports=[...new Set(parsed.legs.map(x=>x.sport).filter(Boolean))];
    const issues=[];
    if(!betId)issues.push("Bet ID missing");else if(knownIds.has(betId))issues.push("Already in tracker");
    if(declaredLegs!=null&&parsed.legs.length!==declaredLegs)issues.push(`Expected ${declaredLegs} legs but parsed ${parsed.legs.length}`);
    if(declaredEvents!=null&&events.length!==declaredEvents)issues.push(`Expected ${declaredEvents} events but parsed ${events.length}`);
    if(!parsed.date)issues.push("Date missing");if(!Number.isFinite(stake)||stake<=0)issues.push("Stake missing");
    if(!Number.isFinite(potential)||potential<0)issues.push("Potential return could not be determined");
    parsed.legs.forEach((l,i)=>{if(!l.event||!l.market||!l.selection)issues.push(`Leg ${i+1} incomplete`)});
    const noteBits=[];if(betId)noteBits.push(`Bet ID: ${betId}`);if(powerUp)noteBits.push("Power up");if(boosted)noteBits.push(`Boosted £${boosted}`);
    return {
      bookmaker:"Paddy Power",sport:sports.length===1?sports[0]:(sports.includes("Football")?"Football":sports[0]||"Football"),date:parsed.date,
      stake:Number.isFinite(stake)?stake:"",returns:Number.isFinite(potential)?potential.toFixed(2):"",returnsPence:Number.isFinite(potential)?Math.round(potential*100):null,
      free:free?free.toFixed(2):"",competition:events.length>1?"Multiple competitions":"",event:"",market:"",selection:"",source:"Paddy Power Text Import",
      betFormat,result,legs:parsed.legs,notes:noteBits.join(" · "),_betId:betId,_receiptOdds:receiptOdds,_originalOdds:originalOdds,_settledReturns:Number.isFinite(settled)?settled:null,
      _riskType:riskType(receiptOdds),_declaredLegs:declaredLegs,_declaredEvents:declaredEvents,_parseIssues:issues,_powerUp:powerUp,_boosted:boosted
    };
  }

  function parseAll(text){
    const raw=String(text||"").replace(/\r/g,"");const src=raw.split("\n"),starts=[];
    for(let i=0;i<src.length;i++)if(/^(?:Bet Builder|Accumulator|Treble|Single)\b/i.test(cleanLine(src[i])))starts.push(i);
    if(!starts.length)throw new Error("No Paddy Power bet headers were found. Copy from the Bet Builder / Accumulator heading through the Bet ID lines.");
    const known=existingBetIds(),items=[];
    for(let k=0;k<starts.length;k++){const chunk=src.slice(starts[k],k+1<starts.length?starts[k+1]:src.length).join("\n");items.push({parsed:parseChunk(chunk,known),raw:chunk})}
    return items;
  }

  function ready(p){return Array.isArray(p?._parseIssues)&&p._parseIssues.length===0&&Array.isArray(p?.legs)&&p.legs.length>0}
  function summary(p){const legs=p?.legs||[];return legs.slice(0,6).map((l,i)=>`<div><b>${i+1}.</b> ${esc(l.event)} · ${esc(l.market)} · <b>${esc(l.selection)}</b>${l._superSubReplacement?` <span style="color:#8299af">→ ${esc(l._superSubReplacement)}</span>`:""}</div>`).join("")+(legs.length>6?`<div>+ ${legs.length-6} more selections</div>`:"")}

  function render(modal,items){
    modal.querySelector(".bt-multi-review")?.remove();modal.__btTextResults=items;
    const good=items.filter(x=>ready(x.parsed)).length,box=document.createElement("section");box.className="bt-multi-review";
    box.innerHTML=`<div class="bt-multi-review-head"><strong>${items.length} bets parsed from Paddy text</strong><span>${good} ready · ${items.length-good} need checking</span></div><div class="bt-multi-list">${items.map((x,i)=>{const p=x.parsed,ok=ready(p),issues=p._parseIssues||[];return `<label class="bt-multi-bet ${ok?"":"bad"}"><input class="bt-multi-check" type="checkbox" data-i="${i}" ${ok?"checked":""} ${ok?"":"disabled"}><div class="bt-multi-bet-main"><div class="bt-multi-bet-top"><strong>Bet ${i+1}${ok?"":" · CHECK REQUIRED"}</strong><span>${esc(p._betId||p.date||"")}</span></div><div class="bt-multi-meta"><i>${esc(p.betFormat)}</i><i>${p.legs.length} legs</i><i>${esc(p.result)}</i><i>Stake £${Number(p.stake||0).toFixed(2)}</i><i>Potential £${Number(p.returns||0).toFixed(2)}</i>${p._receiptOdds?`<i>Price ${esc(p._receiptOdds)}</i>`:""}</div>${issues.length?`<div class="bt-multi-lines bt-text-warning">${issues.map(z=>`<div>${esc(z)}</div>`).join("")}</div>`:`<div class="bt-multi-lines">${summary(p)}</div>`}</div></label>`}).join("")}</div>`;
    $(modal,".bt-import-grid")?.insertAdjacentElement("afterend",box);const use=$(modal,".bt-use-import");
    if(use){use.classList.add("bt-multi-import");use.textContent=`Import selected (${good})`;use.disabled=!good}
    const actions=$(modal,".bt-import-actions");if(actions&&!$(actions,".bt-multi-actions-note")){const n=document.createElement("span");n.className="bt-multi-actions-note";n.textContent="Duplicates and incomplete parses stay unticked.";actions.prepend(n)}
    $$(box,".bt-multi-check").forEach(cb=>cb.addEventListener("change",()=>{const n=$$(box,".bt-multi-check:checked").length;if(use){use.textContent=`Import selected (${n})`;use.disabled=!n}}));
  }

  function setCtl(el,value){if(!el||value==null||value==="")return;const proto=el instanceof HTMLSelectElement?HTMLSelectElement.prototype:el instanceof HTMLInputElement?HTMLInputElement.prototype:HTMLTextAreaElement.prototype,setter=Object.getOwnPropertyDescriptor(proto,"value")?.set;setter?setter.call(el,String(value)):el.value=String(value);el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}))}
  async function openAddForm(){const add=[...document.querySelectorAll("button")].find(x=>x.textContent.trim()==="+ Add bet");if(!add)throw new Error("Open the Bet Tracker page before importing.");add.click();for(let i=0;i<75;i++){const f=document.querySelector(".modal-form");if(f)return f;await wait(40)}throw new Error("Add Bet form did not open.")}
  async function populate(form,p){
    setCtl($(form,'[name="app"]'),p.bookmaker);setCtl($(form,'[name="sport"]'),p.sport||"Football");setCtl($(form,'[name="date"]'),p.date);setCtl($(form,'[name="type"]'),p._riskType);
    setCtl($(form,'[name="source"]'),p.source);setCtl($(form,'[name="competition"]'),p.competition);setCtl($(form,'[name="notes"]'),p.notes);setCtl($(form,'[name="stake"]'),p.stake);setCtl($(form,'[name="potentialReturns"]'),p.returns);setCtl($(form,'[name="betFormat"]'),p.betFormat);setCtl($(form,'[name="result"]'),p.result);
    await wait(120);if(Number(p.free)>0){const cb=$(form,'[name="isFreeBet"]');if(cb&&!cb.checked){cb.click();await wait(70)}setCtl($(form,'[name="freeBetAmount"]'),p.free)}
    const target=p.legs.length;for(let guard=0;guard<60;guard++){const cards=$$(form,".bt-leg-card");if(cards.length===target)break;if(cards.length<target){$(form,".bt-add-leg")?.click();await wait(25)}else if(cards.length>target&&cards.length>1){cards.at(-1)?.querySelector(".bt-leg-head button")?.click();await wait(25)}}
    await wait(70);const cards=$$(form,".bt-leg-card");p.legs.forEach((leg,i)=>{const card=cards[i];if(!card)return;const sels=$$(card,"select"),ins=$$(card,"input");setCtl(sels[0],leg.sport||p.sport||"Football");setCtl(ins[0],leg.event);setCtl(ins[1],leg.market);setCtl(ins[2],leg.selection);if(leg.odds!=null&&leg.odds!=="")setCtl(ins[3],leg.odds);setCtl(sels[1],leg.result||"Pending")});await wait(80);
  }
  async function importSelected(modal){
    const items=modal.__btTextResults||[],selected=$$(modal,".bt-multi-check:checked").map(cb=>items[Number(cb.dataset.i)]).filter(Boolean);if(!selected.length)return;
    const use=$(modal,".bt-use-import");if(use)use.disabled=true;modal.closest(".bt-import-backdrop")?.remove();let added=0;
    try{for(let i=0;i<selected.length;i++){const form=await openAddForm();await populate(form,selected[i].parsed);const submit=$(form,'button[type="submit"]');if(!submit)throw new Error(`Bet ${i+1}: submit button missing.`);form.requestSubmit(submit);for(let t=0;t<75;t++){if(!form.isConnected)break;await wait(40)}if(form.isConnected)throw new Error(`Bet ${i+1}: Add Bet form did not close after saving.`);added++;await wait(80)}window.alert(`${added} bet${added===1?"":"s"} imported from Paddy Power text.`)}catch(err){console.error("Paddy text import",err);window.alert(`${added} bet${added===1?"":"s"} imported before the process stopped. ${err?.message||"A bet could not be saved."}`)}
  }

  function leaveText(modal){
    const panel=$(modal,".bt-text-import-panel");if(panel)panel.style.display="none";const fl=$(modal,".bt-import-file"),pv=$(modal,".bt-import-preview");if(fl)fl.style.display="";if(pv)pv.style.display="";modal.__btTextResults=null;
  }
  function setTextMode(modal){
    modal.dataset.btImportMode="text";$$ (modal,".bt-import-mode button").forEach(b=>b.classList.toggle("active",b.dataset.mode==="text"));
    const h=$(modal,".bt-import-head h2");if(h)h.textContent="Paste Paddy Power bet text";const fl=$(modal,".bt-import-file"),pv=$(modal,".bt-import-preview");if(fl)fl.style.display="none";if(pv)pv.style.display="none";
    const panel=$(modal,".bt-text-import-panel");if(panel)panel.style.display="block";const fields=$(modal,".bt-import-fields");if(fields)fields.style.display="none";modal.querySelector(".bt-multi-review")?.remove();modal.__btMultiResults=null;modal.__btTextResults=null;
    const run=$(modal,".bt-run-ocr");if(run){run.textContent="Parse pasted bets";run.disabled=false}const use=$(modal,".bt-use-import");if(use){use.classList.remove("bt-multi-import");use.textContent="Import selected";use.disabled=true}modal.querySelector(".bt-multi-actions-note")?.remove();
    const progress=$(modal,".bt-import-progress");if(progress)progress.textContent="Paste the copied Paddy Power bet history text, then parse it. 'svg' between two names is treated as the Super Sub arrow.";
  }

  function enhance(modal){
    if(!modal||modal.dataset.btTextReady)return;const modes=$(modal,".bt-import-mode");if(!modes){setTimeout(()=>enhance(modal),25);return}modal.dataset.btTextReady="1";
    if(!$(modes,'button[data-mode="text"]')){const b=document.createElement("button");b.type="button";b.dataset.mode="text";b.textContent="Paste Paddy Text";b.addEventListener("click",e=>{e.preventDefault();e.stopPropagation();setTextMode(modal)});modes.appendChild(b)}
    let panel=$(modal,".bt-text-import-panel");if(!panel){panel=document.createElement("div");panel.className="bt-text-import-panel";panel.innerHTML='<textarea class="bt-paddy-text" spellcheck="false" placeholder="Paste Paddy Power bets here…"></textarea><div class="bt-text-import-help"><b>Works with many bets at once.</b> Bet Builder, multi-event Bet Builder and Accumulator formats are separated by their headings and Bet IDs. Super Sub replacements copied as <b>svg</b> are cleaned automatically.</div>';modes.insertAdjacentElement("afterend",panel)}
    $$(modes,'button[data-mode="single"],button[data-mode="multi"]').forEach(b=>b.addEventListener("click",()=>setTimeout(()=>leaveText(modal),0)));
  }

  document.addEventListener("click",async e=>{
    const run=e.target.closest?.(".bt-run-ocr");if(run){const modal=run.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="text"){e.preventDefault();e.stopImmediatePropagation();const progress=$(modal,".bt-import-progress"),text=$(modal,".bt-paddy-text")?.value||"";try{if(progress)progress.textContent="Parsing copied Paddy Power text…";const items=parseAll(text);render(modal,items);if(progress)progress.textContent=`Parsed ${items.length} bets · ${items.filter(x=>ready(x.parsed)).length} ready to import.`}catch(err){console.error(err);if(progress)progress.textContent=`Text import failed: ${err?.message||"Could not parse the pasted text."}`}return}}
    const use=e.target.closest?.(".bt-use-import");if(use){const modal=use.closest(".bt-import-modal");if(modal?.dataset.btImportMode==="text"){e.preventDefault();e.stopImmediatePropagation();await importSelected(modal);return}}
  },true);

  window.__btParsePaddyText=parseAll;
  const mo=new MutationObserver(()=>document.querySelectorAll(".bt-import-modal").forEach(enhance));mo.observe(document.body,{childList:true,subtree:true});document.querySelectorAll(".bt-import-modal").forEach(enhance);
})();
</script>
'''

if 'id="bt-paddy-text-import"' in html:
    raise SystemExit('Paddy text import patch already present')
if '</head>' not in html or '</body>' not in html:
    raise SystemExit('HTML markers missing')
html = html.replace('</head>', css + '\n</head>', 1)
html = html.replace('</body>', script + '\n</body>', 1)
path.write_text(html, encoding='utf-8')
print('Applied Paddy Power text import patch')