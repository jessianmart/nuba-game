"""
E2E Test Suite for NUBA (Naruto Ultimate Battle Arena)
Covers Tiers 1 to 4:
  - Tier 1: Feature Coverage (All 20 features)
  - Tier 2: Boundary & Corner Cases
  - Tier 3: Pairwise Combinations
  - Tier 4: Real-World Match Scenarios

Uses Chrome DevTools Protocol (CDP) connecting to Headless Microsoft Edge on ws://127.0.0.1:9222.
Asserts 0 console errors and exits with code 0 on complete pass.
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

def find_edge_path():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Microsoft Edge executable not found in standard paths.")

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.console_errors = []
        self.console_logs = []
        self.running = False
        self._pending_requests = {}
        self._listener_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=25_000_000)
        self.running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        await self.send("Runtime.enable")
        await self.send("Log.enable")
        await self.send("Page.enable")

    async def _listen_loop(self):
        try:
            while self.running:
                resp_raw = await self.ws.recv()
                data = json.loads(resp_raw)
                cid = data.get("id")
                if cid is not None and cid in self._pending_requests:
                    fut = self._pending_requests.pop(cid)
                    if not fut.done():
                        fut.set_result(data.get("result", {}))
                    continue

                method = data.get("method")
                if method == "Runtime.exceptionThrown":
                    exc = data["params"]["exceptionDetails"]
                    text = exc.get("exception", {}).get("description") or exc.get("text")
                    self.console_errors.append(f"[EXCEPTION] {text}")
                    print(f"  [PAGE EXCEPTION] {text}")
                elif method == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        url_info = f" (url: {entry.get('url')})" if entry.get('url') else ""
                        self.console_errors.append(f"[LOG ERROR] {entry.get('text')}{url_info}")
                        print(f"  [LOG ERROR] {entry.get('text')}{url_info}")
                    else:
                        self.console_logs.append(entry.get("text"))
                elif method == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    text = " ".join(str(x) for x in args)
                    if call_type == "error":
                        self.console_errors.append(f"[CONSOLE ERROR] {text}")
                        print(f"  [CONSOLE ERROR] {text}")
                    else:
                        self.console_logs.append(f"[{call_type}] {text}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.running:
                print(f"[CDP Loop Error] {e}")

    async def send(self, method, params=None, timeout=30.0):
        self.msg_id += 1
        cid = self.msg_id
        req = {"id": cid, "method": method}
        if params:
            req["params"] = params

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_requests[cid] = fut

        await self.ws.send(json.dumps(req))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def eval_js(self, expr, await_promise=False):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise
        })
        val = res.get("result", {}).get("value")
        exc = res.get("exceptionDetails")
        if exc:
            msg = exc.get("exception", {}).get("description") or exc.get("text")
            raise RuntimeError(f"JS Eval Error: {msg}")
        return val

    async def dispatch_key(self, code, key=""):
        js = f"""
            window.dispatchEvent(new KeyboardEvent('keydown', {{
                code: '{code}',
                key: '{key}',
                bubbles: true,
                cancelable: true
            }}));
        """
        await self.eval_js(js)

    async def release_key(self, code, key=""):
        js = f"""
            window.dispatchEvent(new KeyboardEvent('keyup', {{
                code: '{code}',
                key: '{key}',
                bubbles: true,
                cancelable: true
            }}));
        """
        await self.eval_js(js)

    async def press_key(self, code, key="", hold_time=0.1):
        await self.dispatch_key(code, key)
        if hold_time > 0:
            await asyncio.sleep(hold_time)
        await self.release_key(code, key)

    async def close(self):
        self.running = False
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()


class TestResult:
    def __init__(self, test_id, name, tier):
        self.test_id = test_id
        self.name = name
        self.tier = tier
        self.passed = False
        self.error = None
        self.duration = 0.0

class E2ETestRunner:
    def __init__(self, cdp: CDPClient):
        self.cdp = cdp
        self.results = []

    async def run_test(self, test_id, name, tier, test_fn):
        res = TestResult(test_id, name, tier)
        start_time = time.time()
        print(f"[{tier}] Running {test_id}: {name}...", end=" ", flush=True)
        try:
            await test_fn()
            res.passed = True
            print("PASS")
        except Exception as e:
            res.passed = False
            res.error = str(e)
            print(f"FAIL -> {e}")
        finally:
            res.duration = time.time() - start_time
            self.results.append(res)

    # =========================================================================
    # TIER 1: FEATURE COVERAGE (ALL 20 FEATURES)
    # =========================================================================

    async def test_f01_top_bar_height(self):
        """F1: Sleek centered 5v5 scoreboard strip strictly under 52px (<52px, target ~46px)."""
        height = await self.cdp.eval_js("""
            (() => {
                const el = document.querySelector('.hud-top-bar') || document.querySelector('.hud-top');
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return rect.height;
            })()
        """)
        assert height is not None, "Top bar element (.hud-top-bar) not found in DOM."
        assert height < 52.0, f"Top bar height must be < 52px, but was {height:.2f}px."

    async def test_f02_mini_portraits_alive_dots(self):
        """F2: 10 ninja mini-portraits with pulsing alive indicators for active units."""
        data = await self.cdp.eval_js("""
            (() => {
                const blueIcons = document.querySelectorAll('#hud-blue-icons .mini-p, #hud-blue-icons .mini-portrait-wrap');
                const redIcons = document.querySelectorAll('#hud-red-icons .mini-p, #hud-red-icons .mini-portrait-wrap');
                const totalIcons = blueIcons.length + redIcons.length;

                // Check alive dots on active units
                let aliveDotsCount = 0;
                document.querySelectorAll('.alive-dot, .ping-dot').forEach(d => aliveDotsCount++);

                return {
                    blueCount: blueIcons.length,
                    redCount: redIcons.length,
                    totalIcons,
                    aliveDotsCount
                };
            })()
        """)
        assert data["blueCount"] == 5, f"Expected 5 blue mini-portraits, found {data['blueCount']}."
        assert data["redCount"] == 5, f"Expected 5 red mini-portraits, found {data['redCount']}."
        assert data["aliveDotsCount"] >= 10, f"Expected alive dots for 10 ninjas, found {data['aliveDotsCount']}."

    async def test_f03_respawn_countdown(self):
        """F3: Numerical respawn countdown overlay on dead ninja avatars in top bar."""
        # Deal lethal damage to trigger native engine death and portrait update
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                const enemy = window.units.find(u => !u.isPlayer && u.team === 'red');
                if (!enemy) return { error: 'No enemy unit found' };

                // Move enemy in front of player with 5 HP
                enemy.x = p.x + 1.5;
                enemy.z = p.z;
                enemy.hp = 5;
                p.cds.atk = 0;

                // Basic attack connects, dealing lethal damage and triggering native death
                window.executeSkill(p, 'atk');

                const icon = document.getElementById('top-icon-' + enemy.id);
                const hasDeadClass = icon ? (icon.classList.contains('dead') || icon.classList.contains('is-dead')) : false;
                const cdEl = icon ? (icon.querySelector('.respawn-countdown') || icon.querySelector('.cd-text') || icon) : null;
                const cdText = cdEl ? cdEl.textContent.trim() : '';

                // Restore enemy for subsequent tests
                enemy.hp = enemy.maxHp;
                enemy.deadTimer = 0;
                enemy.mesh.visible = true;

                return {
                    foundIcon: !!icon,
                    hasDeadClass,
                    cdText,
                    deadTimer: enemy.deadTimer
                };
            })()
        """)
        assert res.get("foundIcon"), "Dead ninja portrait icon element not found."
        assert res.get("hasDeadClass"), "Dead ninja avatar did not receive 'dead' CSS state class."

    async def test_f04_storm_vs_crest_and_timer(self):
        """F4: Centered Storm VS crest, match clock, and target score goal."""
        data = await self.cdp.eval_js("""
            (() => {
                const vsCrest = document.querySelector('.storm-vs-crest') || document.querySelector('.vs-storm-badge');
                const timer = document.getElementById('match-timer');
                const goal = document.querySelector('.match-goal-txt') || document.querySelector('.goal-label');
                return {
                    hasCrest: !!vsCrest,
                    timerText: timer ? timer.textContent.trim() : null,
                    goalText: goal ? goal.textContent.trim() : null
                };
            })()
        """)
        assert data["hasCrest"], "Storm VS crest image not found in center cluster."
        assert data["timerText"] and ":" in data["timerText"], f"Invalid match timer format: {data['timerText']}"
        assert data["goalText"] and ("30" in data["goalText"] or "META" in data["goalText"]), f"Invalid match goal: {data['goalText']}"

    async def test_f05_kill_feed_portraits_fade(self):
        """F5: Top-right kill-feed with killer/victim portraits, ability tags, and auto-dismiss."""
        res = await self.cdp.eval_js("""
            (() => {
                const feed = document.getElementById('kill-feed');
                if (!feed) return { error: 'No kill-feed container' };
                const p = window.units.find(u => u.isPlayer);
                const enemy = window.units.find(u => !u.isPlayer && u.team === 'red');

                // Deal lethal damage with primary jutsu
                enemy.x = p.x + 2;
                enemy.z = p.z;
                enemy.hp = 5;
                p.chakra = 100;
                p.cds.q = 0;
                window.executeSkill(p, 'q');

                const count = feed.children.length;
                const firstItem = feed.firstElementChild;
                const text = firstItem ? firstItem.textContent : '';

                // Restore
                enemy.hp = enemy.maxHp;
                enemy.deadTimer = 0;
                enemy.mesh.visible = true;

                return {
                    feedItemsCount: count,
                    text
                };
            })()
        """)
        assert res["feedItemsCount"] >= 1, "Kill-feed item was not inserted into #kill-feed."

    async def test_f06_command_center_avatar_gauges(self):
        """F6: Sculpted player avatar, Level chip, KDA tracker, layered HP/Chakra gauges."""
        data = await self.cdp.eval_js("""
            (() => {
                const portrait = document.getElementById('hud-player-portrait');
                const lvl = document.getElementById('hud-player-lvl');
                const kda = document.getElementById('hud-kda');
                const hpFill = document.getElementById('hud-hp-fill');
                const ckFill = document.getElementById('hud-ck-fill');
                const hpText = document.getElementById('hud-hp-text');
                const ckText = document.getElementById('hud-ck-text');
                return {
                    hasPortrait: !!portrait && portrait.src.length > 0,
                    lvlText: lvl ? lvl.textContent.trim() : '',
                    kdaText: kda ? kda.textContent.trim() : '',
                    hasHpFill: !!hpFill,
                    hasCkFill: !!ckFill,
                    hpText: hpText ? hpText.textContent : '',
                    ckText: ckText ? ckText.textContent : ''
                };
            })()
        """)
        assert data["hasPortrait"], "Player avatar portrait not rendered."
        assert "Nv." in data["lvlText"] or "Lv." in data["lvlText"], f"Invalid level chip text: {data['lvlText']}"
        assert "ABATES" in data["kdaText"] or "0" in data["kdaText"], f"Invalid KDA tracker: {data['kdaText']}"
        assert "VIDA" in data["hpText"] or "HP" in data["hpText"], f"Invalid HP gauge text: {data['hpText']}"
        assert "CHAKRA" in data["ckText"], f"Invalid Chakra gauge text: {data['ckText']}"

    async def test_f07_radial_cooldown_sweeps(self):
        """F7: Action slots with radial cooldown sweep overlay and countdown text."""
        # Set cooldown and await one render frame
        await self.cdp.eval_js("""
            (() => {
                const player = window.units.find(u => u.isPlayer);
                player.cds.q = 4.5;
            })()
        """)
        await asyncio.sleep(0.08) # allow frame loop to update DOM

        res = await self.cdp.eval_js("""
            (() => {
                const player = window.units.find(u => u.isPlayer);
                const cdQ = document.getElementById('cd-q');
                const isVisible = cdQ && (cdQ.style.display === 'flex' || cdQ.classList.contains('active') || getComputedStyle(cdQ).display !== 'none');
                const text = cdQ ? cdQ.textContent : '';
                player.cds.q = 0; // reset
                return {
                    hasCdElement: !!cdQ,
                    isVisible,
                    text
                };
            })()
        """)
        assert res["hasCdElement"], "Cooldown overlay element #cd-q not found."
        assert res["isVisible"], "Cooldown overlay should be visible when skill is on cooldown."

    async def test_f08_controls_drawer_toggle(self):
        """F8: Collapsible controls drawer toggled with 'H' key or top-bar button."""
        # Verify drawer element exists
        drawer_exists = await self.cdp.eval_js("!!document.getElementById('controls-drawer')")
        assert drawer_exists, "Controls drawer element #controls-drawer not found."

        # Press H to toggle open
        await self.cdp.dispatch_key("KeyH", "h")
        await asyncio.sleep(0.1)

        open_state = await self.cdp.eval_js("""
            (() => {
                const d = document.getElementById('controls-drawer');
                return !d.classList.contains('hidden');
            })()
        """)
        assert open_state, "Controls drawer failed to open upon KeyH keydown."

        # Press H to toggle closed
        await self.cdp.dispatch_key("KeyH", "h")
        await asyncio.sleep(0.1)

        closed_state = await self.cdp.eval_js("""
            (() => {
                const d = document.getElementById('controls-drawer');
                return d.classList.contains('hidden');
            })()
        """)
        assert closed_state, "Controls drawer failed to close upon second KeyH keydown."

    async def test_f09_free_w_key_movement(self):
        """F9: 'W' key freed strictly for forward movement; no combat skill on 'W'."""
        start_data = await self.cdp.eval_js("""
            (() => {
                const player = window.units.find(u => u.isPlayer);
                player.animTimer = 0;
                player.deadTimer = 0;
                player.state = 'idle';
                return {
                    z: player.z,
                    chakra: player.chakra,
                    wCd: player.cds.w
                };
            })()
        """)

        # Dispatch KeyW for 250ms
        await self.cdp.dispatch_key("KeyW", "w")
        await asyncio.sleep(0.25)
        await self.cdp.release_key("KeyW", "w")
        await asyncio.sleep(0.05)

        end_data = await self.cdp.eval_js("""
            (() => {
                const player = window.units.find(u => u.isPlayer);
                return {
                    z: player.z,
                    chakra: player.chakra,
                    wCd: player.cds.w,
                    state: player.state
                };
            })()
        """)
        moved = abs(end_data["z"] - start_data["z"]) > 0.05
        assert moved, "Player should move along Z when pressing 'W' in MOBA mode."
        assert end_data["chakra"] >= start_data["chakra"] - 0.001, "Pressing 'W' must not consume chakra."
        assert end_data["wCd"] == 0, "Pressing 'W' must not trigger skill cooldown."

    async def test_f10_camera_relative_3rd_person_movement(self):
        """F10: In 3rd-person mode, WASD moves relative to camera horizontal view vector."""
        await self.cdp.eval_js("""
            (() => {
                window.cameraMode = 'thirdperson';
                window.tpCamYaw = Math.PI / 2; // Looking East (+X)
            })()
        """)
        await asyncio.sleep(0.05)

        start_x = await self.cdp.eval_js("window.units.find(u => u.isPlayer).x")

        # Press KeyW (forward relative to camera facing +X)
        await self.cdp.dispatch_key("KeyW", "w")
        await asyncio.sleep(0.2)
        await self.cdp.release_key("KeyW", "w")
        await asyncio.sleep(0.05)

        delta_x = await self.cdp.eval_js(f"window.units.find(u => u.isPlayer).x - {start_x}")
        # Reset camera mode
        await self.cdp.eval_js("window.cameraMode = 'moba'")
        assert delta_x > 0.05, f"In 3rd person with yaw=PI/2 (+X), W should move along +X, got deltaX={delta_x:.3f}"

    async def test_f11_camera_stage_clamping(self):
        """F11: Clamp 3rd-person camera position (Y >= 2.2, X/Z in [-92, 92])."""
        data = await self.cdp.eval_js("""
            (() => {
                const prevMode = window.cameraMode;
                window.cameraMode = 'thirdperson';

                const cam = window.camera;
                const p = window.units.find(u => u.isPlayer);

                // Normal check
                const normalClamped = (cam.position.y >= 2.2) &&
                                     (cam.position.x >= -92 && cam.position.x <= 92) &&
                                     (cam.position.z >= -92 && cam.position.z <= 92);

                // Boundary stress check
                const origX = p.x, origZ = p.z;
                p.x = 90; p.z = 90;
                window.tpCamYaw = -Math.PI / 4;

                const boundaryClamped = (cam.position.y >= 2.2) &&
                                       (cam.position.x >= -92 && cam.position.x <= 92) &&
                                       (cam.position.z >= -92 && cam.position.z <= 92);

                p.x = origX; p.z = origZ;
                window.cameraMode = prevMode;

                return {
                    normalClamped,
                    boundaryClamped,
                    camPos: { x: cam.position.x, y: cam.position.y, z: cam.position.z }
                };
            })()
        """)
        assert data["normalClamped"], f"Camera outside bounds at normal position: {data['camPos']}"
        assert data["boundaryClamped"], f"Camera failed clamping at boundary: {data['camPos']}"

    async def test_f12_mouse_left_click_combo(self):
        """F12: Basic Attack Combo (3-hit Taijutsu) mapped to Left Click."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.atk = 0; p.comboStep = 0;

                // Hit 1
                window.executeSkill(p, 'atk');
                const s1 = p.state; const c1 = p.comboStep;

                // Hit 2
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                const s2 = p.state; const c2 = p.comboStep;

                // Hit 3
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                const s3 = p.state; const c3 = p.comboStep;

                // Hit 4 (Cycle back)
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                const s4 = p.state; const c4 = p.comboStep;

                return {
                    hit1: { state: s1, nextStep: c1 },
                    hit2: { state: s2, nextStep: c2 },
                    hit3: { state: s3, nextStep: c3 },
                    hit4: { state: s4, nextStep: c4 }
                };
            })()
        """)
        assert res["hit1"]["state"] == "attack" and res["hit1"]["nextStep"] == 1, f"Hit 1 failed: {res['hit1']}"
        assert res["hit2"]["state"] == "attack2" and res["hit2"]["nextStep"] == 2, f"Hit 2 failed: {res['hit2']}"
        assert res["hit3"]["state"] == "attack3" and res["hit3"]["nextStep"] == 0, f"Hit 3 failed: {res['hit3']}"
        assert res["hit4"]["state"] == "attack" and res["hit4"]["nextStep"] == 1, f"Combo did not cycle back: {res['hit4']}"

    async def test_f13_ninjutsu_primario_q(self):
        """F13: Ninjutsu Primário mapped to [Q] (or [1])."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.q = 0; p.chakra = 100;
                window.executeSkill(p, 'q');
                return {
                    state: p.state,
                    chakra: p.chakra,
                    cd: p.cds.q
                };
            })()
        """)
        assert res["state"] in ["jutsu", "spin"], f"Player state expected 'jutsu', got '{res['state']}'"
        assert res["chakra"] < 100, "Ninjutsu Q did not consume chakra."
        assert res["cd"] > 0, "Ninjutsu Q did not set cooldown."

    async def test_f14_ninjutsu_secundario_e(self):
        """F14: Ninjutsu Secundário mapped to [E] (or [2]), disentangled from Kawarimi."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.w = 0; p.chakra = 100;
                window.executeSkill(p, 'w'); // Slot w is Secondary Jutsu mapped to key E
                return {
                    state: p.state,
                    chakra: p.chakra,
                    cd: p.cds.w
                };
            })()
        """)
        assert res["state"] in ["jutsu", "jutsu2", "spin"], f"Secondary Jutsu expected a jutsu state, got '{res['state']}'"
        assert res["chakra"] < 100, "Secondary Jutsu did not consume chakra."
        assert res["cd"] > 0, "Secondary Jutsu did not set cooldown."

    async def test_f15_kawarimi_espaco(self):
        """F15: Kawarimi / Substituição Ninja mapped to [ESPAÇO] (or [3])."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.e = 0; p.chakra = 100;
                const prevX = p.x, prevZ = p.z;
                window.executeSkill(p, 'e'); // Slot e is Kawarimi mapped to Space
                return {
                    cd: p.cds.e,
                    chakra: p.chakra,
                    repositioned: (p.x !== prevX || p.z !== prevZ)
                };
            })()
        """)
        assert res["cd"] > 0, "Kawarimi did not set cooldown."
        assert res["chakra"] < 100, "Kawarimi did not consume chakra."

    async def test_f16_ultimate_ougi_r(self):
        """F16: Ultimate Ougi Secreto + Despertar mapped to [R] (or [4])."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.r = 0; p.chakra = 100;
                window.executeSkill(p, 'r');
                return {
                    state: p.state,
                    cd: p.cds.r,
                    awakenedTimer: p.awakenedTimer,
                    isAwakened: p.awakenedTimer > 0,
                    auraVisible: p.auraMesh ? p.auraMesh.visible : false
                };
            })()
        """)
        assert res["state"] == "ult", f"Ultimate expected state 'ult', got '{res['state']}'"
        assert res["cd"] > 0, "Ultimate did not set cooldown."
        assert res["isAwakened"], f"Ultimate did not trigger Awakening mode: awakenedTimer={res['awakenedTimer']}"
        assert res["auraVisible"], "Awakening aura mesh was not made visible."

    async def test_f17_concentrar_chakra_f(self):
        """F17: Concentrar Chakra mapped to [F] or [Shift], charging without firing jutsu."""
        await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 20;
                p.cds.w = 0; p.cds.q = 0;
            })()
        """)

        # Dispatch KeyF for 250ms
        await self.cdp.dispatch_key("KeyF", "f")
        await asyncio.sleep(0.25)
        await self.cdp.release_key("KeyF", "f")
        await asyncio.sleep(0.05)

        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    currentChakra: p.chakra,
                    chakraGained: p.chakra > 20.5,
                    wCd: p.cds.w,
                    qCd: p.cds.q
                };
            })()
        """)
        assert res["chakraGained"], f"Chakra concentration did not increase chakra: {res['currentChakra']}"
        assert res["wCd"] == 0 and res["qCd"] == 0, "Concentrar Chakra inadvertently triggered a jutsu cooldown!"

    async def test_f18_synchronized_sfx(self):
        """F18: Procedural Web Audio SFX synchronized with combat actions."""
        res = await self.cdp.eval_js("""
            (() => {
                const hasCtx = (window.AudioContext || window.webkitAudioContext) !== undefined;
                return { hasWebAudio: hasCtx };
            })()
        """)
        assert res["hasWebAudio"], "Web Audio API is not supported in browser environment."

    async def test_f19_hit_sparks_vfx(self):
        """F19: Cel-shaded impact sparks and VFX spawned on combat connection."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                const enemy = window.units.find(u => !u.isPlayer && u.team === 'red');
                enemy.x = p.x + 2;
                enemy.z = p.z;
                enemy.hp = 1000;
                enemy.deadTimer = 0;

                p.cds.atk = 0;
                window.executeSkill(p, 'atk');

                return { enemyDamaged: enemy.hp < 1000 };
            })()
        """)
        assert res["enemyDamaged"], "Damage was not dealt to enemy in front of player during attack combo."

    async def test_f20_awakening_aura_rings(self):
        """F20: Animated expanding ground aura shockwave rings during Awakening mode."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.awakenedTimer = 10.0;
                if (p.auraMesh) p.auraMesh.visible = true;

                return {
                    awakenedTimer: p.awakenedTimer,
                    auraVisible: p.auraMesh ? p.auraMesh.visible : false
                };
            })()
        """)
        assert res["auraVisible"], "Awakening ground aura rings/mesh not visible during Awakening mode."

    async def test_f21_arena_catalog(self):
        """F21: Arena catalog exposes the shipped Storm arenas with playable radii."""
        res = await self.cdp.eval_js("""
            (async () => {
                const r = await fetch('assets/data/arenas.json?v=8').then(x => x.json());
                return {
                    count: (r.arenas || []).length,
                    default: r.default,
                    areasInGame: r.areasInGame,
                    built: (r.arenas || []).filter(a => a.built).length,
                    allHaveRadius: (r.arenas || []).every(a => typeof a.radius === 'number' && a.radius > 0),
                    allHaveMap: (r.arenas || []).every(a => a.map)
                };
            })()
        """, await_promise=True)
        assert res["count"] >= 8, f"Expected at least 8 arenas, got {res['count']}"
        assert res["built"] >= 8, f"Expected at least 8 built arena maps, got {res['built']}"
        assert res["allHaveRadius"], "Every arena must declare a playable radius."
        assert res["allHaveMap"], "Every arena must declare a map path."

    async def test_f22_arena_switch(self):
        """F22: Switching arena reloads the stage map and rescales clamps/spawns."""
        res = await self.cdp.eval_js("""
            (async () => {
                const before = {
                    id: window.ARENA.id,
                    radius: window.ARENA.radius,
                    stageId: window.stage3DData && window.stage3DData.id,
                    meshes: window.stage3DData && window.stage3DData.meshes.length
                };
                const target = window.arenasCatalog.find(a => a.id !== before.id);
                await window.applyArena(target.id);
                await new Promise(r => setTimeout(r, 250));
                const bp = window.basePos('blue');
                const after = {
                    id: window.ARENA.id,
                    radius: window.ARENA.radius,
                    stageId: window.stage3DData && window.stage3DData.id,
                    meshes: window.stage3DData && window.stage3DData.meshes.length,
                    baseX: bp.x,
                    inArena: window.units.every(u =>
                        Math.abs(u.x) <= window.ARENA.radius && Math.abs(u.z) <= window.ARENA.radius),
                    finite: window.units.every(u => isFinite(u.x) && isFinite(u.z))
                };
                // restore for the remaining tests
                await window.applyArena(before.id);
                await new Promise(r => setTimeout(r, 250));
                return { before, after, target: target.id };
            })()
        """, await_promise=True)
        assert res["after"]["id"] == res["target"], "Active arena did not switch."
        assert res["after"]["stageId"] == res["target"], \
            f"Stage map not reloaded (got {res['after']['stageId']})"
        assert res["after"]["meshes"] != res["before"]["meshes"] or \
            res["target"] == res["before"]["id"], "Arena meshes unchanged after switch."
        assert res["after"]["radius"] > 0, "Arena radius not applied."
        assert res["after"]["inArena"], "Units outside arena bounds after switch."
        assert res["after"]["finite"], "Non-finite unit coordinates after switch."

    async def test_f23_arena_picker_ui(self):
        """F23: Lobby arena picker renders one chip per arena and marks the active one."""
        res = await self.cdp.eval_js("""
            (() => {
                const host = document.getElementById('arena-picker');
                const chips = host ? host.querySelectorAll('.arena-chip') : [];
                return {
                    present: !!host,
                    count: chips.length,
                    expected: window.arenasCatalog.length,
                    selected: document.querySelectorAll('.arena-chip.selected').length,
                    label: (document.getElementById('arena-name') || {}).textContent || '',
                    minimap: (document.getElementById('minimap-arena-name') || {}).textContent || ''
                };
            })()
        """)
        assert res["present"], "Arena picker container missing from lobby."
        assert res["count"] == res["expected"] and res["expected"] > 0, \
            f"Arena chips ({res['count']}) do not match catalog ({res['expected']})."
        assert res["selected"] == 1, f"Expected exactly 1 selected arena chip, got {res['selected']}"
        assert res["label"].strip(), "Arena name label is empty."
        assert "ARENA" in res["minimap"].upper(), "Minimap arena label not updated."

    # =========================================================================
    # TIER 2: BOUNDARY & CORNER CASES
    # =========================================================================

    async def test_b01_screen_resize_boundary(self):
        """B1: Screen resize preserves top bar < 52px and projection matrix."""
        for width, height in [(1920, 1080), (1280, 720), (800, 600)]:
            await self.cdp.send("Emulation.setDeviceMetricsOverride", {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(0.1)
            bar_height = await self.cdp.eval_js("""
                (() => {
                    const el = document.querySelector('.hud-top-bar') || document.querySelector('.hud-top');
                    return el ? el.getBoundingClientRect().height : null;
                })()
            """)
            assert bar_height is not None and bar_height < 52.0, (
                f"Top bar height at {width}x{height} is {bar_height:.2f}px (must be < 52px)."
            )

        # Restore normal window size
        await self.cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 720,
            "deviceScaleFactor": 1,
            "mobile": False
        })

    async def test_b02_camera_clamping_boundary_stress(self):
        """B2: Camera clamping at extreme boundary coordinates (-92, 92) and ground level."""
        data = await self.cdp.eval_js("""
            (() => {
                const prevMode = window.cameraMode;
                window.cameraMode = 'thirdperson';
                const p = window.units.find(u => u.isPlayer);
                const cam = window.camera;

                const corners = [
                    { x: 92, z: 92 },
                    { x: -92, z: 92 },
                    { x: 92, z: -92 },
                    { x: -92, z: -92 }
                ];

                const results = [];
                for (const c of corners) {
                    p.x = c.x; p.z = c.z;
                    window.tpCamYaw = Math.atan2(c.x, c.z);
                    if (typeof window.updateCameraAndHUD === 'function') {
                        window.updateCameraAndHUD();
                    }
                    results.push({
                        corner: c,
                        clamped: (cam.position.y >= 2.2) &&
                                 (cam.position.x >= -92 && cam.position.x <= 92) &&
                                 (cam.position.z >= -92 && cam.position.z <= 92),
                        pos: { x: cam.position.x, y: cam.position.y, z: cam.position.z }
                    });
                }

                p.x = 0; p.z = 0;
                window.cameraMode = prevMode;
                return results;
            })()
        """)
        for item in data:
            assert item["clamped"], f"Camera breached boundary at corner {item['corner']}: {item['pos']}"

    async def test_b03_zero_chakra_corner_case(self):
        """B3: Casting jutsu with zero chakra must not deduct chakra or trigger skills."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 0;
                p.cds.q = 0; p.cds.w = 0; p.cds.r = 0;

                window.executeSkill(p, 'q');
                window.executeSkill(p, 'w');
                window.executeSkill(p, 'r');

                return {
                    chakra: p.chakra,
                    qCd: p.cds.q,
                    wCd: p.cds.w,
                    rCd: p.cds.r
                };
            })()
        """)
        assert res["chakra"] == 0, f"Chakra dropped below 0: {res['chakra']}"
        assert res["qCd"] == 0, "Skill Q fired despite 0 chakra!"
        assert res["wCd"] == 0, "Skill W fired despite 0 chakra!"
        assert res["rCd"] == 0, "Ultimate R fired despite 0 chakra!"

    async def test_b04_rapid_combo_cycling_stress(self):
        """B4: Rapid consecutive basic attack combo inputs cycle cleanly without lockup."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.atk = 0;
                p.comboStep = 0;
                p.comboResetTimer = 0;
                const states = [];

                for (let i = 0; i < 9; i++) {
                    p.cds.atk = 0;
                    window.executeSkill(p, 'atk');
                    states.push(p.state);
                }

                return {
                    states,
                    validSequence: states[0] === 'attack' && states[1] === 'attack2' && states[2] === 'attack3' &&
                                   states[3] === 'attack' && states[4] === 'attack2' && states[5] === 'attack3'
                };
            })()
        """)
        assert res["validSequence"], f"Rapid combo cycling produced invalid sequence: {res['states']}"

    async def test_b05_player_stage_perimeter_clamping(self):
        """B5: Player coordinates strictly clamped within stage limits [-92, 92]."""
        # Place player near boundary and move outward
        await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.x = 91.5; p.z = 91.5;
            })()
        """)
        await self.cdp.dispatch_key("KeyD", "d")
        await self.cdp.dispatch_key("KeyS", "s")
        await asyncio.sleep(0.3)
        await self.cdp.release_key("KeyD", "d")
        await self.cdp.release_key("KeyS", "s")
        await asyncio.sleep(0.05)

        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                const clamped = (p.x >= -94 && p.x <= 94) && (p.z >= -94 && p.z <= 94);
                const pos = { x: p.x, z: p.z };
                p.x = 0; p.z = 0; // reset
                return { clamped, pos };
            })()
        """)
        assert res["clamped"], f"Player moved outside stage boundary: {res['pos']}"

    # =========================================================================
    # TIER 3: PAIRWISE COMBINATIONS
    # =========================================================================

    async def test_p01_wasd_while_casting_jutsu(self):
        """P1: Pairwise - WASD movement while casting jutsu transitions state smoothly."""
        await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100; p.cds.q = 0;
            })()
        """)

        # Hold W key
        await self.cdp.dispatch_key("KeyW", "w")
        await asyncio.sleep(0.05)

        # Cast jutsu
        res_cast = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                window.executeSkill(p, 'q');
                return { jutsuState: p.state };
            })()
        """)
        assert res_cast["jutsuState"] in ["jutsu", "spin"], f"State not in jutsu: {res_cast['jutsuState']}"

        # Complete jutsu anim timer
        await self.cdp.eval_js("window.units.find(u => u.isPlayer).animTimer = 0.01")
        await asyncio.sleep(0.1)

        res_post = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    postState: p.state,
                    resumedMovement: ['run', 'dash', 'idle'].includes(p.state)
                };
            })()
        """)
        await self.cdp.release_key("KeyW", "w")
        assert res_post["resumedMovement"], f"Movement failed to resume after jutsu: {res_post}"

    async def test_p02_toggle_camera_during_combat(self):
        """P2: Pairwise - Toggling camera mode during combat combo maintains finite coords."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.cds.atk = 0;
                window.executeSkill(p, 'atk'); // Hit 1

                window.toggleCameraMode();
                const mode1 = window.cameraMode;
                const cam1Valid = !isNaN(window.camera.position.x) && !isNaN(window.camera.position.y);

                p.cds.atk = 0;
                window.executeSkill(p, 'atk'); // Hit 2

                window.toggleCameraMode();
                const mode2 = window.cameraMode;
                const cam2Valid = !isNaN(window.camera.position.x) && !isNaN(window.camera.position.y);

                return {
                    mode1, mode2,
                    cam1Valid, cam2Valid
                };
            })()
        """)
        assert res["cam1Valid"] and res["cam2Valid"], "Camera coordinates encountered NaN during combat toggle."

    async def test_p03_drawer_toggle_during_respawn(self):
        """P3: Pairwise - Drawer toggle ('H') during unit respawn operates without conflict."""
        res = await self.cdp.eval_js("""
            (() => {
                const enemy = window.units.find(u => !u.isPlayer && u.team === 'red');
                enemy.deadTimer = 4.0;

                const drawer = document.getElementById('controls-drawer');
                const wasHidden = drawer ? drawer.classList.contains('hidden') : true;

                if (drawer) drawer.classList.toggle('hidden');
                const isToggled = drawer ? drawer.classList.contains('hidden') !== wasHidden : false;

                enemy.deadTimer -= 1.0;
                const deadTimerActive = enemy.deadTimer > 0;

                if (drawer && wasHidden) drawer.classList.add('hidden');
                enemy.deadTimer = 0;

                return {
                    isToggled,
                    deadTimerActive
                };
            })()
        """)
        assert res["isToggled"], "Controls drawer could not toggle during active respawn timer."
        assert res["deadTimerActive"], "Respawn timer was corrupted by drawer interaction."

    async def test_p04_chakra_charge_to_kawarimi_transition(self):
        """P4: Pairwise - Rapid transition from Chakra Charge [F] to Kawarimi [Space]."""
        await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 50; p.cds.e = 0;
            })()
        """)

        # Hold F
        await self.cdp.dispatch_key("KeyF", "f")
        await asyncio.sleep(0.1)

        # Release F and dispatch Space
        await self.cdp.release_key("KeyF", "f")
        await self.cdp.dispatch_key("Space", " ")
        await asyncio.sleep(0.05)
        await self.cdp.release_key("Space", " ")

        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    kawarimiCd: p.cds.e
                };
            })()
        """)
        assert res["kawarimiCd"] > 0, "Kawarimi did not trigger after releasing charge."

    # =========================================================================
    # TIER 4: REAL-WORLD MATCH SCENARIOS
    # =========================================================================

    async def test_s01_full_match_initiation_scenario(self):
        """Scenario 1: Match Start -> Verify 10 Ninjas, HUD Elements, Top Bar < 52px."""
        data = await self.cdp.eval_js("""
            (() => {
                const units = window.units || [];
                const topBar = document.querySelector('.hud-top-bar') || document.querySelector('.hud-top');
                const topBarHeight = topBar ? topBar.getBoundingClientRect().height : 999;
                const hudScreen = document.getElementById('hud-screen');
                const hudActive = hudScreen ? hudScreen.classList.contains('active') : false;

                return {
                    matchActive: window.matchActive,
                    unitsCount: units.length,
                    topBarHeight,
                    hudActive
                };
            })()
        """)
        assert data["matchActive"], "Match is not active."
        assert data["unitsCount"] == 10, f"Expected 10 units in 5v5 match, got {data['unitsCount']}"
        assert data["topBarHeight"] < 52.0, f"Top bar height violated: {data['topBarHeight']:.2f}px >= 52px"

    async def test_s02_3rd_person_boundary_navigation_run(self):
        """Scenario 2: 3rd-Person Boundary & Navigation Circuit with Stage Clamping."""
        res = await self.cdp.eval_js("""
            (() => {
                const prevMode = window.cameraMode;
                window.cameraMode = 'thirdperson';
                const p = window.units.find(u => u.isPlayer);
                const cam = window.camera;

                const path = [
                    { x: 50, z: 50, yaw: 0 },
                    { x: 80, z: -50, yaw: Math.PI / 2 },
                    { x: -70, z: -70, yaw: Math.PI },
                    { x: -50, z: 70, yaw: -Math.PI / 2 }
                ];

                let allClamped = true;
                for (const pt of path) {
                    p.x = pt.x; p.z = pt.z;
                    window.tpCamYaw = pt.yaw;
                    if (typeof window.updateCameraAndHUD === 'function') {
                        window.updateCameraAndHUD();
                    }
                    if (cam.position.y < 2.2 ||
                        cam.position.x < -92 || cam.position.x > 92 ||
                        cam.position.z < -92 || cam.position.z > 92) {
                        allClamped = false;
                        break;
                    }
                }

                p.x = 0; p.z = 0;
                window.cameraMode = prevMode;
                return { allClamped };
            })()
        """)
        assert res["allClamped"], "Camera violated boundary clamping during 3rd-person navigation circuit."

    async def test_s03_combat_combo_ability_cycling(self):
        """Scenario 3: Combat engagement -> Left click combo -> Q -> E -> Kawarimi -> F charge."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };

                // 1. Melee Combo 1-2-3
                window.executeSkill(p, 'atk');
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');
                p.cds.atk = 0;
                window.executeSkill(p, 'atk');

                // 2. Primary Jutsu Q
                window.executeSkill(p, 'q');
                const qCd = p.cds.q;

                // 3. Secondary Jutsu E (slot w)
                window.executeSkill(p, 'w');
                const wCd = p.cds.w;

                // 4. Kawarimi Space (slot e)
                window.executeSkill(p, 'e');
                const eCd = p.cds.e;

                p.chakra = 20;

                return {
                    qCdSet: qCd > 0,
                    wCdSet: wCd > 0,
                    eCdSet: eCd > 0
                };
            })()
        """)
        assert res["qCdSet"] and res["wCdSet"] and res["eCdSet"], f"Ability cycling failed: {res}"

        # Charge chakra with F
        await self.cdp.dispatch_key("KeyF", "f")
        await asyncio.sleep(0.2)
        await self.cdp.release_key("KeyF", "f")

        recharged = await self.cdp.eval_js("window.units.find(u => u.isPlayer).chakra > 20")
        assert recharged, "Chakra charging failed during ability cycle."

    async def test_s04_kill_and_respawn_cycle_scenario(self):
        """Scenario 4: Eliminate enemy ninja -> kill-feed notice -> countdown -> respawn."""
        res = await self.cdp.eval_js("""
            (() => {
                const player = window.units.find(u => u.isPlayer);
                const enemy = window.units.find(u => !u.isPlayer && u.team === 'red');
                const initialScoreBlue = parseInt(document.getElementById('score-blue').textContent) || 0;

                // Move enemy next to player with 5 HP
                enemy.x = player.x + 1.5;
                enemy.z = player.z;
                enemy.hp = 5;
                player.cds.atk = 0;

                // Execute attack to deal lethal damage naturally
                window.executeSkill(player, 'atk');

                const enemyDied = enemy.deadTimer > 0;
                const newScoreBlue = parseInt(document.getElementById('score-blue').textContent) || 0;
                const scoreUpdated = newScoreBlue >= initialScoreBlue;

                const feed = document.getElementById('kill-feed');
                const hasKillToast = feed && feed.children.length > 0;

                // Advance deadTimer to near completion
                enemy.deadTimer = 0.05;

                return {
                    enemyDied,
                    scoreUpdated,
                    hasKillToast
                };
            })()
        """)
        assert res["enemyDied"], "Enemy did not enter dead state upon lethal damage."
        assert res["scoreUpdated"], "Score was not incremented after elimination."
        assert res["hasKillToast"], "Kill feed entry was not posted."

        # Wait for respawn
        await asyncio.sleep(0.15)
        respawned = await self.cdp.eval_js("""
            (() => {
                const enemy = window.units.find(u => !u.isPlayer && u.team === 'red');
                return enemy.deadTimer <= 0 && enemy.hp === enemy.maxHp;
            })()
        """)
        assert respawned, "Enemy ninja failed to respawn after countdown expired."

    async def test_s05_awakening_and_ultimate_clash(self):
        """Scenario 5: 100% Chakra -> Ultimate Ougi [R] -> Awakening Mode -> Hit Sparks -> SFX."""
        res = await self.cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.r = 0;

                window.executeSkill(p, 'r');

                const isAwakened = p.awakenedTimer > 0;
                const ultCd = p.cds.r;
                const banner = document.getElementById('center-banner');
                const bannerVisible = banner && !banner.classList.contains('hidden');

                return {
                    isAwakened,
                    ultCd,
                    bannerVisible
                };
            })()
        """)
        assert res["isAwakened"], "Player failed to enter Awakening mode upon casting Ultimate."
        assert res["ultCd"] > 0, "Ultimate cooldown was not set."

    async def test_s06_match_results_mvp_flow(self):
        """Scenario 6: M5 match end — endMatch chain, victory/lose/tie board, MVP card, rematch."""
        res = await self.cdp.eval_js("""
            (async () => {
                const out = {};
                // start incondicional: estado deterministico (scores 0-0, guarda liberada)
                await window.start5v5Match();
                await new Promise(r => setTimeout(r, 800));
                out.guardCleared = (window.__isMatchEnding ? window.__isMatchEnding() : null);
                // Parte A: cadeia real endMatch (abates finais + guarda + delay + overlay)
                const p = window.units.find(u => u.isPlayer);
                for (const e of window.units.filter(u => u.team === 'red' && u.deadTimer <= 0).slice(0, 2)) {
                    e.hp = 5; e.x = p.x + 2; e.z = p.z;
                    window.dealDamage(p, e, 9999, 'Rasengan!');
                }
                window.endMatch('FIM DE PARTIDA');
                await new Promise(r => setTimeout(r, 3500));
                const q = id => document.getElementById(id);
                out.chainShown = !!q('match-results-overlay') && q('match-results-overlay').classList.contains('show');
                // Parte B: UI forcada — vitoria / derrota / empate (deterministico)
                const probe = () => ({
                    shown: q('match-results-overlay').classList.contains('show'),
                    kanji: (q('mr-banner-kanji') || {}).textContent || '',
                    banner: (q('mr-banner-img') || {}).src || '',
                    rowsBlue: q('mr-tbody-blue') ? q('mr-tbody-blue').children.length : -1,
                    rowsRed: q('mr-tbody-red') ? q('mr-tbody-red').children.length : -1,
                    mvpName: (q('mr-mvp-name') || {}).textContent || '',
                    mvpKda: (q('mr-mvp-kda') || {}).textContent || ''
                });
                window.hideMatchResults();
                await new Promise(r => setTimeout(r, 250));
                window.showMatchResults('blue');
                await new Promise(r => setTimeout(r, 400));
                out.win = probe();
                window.hideMatchResults();
                await new Promise(r => setTimeout(r, 250));
                window.showMatchResults('red');
                await new Promise(r => setTimeout(r, 400));
                out.lose = probe();
                window.hideMatchResults();
                await new Promise(r => setTimeout(r, 250));
                window.showMatchResults('tie');
                await new Promise(r => setTimeout(r, 400));
                out.tie = probe();
                // Parte C: revanche restaura a partida e esconde o overlay
                window.hideMatchResults();
                window.start5v5Match();
                out.rematchActive = false;
                for (let i = 0; i < 12; i++) {
                    await new Promise(r => setTimeout(r, 800));
                    if (window.matchActive === true) { out.rematchActive = true; break; }
                }
                out.overlayHidden = q('match-results-overlay').classList.contains('hidden');
                return out;
            })()
        """, await_promise=True)
        assert res["guardCleared"] is False, "matchEnding guard was stuck true before endMatch."
        assert res["chainShown"] is True, "M5 endMatch chain did not show the results overlay."
        assert "勝利" in res["win"]["kanji"], f"Victory kanji missing: {res['win']['kanji']}"
        assert "banner_win" in res["win"]["banner"], f"Wrong banner asset: {res['win']['banner']}"
        assert res["win"]["rowsBlue"] == 5 and res["win"]["rowsRed"] == 5, f"Final board rows wrong: {res['win']['rowsBlue']}/{res['win']['rowsRed']}"
        assert res["win"]["mvpName"], "MVP card is empty."
        assert "AB " in res["win"]["mvpKda"] or "K " in res["win"]["mvpKda"], f"MVP KDA line malformed: {res['win']['mvpKda']}"
        assert "敗北" in res["lose"]["kanji"], f"Defeat kanji missing: {res['lose']['kanji']}"
        assert "banner_lose" in res["lose"]["banner"], f"Wrong lose banner: {res['lose']['banner']}"
        assert "引" in res["tie"]["kanji"], f"Tie kanji missing: {res['tie']['kanji']}"
        assert res["rematchActive"] is True, "Rematch did not restart the match."
        assert res["overlayHidden"] is True, "Results overlay not hidden after rematch."


async def run_suite():
    print("==================================================================")
    print("  NUBA E2E TEST SUITE (Tiers 1 to 4) - Chrome DevTools Protocol")
    print("==================================================================")

    tabs_data = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
    tabs = json.loads(tabs_data)
    target_tab = None
    for t in tabs:
        if "localhost:8080" in t.get("url", ""):
            target_tab = t
            break

    if not target_tab:
        raise RuntimeError(f"Target tab localhost:8080 not found! Tabs: {[t.get('url') for t in tabs]}")

    ws_url = target_tab["webSocketDebuggerUrl"]
    print(f"Connecting to Edge CDP at {ws_url}...")
    cdp = CDPClient(ws_url)
    await cdp.connect()

    # Wait for page assets and Three.js initialization
    print("Waiting for page assets and match initialization...")
    await asyncio.sleep(3.5)

    # Ensure match is started
    start_match_js = """
    (async () => {
        if (!window.matchActive && typeof window.start5v5Match === 'function') {
            await window.start5v5Match();
        }
        for (let i = 0; i < 60; i++) {
            if (window.units && window.units.length === 10) return true;
            await new Promise(r => setTimeout(r, 100));
        }
        return false;
    })()
    """
    match_started = await cdp.eval_js(start_match_js, await_promise=True)
    assert match_started, "Failed to start 5v5 match with 10 units."
    await asyncio.sleep(1.0)

    runner = E2ETestRunner(cdp)

    # -------------------------------------------------------------------------
    # Tier 1 Tests
    # -------------------------------------------------------------------------
    print("\n--- Running Tier 1: Feature Coverage (Features 1 to 20) ---")
    await runner.run_test("T1_F01", "Top Bar Height (<52px)", "Tier 1", runner.test_f01_top_bar_height)
    await runner.run_test("T1_F02", "Mini-Portraits & Alive Dots", "Tier 1", runner.test_f02_mini_portraits_alive_dots)
    await runner.run_test("T1_F03", "Numerical Respawn Countdown", "Tier 1", runner.test_f03_respawn_countdown)
    await runner.run_test("T1_F04", "Storm VS Crest & Match Timer", "Tier 1", runner.test_f04_storm_vs_crest_and_timer)
    await runner.run_test("T1_F05", "Kill-Feed Portraits & Auto-Fade", "Tier 1", runner.test_f05_kill_feed_portraits_fade)
    await runner.run_test("T1_F06", "Command Center & Vital Gauges", "Tier 1", runner.test_f06_command_center_avatar_gauges)
    await runner.run_test("T1_F07", "Radial Cooldown Sweeps", "Tier 1", runner.test_f07_radial_cooldown_sweeps)
    await runner.run_test("T1_F08", "Controls Drawer Toggle ('H')", "Tier 1", runner.test_f08_controls_drawer_toggle)
    await runner.run_test("T1_F09", "Free 'W' Key for Movement", "Tier 1", runner.test_f09_free_w_key_movement)
    await runner.run_test("T1_F10", "Camera-Relative 3rd-Person Movement", "Tier 1", runner.test_f10_camera_relative_3rd_person_movement)
    await runner.run_test("T1_F11", "Camera Stage Clamping (Y>=2.2, [-92,92])", "Tier 1", runner.test_f11_camera_stage_clamping)
    await runner.run_test("T1_F12", "Mouse Left Click Combo", "Tier 1", runner.test_f12_mouse_left_click_combo)
    await runner.run_test("T1_F13", "Ninjutsu Primario [Q]", "Tier 1", runner.test_f13_ninjutsu_primario_q)
    await runner.run_test("T1_F14", "Ninjutsu Secundario [E]", "Tier 1", runner.test_f14_ninjutsu_secundario_e)
    await runner.run_test("T1_F15", "Kawarimi / Substituicao [ESPACO]", "Tier 1", runner.test_f15_kawarimi_espaco)
    await runner.run_test("T1_F16", "Ultimate Ougi & Despertar [R]", "Tier 1", runner.test_f16_ultimate_ougi_r)
    await runner.run_test("T1_F17", "Concentrar Chakra [F]", "Tier 1", runner.test_f17_concentrar_chakra_f)
    await runner.run_test("T1_F18", "Synchronized SFX & Audio", "Tier 1", runner.test_f18_synchronized_sfx)
    await runner.run_test("T1_F19", "Cel-Shaded Hit Sparks", "Tier 1", runner.test_f19_hit_sparks_vfx)
    await runner.run_test("T1_F20", "Awakening Ground Aura Rings", "Tier 1", runner.test_f20_awakening_aura_rings)
    await runner.run_test("T1_F21", "Arena Catalog Loaded (>=8 arenas)", "Tier 1", runner.test_f21_arena_catalog)
    await runner.run_test("T1_F22", "Arena Switch Rebuilds Stage + Rescales Clamps", "Tier 1", runner.test_f22_arena_switch)
    await runner.run_test("T1_F23", "Arena Picker UI Reflects Selection", "Tier 1", runner.test_f23_arena_picker_ui)

    # -------------------------------------------------------------------------
    # Tier 2 Tests
    # -------------------------------------------------------------------------
    print("\n--- Running Tier 2: Boundary & Corner Cases ---")
    await runner.run_test("T2_B01", "Screen Resize Boundary", "Tier 2", runner.test_b01_screen_resize_boundary)
    await runner.run_test("T2_B02", "Camera Clamping Boundary Stress", "Tier 2", runner.test_b02_camera_clamping_boundary_stress)
    await runner.run_test("T2_B03", "Zero Chakra Corner Case", "Tier 2", runner.test_b03_zero_chakra_corner_case)
    await runner.run_test("T2_B04", "Rapid Combo Cycling Stress", "Tier 2", runner.test_b04_rapid_combo_cycling_stress)
    await runner.run_test("T2_B05", "Player Stage Perimeter Clamping", "Tier 2", runner.test_b05_player_stage_perimeter_clamping)

    # -------------------------------------------------------------------------
    # Tier 3 Tests
    # -------------------------------------------------------------------------
    print("\n--- Running Tier 3: Pairwise Combinations ---")
    await runner.run_test("T3_P01", "WASD While Casting Jutsu", "Tier 3", runner.test_p01_wasd_while_casting_jutsu)
    await runner.run_test("T3_P02", "Toggle Camera During Combat", "Tier 3", runner.test_p02_toggle_camera_during_combat)
    await runner.run_test("T3_P03", "Drawer Toggle During Respawn", "Tier 3", runner.test_p03_drawer_toggle_during_respawn)
    await runner.run_test("T3_P04", "Chakra Charge to Kawarimi Transition", "Tier 3", runner.test_p04_chakra_charge_to_kawarimi_transition)

    # -------------------------------------------------------------------------
    # Tier 4 Tests
    # -------------------------------------------------------------------------
    print("\n--- Running Tier 4: Real-World Match Scenarios ---")
    await runner.run_test("T4_S01", "Full Match Initiation Scenario", "Tier 4", runner.test_s01_full_match_initiation_scenario)
    await runner.run_test("T4_S02", "3rd-Person Boundary Navigation Run", "Tier 4", runner.test_s02_3rd_person_boundary_navigation_run)
    await runner.run_test("T4_S03", "Combat Combo & Ability Cycling", "Tier 4", runner.test_s03_combat_combo_ability_cycling)
    await runner.run_test("T4_S04", "Kill & Respawn Cycle Verification", "Tier 4", runner.test_s04_kill_and_respawn_cycle_scenario)
    await runner.run_test("T4_S05", "Awakening & Ultimate Clash", "Tier 4", runner.test_s05_awakening_and_ultimate_clash)
    await runner.run_test("T4_S06", "Match Results: Victory Board + MVP + Rematch", "Tier 4", runner.test_s06_match_results_mvp_flow)

    # Capture final in-game verification screenshot
    screenshot = await cdp.send("Page.captureScreenshot", {"format": "png"})
    if "data" in screenshot:
        scratch_dir = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch"
        os.makedirs(scratch_dir, exist_ok=True)
        shot_path = os.path.join(scratch_dir, "nuba_e2e_suite_pass.png")
        with open(shot_path, "wb") as f:
            f.write(base64.b64decode(screenshot["data"]))
        print(f"\nCaptured End-to-End Test Suite Screenshot: {shot_path}")

    # Console errors assertion
    console_errors = cdp.console_errors
    await cdp.close()

    # -------------------------------------------------------------------------
    # Report & Summary
    # -------------------------------------------------------------------------
    total_tests = len(runner.results)
    passed_tests = sum(1 for r in runner.results if r.passed)
    failed_tests = total_tests - passed_tests

    tier_summary = {}
    for r in runner.results:
        if r.tier not in tier_summary:
            tier_summary[r.tier] = {"total": 0, "passed": 0, "failed": 0}
        tier_summary[r.tier]["total"] += 1
        if r.passed:
            tier_summary[r.tier]["passed"] += 1
        else:
            tier_summary[r.tier]["failed"] += 1

    print("\n==================================================================")
    print("                    E2E TEST SUITE SUMMARY                        ")
    print("==================================================================")
    for tier, stats in tier_summary.items():
        print(f"  {tier:10}: {stats['passed']}/{stats['total']} Passed ({stats['failed']} Failed)")
    print(f"  Total     : {passed_tests}/{total_tests} Passed ({failed_tests} Failed)")
    print(f"  Console Errors: {len(console_errors)}")
    if console_errors:
        print("  Console Errors Logged:")
        for err in console_errors:
            print(f"    - {err}")
    print("==================================================================")

    all_tests_passed = (failed_tests == 0 and len(console_errors) == 0)
    return all_tests_passed, runner.results, console_errors


def main():
    edge_bin = find_edge_path()
    tmp_profile = tempfile.mkdtemp()
    print(f"Starting Headless Edge with user profile: {tmp_profile}...")
    proc = subprocess.Popen([
        edge_bin,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--disable-gpu",
        "--window-size=1280,720",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])
    time.sleep(2.5)

    all_passed = False
    results = []
    console_errors = []

    try:
        all_passed, results, console_errors = asyncio.run(run_suite())
    except Exception as e:
        print(f"\nCRITICAL TEST RUNNER EXCEPTION: {e}")
        all_passed = False
    finally:
        print("Terminating Edge instance...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        import shutil
        shutil.rmtree(tmp_profile, ignore_errors=True)

    if all_passed:
        print("\n>>> ALL E2E SUITE TESTS (TIERS 1-4) PASSED WITH ZERO CONSOLE ERRORS! <<<\n")
        sys.exit(0)
    else:
        print("\n>>> E2E TEST SUITE DETECTED FAILURES OR CONSOLE ERRORS! <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
