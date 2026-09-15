from pathlib import Path
import re

p=Path('_site/index.html')
h=p.read_text(encoding='utf-8')

m=re.search(r'(<script id="bt-paddy-text-import">)(.*?)(</script>)',h,re.S)
if not m:
    raise SystemExit('Batch reliability patch: Paddy importer script missing')
js=m.group(2)

old_open='''async function openAddForm(){const add=[...document.querySelectorAll("button")].find(x=>x.textContent.trim()==="+ Add bet");if(!add)throw new Error("Open the Bet Tracker page before importing.");add.click();for(let i=0;i<75;i++){const f=document.querySelector(".modal-form");if(f)return f;await wait(40)}throw new Error("Add Bet form did not open.")}'''
new_open='''function storedHasBetId(id){if(!id)return false;try{const d=JSON.parse(localStorage.getItem("bet-tracker-user-v1")||"null");return Array.isArray(d?.bets)&&d.bets.some(b=>JSON.stringify(b).includes(id))}catch(_){return false}}\n  async function waitForAddButton(){for(let i=0;i<200;i++){const add=[...document.querySelectorAll("button")].find(x=>x.textContent.trim()==="+ Add bet"&&!x.disabled);if(add)return add;await wait(40)}return null}\n  async function openAddForm(){const add=await waitForAddButton();if(!add)throw new Error("Bet Tracker did not finish opening. Please retry the import.");add.click();for(let i=0;i<200;i++){const f=document.querySelector(".modal-form");if(f)return f;await wait(40)}throw new Error("Add Bet form did not open after 8 seconds.")}'''
if js.count(old_open)!=1:
    raise SystemExit(f'Batch reliability patch: expected one openAddForm block, found {js.count(old_open)}')
js=js.replace(old_open,new_open,1)

old_import='''async function importSelected(modal){\n    const items=modal.__btTextResults||[],selected=$$(modal,".bt-multi-check:checked").map(cb=>items[Number(cb.dataset.i)]).filter(Boolean);if(!selected.length)return {added:0,total:0,error:null};\n    const use=$(modal,".bt-use-import");if(use)use.disabled=true;modal.closest(".bt-import-backdrop")?.remove();let added=0;const total=selected.length;\n    window.__btPaddyImportProgress?.({added,total});\n    try{for(let i=0;i<selected.length;i++){const form=await openAddForm();await populate(form,selected[i].parsed);const submit=$(form,'button[type="submit"]');if(!submit)throw new Error(`Bet ${i+1}: submit button missing.`);form.requestSubmit(submit);for(let t=0;t<75;t++){if(!form.isConnected)break;await wait(40)}if(form.isConnected)throw new Error(`Bet ${i+1}: Add Bet form did not close after saving.`);added++;window.__btPaddyImportProgress?.({added,total});await wait(80)}return {added,total,error:null}}catch(err){console.error("Paddy text import",err);window.__btPaddyImportProgress?.({added,total,error:err?.message||"A bet could not be saved."});return {added,total,error:err?.message||"A bet could not be saved."}}\n  }'''
new_import='''async function importSelected(modal){\n    const items=modal.__btTextResults||[],selected=$$(modal,".bt-multi-check:checked").map(cb=>items[Number(cb.dataset.i)]).filter(Boolean);if(!selected.length)return {added:0,total:0,error:null,skipped:0};\n    const use=$(modal,".bt-use-import");if(use)use.disabled=true;modal.closest(".bt-import-backdrop")?.remove();let added=0,skipped=0;const total=selected.length;\n    window.__btPaddyImportProgress?.({added,total,skipped});\n    try{for(let i=0;i<selected.length;i++){const parsed=selected[i].parsed||{},betId=parsed._betId||"";if(betId&&storedHasBetId(betId)){skipped++;added++;window.__btPaddyImportProgress?.({added,total,skipped});await wait(40);continue}const form=await openAddForm();await populate(form,parsed);const submit=$(form,'button[type="submit"]');if(!submit)throw new Error(`Bet ${i+1}: submit button missing.`);if(typeof form.checkValidity==="function"&&!form.checkValidity()){const bad=[...form.querySelectorAll(":invalid")].map(x=>`${x.name||x.type}=${x.value||"<blank>"}`).join(", ");throw new Error(`Bet ${i+1}: form validation failed${bad?` (${bad})`:""}.`)}form.requestSubmit(submit);let saved=false;for(let t=0;t<200;t++){if(!form.isConnected){saved=true;break}if(betId&&storedHasBetId(betId)){saved=true;for(let z=0;z<50&&form.isConnected;z++)await wait(40);break}await wait(40)}if(!saved&&form.isConnected){const bad=[...form.querySelectorAll(":invalid")].map(x=>`${x.name||x.type}=${x.value||"<blank>"}`).join(", ");throw new Error(`Bet ${i+1}: save did not complete after 8 seconds${bad?` · invalid: ${bad}`:""}.`)}added++;window.__btPaddyImportProgress?.({added,total,skipped});await wait(120)}return {added,total,error:null,skipped}}catch(err){console.error("Reviewed text import",err);window.__btPaddyImportProgress?.({added,total,skipped,error:err?.message||"A bet could not be saved."});return {added,total,skipped,error:err?.message||"A bet could not be saved."}}\n  }'''
if js.count(old_import)!=1:
    raise SystemExit(f'Batch reliability patch: expected one importSelected block, found {js.count(old_import)}')
js=js.replace(old_import,new_import,1)

h=h[:m.start(2)]+js+h[m.end(2):]

# The review flow previously waited a fixed 120 ms after clicking Bet Tracker. On a real browser
# that can be too short, causing a false "stopped" error before the + Add bet button exists.
old='''goToBetTracker();await sleep(120);window.__btPaddyImportProgress=({added,total,error})=>updateImportScreen(screen,added,total,error||'');'''
new='''goToBetTracker();window.__btPaddyImportProgress=({added,total,error,skipped})=>updateImportScreen(screen,added,total,error||'',skipped||0);'''
if h.count(old)!=1:
    raise SystemExit(f'Batch reliability patch: expected one fixed tracker wait, found {h.count(old)}')
h=h.replace(old,new,1)

old_update='''function updateImportScreen(x,added,total,error=""){const count=x.querySelector(".bt-importing-count"),bar=x.querySelector(".bt-importing-track i"),status=x.querySelector(".bt-importing-status"),spin=x.querySelector(".bt-importing-spinner");if(count)count.textContent=`${added} / ${total}`;if(bar)bar.style.width=`${total?Math.round(added/total*100):0}%`;if(error){x.classList.add("has-error");if(status)status.textContent=`Import stopped after ${added} of ${total}: ${error}`;if(spin)spin.style.display="none";const btn=x.querySelector(".bt-importing-return");if(btn){btn.hidden=false;btn.onclick=()=>{goToBetTracker();x.remove()}}}else if(added===total&&total>0){x.classList.add("is-complete");if(status)status.textContent="Import complete. Opening Bet Tracker…";if(spin)spin.style.display="none"}}'''
new_update='''function updateImportScreen(x,added,total,error="",skipped=0){const count=x.querySelector(".bt-importing-count"),bar=x.querySelector(".bt-importing-track i"),status=x.querySelector(".bt-importing-status"),spin=x.querySelector(".bt-importing-spinner");if(count)count.textContent=`${added} / ${total}`;if(bar)bar.style.width=`${total?Math.round(added/total*100):0}%`;if(error){x.classList.add("has-error");if(status)status.textContent=`Import stopped after ${added} of ${total}: ${error} Safe to retry — bets already saved will be skipped.`;if(spin)spin.style.display="none";const btn=x.querySelector(".bt-importing-return");if(btn){btn.hidden=false;btn.onclick=()=>{goToBetTracker();x.remove()}}}else if(added===total&&total>0){x.classList.add("is-complete");if(status)status.textContent=skipped?`Import complete. ${skipped} already-saved bet${skipped===1?" was":"s were"} skipped. Opening Bet Tracker…`:"Import complete. Opening Bet Tracker…";if(spin)spin.style.display="none"}}'''
if h.count(old_update)!=1:
    raise SystemExit(f'Batch reliability patch: expected one progress updater, found {h.count(old_update)}')
h=h.replace(old_update,new_update,1)

# Final result update must preserve the skipped count too.
old_final="""updateImportScreen(screen,result?.added??0,result?.total??total,result?.error||'');"""
new_final="""updateImportScreen(screen,result?.added??0,result?.total??total,result?.error||'',result?.skipped||0);"""
if h.count(old_final)!=1:
    raise SystemExit(f'Batch reliability patch: expected one final progress update, found {h.count(old_final)}')
h=h.replace(old_final,new_final,1)

p.write_text(h,encoding='utf-8')
print('Hardened reviewed batch imports: wait for real tracker readiness, 8s save window, exact validation errors, and duplicate-safe retry')
