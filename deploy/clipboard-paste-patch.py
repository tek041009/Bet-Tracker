from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")

old_state = '''      [_receiptStatus,setReceiptStatus]=(0,W.useState)("");
  const F='''
new_state = '''      [_receiptStatus,setReceiptStatus]=(0,W.useState)("");
  (0,W.useEffect)(()=>{
    const onPaste=async ev=>{
      const item=[...(ev.clipboardData?.items??[])].find(x=>String(x.type||"").startsWith("image/"));
      if(!item)return;
      const file=item.getAsFile();
      if(!file)return;
      ev.preventDefault();
      setReceiptStatus("Preparing pasted screenshot…");
      try{
        const image=await btCompressReceiptFile(file);
        setReceipt(image);
        setReceiptName(`snipping-tool-${Date.now()}.jpg`);
        setReceiptStatus("Screenshot pasted. Save changes to keep it.");
      }catch(err){
        console.error(err);
        setReceiptStatus("Could not paste that image.");
        window.alert("That pasted image could not be processed.");
      }
    };
    window.addEventListener("paste",onPaste);
    return()=>window.removeEventListener("paste",onPaste);
  },[]);
  const F='''

old_hint = '''(0,c.jsx)("p",{className:"bt-receipt-status",children:_receiptStatus||(_receipt?(_receiptName||"Receipt attached."):"The image is compressed before it is stored in the tracker.")})'''
new_hint = '''(0,c.jsx)("p",{className:"bt-receipt-status",children:_receiptStatus||(_receipt?(_receiptName||"Receipt attached."):"Paste a Snipping Tool image with Ctrl+V, or attach a screenshot.")})'''

for old, new, label in [
    (old_state, new_state, "clipboard listener"),
    (old_hint, new_hint, "clipboard hint"),
]:
    count = html.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} target, found {count}")
    html = html.replace(old, new, 1)

path.write_text(html, encoding="utf-8")
print("Applied Bet Tracker clipboard paste patch")
