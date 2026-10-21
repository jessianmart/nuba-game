import asyncio, json, urllib.request, websockets, subprocess, os, base64

async def capture_skills():
    EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if not os.path.exists(EDGE_PATH):
        EDGE_PATH = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    proc = subprocess.Popen([
        EDGE_PATH, '--headless=new', '--remote-debugging-port=9288',
        '--user-data-dir=C:/temp/edge_skills_vis', '--no-first-run', '--no-default-browser-check',
        '--inprivate', '--window-size=1600,900', 'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(2.5)
        raw = urllib.request.urlopen('http://127.0.0.1:9288/json').read()
        tabs = json.loads(raw)
        ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0]
        ws = await websockets.connect(ws_url, max_size=50_000_000)
        await ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
        await ws.send(json.dumps({'id': 2, 'method': 'Runtime.enable'}))

        async def capture_to(filename):
            await ws.send(json.dumps({'id': 100, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == 100:
                    data = base64.b64decode(r['result']['data'])
                    path = os.path.join(r'C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch', filename)
                    with open(path, 'wb') as f:
                        f.write(data)
                    print(f"Captured: {path} ({len(data)} bytes)")
                    break

        # 1. Start match on sd03b Colosseum and fire Naruto Rasengan [Q] + Sasuke Chidori [Q]
        setup_expr = '''
        (async () => {
            for (let w = 0; w < 40; w++) {
                if (window.applyArena && window.arenasCatalog && window.arenasCatalog.length > 0) break;
                await new Promise(r => setTimeout(r, 200));
            }
            await window.applyArena('sd03b');
            await window.start5v5Match();
            const banner = document.getElementById('center-banner');
            if (banner) banner.style.display = 'none';
            
            const p = window.units[0]; // Naruto
            p.x = 0; p.z = 6;
            if (p.mesh) p.mesh.position.set(p.x, 0, p.z);
            p.cds.q = 0; p.chakra = 100;
            window.executeSkill(p, 'q');

            const ssk = window.units.find(u => u.heroId === '1ssk');
            if (ssk) {
                ssk.x = 4; ssk.z = 2;
                if (ssk.mesh) ssk.mesh.position.set(ssk.x, 0, ssk.z);
                ssk.cds.q = 0; ssk.chakra = 100;
                window.executeSkill(ssk, 'q');
            }

            const nej = window.units.find(u => u.heroId === '1nej');
            if (nej) {
                nej.x = -6; nej.z = 3;
                if (nej.mesh) nej.mesh.position.set(nej.x, 0, nej.z);
                nej.cds.q = 0; nej.chakra = 100;
                window.executeSkill(nej, 'q');
            }

            window.cameraMode = 'cinematic';
            window.camera.position.set(0, 10, 22);
            window.camera.lookAt(0, 2, 3);
            window.camera.updateMatrixWorld(true);
            return { vfxCount: window.vfxList ? window.vfxList.length : 0 };
        })()
        '''
        await ws.send(json.dumps({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': setup_expr, 'awaitPromise': True, 'returnByValue': True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get('id') == 3:
                print('SETUP RESULT:', r.get('result', {}).get('result', {}).get('value'))
                break
        
        await asyncio.sleep(0.4)
        await capture_to('live_skills_storm_vfx_closeup.png')

        # 2. Fire Ultimate Ougi [R] for Naruto and Kirin [R] for Sasuke
        ult_expr = '''
        (() => {
            const p = window.units[0];
            p.cds.r = 0; p.chakra = 100;
            window.executeSkill(p, 'r');

            const ssk = window.units.find(u => u.heroId === '1ssk');
            if (ssk) {
                ssk.cds.r = 0; ssk.chakra = 100;
                window.executeSkill(ssk, 'r');
            }
            window.camera.position.set(0, 16, 28);
            window.camera.lookAt(0, 4, 3);
            window.camera.updateMatrixWorld(true);
        })()
        '''
        await ws.send(json.dumps({'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': ult_expr}}))
        await asyncio.sleep(0.5)
        await capture_to('live_ultimate_storm_vfx.png')

        await ws.close()
    finally:
        proc.kill()

asyncio.run(capture_skills())
