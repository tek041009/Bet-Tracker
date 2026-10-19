"""Non-destructive Bet Tracker V2 live authentication/cloud smoke test.
Creates one random temporary V2-only account, logs in, writes and reads one temporary
record with RLS, then deletes the account and its data.
"""
import json, secrets, urllib.request, urllib.error
ROOT="https://kucwclsjzpavtmhowyem.supabase.co"
PUB="sb_publishable_pZvmArEeJXUCNWGVZwUBGw_PqsKgTMy"
username="v2qa"+secrets.token_hex(5)
password=secrets.token_urlsafe(24)+"A9!"
email=username+"@users.bettrackerv2.app"
token=None
created=False

def request(path,payload=None,method=None,as_user=False,extra=None,allowed=(200,201,204)):
    body=None if payload is None else json.dumps(payload).encode()
    headers={"apikey":PUB,"Authorization":"Bearer "+(token if as_user and token else PUB),"Content-Type":"application/json"}
    headers.update(extra or {})
    req=urllib.request.Request(ROOT+path,data=body,headers=headers,method=method or ("POST" if body is not None else "GET"))
    try:
        with urllib.request.urlopen(req,timeout=18) as resp:
            raw=resp.read().decode()
            status=resp.status
    except urllib.error.HTTPError as exc:
        status=exc.code
        raw=exc.read().decode(errors="replace")
    if status not in allowed:
        raise RuntimeError(f"{req.method} {path.split('?')[0]} returned {status}: {raw[:450]}")
    return json.loads(raw) if raw.strip() else None

try:
    signup=request("/functions/v1/bet-tracker-v2-auth",{"action":"signup","username":username,"password":password})
    if not signup or not signup.get("ok"): raise AssertionError("V2 signup did not return ok")
    created=True
    print("V2 QA: isolated signup passed",flush=True)
    login=request("/auth/v1/token?grant_type=password",{"email":email,"password":password})
    token=login.get("access_token")
    uid=login.get("user",{}).get("id")
    if not token or not uid: raise AssertionError("V2 login did not return a user session")
    print("V2 QA: username/password login passed",flush=True)
    profile=request("/rest/v1/bet_tracker_v2_profiles?select=username&user_id=eq."+uid,as_user=True)
    if len(profile)!=1 or profile[0].get("username")!=username:raise AssertionError("V2 profile not accessible by its owner")
    payload={"user_id":uid,"data":{"cloudVersion":1,"tracker":{"version":1,"bets":[],"transactions":[]},"curves":None},"schema_version":1}
    request("/rest/v1/bet_tracker_v2_state?on_conflict=user_id",payload,as_user=True,
            extra={"Prefer":"resolution=merge-duplicates,return=representation"})
    out=request("/rest/v1/bet_tracker_v2_state?select=data&user_id=eq."+uid,as_user=True)
    if len(out)!=1 or out[0].get("data",{}).get("cloudVersion")!=1:raise AssertionError("V2 state save/read failed")
    print("V2 QA: isolated profile + cloud save/read passed",flush=True)
finally:
    if created and token:
        deleted=request("/functions/v1/bet-tracker-v2-auth",{"action":"delete_account","confirm":"DELETE"},as_user=True)
        if not deleted or not deleted.get("ok"):raise AssertionError("V2 QA cleanup failed")
        print("V2 QA: temporary test account and cloud state deleted",flush=True)
    elif created:
        print("V2 QA WARNING: signup created a test account but login failed, manual cleanup needed",flush=True)
