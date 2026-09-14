from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")

replacements = []

replacements.append((
'''  function readLocalEnvelope() {
    const tracker = safeParse(localStorage.getItem(APP_KEY), BLANK) || BLANK;
    const curves = safeParse(localStorage.getItem(CURVE_KEY), null);
    return { cloudVersion: 1, tracker, curves, syncedAt: new Date().toISOString() };
  }''',
'''  function readLocalEnvelope() {
    const localTracker = safeParse(localStorage.getItem(APP_KEY), BLANK) || BLANK;
    const tracker = Array.isArray(localTracker?.bets)
      ? { ...localTracker, bets: localTracker.bets.map(bet => { const copy = { ...bet }; delete copy.receiptImage; return copy; }) }
      : localTracker;
    const curves = safeParse(localStorage.getItem(CURVE_KEY), null);
    return {
      cloudVersion: 1,
      tracker,
      curves,
      allowEmptyReset: !!window.__BT_ALLOW_EMPTY_CLOUD_SAVE__,
      syncedAt: new Date().toISOString()
    };
  }'''))

replacements.append((
'''  async function flushCloud() {
    if (!client || !currentUser || !window.__BT_CLOUD_READY__) return;
    const payload = readLocalEnvelope();
    const userId = currentUser.id;
    syncInFlight = client.from("tracker_data").upsert({ user_id: userId, data: payload }, { onConflict: "user_id" });
    const { error } = await syncInFlight;
    syncInFlight = null;
    if (error) {
      console.error("Bet Tracker cloud save failed", error);
      showAccountState("Save issue", true);
    } else {
      showAccountState("Saved", false);
    }
  }''',
'''  async function flushCloud() {
    if (!client || !currentUser || !window.__BT_CLOUD_READY__) return false;
    const payload = readLocalEnvelope();
    const userId = currentUser.id;
    const localTracker = payload.tracker || BLANK;
    const localCount = (Array.isArray(localTracker.bets) ? localTracker.bets.length : 0) +
      (Array.isArray(localTracker.transactions) ? localTracker.transactions.length : 0);

    if (localCount === 0 && !window.__BT_ALLOW_EMPTY_CLOUD_SAVE__) {
      const remoteRes = await client.from("tracker_data").select("data").eq("user_id", userId).maybeSingle();
      if (!remoteRes.error && remoteRes.data?.data) {
        const remoteTracker = unpackCloudData(remoteRes.data.data).tracker || BLANK;
        const remoteCount = (Array.isArray(remoteTracker.bets) ? remoteTracker.bets.length : 0) +
          (Array.isArray(remoteTracker.transactions) ? remoteTracker.transactions.length : 0);
        if (remoteCount > 0) {
          console.warn("Blocked blank Bet Tracker overwrite; keeping cloud data.");
          applyCloudData(remoteRes.data.data);
          showAccountState("Synced", false);
          return true;
        }
      }
    }

    syncInFlight = client.from("tracker_data").upsert({ user_id: userId, data: payload }, { onConflict: "user_id" });
    const { error } = await syncInFlight;
    syncInFlight = null;
    if (error) {
      console.error("Bet Tracker cloud save failed", error);
      showAccountState("Save issue", true);
      return false;
    }
    window.__BT_ALLOW_EMPTY_CLOUD_SAVE__ = false;
    showAccountState("Saved", false);
    return true;
  }'''))

replacements.append((
'''          showAccountState("Saving…", false); await flushCloud(); location.reload();''',
'''          showAccountState("Saving…", false);
          const saved = await flushCloud();
          if (saved) location.reload();
          else window.alert("Could not save this backup to your account.");'''))

replacements.append((
'''      console.error("Bet Tracker cloud startup failed", err);
      clearLocalTracker();
      removeNative(BOOT_KEY);
      removeNative(USER_KEY);
      requireAuth("Could not load your account. Please log in again.");''',
'''      console.error("Bet Tracker cloud startup failed", err);
      window.__BT_CLOUD_READY__ = false;
      revealApp();
      showAccountState("Sync issue", true);'''))

replacements.append((
'''    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flushCloud();
    });''',
'''    // Local changes already schedule their own save; tab switching must never force a stale cloud write.'''))

replacements.append((
'''y=()=>{window.confirm("Reset all tracker data? This will clear your bets, transactions and starting balance.")&&(t.clear(),a(si))}''',
'''y=()=>{window.confirm("Reset all tracker data? This will clear your bets, transactions and starting balance.")&&(window.__BT_ALLOW_EMPTY_CLOUD_SAVE__=!0,t.clear(),a(si))}'''))

for old, new in replacements:
    count = html.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one patch target, found {count}: {old[:80]!r}")
    html = html.replace(old, new, 1)

path.write_text(html, encoding="utf-8")
print("Applied Bet Tracker cloud safety patch")
