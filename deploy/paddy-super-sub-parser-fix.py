from pathlib import Path

p = Path('_site/index.html')
h = p.read_text(encoding='utf-8')

old_split = r'''  function splitSuperSub(raw){
    const s=cleanLine(raw);let m=s.match(/^(.+?)svg(.+)$/i);
    if(m&&/[A-Za-zÀ-ÿ]/.test(m[1])&&/[A-Za-zÀ-ÿ]/.test(m[2]))return {selection:cleanLine(m[1]),replacement:cleanLine(m[2])};
    m=s.match(/^(.+?)\s*(?:↔|→|->|=>|⇄|⇆)\s*(.+)$/);
    return m?{selection:cleanLine(m[1]),replacement:cleanLine(m[2])}:{selection:s,replacement:""};
  }
'''
new_split = r'''  function splitSuperSub(raw){
    const s=cleanLine(raw).replace(/[\u200b\u200c\u200d]/g,"");
    let m=s.match(/^(.+?)\s*(?:↔|→|->|=>|⇄|⇆)\s*(.+)$/);
    if(m)return {selection:cleanLine(m[1]),replacement:cleanLine(m[2])};
    const parts=s.split(/svg/i).map(cleanLine).filter(Boolean);
    if(parts.length>=2&&/[A-Za-zÀ-ÿ]/.test(parts[0])&&/[A-Za-zÀ-ÿ]/.test(parts[1]))return {selection:parts[0],replacement:parts[1]};
    return {selection:s,replacement:""};
  }
  function promoKind(raw){
    const s=cleanLine(raw).replace(/\s+/g," ");
    return {promo:/^(?:Super\s*Sub(?:\s*Win\s*More)?|Win\s*More)$/i.test(s),super:/^Super\s*Sub/i.test(s)};
  }
  function looksLikeMarketLine(raw){
    const s=cleanLine(raw);
    if(!s)return false;
    return /\b(?:match odds|match betting|draw no bet|both teams|double chance|handicap|wdw|over\/?under|shots?|shot on target|goals?|fouled|assists?|corners?|cards?|bookings?|woodwork|clean sheet|to have|to be|to score|to win|to qualify|result)\b/i.test(s);
  }
  function takeSelection(lines,start){
    let j=start,superMarked=false;
    while(j<lines.length){const k=promoKind(lines[j]);if(!k.promo)break;if(k.super)superMarked=true;j++}
    let first=cleanLine(lines[j++]||"");
    const firstHadSvgTail=/svg\s*$/i.test(first);
    if(firstHadSvgTail)first=cleanLine(first.replace(/svg\s*$/i,""));
    let ss=splitSuperSub(first);
    while(j<lines.length){const k=promoKind(lines[j]);if(!k.promo)break;if(k.super)superMarked=true;j++}
    if(!ss.replacement){
      const next=cleanLine(lines[j]||"");
      if(/^svg$/i.test(next)){
        j++;
        const replacement=cleanLine(lines[j++]||"").replace(/^svg/i,"").replace(/svg$/i,"").trim();
        if(replacement)ss={selection:ss.selection,replacement};
      }else if(/^svg/i.test(next)){
        const replacement=cleanLine(next.replace(/^svg/i,""));
        if(replacement){ss={selection:ss.selection,replacement};j++}
      }else if((superMarked||firstHadSvgTail)&&next&&!looksLikeMarketLine(next)&&!resultCode(next)&&!parseDateLine(next)&&!/^Stake$/i.test(next)&&!/^£?\s*\d+(?:\.\d+)?$/.test(next)){
        ss={selection:ss.selection,replacement:cleanLine(next).replace(/svg$/i,"").trim()};j++;
      }
    }
    while(j<lines.length){const k=promoKind(lines[j]);if(!k.promo)break;if(k.super)superMarked=true;j++}
    return {selection:ss.selection,replacement:ss.replacement,j,superMarked};
  }
'''
if h.count(old_split) != 1:
    raise SystemExit(f'Expected one old splitSuperSub block, found {h.count(old_split)}')
h = h.replace(old_split, new_split, 1)

old_builder = r'''  function parseBuilder(lines){
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
'''
new_builder = r'''  function parseBuilder(lines){
    let currentEvent="",firstDate="";const legs=[];
    for(let i=1;i<lines.length;){
      if(/^Stake$/i.test(lines[i]))break;
      const d=parseDateLine(lines[i+1]||"");
      if(d&&!resultCode(lines[i])){currentEvent=cleanLine(lines[i]);if(!firstDate)firstDate=d;i+=2;continue}
      const rr=resultCode(lines[i]);
      if(rr){
        const ss=takeSelection(lines,i+1);let j=ss.j;
        const market=cleanLine(lines[j++]||"");
        legs.push({sport:"Football",event:currentEvent,market,selection:ss.selection,odds:null,result:rr,_superSubReplacement:ss.replacement});
        while(j<lines.length&&promoKind(lines[j]).promo)j++;i=j;continue;
      }
      i++;
    }
    return {legs,date:firstDate};
  }
'''
if h.count(old_builder) != 1:
    raise SystemExit(f'Expected one old parseBuilder block, found {h.count(old_builder)}')
h = h.replace(old_builder, new_builder, 1)

old_acc = r'''  function parseAccumulator(lines){
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
'''
new_acc = r'''  function parseAccumulator(lines){
    let firstDate="";const legs=[];
    for(let i=1;i<lines.length;){
      if(/^Stake$/i.test(lines[i]))break;
      const rr=resultCode(lines[i]);if(!rr){i++;continue}
      const ss=takeSelection(lines,i+1);let j=ss.j,legOdds=null;
      if(/^\d+(?:\.\d+)?$/.test(lines[j]||""))legOdds=Number(lines[j++]);
      const me=cleanLine(lines[j++]||"");let market="",event="";const k=me.indexOf(" - ");
      if(k>=0){market=me.slice(0,k).trim();event=me.slice(k+3).trim()}
      const d=parseDateLine(lines[j]||"");if(d){if(!firstDate)firstDate=d;j++}
      legs.push({sport:inferSport(market),event,market,selection:ss.selection,odds:legOdds,result:rr,_superSubReplacement:ss.replacement});i=j;
    }
    return {legs,date:firstDate};
  }
'''
if h.count(old_acc) != 1:
    raise SystemExit(f'Expected one old parseAccumulator block, found {h.count(old_acc)}')
h = h.replace(old_acc, new_acc, 1)

p.write_text(h, encoding='utf-8')
print('Applied robust Paddy Super Sub parser for combined and split clipboard formats')
