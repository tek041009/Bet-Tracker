from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")

# 1) Use a tighter, higher-resolution Bet Builder row crop. The old crop mixed too much
# whitespace/noise into tiny Paddy Power text and was the main source of mangled markets/names.
old_crop = 'const x1=format==="Accumulator"?base.width:520,rc=cropCanvas(base,20,b.y-12,x1,b.y+25,format==="Accumulator"?5:7,false);onProgress(`Reading selection ${i+1}/${badges.length}…`);const rt=await recognize(worker,rc,T.PSM?.SINGLE_BLOCK??6);'
new_crop = 'const x1=format==="Accumulator"?base.width:(format==="Bet Builder"?650:520),rx0=format==="Bet Builder"?35:20,ry0=b.y-(format==="Bet Builder"?15:12),ry1=b.y+(format==="Bet Builder"?25:25),rscale=format==="Accumulator"?5:(format==="Bet Builder"?9:7),rc=cropCanvas(base,rx0,ry0,x1,ry1,rscale,false);onProgress(`Reading selection ${i+1}/${badges.length}…`);const rt=await recognize(worker,rc,T.PSM?.SINGLE_BLOCK??6);'
if html.count(old_crop) != 1:
    raise SystemExit(f"Expected one Bet Builder row crop target, found {html.count(old_crop)}")
html = html.replace(old_crop, new_crop, 1)

# 2) Super Sub replacement is metadata. Keep the original selected player only.
old_sub = 'return m?`${clean(m[1])} ↔ ${clean(m[2])}`:s;'
new_sub = 'return m?clean(m[1]):s;'
if html.count(old_sub) != 1:
    raise SystemExit(f"Expected one substitution target, found {html.count(old_sub)}")
html = html.replace(old_sub, new_sub, 1)

script = r'''
<script id="bt-scanner-regression-patch">
(() => {
  "use strict";

  const STORE_KEY = "bet-tracker-user-v1";
  const BUILTIN_NAMES = [
    "Bruno Fernandes","Bryan Mbeumo","Matheus Cunha","Youri Tielemans","Patrick Dorgu",
    "Kobbie Mainoo","Harry Kane","Luis Diaz","Michael Olise","Jamal Musiala"
  ];

  const clean = v => String(v || "").replace(/\s+/g," ").trim();
  const compact = v => clean(v).toLowerCase().replace(/[^a-z0-9]/g,"");
  const splitTeams = event => {
    const p = clean(event).split(/\s+v\s+/i);
    return p.length === 2 ? p : ["",""];
  };

  function similarity(a,b){
    a=compact(a);b=compact(b);if(!a||!b)return 0;
    const m=a.length,n=b.length;let prev=Array.from({length:n+1},(_,i)=>i),cur=new Array(n+1);
    for(let i=1;i<=m;i++){
      cur[0]=i;
      for(let j=1;j<=n;j++)cur[j]=Math.min(cur[j-1]+1,prev[j]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));
      [prev,cur]=[cur,prev];
    }
    return 1-prev[n]/Math.max(m,n,1);
  }

  function thresholdFrom(market){
    const s=clean(market).replace(/,/g,".");
    let m=s.match(/\b(\d+\.\d+)\b/);if(m)return m[1];
    // OCR often turns O/U 1.5 into O/15. Treat the two digits as X.5 only in this market context.
    m=s.match(/[o0]\s*\/?\s*([1-9])([05])\b/i);if(m)return `${m[1]}.${m[2]}`;
    m=s.match(/\b([1-9])([05])\s*(?:goals?|coals?)\b/i);if(m)return `${m[1]}.${m[2]}`;
    m=s.match(/\b(\d+)\b/);return m?m[1]:"";
  }

  function canonicalMarket(market,selection,event){
    const m=clean(market),low=m.toLowerCase(),c=compact(m),sel=clean(selection);
    if (/both.*team.*score|btts/i.test(low) || similarity(m,"Both Teams To Score")>=.58) return "Both Teams To Score";
    if (/team\s+to\s+sco/i.test(low) && (!sel || /^(?:yes|no)$/i.test(sel))) return "Both Teams To Score";

    const first=(m.match(/^\S+/)||[""])[0];
    const wdwLike=/^(?:wdw|wow|w0w|wwd)$/i.test(first)||similarity(first,"WDW")>=.5;
    const ouLike=/o\s*\/?\s*u|over\s*\/?\s*under/i.test(m)||/[o0]\s*\/\s*\d/i.test(m)||/\b(?:goals?|coals?)\b/i.test(m);
    if(wdwLike&&ouLike)return `WDW & O/U ${thresholdFrom(m)||"1.5"} Goals`;

    if (/(?:match|motch|maach|mach|macth|matoh)\s*odds?/i.test(low) || similarity(m,"Match Odds")>=.58) return "Match Odds";

    const n=thresholdFrom(m);
    const playerLike=similarity(first,"Player")>=.45;
    const teamLike=similarity(first,"Team")>=.5;
    const shots=/shot/i.test(low), target=/target|woodw|includ|inchad|woodv/i.test(low), foul=/foul|footed/i.test(low);
    if(playerLike&&shots&&target)return `Player To Have ${n||"1"} Or More Shots On Target Including Woodwork`;
    if(playerLike&&shots)return `Player To Have ${n||"1"} Or More Shots`;
    if(playerLike&&foul)return `Player To Be Fouled ${n||"1"} Or More Times`;
    if(teamLike&&shots)return `Team To Have ${n||"1"} Or More Shots`;
    return m;
  }

  function stripReplacement(selection){
    const s=clean(selection);
    const parts=s.split(/\s+(?:↔|→|->|=>|⇄|⇆|£|€|¥|§|¤|=|~|\||2|©|>|<|®)\s+/);
    return parts.length>1&&/[A-Za-z]/.test(parts[0])?clean(parts[0]):s;
  }

  function playerLexicon(){
    const names=new Set(BUILTIN_NAMES);
    try{
      const state=JSON.parse(localStorage.getItem(STORE_KEY)||"null");
      const add=value=>{
        const raw=clean(value);if(!raw)return;
        for(const part of raw.split(/\s*(?:↔|→|->|=>|⇄|⇆|=|©|>|<)\s*/)){
          const s=clean(part).replace(/^\d+\)\s*/,"");
          if(/^[A-Za-zÀ-ÿ'’.-]+(?:\s+[A-Za-zÀ-ÿ'’.-]+){1,3}$/.test(s))names.add(s);
        }
      };
      for(const bet of state?.bets||[]){add(bet?.selection);for(const leg of bet?.legs||[])add(leg?.selection)}
    }catch(_){ }
    return [...names];
  }

  function correctPlayerName(selection,market){
    let s=stripReplacement(selection);
    if(!/^Player\s+To\s+/i.test(clean(market))||!/^[A-Za-zÀ-ÿ'’!.-]+(?:\s+[A-Za-zÀ-ÿ'’!.-]+){1,3}$/.test(s))return s;
    const ranked=playerLexicon().map(name=>[similarity(s,name),name]).sort((a,b)=>b[0]-a[0]);
    const best=ranked[0]||[0,s],runner=ranked[1]?.[0]||0;
    if(best[0]>=.72&&(best[0]>=.88||best[0]-runner>=.08))return best[1];
    return s;
  }

  function correctTeamSelection(selection,market,event){
    const s=clean(selection),[home,away]=splitTeams(event);if(!home||!away)return s;
    const candidates=[[similarity(s,home),home],[similarity(s,away),away]].sort((a,b)=>b[0]-a[0]);
    if(/^Match Odds$/i.test(market)&&candidates[0][0]>=.45)return candidates[0][1];
    if(/^Team To /i.test(market)&&candidates[0][0]>=.58)return candidates[0][1];
    if(/^WDW & O\/U/i.test(market)){
      const mm=s.match(/^(.+?)\s+And\s+(Over|Under)\s+(\d+(?:\.\d+)?)$/i);
      if(mm){const t=[[similarity(mm[1],home),home],[similarity(mm[1],away),away]].sort((a,b)=>b[0]-a[0])[0];if(t[0]>=.4)return `${t[1]} And ${mm[2][0].toUpperCase()+mm[2].slice(1).toLowerCase()} ${mm[3]}`}
    }
    return s;
  }

  function knownMarket(m){return /^(?:Both Teams To Score|Match Odds|WDW & O\/U|Player To |Team To |Double Chance|Draw No Bet|To Qualify)/i.test(clean(m))}

  const wait=()=>{
    if(typeof window.__btOCRReceiptData!=="function"){setTimeout(wait,25);return}
    if(window.__btOCRReceiptData.__btRegressionWrapped)return;
    const original=window.__btOCRReceiptData;
    const wrapped=async(...args)=>{
      const out=await original(...args);if(!out||typeof out!=="object")return out;
      if(Array.isArray(out.legs)){
        out.legs=out.legs.map(leg=>{
          let market=canonicalMarket(leg?.market,leg?.selection,leg?.event);
          let selection=correctPlayerName(leg?.selection,market);
          market=canonicalMarket(market,selection,leg?.event);
          selection=correctTeamSelection(selection,market,leg?.event);
          return {...leg,market,selection};
        });

        // Structural fallback: if one team is clearly established elsewhere in the same event
        // (e.g. Team To Have 18+ Shots), a tiny unreadable market row can safely inherit that team
        // as Match Odds only when there is exactly one team candidate for that event.
        const evidence=new Map();
        for(const leg of out.legs){
          if(!/^Team To /i.test(leg.market))continue;
          const [a,b]=splitTeams(leg.event),s=clean(leg.selection);let team="";
          if(similarity(s,a)>=.7)team=a;else if(similarity(s,b)>=.7)team=b;
          if(team){if(!evidence.has(leg.event))evidence.set(leg.event,new Set());evidence.get(leg.event).add(team)}
        }
        out.legs=out.legs.map(leg=>{
          if(knownMarket(leg.market))return leg;
          const teams=[...(evidence.get(leg.event)||[])];
          if(clean(leg.market).length<=12&&teams.length===1)return {...leg,market:"Match Odds",selection:teams[0]};
          return leg;
        });
      }
      if(out.event||out.market||out.selection){
        out.market=canonicalMarket(out.market,out.selection,out.event);
        out.selection=correctPlayerName(out.selection,out.market);
        out.selection=correctTeamSelection(out.selection,out.market,out.event);
      }
      out._scannerAuditVersion="2026-09-14-regression-18";
      return out;
    };
    wrapped.__btRegressionWrapped=true;wrapped.__btOriginalScanner=original;window.__btOCRReceiptData=wrapped;
  };
  wait();
})();
</script>
'''

marker = "</body>"
if marker not in html:
    raise SystemExit("Could not find body close")
html = html.replace(marker, script + "\n" + marker, 1)
path.write_text(html, encoding="utf-8")
print("Applied audited scanner regression patch")
