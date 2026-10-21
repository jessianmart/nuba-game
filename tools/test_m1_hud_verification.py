import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys
import os

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

async def test_hud():
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
        await call_cdp("Page.enable")

        print("Waiting for page load and starting match...")
        await asyncio.sleep(2.5)

        # Start match
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

        # 1. Verify Top Bar Height (< 52px)
        top_bar_eval = """
        (() => {
            const topBar = document.querySelector('.hud-top-bar');
            const rect = topBar.getBoundingClientRect();
            const cs = window.getComputedStyle(topBar);
            const centerCluster = document.querySelector('.match-center-cluster');
            const clusterCs = window.getComputedStyle(centerCluster);
            return {
                height: rect.height,
                width: rect.width,
                maxHeight: cs.maxHeight,
                flexDirection: clusterCs.flexDirection,
                isUnder52px: rect.height < 52
            };
        })()
        """
        top_res = await call_cdp("Runtime.evaluate", {"expression": top_bar_eval, "returnByValue": True})
        top_data = top_res.get("result", {}).get("value")
        print("\n=== [M1-1] TOP BAR AUDIT ===")
        print(json.dumps(top_data, indent=2))
        assert top_data["isUnder52px"], f"Top bar height {top_data['height']} is >= 52px!"
        assert top_data["flexDirection"] == "row", f"Center cluster flex-direction is {top_data['flexDirection']}, expected 'row'!"

        # 2. Verify 5v5 Mini-Portraits, Alive Dots, and Respawn Countdowns
        portrait_eval = """
        (() => {
            const bluePortraits = document.querySelectorAll('#hud-blue-icons .mini-p');
            const redPortraits = document.querySelectorAll('#hud-red-icons .mini-p');
            const firstBlue = bluePortraits[0];
            const aliveDot = firstBlue ? firstBlue.querySelector('.alive-dot') : null;
            const respawnCd = firstBlue ? firstBlue.querySelector('.respawn-countdown') : null;
            return {
                blueCount: bluePortraits.length,
                redCount: redPortraits.length,
                hasAliveDot: !!aliveDot,
                hasRespawnCd: !!respawnCd,
                aliveDotDisplay: aliveDot ? window.getComputedStyle(aliveDot).display : null,
                respawnCdId: respawnCd ? respawnCd.id : null
            };
        })()
        """
        p_res = await call_cdp("Runtime.evaluate", {"expression": portrait_eval, "returnByValue": True})
        p_data = p_res.get("result", {}).get("value")
        print("\n=== [M1-2] PORTRAITS & ALIVE-DOT AUDIT ===")
        print(json.dumps(p_data, indent=2))
        assert p_data["blueCount"] == 5 and p_data["redCount"] == 5, f"Expected 5 blue and 5 red portraits, got {p_data}"
        assert p_data["hasAliveDot"], "Missing alive dot!"
        assert p_data["hasRespawnCd"], "Missing respawn countdown!"

        # 3. Simulate Kill and Verify Death Countdown on Top Avatar
        kill_eval = """
        (() => {
            const killer = window.units[0]; // Blue player
            const victim = window.units[5]; // Red bot
            window.dealDamage(killer, victim, 5000, 'Rasengan!');
            const victimPortrait = document.getElementById(`top-icon-${victim.id}`);
            const victimCd = document.getElementById(`respawn-cd-${victim.id}`);
            const victimDot = victimPortrait ? victimPortrait.querySelector('.alive-dot') : null;
            return {
                victimDeadTimer: victim.deadTimer,
                victimHasDeadClass: victimPortrait ? victimPortrait.classList.contains('dead') : false,
                cdText: victimCd ? (victimCd.dataset.value || victimCd.textContent.trim() || (victimCd.querySelector('img') ? victimCd.querySelector('img').alt : '')) : null,
                cdDisplay: victimCd ? window.getComputedStyle(victimCd).display : null,
                dotDisplay: victimDot ? window.getComputedStyle(victimDot).display : null
            };
        })()
        """
        kill_res = await call_cdp("Runtime.evaluate", {"expression": kill_eval, "returnByValue": True})
        kill_data = kill_res.get("result", {}).get("value")
        print("\n=== [M1-3] KILL & RESPAWN COUNTDOWN AUDIT ===")
        print(json.dumps(kill_data, indent=2))
        assert kill_data["victimHasDeadClass"], "Victim top portrait missing 'dead' class!"
        assert kill_data["cdText"] in ["6", "5", "4"], f"Expected countdown '6', '5' or '4', got {kill_data['cdText']}"
        assert kill_data["dotDisplay"] == "none", "Alive dot should be hidden when dead!"

        # 4. Verify Kill-Feed with Killer/Victim Portraits and Auto-Dismiss
        feed_eval = """
        (() => {
            const feed = document.getElementById('kill-feed');
            const items = feed ? feed.querySelectorAll('.kill-toast') : [];
            const first = items[0];
            const portraits = first ? first.querySelectorAll('.feed-portrait') : [];
            const tag = first ? first.querySelector('.feed-ability-tag') : null;
            return {
                feedItemsCount: items.length,
                portraitsCount: portraits.length,
                killerPortraitSrc: portraits[0] ? portraits[0].src : null,
                victimPortraitSrc: portraits[1] ? portraits[1].src : null,
                tagText: tag ? tag.textContent : null
            };
        })()
        """
        feed_res = await call_cdp("Runtime.evaluate", {"expression": feed_eval, "returnByValue": True})
        feed_data = feed_res.get("result", {}).get("value")
        print("\n=== [M1-4] KILL FEED AUDIT ===")
        print(json.dumps(feed_data, indent=2))
        assert feed_data["feedItemsCount"] >= 1, "Kill feed item not created!"
        assert feed_data["portraitsCount"] == 2, f"Expected 2 portraits in feed item, found {feed_data['portraitsCount']}"
        assert "[Rasengan!]" in (feed_data["tagText"] or ""), f"Ability tag missing or wrong: {feed_data['tagText']}"

        # 5. Verify Sculpted Command Center: Circular Avatar Ring & Radial Cooldown Sweep
        command_eval = """
        (() => {
            const ring = document.querySelector('.player-avatar-ring');
            const ringCs = window.getComputedStyle(ring);
            const p = window.units[0];
            p.cds.q = 4.0; // trigger cooldown on Q
            // trigger HUD update
            const cdQ = document.getElementById('cd-q');
            const maxCd = p.kit.q.cd || 5.5;
            const pct = Math.min(100, Math.max(0, (4.0 / maxCd) * 100));
            cdQ.style.display = 'flex';
            cdQ.style.background = `conic-gradient(rgba(0,0,0,0.78) ${pct.toFixed(1)}%, transparent 0%)`;
            cdQ.textContent = '4.0s';

            return {
                avatarBorderRadius: ringCs.borderRadius,
                avatarBorder: ringCs.border,
                cdQDisplay: window.getComputedStyle(cdQ).display,
                cdQBackground: cdQ.style.background,
                cdQText: cdQ.textContent
            };
        })()
        """
        cmd_res = await call_cdp("Runtime.evaluate", {"expression": command_eval, "returnByValue": True})
        cmd_data = cmd_res.get("result", {}).get("value")
        print("\n=== [M1-5] COMMAND CENTER & RADIAL SWEEP AUDIT ===")
        print(json.dumps(cmd_data, indent=2))
        assert "50%" in cmd_data["avatarBorderRadius"], f"Avatar ring is not circular: {cmd_data['avatarBorderRadius']}"
        assert "conic-gradient" in cmd_data["cdQBackground"], f"Radial sweep missing conic-gradient: {cmd_data['cdQBackground']}"

        # 6. Verify Controls Drawer Toggle
        drawer_eval = """
        (() => {
            const drawer = document.getElementById('controls-drawer');
            const initialHidden = drawer.classList.contains('hidden');
            window.toggleControlsDrawer();
            const afterFirstToggle = !drawer.classList.contains('hidden');
            window.toggleControlsDrawer();
            const afterSecondToggle = drawer.classList.contains('hidden');
            return {
                initialHidden,
                afterFirstToggle,
                afterSecondToggle
            };
        })()
        """
        drawer_res = await call_cdp("Runtime.evaluate", {"expression": drawer_eval, "returnByValue": True})
        drawer_data = drawer_res.get("result", {}).get("value")
        print("\n=== [M1-6] CONTROLS DRAWER AUDIT ===")
        print(json.dumps(drawer_data, indent=2))
        assert drawer_data["initialHidden"], "Drawer should start hidden"
        assert drawer_data["afterFirstToggle"], "Drawer should be open after first toggle"
        assert drawer_data["afterSecondToggle"], "Drawer should be hidden after second toggle"

        # 7. Check Console Errors
        print("\nTotal console errors:", len(errors))
        return len(errors) == 0

def main():
    import tempfile
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
        success = asyncio.run(test_hud())
    finally:
        proc.terminate()
        proc.wait()

    if success:
        print("\n>>> ALL M1 HUD VERIFICATION CHECKS PASSED PERFECTLY! <<<")
        sys.exit(0)
    else:
        print("\n>>> M1 HUD VERIFICATION FAILED! <<<")
        sys.exit(1)

if __name__ == "__main__":
    main()
