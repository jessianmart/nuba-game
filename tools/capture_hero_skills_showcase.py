import asyncio, json, urllib.request, websockets, subprocess, os, base64

EDGE_PATHS = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]
def get_edge():
    for p in EDGE_PATHS:
        if os.path.exists(p): return p
    raise FileNotFoundError("Edge not found")

SCRATCH_DIR = r'C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch'

async def capture_showcase():
    edge_bin = get_edge()
    proc = subprocess.Popen([
        edge_bin, '--headless=new', '--remote-debugging-port=9299',
        '--user-data-dir=C:/temp/edge_showcase_v2', '--no-first-run', '--no-default-browser-check',
        '--inprivate', '--window-size=1600,900', 'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        await asyncio.sleep(2.5)
        raw = urllib.request.urlopen('http://127.0.0.1:9299/json').read()
        tabs = json.loads(raw)
        ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0]
        ws = await websockets.connect(ws_url, max_size=50_000_000)
        await ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
        await ws.send(json.dumps({'id': 2, 'method': 'Runtime.enable'}))

        async def eval_js(expr):
            await ws.send(json.dumps({'id': 10, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == 10:
                    return r.get('result', {}).get('result', {}).get('value')

        async def snap(filename):
            await ws.send(json.dumps({'id': 20, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == 20:
                    data = base64.b64decode(r['result']['data'])
                    path = os.path.join(SCRATCH_DIR, filename)
                    with open(path, 'wb') as f:
                        f.write(data)
                    print(f"Captured: {path} ({len(data)} bytes)")
                    break

        # Setup match on Chunin Colosseum
        await eval_js('''
        (async () => {
            for (let w = 0; w < 40; w++) {
                if (window.applyArena && window.arenasCatalog && window.arenasCatalog.length > 0) break;
                await new Promise(r => setTimeout(r, 200));
            }
            await window.applyArena('sd03b');
            await window.start5v5Match();
            const b = document.getElementById('center-banner');
            if (b) b.style.display = 'none';
            const deathOv = document.getElementById('death-overlay');
            if (deathOv) deathOv.style.display = 'none';
            for (const u of window.units) {
                u.hp = 1000;
                u.maxHp = 1000;
                u.deadTimer = 0;
            }
        })()
        ''')
        await asyncio.sleep(0.5)

        # 1. Ranged Basic Attack: 3D Kunais & Shurikens flying towards distant target
        await eval_js('''
        (() => {
            const p = window.units[0];
            p.x = -18; p.z = -10;
            p.rotY = Math.PI / 2; // Facing +X
            if (p.mesh) p.mesh.position.set(p.x, 0, p.z);
            p.cds.atk = 0;
            p.comboStep = 1;
            window.executeSkill(p, 'atk'); // Fires Shurikens
            window.cameraMode = 'cinematic';
            window.camera.position.set(-20, 8, -2);
            window.camera.lookAt(-10, 2.5, -10);
            window.camera.updateMatrixWorld(true);
        })()
        ''')
        await asyncio.sleep(0.2)
        await snap('showcase_basic_ranged_shuriken.png')

        # 2. Melee Taijutsu Combo: Close-quarters kick finisher with cel-shaded hit sparks
        await eval_js('''
        (() => {
            const p = window.units[0];
            const enemy = window.units.find(u => u.team === 'red');
            p.x = -14; p.z = 10;
            p.hp = 1000; p.deadTimer = 0;
            enemy.x = -11.5; enemy.z = 10;
            enemy.hp = 1000; enemy.deadTimer = 0;
            p.rotY = Math.PI / 2;
            enemy.rotY = -Math.PI / 2;
            if (p.mesh) p.mesh.position.set(p.x, 0, p.z);
            if (enemy.mesh) enemy.mesh.position.set(enemy.x, 0, enemy.z);
            p.cds.atk = 0;
            p.comboStep = 2; // Finisher Kick!
            window.executeSkill(p, 'atk');
            window.cameraMode = 'cinematic';
            window.camera.position.set(-16, 4.5, 17);
            window.camera.lookAt(-12.5, 2.0, 10);
            window.camera.updateMatrixWorld(true);
        })()
        ''')
        await asyncio.sleep(0.2)
        await snap('showcase_basic_melee_taijutsu.png')

        # 3. Gaara Suna no Tate (Sand Shield) & Itachi Katon Fireball
        await eval_js('''
        (() => {
            const gar = window.units.find(u => u.heroId === '1gar');
            if (gar) {
                gar.x = 8; gar.z = -12;
                gar.hp = 1000; gar.deadTimer = 0;
                if (gar.mesh) gar.mesh.position.set(gar.x, 0, gar.z);
                gar.cds.w = 0; gar.chakra = 100;
                window.executeSkill(gar, 'w'); // Sand shield
            }
            const itc = window.units.find(u => u.heroId === '1itc');
            if (itc) {
                itc.x = 18; itc.z = -12;
                itc.rotY = -Math.PI / 2; // Facing west towards Gaara
                itc.hp = 1000; itc.deadTimer = 0;
                if (itc.mesh) itc.mesh.position.set(itc.x, 0, itc.z);
                itc.cds.w = 0; itc.chakra = 100;
                window.executeSkill(itc, 'w'); // Katon Goukakyuu Fireball
            }
            window.cameraMode = 'cinematic';
            window.camera.position.set(13, 7.5, -2);
            window.camera.lookAt(13, 2.0, -12);
            window.camera.updateMatrixWorld(true);
        })()
        ''')
        await asyncio.sleep(0.3)
        await snap('showcase_gaara_itachi_skills.png')

        # 4. Kakashi Raikiri / Water Dragon & Sasuke Chidori
        await eval_js('''
        (() => {
            const kks = window.units.find(u => u.heroId === '1kks');
            if (kks) {
                kks.x = -10; kks.z = -15;
                kks.rotY = Math.PI / 2;
                kks.hp = 1000; kks.deadTimer = 0;
                if (kks.mesh) kks.mesh.position.set(kks.x, 0, kks.z);
                kks.cds.q = 0; kks.chakra = 100;
                window.executeSkill(kks, 'q'); // Raikiri
            }
            const ssk = window.units.find(u => u.heroId === '1ssk');
            if (ssk) {
                ssk.x = 0; ssk.z = -15;
                ssk.rotY = -Math.PI / 2;
                ssk.hp = 1000; ssk.deadTimer = 0;
                if (ssk.mesh) ssk.mesh.position.set(ssk.x, 0, ssk.z);
                ssk.cds.q = 0; ssk.chakra = 100;
                window.executeSkill(ssk, 'q'); // Chidori
            }
            window.cameraMode = 'cinematic';
            window.camera.position.set(-5, 6.0, -6);
            window.camera.lookAt(-5, 2.0, -15);
            window.camera.updateMatrixWorld(true);
        })()
        ''')
        await asyncio.sleep(0.3)
        await snap('showcase_kakashi_sasuke_lightning.png')

        await ws.close()
    finally:
        proc.kill()

asyncio.run(capture_showcase())
