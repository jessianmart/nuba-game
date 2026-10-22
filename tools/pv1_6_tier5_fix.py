"""Fix Tier 5 (2a rodada, baseada em diags reais):
  F1 M03: __matchState NAO tem 'mode' (chaves reais: time/br/overtime/suddenDeath/
     blue/red; CDP descarta valores undefined -> KeyError). Discriminador real do
     modo DM: __matchState.br === null.
  F2 M08: startMatch('br_vila') em MOBILE demora ~32s (desktop 8.6s) — estoura o
     timeout CDP de 30s do eval_js (TimeoutError de mensagem vazia). Helper
     _t5_eval_slow com timeout 90s para os startMatch.
  F3 M09: clearUserAgentOverride NAO propagou no headless — usar SET (mecanismo
     provado no M01) com UA desktop + metrics 1280x720.
Run: python tools/pv1_6_tier5_fix.py   (cwd = repo root)
"""
import py_compile
import shutil

SUITE = 'tools/test_e2e_suite.py'
shutil.copy2(SUITE, SUITE + '.bak_pv1_6fix')
s = open(SUITE, 'r', encoding='utf-8', newline='').read()
sep = '\r\n' if '\r\n' in s else '\n'


def rep(old, new, count=1):
    global s
    old = old.replace('\n', sep)
    new = new.replace('\n', sep)
    assert s.count(old) == count, f'ancora com {s.count(old)} ocorrencias (esperava {count}): {old[:80]}'
    s = s.replace(old, new, count)


# --- F2: helper de eval lento ---
rep("""            await asyncio.sleep(delay)
        return False

    async def _t5_boot_mobile(self):""",
    """            await asyncio.sleep(delay)
        return False

    async def _t5_eval_slow(self, expr, timeout=90.0):
        \"\"\"Runtime.evaluate com timeout estendido: startMatch('br_vila') em mobile
        carrega a vila (7 MB) e levou 32.2s medido vs 8.6s no desktop — o default
        de 30s do eval_js estoura com TimeoutError de mensagem VAZIA (diag real).\"\"\"
        res = await self.cdp.send("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True}, timeout=timeout)
        exc = res.get("exceptionDetails")
        if exc:
            msg = (exc.get("exception") or {}).get("description") or exc.get("text")
            raise RuntimeError(f"JS Eval Error: {msg}")
        return res.get("result", {}).get("value")

    async def _t5_boot_mobile(self):""")

# --- F2b: startMatch 3v3 via eval lento (60s) ---
rep("""        ok = await self.cdp.eval_js(\"\"\"(async () => {
            try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; }
        })()\"\"\", await_promise=True)""",
    """        ok = await self._t5_eval_slow(\"\"\"(async () => {
            try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; }
        })()\"\"\", timeout=60.0)""")

# --- F2c: startMatch br_vila via eval lento (90s) ---
rep("""        ok = await self.cdp.eval_js(\"\"\"(async () => {
            try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; }
        })()\"\"\", await_promise=True)""",
    """        ok = await self._t5_eval_slow(\"\"\"(async () => {
            try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; }
        })()\"\"\", timeout=90.0)""")

# --- F1a: M03 JS — discriminador real (br null) em vez de 'mode' inexistente ---
rep("""            mode: window.__matchState ? window.__matchState.mode : null""",
    """            brNull: (window.__matchState && window.__matchState.br === null) ? true : (window.__matchState ? false : null)""")

# --- F1b: M03 assert ---
rep("""        assert res["mode"] in ("dm_3v3", "dm"), f"matchState.mode inesperado: {res}\"""",
    """        assert res["brNull"] is True, f"modo DM deveria ter __matchState.br null (sem estado BR): {res}\"""")

# --- F3: M09 — SET desktop (proven) em vez de CLEAR (nao propagou) ---
rep("""        await self.cdp.send("Emulation.clearUserAgentOverride")
        await self.cdp.send("Emulation.clearDeviceMetricsOverride")
        ok = await self._t5_wait_js("!(/iPhone/.test(navigator.userAgent))", tries=10, delay=0.3)
        assert ok, "clearUserAgentOverride nao aplicou (UA ainda iPhone)\"""",
    """        # SET (mecanismo provado no M01) em vez de CLEAR — clearUserAgentOverride
        # nao propagou no headless (M09 falhou com UA ainda iPhone na 1a rodada)
        await self.cdp.send("Emulation.setUserAgentOverride", {"userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})
        await self.cdp.send("Emulation.setDeviceMetricsOverride",
                            {"width": 1280, "height": 720, "deviceScaleFactor": 1, "mobile": False})
        ok = await self._t5_wait_js("!(/iPhone/.test(navigator.userAgent))", tries=10, delay=0.3)
        assert ok, "override desktop nao aplicou (UA ainda iPhone)\"""")

open(SUITE, 'w', encoding='utf-8', newline='').write(s)
py_compile.compile(SUITE, doraise=True)
print('[ok] Tier 5 fix: M03 brNull, M08 eval 90s, M09 SET desktop; suite compila')
