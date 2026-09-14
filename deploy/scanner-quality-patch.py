from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")

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
    const splitTeams = event => {
      const p = cleanText(event).split(/\s+v\s+/i);
      return p.length === 2 ? p : ["", ""];
    };
    const norm = value => cleanText(value).toLowerCase().replace(/[^a-z0-9]/g, "");

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
      const parts = s.split(/\s*(?:↔|→|->|=>|⇄|⇆)\s*/);
      if (parts.length > 1 && parts[0]) return cleanText(parts[0]);
      return s;
    }

    function fixMarket(market, selection, event) {
      let m = cleanText(market);
      const [home, away] = splitTeams(event);
      const sel = norm(selection);
      const teamSelection = sel && (sel === norm(home) || sel === norm(away));

      if (/^means$/i.test(m)) return "Match Odds";
      if (teamSelection && (!m || (m.length <= 10 && !/\d/.test(m) && !/(shots?|fouls?|goals?|corners?|cards?|odds|chance|qualify|draw|team|player)/i.test(m)))) {
        return "Match Odds";
      }
      return m;
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
          selection = stripSubReplacement(selection, market);
          market = fixMarket(market, selection, event);
          return { ...leg, event, market, selection };
        });
      }

      if (out.event) out.event = fixEvent(out.event);
      if (out.selection || out.market) {
        out.selection = stripSubReplacement(out.selection, out.market);
        out.market = fixMarket(out.market, out.selection, out.event);
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
