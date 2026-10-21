import asyncio, json, urllib.request, websockets, subprocess, os, base64

async def capture_sd01a():
    EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if not os.path.exists(EDGE_PATH):
        EDGE_PATH = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    proc = subprocess.Popen([
        EDGE_PATH, '--headless=new', '--remote-debugging-port=9292',
        '--user-data-dir=C:/temp/edge_sd01a', '--no-first-run', '--no-default-browser-check',
        '--inprivate', '--window-size=1600,900', 'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(2.5)
        raw = urllib.request.urlopen('http://127.0.0.1:9292/json').read()
        tabs = json.loads(raw)
        ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0]
        ws = await websockets.connect(ws_url, max_size=50_000_000)
        await ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
        await ws.send(json.dumps({'id': 2, 'method': 'Runtime.enable'}))

        # Check console logs
        expr = '''
        (async () => {
            for (let w = 0; w < 40; w++) {
                if (window.applyArena && window.arenasCatalog && window.arenasCatalog.length > 0) break;
                await new Promise(r => setTimeout(r, 200));
            }
            const res = await window.applyArena('sd01a');
            await window.start5v5Match();
            const banner = document.getElementById('center-banner');
            if (banner) banner.style.display = 'none';
            window.cameraMode = 'moba';
            window.updateCameraAndHUD();
            window.camera.updateMatrixWorld(true);
            return {
                selectedArenaId: window.selectedArenaId,
                stageId: window.stage3DData ? window.stage3DData.id : null,
                meshes: window.stage3DData ? window.stage3DData.meshes.length : 0,
                bounds: window.stage3DData ? window.stage3DData.bounds : null,
                playerPos: window.units && window.units[0] ? { x: window.units[0].x, y: window.units[0].y, z: window.units[0].z } : null
            };
        })()
        '''
        await ws.send(json.dumps({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
        
        while True:
            r = json.loads(await ws.recv())
            if r.get('method') == 'Runtime.consoleAPICalled':
                print('CONSOLE:', r['params']['type'], [arg.get('value') for arg in r['params']['args']])
            if r.get('id') == 3:
                print('SD01A STATUS:', r.get('result', {}).get('result', {}).get('value'))
                break
        
        await asyncio.sleep(1.0)
        await ws.send(json.dumps({'id': 4, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get('id') == 4:
                shot_data = base64.b64decode(r['result']['data'])
                out_path = r'C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\sd01a_valedamorte_debug.png'
                with open(out_path, 'wb') as f:
                    f.write(shot_data)
                print('Saved screenshot to:', out_path)
                break
        await ws.close()
    finally:
        proc.kill()

asyncio.run(capture_sd01a())
