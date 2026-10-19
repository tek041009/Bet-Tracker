"""Route September Bet Tracker's hosted app to isolated V2 storage/auth.
No changes to its React bundle, importers, calculations or existing Supabase data.
A missing expected source marker fails the Pages build instead of publishing a broken site.
"""
from pathlib import Path
import re, base64, json

p=Path("_site/index.html")
html=p.read_text(encoding="utf-8")
OLD="cjixhhbbtrhtenvwjvzv"
NEW="kucwclsjzpavtmhowyem"
PUB="sb_publishable_pZvmArEeJXUCNWGVZwUBGw_PqsKgTMy"
old_urls=sorted(set(re.findall(r"https://[a-z]{20}\.supabase\.co",html)))
print("V2 audit original Supabase project URLs:",old_urls, flush=True)
if OLD not in html:
    raise SystemExit("V2 rewire aborted: dedicated September Supabase ID not found in generated app")
if "tracker_data" not in html:
    raise SystemExit("V2 rewire aborted: legacy tracker_data store not found in generated app")
if "bt-auth-form" not in html:
    raise SystemExit("V2 rewire aborted: account form not found in generated app")

# Replace only anon JWTs issued for the old dedicated project; never touch session tokens.
def jwt_rewrite(m):
    token=m.group(0)
    try:
        part=token.split(".")[1]
        payload=json.loads(base64.urlsafe_b64decode(part+"="*(-len(part)%4)))
    except Exception:
        return token
    if payload.get("ref")==OLD and payload.get("role")=="anon":
        return PUB
    return token

html,n=re.subn(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",jwt_rewrite,html)
html=html.replace(OLD,NEW)
# Supabase publishable keys generated for the dedicated old project.
keys=set(re.findall(r"sb_publishable_[a-zA-Z0-9_-]{12,}",html))
for key in keys:
    if key != PUB:
        html=html.replace(key,PUB)
html=html.replace("tracker_data","bet_tracker_v2_state")
html=html.replace("bet-tracker-auth","bet-tracker-v2-auth")
html=html.replace("@users.bettracker.app","@users.bettrackerv2.app")
# The September site explicitly uses the generic profile name and older synthetic-email domain.
# V2 must use its own newly created table and username domain.
html=html.replace('client.from("profiles")','client.from("bet_tracker_v2_profiles")')
html=html.replace("@users.bet-tracker.invalid","@users.bettrackerv2.app")
html=html.replace("bet-tracker-signup","bet-tracker-v2-auth")
html=html.replace("JSON.stringify({ username, password })","JSON.stringify({ action: 'signup', username, password })")
if 'client.from("profiles")' in html or '@users.bet-tracker.invalid' in html:
    raise SystemExit("V2 rewire aborted: stale username/profile route remains")
if html.count('client.from("bet_tracker_v2_profiles")') < 2:
    raise SystemExit("V2 rewire aborted: V2 profile lookups missing")

# Support plain username-to-email conversions in old SDK login requests.
js=r"""
<script id="bt-v2-account-compatibility">
(()=> {
  'use strict';
  const ROOT='https://kucwclsjzpavtmhowyem.supabase.co';
  const PUBLIC='sb_publishable_pZvmArEeJXUCNWGVZwUBGw_PqsKgTMy';
  const SUFFIX='@users.bettrackerv2.app';
  const nativeFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    try {
      const u=typeof input==='string'?input:input?.url;
      if(u && u.startsWith(ROOT+'/auth/v1/token') && u.includes('grant_type=password') && init && typeof init.body==='string') {
        const b=JSON.parse(init.body);
        if(typeof b.email==='string' && b.email.includes('@')) {
          const username=b.email.split('@')[0].trim().toLowerCase();
          if(/^[a-z0-9._-]{3,24}$/.test(username)){
            return nativeFetch(input,{...init,body:JSON.stringify({...b,email:username+SUFFIX})});
          }
        }
      }
    } catch(e){ console.warn('V2 login compatibility',e); }
    return nativeFetch(input,init);
  };
  document.addEventListener('submit',async (evt)=>{
    const form=evt.target;
    if(form?.id!=='bt-auth-form')return;
    const signupTab=document.getElementById('bt-signup-tab');
    const submit=document.getElementById('bt-auth-submit');
    const signingUp=signupTab?.classList.contains('active')||
      /create (an? )?account|sign ?up/i.test(submit?.textContent||'');
    if(!signingUp)return; // Normal login keeps the existing client/session flow.
    evt.preventDefault();
    evt.stopImmediatePropagation();
    const msg=document.getElementById('bt-auth-msg');
    const username=String(document.getElementById('bt-auth-username')?.value||'').trim().toLowerCase();
    const password=String(document.getElementById('bt-auth-password')?.value||'');
    if(!/^[a-z0-9._-]{3,24}$/.test(username)||password.length<8){
      if(msg)msg.textContent='Use a 3–24 character username and password of at least 8 characters.';
      return;
    }
    if(submit)submit.disabled=true;
    if(msg){msg.textContent='Creating your V2 account…';msg.classList.remove('ok');}
    try{
      const res=await nativeFetch(ROOT+'/functions/v1/bet-tracker-v2-auth',{
        method:'POST',
        headers:{'Content-Type':'application/json',apikey:PUBLIC,Authorization:'Bearer '+PUBLIC},
        body:JSON.stringify({action:'signup',username,password})
      });
      const data=await res.json();
      if(!res.ok || !data.ok)throw new Error(data.error||'Could not create account.');
      const code=data.recovery_code||'';
      const box=document.createElement('div');
      box.id='bt-v2-recovery';
      box.setAttribute('role','status');
      box.style.cssText='font:12px system-ui;line-height:1.6;border:1px solid #1e9c83;border-radius:10px;padding:14px;margin:12px 0;color:#dcfff6;background:#083027;overflow-wrap:anywhere';
      const heading=document.createElement('strong');
      heading.textContent='Account created. Save this recovery code:';
      const codeEl=document.createElement('code');
      codeEl.textContent=code;
      codeEl.style.cssText='display:block;font-size:13px;margin:8px 0;user-select:all;word-break:break-all';
      const note=document.createElement('span');
      note.textContent='The code is displayed only once. You can now log in using your username and password.';
      box.append(heading,codeEl,note);
      (form.parentNode||form).insertBefore(box,form);
      document.getElementById('bt-login-tab')?.click();
      if(msg){msg.textContent='V2 account created. Log in to begin.';msg.classList.add('ok');}
    }catch(error){
      if(msg)msg.textContent=error?.message||'Could not create account. Please try again.';
    }finally{
      if(submit)submit.disabled=false;
    }
  },true);
})();
</script>
"""
if "</head>" not in html: raise SystemExit("V2 rewire aborted: closing head tag not found")
html=html.replace("</head>",js+"\n</head>",1)
if OLD in html: raise SystemExit("V2 rewire aborted: old project ID remains in generated HTML")
p.write_text(html,encoding="utf-8")
print("V2 route configured: new Supabase project, isolated state, auth compatibility script, signup handler.",flush=True)
