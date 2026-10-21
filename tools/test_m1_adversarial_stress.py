import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys
import os
import tempfile

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

async def stress_test_hud():
    tabs = None
    for _ in range(12):
        try:
            tabs_data = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5).read()
            tabs = json.loads(tabs_data)
            if tabs:
                break
        except Exception:
            time.sleep(0.8)

    if not tabs:
        print("ERROR: Could not connect to remote debugging port!")
        return False

    target_tab = None
    for t in tabs:
        if "localhost:8080" in t.get("url", ""):
            target_tab = t
            break

    if not target_tab:
        print("ERROR: Target tab not found! Available:", [t.get("url") for t in tabs])
        return False

    ws_url = target_tab["webSocketDebuggerUrl"]
    print(f"Connecting to {ws_url}...")

    errors = []
    msg_id = 0

    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
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
                    print(f"[PAGE EXCEPTION] {text}")
                    errors.append(text)
                elif m == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        print(f"[LOG ERROR] {json.dumps(entry)}")
                        errors.append(entry.get("text"))
                elif m == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    if call_type == "error":
                        print(f"[CONSOLE ERROR] {' '.join(str(x) for x in args)}")
                        errors.append(" ".join(str(x) for x in args))

        await call_cdp("Runtime.enable")
        await call_cdp("Log.enable")
        await call_cdp("Page.enable")

        print("Waiting for page load and starting match...")
        await asyncio.sleep(2.5)

        start_eval = """
        (async () => {
            await window.start5v5Match();
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
        print("Match Start Result:", match_res.get("result", {}).get("value"))
        await asyncio.sleep(1.0)

        # STRESS 1: Multi-Kill Frame Burst (4 simultaneous kills)
        print("\n--- STRESS 1: Simultaneous Multi-Kill Frame Burst ---")
        multikill_eval = """
        (() => {
            const killer = window.units[0]; // player (blue_0)
            const victims = window.units.filter(u => u.team === 'red').slice(0, 4); // red_0..3
            victims.forEach((v, idx) => {
                window.dealDamage(killer, v, 5000, `Jutsu-Burst-${idx + 1}`);
            });
            const results = victims.map(v => {
                const icon = document.getElementById(`top-icon-${v.id}`);
                const cd = document.getElementById(`respawn-cd-${v.id}`);
                const dot = icon ? icon.querySelector('.alive-dot') : null;
                return {
                    id: v.id,
                    deadTimer: v.deadTimer,
                    hasDeadClass: icon ? icon.classList.contains('dead') : false,
                    cdText: cd ? cd.textContent : null,
                    dotDisplay: dot ? window.getComputedStyle(dot).display : null
                };
            });
            const feed = document.getElementById('kill-feed');
            return {
                victimsStatus: results,
                feedLength: feed ? feed.children.length : 0
            };
        })()
        """
        mk_res = await call_cdp("Runtime.evaluate", {"expression": multikill_eval, "returnByValue": True})
        mk_data = mk_res.get("result", {}).get("value")
        print("Multi-kill Result:", json.dumps(mk_data, indent=2))
        for vs in mk_data["victimsStatus"]:
            assert vs["hasDeadClass"], f"Victim {vs['id']} missing dead class"
            assert vs["cdText"] in ["5", "4"], f"Victim {vs['id']} expected countdown 5 or 4, got {vs['cdText']}"
            assert vs["dotDisplay"] == "none", f"Victim {vs['id']} alive dot should be none"
        assert mk_data["feedLength"] <= 5, f"Kill feed exceeded 5 items: {mk_data['feedLength']}"

        # STRESS 2: Kill Feed Overflow & Auto-Dismiss Lifecycles
        print("\n--- STRESS 2: Kill Feed Rapid Burst (20 kills) & Auto-Dismiss ---")
        burst_eval = """
        (() => {
            const killer = window.units[0];
            const victim = window.units[5];
            for (let i = 0; i < 20; i++) {
                victim.deadTimer = 0;
                victim.hp = 1000;
                window.dealDamage(killer, victim, 5000, `Super-Strike-${i}`);
            }
            const feed = document.getElementById('kill-feed');
            return {
                feedCountAfter20: feed ? feed.children.length : 0
            };
        })()
        """
        burst_res = await call_cdp("Runtime.evaluate", {"expression": burst_eval, "returnByValue": True})
        burst_data = burst_res.get("result", {}).get("value")
        print("Burst Feed Count:", burst_data["feedCountAfter20"])
        assert burst_data["feedCountAfter20"] == 5, f"Feed count should be capped at 5, got {burst_data['feedCountAfter20']}"

        print("Waiting 5.2s for auto-dismiss lifecycle...")
        await asyncio.sleep(5.2)

        dismiss_eval = """
        (() => {
            const feed = document.getElementById('kill-feed');
            return {
                remainingItems: feed ? feed.children.length : 0
            };
        })()
        """
        dismiss_res = await call_cdp("Runtime.evaluate", {"expression": dismiss_eval, "returnByValue": True})
        dismiss_data = dismiss_res.get("result", {}).get("value")
        print("Feed Count after auto-dismiss:", dismiss_data["remainingItems"])
        assert dismiss_data["remainingItems"] == 0, f"Expected 0 items remaining after 5.2s auto-dismiss, got {dismiss_data['remainingItems']}"

        # STRESS 3: Rapid Drawer Toggling (50 cycles)
        print("\n--- STRESS 3: Rapid Controls Drawer Toggling (50 toggles) ---")
        drawer_stress_eval = """
        (() => {
            const drawer = document.getElementById('controls-drawer');
            const initialHidden = drawer.classList.contains('hidden');
            for (let i = 0; i < 50; i++) {
                window.toggleControlsDrawer();
            }
            const finalHidden = drawer.classList.contains('hidden');
            // Toggle one more time to test open state
            window.toggleControlsDrawer();
            const openState = !drawer.classList.contains('hidden');
            window.toggleControlsDrawer(); // close again
            return {
                initialHidden,
                finalHidden,
                matchesInitial: initialHidden === finalHidden,
                openState
            };
        })()
        """
        ds_res = await call_cdp("Runtime.evaluate", {"expression": drawer_stress_eval, "returnByValue": True})
        ds_data = ds_res.get("result", {}).get("value")
        print("Drawer Stress Result:", json.dumps(ds_data, indent=2))
        assert ds_data["matchesInitial"], "Drawer parity failed after 50 toggles!"
        assert ds_data["openState"], "Drawer should be open after odd toggle!"

        # STRESS 4: Viewport Sizing & Top Bar Conformance (1024, 1280, 1920)
        print("\n--- STRESS 4: Multi-Resolution Top Bar Height Check ---")
        for w, h in [(1024, 768), (1280, 720), (1920, 1080)]:
            await call_cdp("Emulation.setDeviceMetricsOverride", {
                "width": w,
                "height": h,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(0.3)
            res_res = await call_cdp("Runtime.evaluate", {
                "expression": """
                (() => {
                    const topBar = document.querySelector('.hud-top-bar');
                    const rect = topBar.getBoundingClientRect();
                    return {
                        width: rect.width,
                        height: rect.height,
                        isUnder52px: rect.height < 52
                    };
                })()
                """,
                "returnByValue": True
            })
            res_data = res_res.get("result", {}).get("value")
            print(f"Viewport {w}x{h} -> Top Bar Height: {res_data['height']}px (under 52px: {res_data['isUnder52px']})")
            assert res_data["isUnder52px"], f"Top bar at {w}x{h} is {res_data['height']}px (>= 52px)!"

        # STRESS 5: Pointer Events & Pass-Through Audit
        print("\n--- STRESS 5: Pointer Events Overlay Pass-Through Audit ---")
        pe_eval = """
        (() => {
            const killFeed = document.getElementById('kill-feed');
            const worldLabels = document.getElementById('world-labels');
            const centerBanner = document.getElementById('center-banner');
            const bottomHud = document.querySelector('.hud-bottom-moba');
            const cdOverlay = document.querySelector('.cd-radial-overlay');
            const abilityBtn = document.querySelector('.moba-ability-btn');
            const topBar = document.querySelector('.hud-top-bar');

            return {
                killFeedPE: window.getComputedStyle(killFeed).pointerEvents,
                worldLabelsPE: window.getComputedStyle(worldLabels).pointerEvents,
                centerBannerPE: window.getComputedStyle(centerBanner).pointerEvents,
                bottomHudPE: window.getComputedStyle(bottomHud).pointerEvents,
                cdOverlayPE: window.getComputedStyle(cdOverlay).pointerEvents,
                abilityBtnPE: window.getComputedStyle(abilityBtn).pointerEvents,
                topBarPE: window.getComputedStyle(topBar).pointerEvents
            };
        })()
        """
        pe_res = await call_cdp("Runtime.evaluate", {"expression": pe_eval, "returnByValue": True})
        pe_data = pe_res.get("result", {}).get("value")
        print("Pointer Events Result:", json.dumps(pe_data, indent=2))
        assert pe_data["killFeedPE"] == "none", "Kill feed should have pointer-events: none"
        assert pe_data["worldLabelsPE"] == "none", "World labels should have pointer-events: none"
        assert pe_data["bottomHudPE"] == "none", "Bottom HUD container should have pointer-events: none"
        assert pe_data["cdOverlayPE"] == "none", "Cooldown overlay should have pointer-events: none"
        assert pe_data["abilityBtnPE"] == "auto", "Ability button should have pointer-events: auto"
        assert pe_data["topBarPE"] == "auto", "Top bar should have pointer-events: auto"

        # Check Console Errors
        print("\nTotal console errors during stress testing:", len(errors))
        return len(errors) == 0

def main():
    tmp_profile = tempfile.mkdtemp()
    proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--disable-gpu",
        "--window-size=1280,720",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])
    time.sleep(2.5)
    success = False
    try:
        success = asyncio.run(stress_test_hud())
    finally:
        proc.terminate()
        proc.wait()

    if success:
        print("\n>>> ALL ADVERSARIAL STRESS CHECKS PASSED WITH 0 CONSOLE ERRORS! <<<")
        sys.exit(0)
    else:
        print("\n>>> ADVERSARIAL STRESS CHECKS FAILED! <<<")
        sys.exit(1)

if __name__ == "__main__":
    main()
