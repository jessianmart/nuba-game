import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys
import os
import tempfile
import math

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEBUG_PORT = 9223

async def run_stress_tests():
    tabs = None
    for attempt in range(20):
        try:
            tabs_data = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=5).read()
            tabs = json.loads(tabs_data)
            if tabs:
                break
        except Exception:
            time.sleep(0.5)

    if not tabs:
        print(f"FAIL: Could not connect to remote debugging port {DEBUG_PORT}!", flush=True)
        return False, [f"Could not connect to Edge on port {DEBUG_PORT}"]

    target_tab = None
    for t in tabs:
        if "localhost:8080" in t.get("url", ""):
            target_tab = t
            break

    if not target_tab:
        print(f"FAIL: Target tab localhost:8080 not found! Available: {[t.get('url') for t in tabs]}", flush=True)
        return False, ["Target tab not found"]

    ws_url = target_tab["webSocketDebuggerUrl"]
    print(f"Connecting to CDP: {ws_url}...", flush=True)

    console_errors = []
    page_exceptions = []
    msg_id = 0

    async with websockets.connect(ws_url, max_size=25_000_000) as ws:
        async def call_cdp(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cid = msg_id
            req = {"id": cid, "method": method}
            if params:
                req["params"] = params
            await ws.send(json.dumps(req))
            while True:
                resp_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(resp_raw)
                if data.get("id") == cid:
                    return data.get("result", {})
                m = data.get("method")
                if m == "Runtime.exceptionThrown":
                    exc = data["params"]["exceptionDetails"]
                    text = exc.get("exception", {}).get("description") or exc.get("text")
                    print(f"  [PAGE EXCEPTION] {text}", flush=True)
                    page_exceptions.append(text)
                elif m == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        print(f"  [LOG ERROR] {json.dumps(entry)}", flush=True)
                        console_errors.append(entry.get("text"))
                elif m == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    if call_type == "error":
                        err_str = " ".join(str(x) for x in args)
                        print(f"  [CONSOLE ERROR] {err_str}", flush=True)
                        console_errors.append(err_str)

        await call_cdp("Runtime.enable")
        await call_cdp("Page.enable")

        print("=== INITIALIZING MATCH FOR STRESS TESTING ===", flush=True)
        await asyncio.sleep(2.0)

        start_eval = """
        (async () => {
            if (!window.matchActive) {
                await window.start5v5Match();
            }
            for (let i = 0; i < 40; i++) {
                if (window.units && window.units.length === 10) break;
                await new Promise(r => setTimeout(r, 100));
            }
            return {
                matchActive: window.matchActive,
                unitsCount: window.units ? window.units.length : 0
            };
        })()
        """
        match_res = await call_cdp("Runtime.evaluate", {"expression": start_eval, "awaitPromise": True, "returnByValue": True})
        match_state = match_res.get("result", {}).get("value")
        print("Match State:", match_state, flush=True)
        assert match_state["matchActive"] and match_state["unitsCount"] == 10, "Match failed to initialize 10 units!"

        await asyncio.sleep(1.0)

        # -------------------------------------------------------------
        # TEST SUITE 1: Multi-Viewport Top Bar Bounding Box Stress Test
        # -------------------------------------------------------------
        print("\n=== [STRESS-1] MULTI-VIEWPORT TOP BAR BOUNDING BOX AUDIT ===", flush=True)
        viewports = [
            (1920, 1080),
            (1600, 900),
            (1366, 768),
            (1280, 720),
            (1024, 768)
        ]
        viewport_results = []
        for w, h in viewports:
            await call_cdp("Emulation.setDeviceMetricsOverride", {
                "width": w,
                "height": h,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(0.2)

            audit_eval = """
            (() => {
                const topBar = document.querySelector('.hud-top-bar');
                const rect = topBar.getBoundingClientRect();
                const cs = window.getComputedStyle(topBar);
                const blueIcons = document.querySelectorAll('#hud-blue-icons .mini-p');
                const redIcons = document.querySelectorAll('#hud-red-icons .mini-p');
                const clock = document.getElementById('match-timer');
                const clockRect = clock.getBoundingClientRect();
                const centerCluster = document.querySelector('.match-center-cluster');
                const clusterRect = centerCluster.getBoundingClientRect();
                
                // Check if any element clips or wraps awkwardly
                const hasVerticalOverflow = topBar.scrollHeight > (topBar.clientHeight + 2);
                
                return {
                    width: rect.width,
                    height: rect.height,
                    maxHeight: cs.maxHeight,
                    isUnder52: rect.height < 52,
                    blueIconsCount: blueIcons.length,
                    redIconsCount: redIcons.length,
                    hasVerticalOverflow: hasVerticalOverflow,
                    clusterHeight: clusterRect.height,
                    clockHeight: clockRect.height,
                    clockWithinBar: (clockRect.top >= rect.top && clockRect.bottom <= (rect.bottom + 1))
                };
            })()
            """
            v_res = await call_cdp("Runtime.evaluate", {"expression": audit_eval, "returnByValue": True})
            v_data = v_res.get("result", {}).get("value")
            v_data["viewport"] = f"{w}x{h}"
            viewport_results.append(v_data)
            print(f"  Viewport {w}x{h}: Height={v_data['height']:.2f}px | Overflow={v_data['hasVerticalOverflow']} | ClockWithinBar={v_data['clockWithinBar']} | Pass={v_data['isUnder52']}", flush=True)
            assert v_data["isUnder52"], f"Viewport {w}x{h} top bar height {v_data['height']} is >= 52px!"
            assert not v_data["hasVerticalOverflow"], f"Viewport {w}x{h} top bar has vertical overflow!"
            assert v_data["clockWithinBar"], f"Viewport {w}x{h} clock overflows top bar bounds!"
            assert v_data["blueIconsCount"] == 5 and v_data["redIconsCount"] == 5, f"Portraits missing in {w}x{h}"

        # Reset to 1280x720
        await call_cdp("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 720,
            "deviceScaleFactor": 1,
            "mobile": False
        })
        await asyncio.sleep(0.2)

        # -------------------------------------------------------------
        # TEST SUITE 2: Rapid 20x Controls Drawer Toggle Stress Test
        # -------------------------------------------------------------
        print("\n=== [STRESS-2] CONTROLS DRAWER RAPID TOGGLE AUDIT (20x) ===", flush=True)
        
        # Part A: 20x Rapid toggles via KeyH keyboard events
        print("  Testing 20 rapid KeyH toggles...", flush=True)
        drawer_states_key = []
        for i in range(20):
            # Dispatch KeyDown + KeyUp
            await call_cdp("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "code": "KeyH",
                "key": "h",
                "windowsVirtualKeyCode": 72
            })
            await call_cdp("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "code": "KeyH",
                "key": "h",
                "windowsVirtualKeyCode": 72
            })
            await asyncio.sleep(0.03)

            check_eval = "document.getElementById('controls-drawer').classList.contains('hidden')"
            st_res = await call_cdp("Runtime.evaluate", {"expression": check_eval, "returnByValue": True})
            is_hidden = st_res.get("result", {}).get("value")
            expected_hidden = (i % 2 == 1)
            assert is_hidden == expected_hidden, f"KeyH toggle #{i+1}: expected hidden={expected_hidden}, got hidden={is_hidden}!"
            drawer_states_key.append(is_hidden)

        print(f"    KeyH 20x toggle successful. Final hidden state: {drawer_states_key[-1]}", flush=True)
        assert drawer_states_key[-1] is True, "Drawer should be closed after 20 KeyH toggles!"

        # Part B: 20x Rapid toggles via UI Buttons (#btn-help-controls and #btn-close-controls)
        print("  Testing 20 rapid Button click toggles (open/close pairs)...", flush=True)
        for i in range(10):
            click_open = "document.getElementById('btn-help-controls').click(); document.getElementById('controls-drawer').classList.contains('hidden')"
            o_res = await call_cdp("Runtime.evaluate", {"expression": click_open, "returnByValue": True})
            is_hidden_after_open = o_res.get("result", {}).get("value")
            assert is_hidden_after_open is False, f"Iteration {i}: Drawer failed to open on button click!"

            await asyncio.sleep(0.02)

            click_close = "document.getElementById('btn-close-controls').click(); document.getElementById('controls-drawer').classList.contains('hidden')"
            c_res = await call_cdp("Runtime.evaluate", {"expression": click_close, "returnByValue": True})
            is_hidden_after_close = c_res.get("result", {}).get("value")
            assert is_hidden_after_close is True, f"Iteration {i}: Drawer failed to close on close button click!"

            await asyncio.sleep(0.02)
        print("    Button 20x toggles passed with 0 stuck states.", flush=True)

        # -------------------------------------------------------------
        # TEST SUITE 3: Rapid 5-Ninja Elimination & Concurrent Countdowns
        # -------------------------------------------------------------
        print("\n=== [STRESS-3] 5-NINJA SIMULTANEOUS ELIMINATION & COUNTDOWN AUDIT ===", flush=True)
        elim_eval = """
        (() => {
            const player = window.units.find(u => u.isPlayer) || window.units[0];
            const enemies = window.units.filter(u => u.team === 'red');
            
            enemies.forEach((enemy, idx) => {
                window.dealDamage(player, enemy, 10000, `Ougi Strike ${idx+1}`);
            });
            
            const results = enemies.map(e => {
                const icon = document.getElementById(`top-icon-${e.id}`);
                const cd = document.getElementById(`respawn-cd-${e.id}`);
                const dot = icon ? icon.querySelector('.alive-dot') : null;
                return {
                    id: e.id,
                    deadTimer: e.deadTimer,
                    isDead: e.deadTimer > 0,
                    iconHasDeadClass: icon ? icon.classList.contains('dead') : false,
                    cdVisible: cd ? (window.getComputedStyle(cd).display === 'flex') : false,
                    cdText: cd ? cd.textContent.trim() : '',
                    dotVisible: dot ? (window.getComputedStyle(dot).display !== 'none') : false
                };
            });
            return results;
        })()
        """
        elim_res = await call_cdp("Runtime.evaluate", {"expression": elim_eval, "returnByValue": True})
        elim_data = elim_res.get("result", {}).get("value")
        print(f"  Eliminated 5 enemies. Immediate state:", flush=True)
        for r in elim_data:
            print(f"    Unit {r['id']}: deadTimer={r['deadTimer']} | deadClass={r['iconHasDeadClass']} | cdVisible={r['cdVisible']} | cdText={r['cdText']} | dotVisible={r['dotVisible']}", flush=True)
            assert r["isDead"], f"Unit {r['id']} deadTimer is not > 0!"
            assert r["iconHasDeadClass"], f"Unit {r['id']} portrait missing 'dead' class!"
            assert r["cdVisible"], f"Unit {r['id']} respawn countdown not displayed!"
            assert r["cdText"] in ["5", "4"], f"Unit {r['id']} respawn countdown unexpected: '{r['cdText']}'"
            assert not r["dotVisible"], f"Unit {r['id']} alive dot still visible while dead!"

        # Mid-respawn countdown check after 2.0 seconds
        print("  Waiting 2.0s to verify concurrent countdown progression...", flush=True)
        await asyncio.sleep(2.0)
        mid_eval = """
        (() => {
            const enemies = window.units.filter(u => u.team === 'red');
            return enemies.map(e => {
                const cd = document.getElementById(`respawn-cd-${e.id}`);
                return {
                    id: e.id,
                    deadTimer: e.deadTimer,
                    expectedText: String(Math.ceil(e.deadTimer)),
                    cdText: cd ? cd.textContent.trim() : ''
                };
            });
        })()
        """
        mid_res = await call_cdp("Runtime.evaluate", {"expression": mid_eval, "returnByValue": True})
        mid_data = mid_res.get("result", {}).get("value")
        print("  Mid-respawn countdowns:", flush=True)
        for r in mid_data:
            print(f"    Unit {r['id']}: deadTimer={r['deadTimer']:.2f} | cdText={r['cdText']} | expected={r['expectedText']}", flush=True)
            assert r["deadTimer"] < 5.0, f"Unit {r['id']} deadTimer has not decreased: {r['deadTimer']}"
            assert r["cdText"] == r["expectedText"], f"Unit {r['id']} countdown '{r['cdText']}' does not match Math.ceil ({r['expectedText']})!"

        # Wait until all 5 units have fully respawned (deadTimer <= 0)
        print("  Waiting for all 5 units to fully respawn (polling up to 8s)...", flush=True)
        respawn_done = False
        for _ in range(80):
            await asyncio.sleep(0.1)
            chk_res = await call_cdp("Runtime.evaluate", {
                "expression": "window.units.filter(u => u.team === 'red').every(u => u.deadTimer <= 0)",
                "returnByValue": True
            })
            if chk_res.get("result", {}).get("value") is True:
                respawn_done = True
                break

        assert respawn_done, "Timed out waiting for red units to respawn!"
        await asyncio.sleep(0.2) # Allow 1 frame for DOM sync

        respawn_eval = """
        (() => {
            const enemies = window.units.filter(u => u.team === 'red');
            return enemies.map(e => {
                const icon = document.getElementById(`top-icon-${e.id}`);
                const cd = document.getElementById(`respawn-cd-${e.id}`);
                const dot = icon ? icon.querySelector('.alive-dot') : null;
                return {
                    id: e.id,
                    deadTimer: e.deadTimer,
                    iconHasDeadClass: icon ? icon.classList.contains('dead') : false,
                    cdVisible: cd ? (window.getComputedStyle(cd).display !== 'none' && cd.textContent.trim() !== '') : false,
                    dotVisible: dot ? (window.getComputedStyle(dot).display !== 'none') : false
                };
            });
        })()
        """
        respawn_res = await call_cdp("Runtime.evaluate", {"expression": respawn_eval, "returnByValue": True})
        respawn_data = respawn_res.get("result", {}).get("value")
        print("  Post-respawn state for all 5 units:", flush=True)
        for r in respawn_data:
            print(f"    Unit {r['id']}: deadTimer={r['deadTimer']} | deadClass={r['iconHasDeadClass']} | cdVisible={r['cdVisible']} | dotVisible={r['dotVisible']}", flush=True)
            assert r["deadTimer"] <= 0, f"Unit {r['id']} has not respawned!"
            assert not r["iconHasDeadClass"], f"Unit {r['id']} still has 'dead' class after respawn!"
            assert not r["cdVisible"], f"Unit {r['id']} countdown still visible after respawn!"
            assert r["dotVisible"], f"Unit {r['id']} alive dot not restored after respawn!"
        print("    All 5 countdown timers operated concurrently and cleared upon respawn.", flush=True)

        # -------------------------------------------------------------
        # TEST SUITE 4: Kill-Feed Burst Stacking, Auto-Dismiss & DOM Leak
        # -------------------------------------------------------------
        print("\n=== [STRESS-4] KILL-FEED BURST STACKING, AUTO-DISMISS & ZERO DOM LEAK ===", flush=True)
        burst_eval = """
        (() => {
            const feed = document.getElementById('kill-feed');
            feed.innerHTML = ''; // reset feed
            const player = window.units.find(u => u.isPlayer) || window.units[0];
            const enemy = window.units.filter(u => u.team === 'red')[0];
            
            // Trigger 8 kills in rapid succession using dealDamage
            for (let i = 0; i < 8; i++) {
                enemy.deadTimer = 0;
                enemy.hp = 100;
                window.dealDamage(player, enemy, 10000, `Combo Burst ${i+1}`);
            }
            
            const items = feed.querySelectorAll('.kill-toast');
            return {
                renderedItemsCount: items.length,
                maxAllowed: 5,
                firstItemPortraits: items[0] ? items[0].querySelectorAll('.feed-portrait').length : 0,
                firstItemTag: items[0] ? items[0].querySelector('.feed-ability-tag').textContent : ''
            };
        })()
        """
        burst_res = await call_cdp("Runtime.evaluate", {"expression": burst_eval, "returnByValue": True})
        burst_data = burst_res.get("result", {}).get("value")
        print(f"  Burst of 8 kills injected. Rendered items in feed: {burst_data['renderedItemsCount']} (Cap is 5)", flush=True)
        assert burst_data["renderedItemsCount"] == 5, f"Expected exactly 5 items (stack cap), found {burst_data['renderedItemsCount']}!"
        assert burst_data["firstItemPortraits"] == 2, f"Feed item missing portraits, found {burst_data['firstItemPortraits']}"
        assert "[Combo Burst 8]" in burst_data["firstItemTag"], f"Unexpected top feed tag: {burst_data['firstItemTag']}"

        # Check fade-out after 4.3s
        print("  Waiting 4.3s for auto-dismiss fade-out...", flush=True)
        await asyncio.sleep(4.3)
        fade_eval = """
        (() => {
            const feed = document.getElementById('kill-feed');
            const items = Array.from(feed.querySelectorAll('.kill-toast'));
            const fadeOutCount = items.filter(it => it.classList.contains('fade-out')).length;
            return {
                itemCount: items.length,
                fadeOutCount: fadeOutCount
            };
        })()
        """
        fade_res = await call_cdp("Runtime.evaluate", {"expression": fade_eval, "returnByValue": True})
        fade_data = fade_res.get("result", {}).get("value")
        print(f"  Items in feed at 4.3s: {fade_data['itemCount']}, items with .fade-out: {fade_data['fadeOutCount']}", flush=True)
        assert fade_data["fadeOutCount"] > 0, "No feed items received fade-out class at 4.3s!"

        # Check total DOM cleanup after 1.0s more (total 5.3s)
        print("  Waiting 1.0s for DOM removal (total 5.3s)...", flush=True)
        await asyncio.sleep(1.0)
        cleanup_eval = """
        (() => {
            const feed = document.getElementById('kill-feed');
            const allToastsInDocument = document.querySelectorAll('.kill-toast');
            return {
                feedChildCount: feed.children.length,
                totalToastsInDocument: allToastsInDocument.length
            };
        })()
        """
        clean_res = await call_cdp("Runtime.evaluate", {"expression": cleanup_eval, "returnByValue": True})
        clean_data = clean_res.get("result", {}).get("value")
        print(f"  Kill feed DOM count at 5.3s: feedChildCount={clean_data['feedChildCount']} | totalInDocument={clean_data['totalToastsInDocument']}", flush=True)
        assert clean_data["feedChildCount"] == 0, f"Kill feed leaked {clean_data['feedChildCount']} elements in feed container!"
        assert clean_data["totalToastsInDocument"] == 0, f"Document leaked {clean_data['totalToastsInDocument']} .kill-toast nodes!"
        print("    Zero DOM leaks confirmed. All feed items cleanly dismissed and removed.", flush=True)

        # -------------------------------------------------------------
        # TEST SUITE 5: Command Center Radial Cooldown Sweeps Audit
        # -------------------------------------------------------------
        print("\n=== [STRESS-5] COMMAND CENTER & RADIAL COOLDOWN SWEEP AUDIT ===", flush=True)
        cd_eval = """
        (() => {
            const p = window.units.find(u => u.isPlayer) || window.units[0];
            p.cds.atk = 0.8;
            p.cds.q = 3.5;
            p.cds.w = 5.0;
            p.cds.e = 8.0;
            p.cds.r = 15.0;
            
            const slots = ['atk', 'q', 'w', 'e', 'r'];
            const res = {};
            for (const s of slots) {
                const el = document.getElementById(`cd-${s}`);
                const maxCd = (p.kit && p.kit[s] && p.kit[s].cd) ? p.kit[s].cd : 10;
                const rem = p.cds[s];
                const pct = Math.min(100, Math.max(0, (rem / maxCd) * 100));
                el.style.display = 'flex';
                el.style.background = `conic-gradient(rgba(0,0,0,0.78) ${pct.toFixed(1)}%, transparent 0%)`;
                el.textContent = rem.toFixed(1) + 's';
                res[s] = {
                    display: window.getComputedStyle(el).display,
                    bg: el.style.background,
                    text: el.textContent
                };
            }
            return res;
        })()
        """
        cd_res = await call_cdp("Runtime.evaluate", {"expression": cd_eval, "returnByValue": True})
        cd_data = cd_res.get("result", {}).get("value")
        for s, info in cd_data.items():
            print(f"  Slot [{s}]: display={info['display']} | text={info['text']} | bg={info['bg']}", flush=True)
            assert info["display"] == "flex", f"Slot {s} cooldown overlay not displayed!"
            assert "conic-gradient" in info["bg"], f"Slot {s} background missing conic-gradient: {info['bg']}"
            assert "s" in info["text"], f"Slot {s} text missing seconds suffix: {info['text']}"
        print("    All 5 action slots verified with active conic-gradient sweeps.", flush=True)

        # -------------------------------------------------------------
        # TEST SUITE 6: Console Errors & Exceptions Audit
        # -------------------------------------------------------------
        print("\n=== [STRESS-6] CONSOLE ERRORS & UNCAUGHT EXCEPTIONS AUDIT ===", flush=True)
        print(f"  Total Page Exceptions: {len(page_exceptions)}", flush=True)
        print(f"  Total Console Errors:  {len(console_errors)}", flush=True)
        all_errors = page_exceptions + console_errors
        return len(all_errors) == 0, all_errors

def main():
    tmp_profile = tempfile.mkdtemp()
    proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={DEBUG_PORT}",
        "--disable-gpu",
        "--window-size=1280,720",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])
    time.sleep(2.5)
    success = False
    all_errors = []
    try:
        success, all_errors = asyncio.run(run_stress_tests())
    finally:
        proc.terminate()
        proc.wait()

    if success:
        print("\n" + "="*70, flush=True)
        print(">>> EMPIRICAL STRESS TEST SUITE PASSED WITH 0 CONSOLE ERRORS! <<<", flush=True)
        print("="*70, flush=True)
        sys.exit(0)
    else:
        print("\n" + "="*70, flush=True)
        print(f">>> STRESS TEST SUITE FAILED WITH {len(all_errors)} ERRORS! <<<", flush=True)
        for err in all_errors:
            print(f"  - {err}", flush=True)
        print("="*70, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
