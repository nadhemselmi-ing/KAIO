/* Added by the ground-segment server to the dashboard it serves (the offline file does not have it).
   - shows who is signed in, with a Sign out button
   - refreshes the access token silently before it expires (httpOnly cookies: this script never sees a token)
   - adds the Telecommands panel: operators send signed commands, everyone sees the onboard log */
(function(){
  const H = {'Content-Type':'application/json','X-KAIO':'1'};
  const api = (url, body) => fetch(url, {method: body === undefined ? 'GET' : 'POST', headers:H, credentials:'same-origin',
                                          body: body === undefined ? undefined : JSON.stringify(body)});
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const toLogin = () => location.replace('/login');

  window.kaioAddFR && window.kaioAddFR({
    'Sign out':'Se déconnecter','operator':'opérateur','viewer':'observateur','Telecommands':'Télécommandes',
    'Authenticated commands to the onboard engine':'Commandes authentifiées vers le moteur embarqué',
    'Each command is signed on the ground with HMAC-SHA256 and a sequence number. The satellite applies it only if the signature is valid, the sequence number is new and the value is inside safe limits.':
      'Chaque commande est signée au sol avec HMAC-SHA256 et un numéro de séquence. Le satellite ne l’applique que si la signature est valide, si le numéro est nouveau et si la valeur reste dans les limites sûres.',
    'Onboard settings now':'Réglages à bord actuels','Send a command':'Envoyer une commande','Parameter':'Paramètre','Value':'Valeur','Sign and send':'Signer et envoyer',
    'Security tests':'Tests de sécurité','Replay the last packet':'Rejouer le dernier paquet','Tamper with the last packet':'Modifier le dernier paquet',
    'Onboard log, newest first':'Journal de bord, plus récent en premier','Seq':'Séq','Time':'Heure','User':'Utilisateur','Result':'Résultat',
    'Only operators can send commands. You are signed in as a viewer.':'Seuls les opérateurs peuvent envoyer des commandes. Vous êtes connecté en observateur.',
    'No command yet.':'Aucune commande pour l’instant.','bad signature':'signature invalide','accepted':'acceptée','rejected':'rejetée',
    'engine trade-off knob (Lyapunov V)':'réglage du compromis du moteur (V de Lyapunov)',
    'battery reserve above the eclipse-survival floor [Wh]':'réserve de batterie au-dessus du seuil de survie en éclipse [Wh]',
    'extra margin below the 45 C limit [K]':'marge supplémentaire sous la limite de 45 °C [K]',
    'fire alerts may run up to the 60 C hardware limit (0/1)':'les alertes feu peuvent aller jusqu’à la limite matérielle de 60 °C (0/1)',
    'laser offload to neighbours allowed (0/1)':'délégation laser vers les voisins autorisée (0/1)',
    'send one valid telecommand first':'envoyez d’abord une télécommande valide',
  });

  // ---- session badge + silent refresh ------------------------------------------------------------
  let refreshTimer = null;
  function schedule(exp){
    clearTimeout(refreshTimer);
    const ms = Math.max(5000, (exp * 1000 - Date.now()) - 60000);   // one minute before the access token expires
    refreshTimer = setTimeout(doRefresh, ms);
  }
  async function doRefresh(){
    try { const r = await api('/api/auth/refresh', {}); if(!r.ok) return toLogin(); const m = await api('/api/me'); if(!m.ok) return toLogin(); schedule((await m.json()).exp); }
    catch(e){ refreshTimer = setTimeout(doRefresh, 15000); }   // network hiccup: try again shortly
  }
  document.addEventListener('visibilitychange', ()=>{ if(!document.hidden) api('/api/me').then(r=>{ if(r.status === 401) doRefresh(); }); });

  async function start(){
    const r = await api('/api/me'); if(!r.ok) return toLogin();
    const me = await r.json(); schedule(me.exp);
    const meta = document.querySelector('.meta');
    const badge = document.createElement('div'); badge.className = 'who';
    badge.innerHTML = `<span class="whoname">${esc(me.username)}</span><span class="pill">${esc(me.role)}</span><button type="button" class="ghost" id="logoutBtn">Sign out</button>`;
    meta.prepend(badge);
    document.getElementById('logoutBtn').addEventListener('click', async ()=>{ try { await api('/api/auth/logout', {}); } finally { toLogin(); } });
    const nav = document.querySelector('nav.nav'); if(nav){ const a = document.createElement('a'); a.href = '#tc'; a.textContent = 'Telecommands'; nav.appendChild(a); }
    buildTC(me.role === 'operator');
  }

  // ---- telecommand panel --------------------------------------------------------------------------
  const css = document.createElement('style');
  css.textContent = `.who{display:flex;align-items:center;gap:8px;font-size:13px}.whoname{color:var(--ink);font-weight:600}
  .who button{padding:4px 10px;font-size:13px}
  .tcgrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:16px}
  .tcgrid .panel{padding:16px;display:grid;gap:10px;align-content:start}
  .tcform{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,.8fr) auto;gap:10px;align-items:end}
  .tcform select,.tcform input{font:inherit;color:var(--ink);background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;width:100%}
  .tcres{font-size:13.5px;min-height:1.4em;margin:0}.tcres.ok{color:var(--ok)}.tcres.bad{color:var(--alert)}
  .tcpkt{font-family:var(--mono);font-size:11.5px;color:var(--muted);word-break:break-all;margin:0}
  .tclog td,.tclog th{font-size:12.5px;padding:5px 8px;text-align:left}.tclog .bad{color:var(--alert)}.tclog .ok{color:var(--ok)}
  .tcstate{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.tcstate div{display:grid}.tcstate b{font-size:18px}.tcstate span{font-size:12px;color:var(--muted)}
  @media (max-width:900px){.tcgrid,.tcform{grid-template-columns:1fr}.tcstate{grid-template-columns:repeat(2,minmax(0,1fr))}}`;
  document.head.appendChild(css);

  function buildTC(canSend){
    const sec = document.createElement('section'); sec.className = 'blk'; sec.id = 'tc';
    sec.innerHTML = `<div class="sechead"><div><h2>Telecommands</h2><div class="eyebrow">Authenticated commands to the onboard engine</div></div>
      <p>Each command is signed on the ground with HMAC-SHA256 and a sequence number. The satellite applies it only if the signature is valid, the sequence number is new and the value is inside safe limits.</p></div>
      <div class="panel" style="padding:16px;margin-bottom:16px"><div class="eyebrow">Onboard settings now</div><div class="tcstate" id="tcState"></div></div>
      <div class="tcgrid">
        <div class="panel"><div class="eyebrow">Send a command</div>
          ${canSend ? `<div class="tcform"><label class="field"><span>Parameter</span><select id="tcParam"></select></label>
            <label class="field"><span>Value</span><input id="tcVal" type="number" step="any"></label><button type="button" id="tcSend">Sign and send</button></div>
            <p class="fine" id="tcHint"></p><p class="tcres" id="tcRes" role="status"></p><p class="tcpkt" id="tcPkt"></p>
            <div class="eyebrow" style="margin-top:6px">Security tests</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" class="ghost" id="tcReplay">Replay the last packet</button><button type="button" class="ghost" id="tcTamper">Tamper with the last packet</button></div>`
          : `<p>Only operators can send commands. You are signed in as a viewer.</p>`}
        </div>
        <div class="panel"><div class="eyebrow">Onboard log, newest first</div><div style="overflow-x:auto"><table class="tclog" id="tcLog"></table></div></div>
      </div>`;
    const anchor = document.querySelector('footer') || document.querySelector('.wrap').lastElementChild;
    anchor.parentNode.insertBefore(sec, anchor);
    let limits = {};
    const fmtState = st => Object.entries(st).map(([k,v])=>`<div><b>${(k==='alert_override'||k==='use_isl') ? (v ? 'ON' : 'OFF') : Number(v).toFixed(2)}</b><span>${esc(k)}</span></div>`).join('');
    const fmtLog = log => log.length ? '<thead><tr><th>Seq</th><th>Time</th><th>User</th><th>Parameter</th><th>Value</th><th>Result</th></tr></thead><tbody>' +
      log.map(r=>`<tr><td>${r.seq ?? ''}</td><td>${new Date(r.ts*1000).toLocaleTimeString()}</td><td>${esc(r.username)}</td><td>${esc(r.param)}</td><td>${r.value}</td><td class="${r.ok?'ok':'bad'}">${esc(r.result)}</td></tr>`).join('') + '</tbody>'
      : '<tbody><tr><td>No command yet.</td></tr></tbody>';
    async function refresh(){
      const r = await api('/api/tc'); if(r.status === 401){ await doRefresh(); return; } if(!r.ok) return;
      const d = await r.json(); limits = d.limits;
      document.getElementById('tcState').innerHTML = fmtState(d.state);
      document.getElementById('tcLog').innerHTML = fmtLog(d.log);
      const sel = document.getElementById('tcParam');
      if(sel && !sel.options.length){ sel.innerHTML = Object.keys(limits).map(k=>`<option value="${k}">${k}</option>`).join(''); sel.dispatchEvent(new Event('change')); }
    }
    if(canSend){
      const sel = document.getElementById('tcParam'), val = document.getElementById('tcVal'), res = document.getElementById('tcRes'), pk = document.getElementById('tcPkt');
      sel.addEventListener('change', ()=>{ const l = limits[sel.value]; if(!l) return; document.getElementById('tcHint').textContent = `${l[2]} · [${l[0]}, ${l[1]}]`; });
      const show = async r => { const d = await r.json().catch(()=>({detail:'error'}));
        if(!r.ok){ res.className = 'tcres bad'; res.textContent = d.detail || ('HTTP ' + r.status); return; }
        res.className = 'tcres ' + (d.ok ? 'ok' : 'bad'); res.textContent = (d.ok ? '✔ ' : '✖ ') + d.result;
        pk.textContent = JSON.stringify(d.packet); refresh(); };
      document.getElementById('tcSend').addEventListener('click', async ()=>{ if(val.value === '') return; show(await api('/api/tc', {param: sel.value, value: Number(val.value)})); });
      document.getElementById('tcReplay').addEventListener('click', async ()=> show(await api('/api/tc/attack', {kind:'replay'})));
      document.getElementById('tcTamper').addEventListener('click', async ()=> show(await api('/api/tc/attack', {kind:'tamper'})));
    }
    refresh(); setInterval(refresh, 10000);
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
