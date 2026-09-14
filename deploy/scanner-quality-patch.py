from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")

# Bet Builder event handling must be block-based. A selection-row OCR pass is allowed to
# discover an event only when the block header failed; it must never overwrite a fixture
# that was already read from the event header above the block.
replacements = [
    (
        'const useful=[];for(const l of ls){if(isHeader(l)||isDateLine(l)||isFooter(l))continue;const f=fixture(l);if(f){event=f;continue}useful.push(l)}',
        'const useful=[];for(const l of ls){if(isHeader(l)||isDateLine(l)||isFooter(l))continue;const f=fixture(l);if(f){if(format!=="Bet Builder"||!event)event=f;continue}useful.push(l)}'
    ),
    (
        'if(format==="Bet Builder"&&(i===0||b.y-prev.y>50)){',
        'if(format==="Bet Builder"&&(i===0||b.y-prev.y>50)){currentEvent="";'
    ),
    (
        'let p=parseRowText(rt,currentEvent,format);if(format==="Accumulator")currentEvent=p.event;',
        'let p=parseRowText(rt,currentEvent,format);if(format==="Bet Builder"&&currentEvent)p.event=currentEvent;if(format==="Accumulator")currentEvent=p.event;'
    ),
]

for old, new in replacements:
    count = html.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one Bet Builder event patch target, found {count}: {old[:90]!r}")
    html = html.replace(old, new, 1)

script = r'''
<script id="bt-scanner-quality-patch">
(() => {
  "use strict";

  const waitForScanner = () => {
    if (typeof window.__btOCRReceiptData !== "function") {
      setTimeout(waitForScanner, 25);
      return;
    }
    if (window.__btOCRReceiptData.__btQualityWrapped) return;

    const original = window.__btOCRReceiptData;

    const cleanText = value => String(value || "").replace(/\s+/g, " ").trim();
    const compact = value => cleanText(value).toLowerCase().replace(/[^a-z0-9]/g, "");
    const wordish = value => cleanText(value).toLowerCase().replace(/[^a-z0-9.]+/g, " ").trim();
    const splitTeams = event => {
      const p = cleanText(event).split(/\s+v\s+/i);
      return p.length === 2 ? p : ["", ""];
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

    function fixEvent(event) {
      let s = cleanText(event);
      s = s
        .replace(/\bBodo\s+Game\b/gi, "Bodo Glimt")
        .replace(/\bBodo\s+Glim(?:l|t)?\b/gi, "Bodo Glimt")
        .replace(/\bMan\s+Utd\s+v\s+FC\s+Sabah\b/gi, "Man Utd v FC Sabah")
        .replace(/\bComo\s+v\s+RB\s+Leipz(?:ig|iq)\b/gi, "Como v RB Leipzig");
      return s;
    }

    function stripSubReplacement(selection, market) {
      let s = cleanText(selection);
      if (!/^Player\s+To\s+/i.test(cleanText(market))) return s;

      // Paddy Power's Super Sub arrow is tiny and OCR commonly reads it as £, €, 2, = or another symbol.
      // The selected player is always the name on the LEFT; the replacement player is metadata only.
      const marker = /\s+(?:↔|→|->|=>|⇄|⇆|£|€|¥|§|¤|=|~|\||2)\s+/;
      const parts = s.split(marker);
      if (parts.length > 1 && /[A-Za-z]/.test(parts[0])) return cleanText(parts[0]);

      // Catch a single OCR punctuation glyph between two name-like groups without touching normal names.
      const m = s.match(/^([A-Za-zÀ-ÿ'’.-]+(?:\s+[A-Za-zÀ-ÿ'’.-]+){1,3})\s+[^A-Za-z0-9\s]{1,3}\s+([A-Za-zÀ-ÿ'’.-]+(?:\s+[A-Za-zÀ-ÿ'’.-]+){1,3})$/);
      return m ? cleanText(m[1]) : s;
    }

    function extractThreshold(text) {
      const m = cleanText(text).replace(/,/g,".").match(/\b(\d+(?:\.5)?)\b/);
      return m ? m[1] : "";
    }

    function canonicalMarket(market, selection, event) {
      let m = cleanText(market);
      const low = wordish(m);
      const c = compact(m);
      const sel = cleanText(selection);
      const selLow = sel.toLowerCase();
      const [home, away] = splitTeams(event);
      const teamSelection = compact(sel) && (compact(sel) === compact(home) || compact(sel) === compact(away));

      // Yes/No is a structural clue on Paddy receipts. A short garbled "Team To" line above Yes/No
      // is BTTS, not a generic Team To market.
      if (/^(?:yes|no)$/i.test(sel) && !/\b(?:over|under|qualify|draw|winner|odds)\b/i.test(low)) {
        return "Both Teams To Score";
      }
      if (/both.*team.*score|btts/i.test(low) || similarity(m,"Both Teams To Score") >= .62) {
        return "Both Teams To Score";
      }

      // WDW & O/U is particularly hostile to OCR because &, / and the decimal are tiny.
      // Accept common OCR forms such as WOW/W0W and Coals, then rebuild a legal canonical market.
      const ouLike = /o\s*\/?\s*u|over\s*\/?\s*under|overunder/i.test(m);
      const wdwLike = /\b(?:wdw|wow|w0w|wwd)\b/i.test(m) || similarity((m.match(/^\S+/)||[""])[0],"WDW") >= .55;
      if (ouLike && (wdwLike || /\bgoals?\b|\bcoals?\b/i.test(low))) {
        const line = extractThreshold(m) || "1.5";
        return `WDW & O/U ${line} Goals`;
      }

      if (/match\s*odds?/i.test(low) || /(?:maach|mach|macth|matoh)\s*odds?/i.test(low) || similarity(m,"Match Odds") >= .68) {
        return "Match Odds";
      }

      const num = extractThreshold(m);
      const playerLike = /player|p1ayer|plaver|mayer|nayer/i.test(low);
      const teamLike = /\bteam\b|tearn|tean/i.test(low);
      const shotsLike = /shot/i.test(low);
      const targetLike = /target|woodw|includ|inchad|woodv/i.test(low);
      const fouledLike = /foul/i.test(low);

      if (playerLike && shotsLike && targetLike) {
        return `Player To Have ${num || "1"} Or More Shots On Target Including Woodwork`;
      }
      if (playerLike && shotsLike && num) {
        return `Player To Have ${num} Or More Shots`;
      }
      if (playerLike && fouledLike) {
        return `Player To Be Fouled ${num || "1"} Or More Times`;
      }
      if (teamLike && shotsLike && num) {
        return `Team To Have ${num} Or More Shots`;
      }

      if (/^means$/i.test(m)) return "Match Odds";
      if (teamSelection && (!m || (m.length <= 12 && !/\d/.test(m) && !/(shots?|fouls?|goals?|corners?|cards?|odds|chance|qualify|draw|team|player)/i.test(m)))) {
        return "Match Odds";
      }
      return m;
    }

    function tidySelection(selection, market) {
      let s = stripSubReplacement(selection, market);
      // Safe character-level OCR repairs that don't invent a different player.
      s = s.replace(/!/g,"l").replace(/\s{2,}/g," ").trim();
      return s;
    }

    function fixMoney(out) {
      const stake = Number(out?.stake);
      const price = Number(out?._receiptOdds);
      const free = Number(out?.free || 0);
      if (!Number.isFinite(stake) || stake <= 0 || !Number.isFinite(price) || price < 1) return out;

      const expected = Math.max(0, Math.round((stake * price - Math.min(stake, Math.max(0, free))) * 100) / 100);
      if (!Number.isFinite(expected) || expected <= 0) return out;

      const current = Number(out?.returns);
      const result = cleanText(out?.result);
      let replace = false;

      if (/^(?:Loss|Void)$/i.test(result)) {
        replace = !Number.isFinite(current) || Math.abs(current - expected) > Math.max(0.05, expected * 0.02);
      } else if (!/^Win$/i.test(result)) {
        replace = !Number.isFinite(current) || current <= 0 || current > expected * 1.35 || current < expected * 0.65;
      }

      if (replace) {
        out.returns = expected.toFixed(2);
        out.returnsPence = Math.round(expected * 100);
        out._exactReturnSource = "price-sanity-reconstruction";
        const bad = Number.isFinite(current) ? `£${current.toFixed(2)}` : "an unreadable value";
        out._moneyWarning = `OCR return ${bad} was rejected because it conflicted with stake × displayed odds. Potential return was reconstructed as £${expected.toFixed(2)}.`;
      }
      return out;
    }

    const wrapped = async (...args) => {
      const out = await original(...args);
      if (!out || typeof out !== "object") return out;

      if (Array.isArray(out.legs)) {
        out.legs = out.legs.map(leg => {
          const event = fixEvent(leg?.event);
          let market = cleanText(leg?.market);
          let selection = cleanText(leg?.selection);
          market = canonicalMarket(market, selection, event);
          selection = tidySelection(selection, market);
          // Re-run market inference after selection cleanup (important for team/Yes-No structural clues).
          market = canonicalMarket(market, selection, event);
          return { ...leg, event, market, selection };
        });
      }

      if (out.event) out.event = fixEvent(out.event);
      if (out.selection || out.market) {
        out.market = canonicalMarket(out.market, out.selection, out.event);
        out.selection = tidySelection(out.selection, out.market);
        out.market = canonicalMarket(out.market, out.selection, out.event);
      }

      return fixMoney(out);
    };

    wrapped.__btQualityWrapped = true;
    wrapped.__btOriginalScanner = original;
    window.__btOCRReceiptData = wrapped;
  };

  waitForScanner();
})();
</script>
'''

marker = "</body>"
if marker not in html:
    raise SystemExit("Could not find body close")
html = html.replace(marker, script + "\n" + marker, 1)
path.write_text(html, encoding="utf-8")
print("Applied scanner quality patch")
