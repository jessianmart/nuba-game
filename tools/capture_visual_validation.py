"""Capture high-fidelity visual validation screenshots of the Chunin Exam arenas
and authentic Storm skills in NUBA.
"""
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import websockets

sys.stdout.reconfigure(encoding='utf-8')

PORT = 8080
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

SCRATCH_DIR = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch"
os.makedirs(SCRATCH_DIR, exist_ok=True)

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

async def main():
    free_port = get_free_port()
    tmp_profile = os.path.join(os.environ.get('TEMP', '.'), f'edge_vis_{free_port}')
    proc = subprocess.Popen([
        EDGE_PATH,
        '--headless=new',
        f'--remote-debugging-port={free_port}',
        f'--user-data-dir={tmp_profile}',
        '--no-first-run',
        '--no-default-browser-check',
        '--inprivate',
        '--window-size=1600,900',
        '--disable-gpu',
        '--hide-scrollbars',
        f'http://localhost:{PORT}/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    msg_id = 0
    ws = None

    try:
        await asyncio.sleep(3.0)
        # Wait for CDP endpoint
        for _ in range(30):
            try:
                data = urllib.request.urlopen(f'http://127.0.0.1:{free_port}/json', timeout=1).read()
                tabs = json.loads(data.decode('utf-8'))
                target_tab = None
                for t in tabs:
                    if "localhost" in t.get("url", ""):
                        target_tab = t
                        break
                if target_tab:
                    ws_url = target_tab['webSocketDebuggerUrl']
                    ws = await websockets.connect(ws_url, max_size=50_000_000)
                    break
            except Exception:
                await asyncio.sleep(0.3)

        if not ws:
            raise RuntimeError("Failed to connect to Edge CDP")

        async def send_cdp(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cur_id = msg_id
            payload = {"id": cur_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get("id") == cur_id:
                    res = data.get("result", {})
                    if "exceptionDetails" in res:
                        print("CDP EVAL EXCEPTION:", res["exceptionDetails"])
                    return res

        await send_cdp("Page.enable")
        await send_cdp("Runtime.enable")

        # Wait for page assets and Three.js initialization
        print("Waiting for page assets and Three.js initialization...")
        for _ in range(40):
            res_rdy = await send_cdp("Runtime.evaluate", {
                "expression": "Boolean(window.rosterMeta && window.animationsData && window.lobbyHeroMesh && window.start5v5Match)",
                "returnByValue": True
            })
            if res_rdy.get("result", {}).get("value") is True:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.0)

        async def capture_screenshot(filename):
            shot = await send_cdp("Page.captureScreenshot", {"format": "png"})
            data_bytes = base64.b64decode(shot["data"])
            filepath = os.path.join(SCRATCH_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(data_bytes)
            print(f"Saved: {filepath} ({len(data_bytes)} bytes)")
            return filepath

        # --- 1. CHŪNIN EXAM COLISEUM (sd03b) PANORAMA ---
        print("\n--- 1. Capturing Chūnin Exam Colosseum (sd03b) ---")
        await send_cdp("Runtime.evaluate", {
            "expression": """
            (async () => {
                await window.applyArena('sd03b');
                await window.start5v5Match();
                const b = document.getElementById('center-banner');
                if (b) b.classList.add('hidden');
                window.cameraMode = 'cinematic';
                window.camera.position.set(0, 48, 85);
                window.camera.lookAt(0, 4, 0);
                window.camera.fov = 55;
                window.camera.updateProjectionMatrix();
            })()
            """,
            "awaitPromise": True
        })
        await asyncio.sleep(1.2)
        await capture_screenshot("chunin_colosseum_overview.png")

        # --- 2. CHŪNIN EXAM COLISEUM BATTLE ACTION WITH SKILLS ---
        print("\n--- 2. Capturing Chūnin Battle Action with Skills ---")
        await send_cdp("Runtime.evaluate", {
            "expression": """
            (() => {
                window.cameraMode = 'cinematic';
                const p = window.units[0];
                p.x = 0; p.z = 8;
                if (p.mesh) p.mesh.position.set(p.x, 0, p.z);
                // Trigger Rasengan Dash [Q]
                p.cds.q = 0; p.chakra = 100;
                window.executeSkill(p, 'q');
                // Bot triggers Chidori [Q]
                const b = window.units.find(u => u.heroId === '1ssk');
                if (b) {
                    b.x = 0; b.z = -8;
                    if (b.mesh) b.mesh.position.set(b.x, 0, b.z);
                    b.cds.q = 0; b.chakra = 100;
                    window.executeSkill(b, 'q');
                }
                // Cinematic action camera
                window.camera.position.set(16, 8, 12);
                window.camera.lookAt(0, 2, 0);
                window.camera.fov = 50;
                window.camera.updateProjectionMatrix();
            })()
            """
        })
        await asyncio.sleep(0.4)
        await capture_screenshot("chunin_battle_action_closeup.png")

        # --- 3. CHŪNIN FINALS STADIUM (sd04a) PANORAMA ---
        print("\n--- 3. Capturing Chūnin Finals Stadium (sd04a) ---")
        await send_cdp("Runtime.evaluate", {
            "expression": """
            (async () => {
                await window.applyArena('sd04a');
                window.cameraMode = 'cinematic';
                window.camera.position.set(0, 50, 95);
                window.camera.lookAt(0, 4, 0);
                window.camera.fov = 55;
                window.camera.updateProjectionMatrix();
            })()
            """,
            "awaitPromise": True
        })
        await asyncio.sleep(1.2)
        await capture_screenshot("chunin_finals_stadium_overview.png")

        # --- 4. CHŪNIN PRELIMINARIES TOWER (sd01b) WITH HAND SEAL STATUE ---
        print("\n--- 4. Capturing Chūnin Preliminaries Tower (sd01b) ---")
        await send_cdp("Runtime.evaluate", {
            "expression": """
            (async () => {
                await window.applyArena('sd01b');
                window.cameraMode = 'cinematic';
                window.camera.position.set(0, 16, 38);
                window.camera.lookAt(0, 10, -18);
                window.camera.fov = 55;
                window.camera.updateProjectionMatrix();
            })()
            """,
            "awaitPromise": True
        })
        await asyncio.sleep(1.2)
        await capture_screenshot("chunin_tower_overview.png")

        print("\n>>> ALL VISUAL VALIDATION SCREENSHOTS CAPTURED SUCCESSFULLY! <<<")

    finally:
        if ws:
            await ws.close()
        proc.kill()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        try:
            import shutil
            shutil.rmtree(tmp_profile, ignore_errors=True)
        except Exception:
            pass

if __name__ == '__main__':
    asyncio.run(main())
