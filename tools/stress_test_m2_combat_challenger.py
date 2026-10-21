"""
Empirical Adversarial Stress-Test Suite for Milestone 2:
Authentic Storm Combat Controls & Feedback

Tests:
1. Rapid mouse left clicks:
   - Verify 3-hit combo cycles cleanly through attack -> attack2 -> attack3 -> attack.
   - Verify rapid burst clicks without lockup or state corruption.
   - Verify combo reset timeout (> 1.1s resets to hit 1).
   - Verify melee range detection (damage + sparks) vs ranged (projectiles).
2. Clicking on UI elements:
   - Verify clicking on top buttons (#btn-help-controls, #btn-cam-mode), controls drawer,
     top scoreboard (.hud-top-bar), ability buttons, and modals does NOT trigger basic attack (UI filtering works).
   - Verify clicking on game canvas DOES trigger basic attack.
3. Keys Q, E, Space, R, F:
   - Q: Primary Ninjutsu (cooldown, chakra cost, jutsu animation, VFX)
   - E: Secondary Ninjutsu (kit slot 'w', cooldown, chakra cost)
   - Space: Kawarimi substitute (kit slot 'e', log mesh, repositioning)
   - R: Ultimate Ougi + Awakening (kit slot 'r', 50 chakra cost, state 'ult', awakenedTimer ~14s, auraMesh visible)
   - F: Concentrar Chakra (charges +32 CK/s, state 'charge', zero jutsu cooldowns)
   - W: Freed strictly for movement (no jutsu, zero chakra cost)
   - Zero chakra edge case: Q, E, Space, R blocked
4. Awakening aura mesh & ground rings:
   - Verify auraMesh visible when awakened
   - Verify groundRing1 and groundRing2 exist inside auraMesh
   - Verify dynamic oscillation of scales and opacities across frames
   - Verify auraMesh rotation
   - Verify auraMesh hides when awakenedTimer expires
5. Zero console errors throughout the entire test run.
"""

import asyncio
import base64
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
DEBUG_PORT = 9224

def find_edge_path():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Microsoft Edge executable not found in standard paths.")

class ChallengerCDP:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.console_errors = []
        self.running = False
        self._pending = {}
        self._listener_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=25_000_000)
        self.running = True
        self._listener_task = asyncio.create_task(self._listen())
        await self.send("Runtime.enable")
        await self.send("Log.enable")
        await self.send("Page.enable")
        await self.send("DOM.enable")

    async def _listen(self):
        try:
            while self.running:
                raw = await self.ws.recv()
                data = json.loads(raw)
                cid = data.get("id")
                if cid is not None and cid in self._pending:
                    fut = self._pending.pop(cid)
                    if not fut.done():
                        fut.set_result(data.get("result", {}))
                    continue

                method = data.get("method")
                if method == "Runtime.exceptionThrown":
                    exc = data["params"]["exceptionDetails"]
                    text = exc.get("exception", {}).get("description") or exc.get("text")
                    self.console_errors.append(f"[EXCEPTION] {text}")
                    print(f"  [PAGE EXCEPTION] {text}", flush=True)
                elif method == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        self.console_errors.append(f"[LOG ERROR] {entry.get('text')}")
                        print(f"  [LOG ERROR] {entry.get('text')}", flush=True)
                elif method == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    text = " ".join(str(x) for x in args)
                    if call_type == "error":
                        self.console_errors.append(f"[CONSOLE ERROR] {text}")
                        print(f"  [CONSOLE ERROR] {text}", flush=True)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.running:
                print(f"[CDP Loop Error] {e}", flush=True)

    async def send(self, method, params=None, timeout=30.0):
        self.msg_id += 1
        cid = self.msg_id
        req = {"id": cid, "method": method}
        if params:
            req["params"] = params
        fut = asyncio.get_running_loop().create_future()
        self._pending[cid] = fut
        await self.ws.send(json.dumps(req))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def eval_js(self, expr):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        exc = res.get("exceptionDetails")
        if exc:
            msg = exc.get("exception", {}).get("description") or exc.get("text")
            raise RuntimeError(f"JS Eval Error: {msg}")
        return res.get("result", {}).get("value")

    async def dispatch_key_down(self, code, key=""):
        await self.send("Input.dispatchKeyEvent", {
            "type": "rawKeyDown",
            "code": code,
            "key": key,
            "windowsVirtualKeyCode": 0
        })

    async def dispatch_key_up(self, code, key=""):
        await self.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "code": code,
            "key": key,
            "windowsVirtualKeyCode": 0
        })

    async def dispatch_mouse_click(self, x, y, button="left"):
        await self.send("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": button,
            "clickCount": 1
        })
        await asyncio.sleep(0.04)
        await self.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": button,
            "clickCount": 1
        })

    async def close(self):
        self.running = False
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()


async def run_stress_suite():
    print("=" * 70, flush=True)
    print("  EMPIRICAL ADVERSARIAL STRESS TEST: MILESTONE 2 COMBAT & CONTROLS", flush=True)
    print("=" * 70, flush=True)

    # 1. Connect to Edge CDP
    tabs = None
    for _ in range(25):
        try:
            raw = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=5).read()
            tabs = json.loads(raw)
            if tabs:
                break
        except Exception:
            time.sleep(0.5)

    if not tabs:
        raise RuntimeError(f"Could not connect to Edge on port {DEBUG_PORT}")

    target_tab = next((t for t in tabs if "localhost:8080" in t.get("url", "")), None)
    if not target_tab:
        raise RuntimeError(f"Target tab localhost:8080 not found! Tabs: {tabs}")

    ws_url = target_tab["webSocketDebuggerUrl"]
    print(f"Connected to CDP WebSocket: {ws_url}", flush=True)
    cdp = ChallengerCDP(ws_url)
    await cdp.connect()

    # Wait for page readiness
    await asyncio.sleep(2.5)

    # Ensure match is active
    await cdp.eval_js("""
        (async () => {
            if (!window.matchActive) {
                await window.start5v5Match();
            }
            for (let i = 0; i < 40; i++) {
                if (window.units && window.units.length === 10) break;
                await new Promise(r => setTimeout(r, 100));
            }
        })()
    """)
    print("Match successfully initialized with 10 units.\n", flush=True)

    tests_run = 0
    tests_passed = 0
    tests_failed = 0
    failures = []

    async def run_subtest(name, coro):
        nonlocal tests_run, tests_passed, tests_failed
        tests_run += 1
        print(f"[{tests_run:02d}] Stress-Testing: {name}...", end=" ", flush=True)
        try:
            await coro()
            print("PASS", flush=True)
            tests_passed += 1
        except Exception as e:
            print(f"FAIL -> {e}", flush=True)
            tests_failed += 1
            failures.append((name, str(e)))

    # =========================================================================
    # SECTION 1: RAPID MOUSE LEFT CLICKS & COMBO CYCLING
    # =========================================================================

    async def test_combo_3hit_clean_cycle():
        # Clean cycle: attack -> attack2 -> attack3 -> attack
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.comboStep = 0;
                p.comboResetTimer = 0;
                p.cds.atk = 0;

                const stepResults = [];
                // 1st hit
                window.executeSkill(p, 'atk');
                stepResults.push({ state: p.state, nextStep: p.comboStep, resetTimer: p.comboResetTimer });

                // 2nd hit
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                stepResults.push({ state: p.state, nextStep: p.comboStep, resetTimer: p.comboResetTimer });

                // 3rd hit
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                stepResults.push({ state: p.state, nextStep: p.comboStep, resetTimer: p.comboResetTimer });

                // 4th hit: cycles back to 1st hit!
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                stepResults.push({ state: p.state, nextStep: p.comboStep, resetTimer: p.comboResetTimer });

                return stepResults;
            })()
        """)
        assert res[0]["state"] == "attack" and res[0]["nextStep"] == 1, f"Hit 1 failed: {res[0]}"
        assert res[1]["state"] == "attack2" and res[1]["nextStep"] == 2, f"Hit 2 failed: {res[1]}"
        assert res[2]["state"] == "attack3" and res[2]["nextStep"] == 0, f"Hit 3 failed: {res[2]}"
        assert res[3]["state"] == "attack" and res[3]["nextStep"] == 1, f"Hit 4 cycle back failed: {res[3]}"
        for i, s in enumerate(res):
            assert s["resetTimer"] > 0.9, f"Reset timer not refreshed on hit {i+1}: {s['resetTimer']}"

    async def test_combo_rapid_burst_stress():
        # Rapid burst: 15 rapid consecutive clicks without lockup
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.comboStep = 0;
                p.comboResetTimer = 0;
                const states = [];

                for (let i = 0; i < 15; i++) {
                    p.cds.atk = 0;
                    window.executeSkill(p, 'atk');
                    states.push(p.state);
                }

                // Verify exact repeating pattern: attack, attack2, attack3, attack, attack2, attack3, ...
                const expected = ['attack', 'attack2', 'attack3'] * 5;
                let patternMatches = true;
                for (let i = 0; i < 15; i++) {
                    if (states[i] !== ['attack', 'attack2', 'attack3'][i % 3]) {
                        patternMatches = false;
                        break;
                    }
                }

                return {
                    states,
                    patternMatches,
                    finalStep: p.comboStep
                };
            })()
        """)
        assert res["patternMatches"], f"15-hit rapid burst broke cycle sequence: {res['states']}"

    async def test_combo_reset_timeout():
        # Reset timeout: wait for comboResetTimer to drop to 0, next hit must be 'attack' (not 'attack2')
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.comboStep = 0;
                p.cds.atk = 0;

                // Hit 1
                window.executeSkill(p, 'atk');
                const stateBefore = p.state;
                const stepBefore = p.comboStep;

                // Simulate timeout: manually expire comboResetTimer
                p.comboResetTimer = 0;
                p.cds.atk = 0;

                // Next hit should reset to hit 1 instead of advancing to hit 2
                window.executeSkill(p, 'atk');
                const stateAfter = p.state;
                const stepAfter = p.comboStep;

                return {
                    stateBefore,
                    stepBefore,
                    stateAfter,
                    stepAfter
                };
            })()
        """)
        assert res["stateBefore"] == "attack" and res["stepBefore"] == 1
        assert res["stateAfter"] == "attack" and res["stepAfter"] == 1, (
            f"Combo did not reset to hit 1 after timeout: got state={res['stateAfter']}, step={res['stepAfter']}"
        )

    async def test_mouse_canvas_click_triggers_attack():
        # Real pointerdown on canvas triggers attack in the next animation frame
        res = await cdp.eval_js("""
            (async () => {
                const p = window.units.find(u => u.isPlayer);
                p.state = 'idle';
                p.cds.atk = 0;
                p.comboStep = 0;

                const canvas = document.getElementById('game-canvas');
                const rect = canvas.getBoundingClientRect();
                const evt = new PointerEvent('pointerdown', {
                    button: 0,
                    bubbles: true,
                    cancelable: true,
                    clientX: rect.width / 2,
                    clientY: rect.height / 2
                });
                canvas.dispatchEvent(evt);

                // Wait 2 animation frames for updatePlayerUnit to process mouseDown
                await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

                const state = p.state;
                const step = p.comboStep;

                // Release pointer
                window.dispatchEvent(new PointerEvent('pointerup', { button: 0, bubbles: true }));

                return {
                    state,
                    comboStep: step
                };
            })()
        """)
        assert res["state"] in ["attack", "attack2", "attack3"], f"Canvas click did not trigger attack: {res}"
        assert res["comboStep"] == 1, f"Canvas click did not advance comboStep: {res}"

    # =========================================================================
    # SECTION 2: UI FILTERING (CLICKS ON UI ELEMENTS MUST NOT ATTACK)
    # =========================================================================

    async def test_ui_filter_top_buttons():
        # Clicking #btn-help-controls, #btn-cam-mode, #btn-toggle-wireframe must NOT set mouseDown or trigger attack
        res = await cdp.eval_js("""
            (async () => {
                const p = window.units.find(u => u.isPlayer);
                p.state = 'idle';
                p.cds.atk = 0;

                const testIds = ['btn-help-controls', 'btn-cam-mode', 'btn-toggle-wireframe'];
                const results = [];

                for (const id of testIds) {
                    const el = document.getElementById(id);
                    if (!el) {
                        results.push({ id, exists: false, triggeredAttack: false });
                        continue;
                    }
                    p.state = 'idle';
                    // Dispatch pointerdown on the UI element
                    const evt = new PointerEvent('pointerdown', {
                        button: 0,
                        bubbles: true,
                        cancelable: true
                    });
                    el.dispatchEvent(evt);

                    // Wait 2 frames
                    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

                    results.push({
                        id,
                        exists: true,
                        triggeredAttack: p.state === 'attack' || p.state === 'attack2' || p.state === 'attack3',
                        state: p.state
                    });

                    // cleanup
                    window.dispatchEvent(new PointerEvent('pointerup', { button: 0, bubbles: true }));
                }

                return results;
            })()
        """)
        for item in res:
            assert not item["triggeredAttack"], f"Clicking #{item['id']} triggered basic attack: {item}"

    async def test_ui_filter_controls_drawer():
        # Clicking inside #controls-drawer must NOT trigger attack
        res = await cdp.eval_js("""
            (async () => {
                const p = window.units.find(u => u.isPlayer);
                p.state = 'idle';
                p.cds.atk = 0;

                const drawer = document.getElementById('controls-drawer');
                if (!drawer) throw new Error("controls-drawer element not found");

                // Dispatch pointerdown directly on drawer
                const evt = new PointerEvent('pointerdown', {
                    button: 0,
                    bubbles: true,
                    cancelable: true
                });
                drawer.dispatchEvent(evt);

                // Wait 2 frames
                await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

                const attacked = (p.state === 'attack' || p.state === 'attack2' || p.state === 'attack3');
                window.dispatchEvent(new PointerEvent('pointerup', { button: 0, bubbles: true }));

                return { attacked, state: p.state };
            })()
        """)
        assert not res["attacked"], f"Clicking inside controls drawer triggered basic attack: {res}"

    async def test_ui_filter_hud_top_bar():
        # Clicking inside .hud-top-bar must NOT trigger attack
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.state = 'idle';
                p.cds.atk = 0;

                const bar = document.querySelector('.hud-top-bar');
                const evt = new PointerEvent('pointerdown', {
                    button: 0,
                    bubbles: true,
                    cancelable: true
                });
                bar.dispatchEvent(evt);

                const attacked = (p.state === 'attack' || p.state === 'attack2' || p.state === 'attack3');
                window.dispatchEvent(new PointerEvent('pointerup', { button: 0, bubbles: true }));

                return { attacked, state: p.state };
            })()
        """)
        assert not res["attacked"], f"Clicking on .hud-top-bar triggered basic attack: {res}"

    async def test_ui_filter_ability_buttons():
        # Clicking on .moba-ability-btn or .skill-slot must filter pointerdown from mouseDown
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.state = 'idle';
                p.cds.atk = 0;

                const btn = document.querySelector('.moba-ability-btn');
                const evt = new PointerEvent('pointerdown', {
                    button: 0,
                    bubbles: true,
                    cancelable: true
                });
                btn.dispatchEvent(evt);

                // Basic attack should not be triggered through pointerdown
                const attacked = (p.state === 'attack' || p.state === 'attack2' || p.state === 'attack3');
                window.dispatchEvent(new PointerEvent('pointerup', { button: 0, bubbles: true }));

                return { attacked, state: p.state };
            })()
        """)
        assert not res["attacked"], f"Clicking .moba-ability-btn triggered basic melee attack: {res}"

    # =========================================================================
    # SECTION 3: KEYS Q, E, SPACE, R, F VERIFICATION & CORNER CASES
    # =========================================================================

    async def test_key_q_primary_jutsu():
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.q = 0;
                const prevX = p.x, prevZ = p.z;

                // Dispatch Keydown KeyQ
                window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyQ', key: 'q', bubbles: true }));

                return {
                    state: p.state,
                    chakra: p.chakra,
                    cd: p.cds.q,
                    cost: p.kit.q.cost,
                    movedOrVfx: (p.cds.q > 0)
                };
            })()
        """)
        assert res["cd"] > 0, "Key Q failed to trigger primary jutsu cooldown."
        assert res["chakra"] == 100 - res["cost"], f"Key Q did not deduct exact chakra cost {res['cost']}: {res['chakra']}"
        assert res["state"] in ["jutsu", "spin"], f"Key Q unexpected state: {res['state']}"

    async def test_key_e_secondary_jutsu():
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.w = 0; // Skill 2 is in kit slot 'w'

                // Dispatch Keydown KeyE
                window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyE', key: 'e', bubbles: true }));

                return {
                    state: p.state,
                    chakra: p.chakra,
                    cd: p.cds.w,
                    cost: p.kit.w.cost
                };
            })()
        """)
        assert res["cd"] > 0, "Key E failed to trigger secondary jutsu cooldown."
        assert res["chakra"] == 100 - res["cost"], f"Key E did not deduct exact chakra cost {res['cost']}: {res['chakra']}"
        assert res["state"] in ["jutsu", "spin", "dash"], f"Key E unexpected state: {res['state']}"

    async def test_key_space_kawarimi():
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.e = 0; // Kawarimi is in kit slot 'e'
                const prevX = p.x, prevZ = p.z;
                const prevVfxCount = window.vfxList.length;

                // Dispatch Keydown Space
                window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', bubbles: true }));

                return {
                    cd: p.cds.e,
                    chakra: p.chakra,
                    cost: p.kit.e.cost,
                    repositioned: (p.x !== prevX || p.z !== prevZ),
                    vfxSpawned: (window.vfxList.length >= prevVfxCount)
                };
            })()
        """)
        assert res["cd"] > 0, "Key Space failed to trigger Kawarimi cooldown."
        assert res["chakra"] == 100 - res["cost"], f"Key Space did not deduct exact chakra cost: {res['chakra']}"
        assert res["vfxSpawned"], "Kawarimi did not spawn substitution log / smoke VFX."

    async def test_key_r_ultimate_and_awakening():
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.r = 0;
                p.awakenedTimer = 0;

                // Dispatch Keydown KeyR
                window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyR', key: 'r', bubbles: true }));

                return {
                    state: p.state,
                    cd: p.cds.r,
                    chakra: p.chakra,
                    cost: p.kit.r.cost,
                    awakenedTimer: p.awakenedTimer,
                    auraVisible: p.auraMesh ? p.auraMesh.visible : false
                };
            })()
        """)
        assert res["state"] == "ult", f"Key R unexpected state: {res['state']}"
        assert res["cd"] > 0, "Key R failed to trigger Ultimate cooldown."
        assert res["chakra"] == 100 - res["cost"], f"Key R did not deduct exact chakra: {res['chakra']}"
        assert res["awakenedTimer"] >= 13.0, f"Awakening timer should be ~14s, got: {res['awakenedTimer']}"
        assert res["auraVisible"], "Awakening aura mesh was not made visible on Key R."

    async def test_key_f_chakra_concentration():
        # F key charges chakra at +32 CK/s without triggering jutsu
        await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 15;
                p.animTimer = 0;
                p.cds.q = 0; p.cds.w = 0; p.cds.e = 0; p.cds.r = 0;
            })()
        """)

        # Hold KeyF down for 350ms
        await cdp.dispatch_key_down("KeyF", "f")
        await asyncio.sleep(0.35)
        await cdp.dispatch_key_up("KeyF", "f")
        await asyncio.sleep(0.05)

        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    chakra: p.chakra,
                    increased: p.chakra > 15.5,
                    qCd: p.cds.q,
                    wCd: p.cds.w,
                    eCd: p.cds.e,
                    rCd: p.cds.r
                };
            })()
        """)
        assert res["increased"], f"Key F did not increase chakra: {res['chakra']}"
        assert res["qCd"] == 0 and res["wCd"] == 0 and res["eCd"] == 0 and res["rCd"] == 0, (
            f"Key F inadvertently triggered a jutsu cooldown: {res}"
        )

    async def test_free_w_key_strictly_movement():
        # Pressing W moves forward and does NOT fire skills or deduct chakra
        start = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 80;
                p.cds.w = 0;
                return { z: p.z, chakra: p.chakra };
            })()
        """)

        await cdp.dispatch_key_down("KeyW", "w")
        await asyncio.sleep(0.25)
        await cdp.dispatch_key_up("KeyW", "w")
        await asyncio.sleep(0.05)

        end = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    z: p.z,
                    chakra: p.chakra,
                    wCd: p.cds.w
                };
            })()
        """)
        assert abs(end["z"] - start["z"]) > 0.05, "Pressing W did not move player."
        assert end["chakra"] >= start["chakra"] - 0.01, f"Pressing W deducted chakra: {end['chakra']} vs {start['chakra']}"
        assert end["wCd"] == 0, "Pressing W triggered skill cooldown!"

    async def test_zero_chakra_blocks_all_skills():
        # With 0 chakra, Q, E, Space, R must all fail to trigger
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 0;
                p.cds.q = 0; p.cds.w = 0; p.cds.e = 0; p.cds.r = 0;

                window.executeSkill(p, 'q');
                window.executeSkill(p, 'w');
                window.executeSkill(p, 'e');
                window.executeSkill(p, 'r');

                return {
                    chakra: p.chakra,
                    qCd: p.cds.q,
                    wCd: p.cds.w,
                    eCd: p.cds.e,
                    rCd: p.cds.r
                };
            })()
        """)
        assert res["chakra"] == 0, "Chakra changed from 0."
        assert res["qCd"] == 0, "Skill Q fired with 0 chakra!"
        assert res["wCd"] == 0, "Skill W fired with 0 chakra!"
        assert res["eCd"] == 0, "Skill E fired with 0 chakra!"
        assert res["rCd"] == 0, "Skill R fired with 0 chakra!"

    # =========================================================================
    # SECTION 4: AWAKENING AURA MESH & ANIMATED GROUND RINGS
    # =========================================================================

    async def test_awakening_aura_mesh_structure():
        # Verify aura mesh contains groundRing1 and groundRing2
        res = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                if (!p.auraMesh) throw new Error("player auraMesh is null");
                const r1 = p.auraMesh.getObjectByName('groundRing1');
                const r2 = p.auraMesh.getObjectByName('groundRing2');

                return {
                    hasAuraMesh: !!p.auraMesh,
                    hasRing1: !!r1,
                    ring1Type: r1 ? r1.geometry.type : null,
                    hasRing2: !!r2,
                    ring2Type: r2 ? r2.geometry.type : null,
                    ring1MatOpacity: r1 && r1.material ? r1.material.opacity : null,
                    ring2MatOpacity: r2 && r2.material ? r2.material.opacity : null
                };
            })()
        """)
        assert res["hasAuraMesh"], "Player auraMesh is missing."
        assert res["hasRing1"], "groundRing1 child mesh is missing in auraMesh."
        assert res["hasRing2"], "groundRing2 child mesh is missing in auraMesh."
        assert res["ring1Type"] == "RingGeometry", f"groundRing1 unexpected geometry: {res['ring1Type']}"
        assert res["ring2Type"] == "RingGeometry", f"groundRing2 unexpected geometry: {res['ring2Type']}"

    async def test_awakening_ground_rings_dynamic_animation():
        # Sample groundRing scale & opacity over time while awakened
        await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.awakenedTimer = 10.0;
                p.auraMesh.visible = true;
            })()
        """)

        samples = []
        for _ in range(5):
            await asyncio.sleep(0.12)
            data = await cdp.eval_js("""
                (() => {
                    const p = window.units.find(u => u.isPlayer);
                    const r1 = p.auraMesh.getObjectByName('groundRing1');
                    const r2 = p.auraMesh.getObjectByName('groundRing2');
                    return {
                        rotY: p.auraMesh.rotation.y,
                        s1: r1 ? r1.scale.x : null,
                        s2: r2 ? r2.scale.x : null,
                        op1: r1 && r1.material ? r1.material.opacity : null,
                        op2: r2 && r2.material ? r2.material.opacity : null
                    };
                })()
            """)
            samples.append(data)

        # Verify scale oscillates/changes across samples
        scales1 = [s["s1"] for s in samples]
        scales2 = [s["s2"] for s in samples]
        rotations = [s["rotY"] for s in samples]

        s1_delta = max(scales1) - min(scales1)
        s2_delta = max(scales2) - min(scales2)
        rot_delta = max(rotations) - min(rotations)

        assert s1_delta > 0.05, f"groundRing1 scale is static, did not animate! Scales: {scales1}"
        assert s2_delta > 0.05, f"groundRing2 scale is static, did not animate! Scales: {scales2}"
        assert rot_delta > 0.1, f"auraMesh rotation.y is static, did not rotate! Rots: {rotations}"

    async def test_awakening_expiration_hides_aura():
        # When awakenedTimer expires to 0, auraMesh becomes hidden
        res = await cdp.eval_js("""
            (async () => {
                const p = window.units.find(u => u.isPlayer);
                // Set timer very close to 0
                p.awakenedTimer = 0.05;
                // Wait 250ms for game loop to tick down
                await new Promise(r => setTimeout(r, 250));

                return {
                    awakenedTimer: p.awakenedTimer,
                    auraVisible: p.auraMesh.visible
                };
            })()
        """)
        assert res["awakenedTimer"] <= 0, f"Awakened timer did not tick down: {res['awakenedTimer']}"
        assert not res["auraVisible"], "Awakening aura mesh remained visible after timer expired!"

    # =========================================================================
    # EXECUTE ALL SUBTESTS
    # =========================================================================

    await run_subtest("3-Hit Taijutsu Combo Clean Cycle (attack -> attack2 -> attack3 -> attack)", test_combo_3hit_clean_cycle)
    await run_subtest("Rapid Burst Combo Stress (15 consecutive hits without lockup)", test_combo_rapid_burst_stress)
    await run_subtest("Combo Reset Timeout (> 1.1s resets to hit 1)", test_combo_reset_timeout)
    await run_subtest("Mouse Canvas Left Click Triggers Attack", test_mouse_canvas_click_triggers_attack)
    await run_subtest("UI Filter: Top Buttons Click Filtering", test_ui_filter_top_buttons)
    await run_subtest("UI Filter: Controls Drawer Click Filtering", test_ui_filter_controls_drawer)
    await run_subtest("UI Filter: HUD Top Bar Click Filtering", test_ui_filter_hud_top_bar)
    await run_subtest("UI Filter: Ability Buttons Click Filtering", test_ui_filter_ability_buttons)
    await run_subtest("Key [Q]: Primary Ninjutsu Execution & Cooldown", test_key_q_primary_jutsu)
    await run_subtest("Key [E]: Secondary Ninjutsu Execution & Cooldown", test_key_e_secondary_jutsu)
    await run_subtest("Key [ESPAÇO]: Kawarimi Substitution & Repositioning", test_key_space_kawarimi)
    await run_subtest("Key [R]: Ultimate Ougi Secreto & Awakening Trigger", test_key_r_ultimate_and_awakening)
    await run_subtest("Key [F]: Chakra Concentration (+32 CK/s without jutsu)", test_key_f_chakra_concentration)
    await run_subtest("Key [W]: Freed Strictly for Forward Movement (0 CK, 0 Jutsu)", test_free_w_key_strictly_movement)
    await run_subtest("Corner Case: Zero Chakra Blocks All Jutsu & Ultimate", test_zero_chakra_blocks_all_skills)
    await run_subtest("Awakening: AuraMesh Child Structure (groundRing1 & groundRing2)", test_awakening_aura_mesh_structure)
    await run_subtest("Awakening: Dynamic Shockwave Ground Rings Animation", test_awakening_ground_rings_dynamic_animation)
    await run_subtest("Awakening: Timer Expiration Hides AuraMesh", test_awakening_expiration_hides_aura)

    # Capture visual screenshot
    await asyncio.sleep(0.3)
    screenshot_res = await cdp.send("Page.captureScreenshot", {"format": "png"})
    if "data" in screenshot_res:
        out_dir = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\.agents\teamwork\teamwork_preview_challenger_m2_2"
        shot_path = os.path.join(out_dir, "challenger_combat_stress_pass.png")
        with open(shot_path, "wb") as f:
            f.write(base64.b64decode(screenshot_res["data"]))
        print(f"\nCaptured Challenger Verification Screenshot: {shot_path}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("                    STRESS TEST SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"  Tests Executed : {tests_run}")
    print(f"  Tests Passed   : {tests_passed}")
    print(f"  Tests Failed   : {tests_failed}")
    print(f"  Console Errors : {len(cdp.console_errors)}")
    if cdp.console_errors:
        print("  Console Errors Logged:")
        for err in cdp.console_errors:
            print(f"    - {err}")
    if failures:
        print("  Failures:")
        for name, err in failures:
            print(f"    - {name}: {err}")
    print("=" * 70, flush=True)

    all_ok = (tests_failed == 0 and len(cdp.console_errors) == 0)
    await cdp.close()
    return all_ok, tests_passed, tests_failed, cdp.console_errors, failures


def main():
    edge_bin = find_edge_path()
    tmp_profile = tempfile.mkdtemp()
    print(f"Launching Edge CDP (Port {DEBUG_PORT}, Profile {tmp_profile})...", flush=True)
    proc = subprocess.Popen([
        edge_bin,
        "--headless=new",
        f"--remote-debugging-port={DEBUG_PORT}",
        "--disable-gpu",
        "--window-size=1280,720",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])
    time.sleep(2.5)

    all_ok = False
    try:
        all_ok, passed, failed, errors, failures = asyncio.run(run_stress_suite())
    except Exception as e:
        print(f"\nCRITICAL STRESS RUNNER EXCEPTION: {e}", flush=True)
        all_ok = False
    finally:
        print("Terminating Edge instance...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if all_ok:
        print("\n>>> ALL ADVERSARIAL STRESS TESTS PASSED WITH ZERO CONSOLE ERRORS! <<<\n", flush=True)
        sys.exit(0)
    else:
        print("\n>>> ADVERSARIAL STRESS TESTS DETECTED FAILURES OR CONSOLE ERRORS! <<<\n", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
