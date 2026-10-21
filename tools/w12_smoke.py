# -*- coding: utf-8 -*-
"""Smoke W1.2 AJUSTES: 9 asserts — aba existe, troca de aba, zero scroll,
volume aplica, qualidade aplica (pixel ratio), juice gate, toggle de som,
persistencia via reload, perfil intacto (5 tabs)."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

PROBE1 = """(async () => {
  let out = {};
  try {
    const $ = (s) => document.querySelector(s);
    // 1) aba + pagina existem
    out.pageExists = !!(document.querySelector('.nav-tab[data-page="ajustes"]') && document.getElementById('page-ajustes'));
    // 2) troca de aba
    const tab = document.querySelector('.nav-tab[data-page="ajustes"]');
    tab.click();
    await new Promise(r => setTimeout(r, 250));
    const sec = document.getElementById('page-ajustes');
    out.tabSwitch = !!(sec && sec.classList.contains('active') && tab.getAttribute('aria-selected') === 'true');
    // 3) zero scroll na pagina
    out.noScroll = sec && sec.scrollWidth <= sec.clientWidth + 1 && document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1;
    // 4) volume aplica
    const vol = document.getElementById('aj-volume');
    vol.value = 50; vol.dispatchEvent(new Event('input')); vol.dispatchEvent(new Event('change'));
    await new Promise(r => setTimeout(r, 120));
    out.volumeApplies = { vol: window.AUTH_SFX.volume, label: document.getElementById('aj-volume-label').textContent };
    // 5) qualidade aplica (pixel ratio)
    const med = document.getElementById('aj-q-med'); med.click();
    await new Promise(r => setTimeout(r, 150));
    const expRatio = Math.min(window.devicePixelRatio || 1, 1.25);
    out.qualityApplies = { ratio: window.__renderer.getPixelRatio(), exp: expRatio, active: med.classList.contains('active') };
    // 6) juice gate
    const ju = document.getElementById('aj-juice');
    ju.checked = false; ju.dispatchEvent(new Event('change'));
    out.juiceOff = window.JUICE.enabled === false;
    // 7) toggle de som bloqueia playback
    const snd = document.getElementById('aj-sound');
    snd.checked = false; snd.dispatchEvent(new Event('change'));
    window.AUTH_SFX._last = {};
    const blocked = window.AUTH_SFX.play('ko') === false;
    snd.checked = true; snd.dispatchEvent(new Event('change'));
    window.AUTH_SFX._last = {};
    const unblocked = window.AUTH_SFX.play('ko') === true;
    out.soundToggle = { blocked, unblocked, prefSync: document.getElementById('pref-sound').checked === true };
    // 8a) persistiu no perfil
    const prof = JSON.parse(localStorage.getItem('nuba.profile.v1') || '{}');
    out.persisted = { volume: prof.volume, quality: prof.quality, juice: prof.juice, sound: prof.sound };
    return out;
  } catch (e) { return { err: String(e && e.message ? e.message : e), out }; }
})()"""

PROBE2 = """(async () => {
  let out = {};
  try {
    const $ = (s) => document.querySelector(s);
    // 8b) estado restaurado do perfil apos reload
    await new Promise(r => setTimeout(r, 300));
    out.restored = {
      volume: window.AUTH_SFX.volume,
      ratio: window.__renderer.getPixelRatio(),
      juice: window.JUICE.enabled,
      juiceUnchecked: document.getElementById('aj-juice').checked === false,
      medActive: document.getElementById('aj-q-med').classList.contains('active')
    };
    // 9) perfil intacto: 5 tabs + perfil ainda troca
    out.navCount = document.querySelectorAll('.lobby-nav .nav-tab').length;
    document.querySelector('.nav-tab[data-page="perfil"]').click();
    await new Promise(r => setTimeout(r, 200));
    out.perfilSwitch = document.getElementById('page-perfil').classList.contains('active');
    out.perfilSoundExists = !!document.getElementById('pref-sound');
    // restaura defaults (higiene do smoke)
    const ju = document.getElementById('aj-juice');
    document.querySelector('.nav-tab[data-page="ajustes"]').click();
    await new Promise(r => setTimeout(r, 150));
    ju.checked = true; ju.dispatchEvent(new Event('change'));
    const vol = document.getElementById('aj-volume');
    vol.value = 85; vol.dispatchEvent(new Event('input')); vol.dispatchEvent(new Event('change'));
    document.getElementById('aj-q-high').click();
    await new Promise(r => setTimeout(r, 150));
    out.defaultsRestored = window.AUTH_SFX.volume === 0.85 && window.JUICE.enabled === true;
    return out;
  } catch (e) { return { err: String(e && e.message ? e.message : e), out }; }
})()"""

async def main(port):
    info = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
    page = next(t for t in info if t.get('type') == 'page')
    async with websockets.connect(page['webSocketDebuggerUrl'], max_size=20_000_000) as ws:
        mid = 0
        async def call(method, params=None):
            nonlocal mid
            mid += 1
            req = {"id": mid, "method": method}
            if params: req["params"] = params
            await ws.send(json.dumps(req))
            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
                if data.get("id") == mid:
                    if "error" in data: raise RuntimeError(str(data["error"]))
                    return data.get("result", {})
        async def ev(expr):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            if r.get("exceptionDetails"):
                return {"err": r["exceptionDetails"].get("text", "")}
            return r.get("result", {}).get("value")
        await call("Page.enable")
        await call("Page.navigate", {"url": BASE})
        # readiness determinístico: __ajustesReady só existe com listeners attached (W1.2.1)
        for _ in range(40):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true"): break
        v = await ev(PROBE1)
        print("PROBE1:", json.dumps(v, indent=1, ensure_ascii=False))
        # reload para validar persistencia
        await call("Page.navigate", {"url": BASE})
        for _ in range(40):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true"): break
        w = await ev(PROBE2)
        print("PROBE2:", json.dumps(w, indent=1, ensure_ascii=False))
        va, qa, pa, sa = v.get('volumeApplies') or {}, v.get('qualityApplies') or {}, v.get('persisted') or {}, v.get('soundToggle') or {}
        ra = w.get('restored') or {}
        ok = bool(v and not v.get('err') and v.get('pageExists') and v.get('tabSwitch')
              and v.get('noScroll')
              and va.get('vol') == 0.5 and va.get('label') == '50%'
              and qa.get('ratio') == qa.get('exp') and qa.get('active')
              and v.get('juiceOff')
              and sa.get('blocked') and sa.get('unblocked') and sa.get('prefSync')
              and pa.get('volume') == 0.5 and pa.get('quality') == 'med' and pa.get('juice') is False
              and w and not w.get('err') and ra.get('volume') == 0.5
              and ra.get('juice') is False and ra.get('juiceUnchecked')
              and ra.get('medActive')
              and w.get('navCount') == 5 and w.get('perfilSwitch') and w.get('perfilSoundExists')
              and w.get('defaultsRestored'))
        print('SMOKE RESULT:', 'PASS' if ok else 'FAIL')
        return 0 if ok else 1

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=1280,720", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
code = 1
try:
    code = asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(code)
