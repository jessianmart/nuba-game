"""PV1.6 + PV2.6 — TIER 5 FORMAL: tests mobile reais na suite canonica.

Insere 9 testes "Tier 5" em tools/test_e2e_suite.py (38 -> 47):
  M01 emulacao iPhone 844x390 no boot (UA override VERIFICADO antes de navegar
      — o override pode chegar atrasado ao processo e bootar com UA antigo)
  M02 governor (__GOV dprCap/vfxCap) + arena default .mobile.json (PV3.2)
  M03 3v3 mobile: 6 units, 3 retratos/time, META 15, touch-cluster grid
  M04 joystick via Input.dispatchTouchEvent REAL -> vetor INPUT + move + reset
  M05 hold ATK -> INPUT.fire + ataque dispara + .pressed
  M06 tap Q -> executeSkill + espelho de CD em #cdt-q (PV4)
  M07 hold chakra -> INPUT.chakra true/false
  M08 Realeza na Vila mobile: 10 ninjas, zona 65->6 encolhendo, 12 baus,
      vila .mobile.json
  M09 portrait -> overlay "gire o dispositivo"; restaura desktop no fim
      (a proxima bateria anexa na mesma aba)

Suite em CRLF: todas as insercoes usam o separador detectado do arquivo.
Run: python tools/pv1_6_tier5_patch.py   (cwd = repo root)
"""
import py_compile
import shutil

SUITE = 'tools/test_e2e_suite.py'
shutil.copy2(SUITE, SUITE + '.bak_pv1_6')
s = open(SUITE, 'r', encoding='utf-8', newline='').read()
sep = '\r\n' if '\r\n' in s else '\n'

METHODS = r'''    # =========================================================================
    # TIER 5: MOBILE PIVOT — PV1.6 + PV2.6 formais (docs/PIVOT_MOBILE.md)
    # Toque REAL via Input.dispatchTouchEvent; emulacao iPhone 844x390.
    # =========================================================================

    T5_IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

    async def _t5_touch(self, evtype, x, y, tid=1):
        """Toque real (mesma pipeline de um dedo): gera pointerdown/up com pointerType touch."""
        await self.cdp.send("Input.dispatchTouchEvent", {
            "type": evtype,
            "touchPoints": [{"x": x, "y": y, "id": tid, "force": 1.0}]
        })

    async def _t5_wait_js(self, expr, tries=40, delay=0.5):
        for _ in range(tries):
            try:
                if await self.cdp.eval_js(expr):
                    return True
            except RuntimeError:
                pass
            await asyncio.sleep(delay)
        return False

    async def _t5_boot_mobile(self):
        """Emulacao iPhone + reload. O UA override e VERIFICADO antes de navegar:
        o override pode chegar atrasado ao processo e bootar com o UA antigo
        (race real, medida na fase PV3.2 — inverte o resultado da sessao)."""
        await self.cdp.send("Emulation.setDeviceMetricsOverride",
                            {"width": 844, "height": 390, "deviceScaleFactor": 2, "mobile": True})
        await self.cdp.send("Emulation.setUserAgentOverride", {"userAgent": self.T5_IPHONE_UA})
        ok = await self._t5_wait_js("/iPhone/.test(navigator.userAgent)", tries=10, delay=0.3)
        assert ok, "T5: setUserAgentOverride nao aplicou (navigator.userAgent sem iPhone)"
        await self.cdp.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
        ok = await self._t5_wait_js("typeof window.startMatch === 'function'")
        assert ok, "T5: boot do jogo nao subiu apos reload mobile"

    async def test_m01_mobile_emulation_boot(self):
        """M1: iPhone UA + 844x390 no boot -> __DEVICE.isMobile, overlay oculto, governor 1.25."""
        await self._t5_boot_mobile()
        res = await self.cdp.eval_js("""(() => {
            // headless pode nao expor maxTouchPoints: garante o gate de layout
            // (no device real o boot seta body.touch sozinho via __DEVICE.isTouch)
            document.body.classList.add('touch');
            const ov = document.getElementById('rotate-overlay');
            return { isMobile: !!(window.__DEVICE && window.__DEVICE.isMobile),
                     uaMobile: /iPhone/.test(navigator.userAgent),
                     overlay: ov ? getComputedStyle(ov).display : 'missing',
                     dprCap: window.__GOV ? window.__GOV.dprCap : null,
                     vfxCap: window.__GOV ? window.__GOV.vfxCap : null,
                     iw: window.innerWidth, ih: window.innerHeight };
        })()""")
        assert res["isMobile"] is True, f"__DEVICE.isMobile deveria ser true no boot mobile: {res}"
        assert res["uaMobile"] is True, f"navigator.userAgent deveria ser iPhone: {res}"
        assert res["overlay"] == "none", f"rotate-overlay deveria ficar oculto em landscape: {res}"
        assert res["dprCap"] == 1.25, f"governor mobile deveria cap dpr em 1.25: {res}"
        assert res["vfxCap"] == 24, f"governor mobile deveria cap VFX em 24: {res}"
        assert res["iw"] == 844 and res["ih"] == 390, f"viewport deveria ser 844x390: {res}"

    async def test_m02_governor_arena_variante(self):
        """M2: arena DEFAULT do lobby carrega a VARIANTE .mobile.json (PV3.2) com poucas meshes."""
        ok = await self._t5_wait_js("!!window.__ARENA_LOADED", tries=30, delay=0.5)
        assert ok, "T5: arena nao carregou no boot (window.__ARENA_LOADED ausente)"
        res = await self.cdp.eval_js("""(() => ({
            asset: window.__ARENA_LOADED.asset,
            meshes: window.__ARENA_LOADED.meshes,
            isMobile: window.__ARENA_LOADED.isMobile
        }))()""")
        assert str(res["asset"]).endswith(".mobile.json"), f"mobile deveria carregar variante .mobile.json: {res}"
        assert res["meshes"] <= 40, f"variante mobile deveria ter <=40 meshes: {res}"
        assert res["isMobile"] is True, f"telemetria da arena deveria marcar isMobile: {res}"

    async def test_m03_3v3_mobile(self):
        """M3: startMatch('dm_3v3') em mobile -> 6 units, 3 retratos/time, META 15, cluster grid."""
        ok = await self.cdp.eval_js("""(async () => {
            try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; }
        })()""", await_promise=True)
        assert ok == "ok", f"startMatch dm_3v3 falhou: {ok}"
        ok = await self._t5_wait_js("window.units && window.units.length === 6", tries=40, delay=0.4)
        assert ok, "dm_3v3 nao spawnou 6 unidades"
        res = await self.cdp.eval_js("""(() => ({
            units: window.units.length,
            blue: document.querySelectorAll('#hud-blue-icons .mini-p').length,
            red: document.querySelectorAll('#hud-red-icons .mini-p').length,
            goal: (document.querySelector('.match-goal-txt') || {}).textContent || '',
            cluster: getComputedStyle(document.getElementById('touch-cluster')).display,
            mode: window.__matchState ? window.__matchState.mode : null
        }))()""")
        assert res["units"] == 6, f"3v3 deveria ter 6 unidades: {res}"
        assert res["blue"] == 3 and res["red"] == 3, f"3v3 deveria renderizar 3 retratos/time: {res}"
        assert "META" in res["goal"] and "15" in res["goal"], f"goal 3v3 deveria ser META 15: {res['goal']}"
        assert res["cluster"] == "grid", f"touch-cluster deveria estar display:grid com body.touch: {res}"
        assert res["mode"] in ("dm_3v3", "dm"), f"matchState.mode inesperado: {res}"

    async def test_m04_joystick_touch_real(self):
        """M4: Joystick via dispatchTouchEvent -> vetor INPUT + unidade move + reset (PV1.3)."""
        pos = await self.cdp.eval_js("""(() => {
            const r = document.getElementById('touch-joystick').getBoundingClientRect();
            return { x: r.left + r.width * 0.5,
                     y: Math.min(r.top + r.height * 0.75, window.innerHeight - 20),
                     w: r.width, h: r.height };
        })()""")
        assert pos and pos["w"] > 0 and pos["h"] > 0, f"touch-joystick deveria ter rect visivel: {pos}"
        x0, y0 = pos["x"], pos["y"]
        await self._t5_touch("touchStart", x0, y0)
        await asyncio.sleep(0.1)
        await self._t5_touch("touchMove", x0 + 90, y0 - 80)
        await asyncio.sleep(0.15)
        j = await self.cdp.eval_js("({ mx: window.INPUT.moveX, mz: window.INPUT.moveZ })")
        assert j["mx"] > 0.3 and j["mz"] > 0.3, f"joystick deveria apontar direita/frente: {j}"
        px0 = await self.cdp.eval_js("window.units.find(u => u.isPlayer).x")
        await asyncio.sleep(0.8)
        px1 = await self.cdp.eval_js("window.units.find(u => u.isPlayer).x")
        assert px1 > px0 + 0.3, f"unidade deveria mover +X com joystick: {px0} -> {px1}"
        await self._t5_touch("touchEnd", x0 + 90, y0 - 80)
        await asyncio.sleep(0.15)
        j2 = await self.cdp.eval_js("({ mx: window.INPUT.moveX, mz: window.INPUT.moveZ })")
        assert j2["mx"] == 0 and j2["mz"] == 0, f"INPUT deveria zerar ao soltar: {j2}"

    async def test_m05_atk_hold_touch(self):
        """M5: botao ATK real -> INPUT.fire hold + ataque dispara; soltar zera (PV1.4)."""
        c = await self.cdp.eval_js("""(() => {
            const r = document.getElementById('tbtn-atk').getBoundingClientRect();
            const p = window.units.find(u => u.isPlayer);
            p.cds.atk = 0;
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        })()""")
        await self._t5_touch("touchStart", c["x"], c["y"])
        await asyncio.sleep(0.45)
        mid = await self.cdp.eval_js("""(() => ({ fire: window.INPUT.fire,
            st: window.units.find(u => u.isPlayer).state,
            cd: window.units.find(u => u.isPlayer).cds.atk,
            pressed: document.getElementById('tbtn-atk').classList.contains('pressed') }))()""")
        await self._t5_touch("touchEnd", c["x"], c["y"])
        await asyncio.sleep(0.1)
        fire2 = await self.cdp.eval_js("window.INPUT.fire")
        assert mid["fire"] is True, f"hold ATK deveria setar INPUT.fire: {mid}"
        assert mid["pressed"] is True, f"botao deveria ganhar .pressed: {mid}"
        assert mid["cd"] > 0 or str(mid["st"]).startswith("attack"), f"ATK deveria disparar ataque: {mid}"
        assert fire2 is False, f"soltar ATK deveria zerar INPUT.fire: {fire2}"

    async def test_m06_skill_q_touch_cd_mirror(self):
        """M6: tap tbtn-q -> executeSkill (cd sobe) + espelho de CD vivo em #cdt-q (PV4)."""
        c = await self.cdp.eval_js("""(() => {
            const p = window.units.find(u => u.isPlayer);
            p.cds.q = 0; p.chakra = 100;
            const r = document.getElementById('tbtn-q').getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        })()""")
        await self._t5_touch("touchStart", c["x"], c["y"])
        await self._t5_touch("touchEnd", c["x"], c["y"])
        await asyncio.sleep(0.2)
        res = await self.cdp.eval_js("""(() => {
            const el = document.getElementById('cdt-q');
            const p = window.units.find(u => u.isPlayer);
            const m = ((el && el.textContent) || '').match(/[0-9]+(\.[0-9]+)?/);
            const cs = el ? getComputedStyle(el) : null;
            return { cd: p.cds.q,
                     num: m ? parseFloat(m[0]) : 0,
                     conic: cs ? ((cs.backgroundImage || '') + ' ' + (cs.background || '')).indexOf('conic') >= 0 : false };
        })()""")
        assert res["cd"] > 0, f"tap em Q deveria disparar executeSkill (cd>0): {res}"
        assert res["num"] > 0 or res["conic"], f"espelho de CD #cdt-q deveria exibir contagem/conic: {res}"

    async def test_m07_chakra_hold_touch(self):
        """M7: hold tbtn-c -> INPUT.chakra true; soltar -> false (PV1.4)."""
        c = await self.cdp.eval_js("""(() => { const r = document.getElementById('tbtn-c').getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()""")
        await self._t5_touch("touchStart", c["x"], c["y"])
        await asyncio.sleep(0.15)
        v = await self.cdp.eval_js("window.INPUT.chakra")
        await self._t5_touch("touchEnd", c["x"], c["y"])
        await asyncio.sleep(0.1)
        v2 = await self.cdp.eval_js("window.INPUT.chakra")
        assert v is True, f"hold chakra deveria setar INPUT.chakra: {v}"
        assert v2 is False, f"soltar deveria zerar INPUT.chakra: {v2}"

    async def test_m08_br_vila_mobile(self):
        """M8: Realeza na Vila mobile -> 10 ninjas, zona encolhe, HUD BR, vila .mobile.json (PV2.6)."""
        ok = await self.cdp.eval_js("""(async () => {
            try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; }
        })()""", await_promise=True)
        assert ok == "ok", f"startMatch br_vila falhou: {ok}"
        ok = await self._t5_wait_js("window.units && window.units.length === 10", tries=40, delay=0.4)
        assert ok, "br_vila nao spawnou 10 ninjas"
        res = await self.cdp.eval_js("""(() => ({
            alive: window.__matchState.br.alive,
            zoneR: window.__matchState.br.zoneR,
            zoneMin: window.__matchState.br.zoneMin,
            chests: window.__matchState.br.chests.length,
            phase: window.__matchState.br.phase,
            hud: getComputedStyle(document.getElementById('br-hud')).display,
            arena: window.__ARENA_LOADED ? window.__ARENA_LOADED.asset : null
        }))()""")
        assert res["alive"] == 10, f"BR deveria comecar com 10 vivos: {res}"
        assert res["zoneR"] == 65 and res["zoneMin"] == 6, f"zona deveria nascer 65->min 6: {res}"
        assert res["chests"] == 12, f"layout deveria ter 12 baus: {res}"
        assert res["hud"] not in ("none", ""), f"HUD BR deveria estar visivel: {res}"
        assert res["arena"] and str(res["arena"]).endswith("sa00z.mobile.json"), f"BR mobile deveria usar variante da vila: {res}"
        await self.cdp.eval_js("window.__matchState.br.zoneTimer = 0.01")
        await asyncio.sleep(0.4)
        z = await self.cdp.eval_js("({ phase: window.__matchState.br.phase, r: window.__matchState.br.zoneR })")
        assert z["phase"] >= 1 and z["r"] < res["zoneR"], f"zona deveria encolher apos a fase: {z} (antes {res['zoneR']})"

    async def test_m09_rotate_overlay_restore_desktop(self):
        """M9: portrait -> overlay "gire o dispositivo"; restaura desktop no fim (higiene p/ proxima bateria)."""
        await self.cdp.send("Emulation.setDeviceMetricsOverride",
                            {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        await asyncio.sleep(0.6)
        ov = await self.cdp.eval_js("(() => { const o = document.getElementById('rotate-overlay'); return o ? getComputedStyle(o).display : 'missing'; })()")
        assert ov not in ("none", "missing"), f"rotate-overlay deveria aparecer em portrait: {ov}"
        await self.cdp.send("Emulation.clearUserAgentOverride")
        await self.cdp.send("Emulation.clearDeviceMetricsOverride")
        ok = await self._t5_wait_js("!(/iPhone/.test(navigator.userAgent))", tries=10, delay=0.3)
        assert ok, "clearUserAgentOverride nao aplicou (UA ainda iPhone)"
        await self.cdp.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
        ok = await self._t5_wait_js("typeof window.startMatch === 'function'")
        assert ok, "boot desktop nao subiu apos restore"
        ok = await self._t5_wait_js("!!window.__ARENA_LOADED", tries=30, delay=0.5)
        assert ok, "arena nao carregou no boot desktop do restore"
        res = await self.cdp.eval_js("""(() => ({
            isMobile: !!(window.__DEVICE && window.__DEVICE.isMobile),
            touchCls: document.body.classList.contains('touch'),
            vfxCap: window.__GOV ? window.__GOV.vfxCap : null,
            arena: window.__ARENA_LOADED.asset
        }))()""")
        assert res["isMobile"] is False, f"restore deveria voltar ao desktop: {res}"
        assert res["touchCls"] is False, f"body.touch nao deveria existir no desktop: {res}"
        assert res["vfxCap"] is None or res["vfxCap"] == float("inf"), f"desktop deveria ter vfxCap ilimitado: {res}"
        assert not str(res["arena"]).endswith(".mobile.json"), f"desktop deveria carregar arena FULL: {res}"

'''

CALLS = '''    # -------------------------------------------------------------------------
    # Tier 5 Tests — Mobile Pivot formal (PV1.6 + PV2.6)
    # -------------------------------------------------------------------------
    print("\\n--- Running Tier 5: Mobile Pivot (real touch via CDP) ---")
    await runner.run_test("T5_M01", "Mobile Emulation Boot (iPhone UA, 844x390)", "Tier 5", runner.test_m01_mobile_emulation_boot)
    await runner.run_test("T5_M02", "Governor + Arena .mobile.json Variant (PV3.1/PV3.2)", "Tier 5", runner.test_m02_governor_arena_variante)
    await runner.run_test("T5_M03", "3v3 Mobile Match (6 units, META 15, cluster grid)", "Tier 5", runner.test_m03_3v3_mobile)
    await runner.run_test("T5_M04", "Joystick Real Touch (dispatchTouchEvent, move +X)", "Tier 5", runner.test_m04_joystick_touch_real)
    await runner.run_test("T5_M05", "ATK Hold Touch (fire + ataque dispara)", "Tier 5", runner.test_m05_atk_hold_touch)
    await runner.run_test("T5_M06", "Skill Q Tap + CD Mirror #cdt-q (PV4)", "Tier 5", runner.test_m06_skill_q_touch_cd_mirror)
    await runner.run_test("T5_M07", "Chakra Hold Touch (INPUT.chakra)", "Tier 5", runner.test_m07_chakra_hold_touch)
    await runner.run_test("T5_M08", "Realeza na Vila Mobile (10 ninjas, zona, vila .mobile)", "Tier 5", runner.test_m08_br_vila_mobile)
    await runner.run_test("T5_M09", "Rotate Overlay Portrait + Desktop Restore", "Tier 5", runner.test_m09_rotate_overlay_restore_desktop)

'''

# --- conversao de separador (arquivo em CRLF) ---
METHODS = METHODS.replace('\n', sep)
CALLS = CALLS.replace('\n', sep)

# --- E1: metodos da classe (antes de run_suite, que e module-level) ---
anchor_def = 'async def run_suite():'
assert s.count(anchor_def) == 1, f'ancora run_suite: {s.count(anchor_def)}'
s = s.replace(anchor_def, METHODS + anchor_def, 1)

# --- E2: chamadas run_test apos o T4_S06 ---
anchor_s06 = '    await runner.run_test("T4_S06", "Match Results: Victory Board + MVP + Rematch", "Tier 4", runner.test_s06_match_results_mvp_flow)'
assert s.count(anchor_s06) == 1, f'ancora T4_S06: {s.count(anchor_s06)}'
s = s.replace(anchor_s06, anchor_s06 + sep + sep + CALLS.rstrip(sep), 1)

# --- E3: cabecalho/docstring/banner/mensagem final ---
old_doc = 'Covers Tiers 1 to 4:'
assert s.count(old_doc) == 1
s = s.replace(old_doc, 'Covers Tiers 1 to 5:', 1)

anchor_t4line = '  - Tier 4: Real-World Match Scenarios'
assert s.count(anchor_t4line) == 1
s = s.replace(anchor_t4line,
              anchor_t4line + sep +
              '  - Tier 5: Mobile Pivot (PV1.6/PV2.6 — touch real via CDP, 3v3/BR mobile, governor, arena .mobile.json)', 1)

old_banner = 'NUBA E2E TEST SUITE (Tiers 1 to 4)'
assert s.count(old_banner) == 1
s = s.replace(old_banner, 'NUBA E2E TEST SUITE (Tiers 1 to 5)', 1)

old_final = 'ALL E2E SUITE TESTS (TIERS 1-4) PASSED'
assert s.count(old_final) == 1
s = s.replace(old_final, 'ALL E2E SUITE TESTS (TIERS 1-5) PASSED', 1)

open(SUITE, 'w', encoding='utf-8', newline='').write(s)

py_compile.compile(SUITE, doraise=True)
print('[ok] Tier 5 inserido: 9 testes + helpers; suite compila (py_compile)')
print('[ok] cabecalho/banner/mensagem final -> Tiers 1 to 5')
print('PV1.6 TIER5 PATCH DONE')
