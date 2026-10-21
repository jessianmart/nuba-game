import asyncio, json, urllib.request, websockets, subprocess, os

async def find_mesh():
    EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if not os.path.exists(EDGE_PATH):
        EDGE_PATH = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    proc = subprocess.Popen([
        EDGE_PATH, '--headless=new', '--remote-debugging-port=9293',
        '--user-data-dir=C:/temp/edge_mesh_find', '--no-first-run', '--no-default-browser-check',
        '--inprivate', '--window-size=1600,900', 'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(2.5)
        raw = urllib.request.urlopen('http://127.0.0.1:9293/json').read()
        tabs = json.loads(raw)
        ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0]
        ws = await websockets.connect(ws_url)
        await ws.send(json.dumps({'id': 1, 'method': 'Runtime.enable'}))

        expr = '''
        (async () => {
            for (let w = 0; w < 40; w++) {
                if (window.applyArena && window.start5v5Match) break;
                await new Promise(r => setTimeout(r, 200));
            }
            await window.applyArena('sd03b');
            await window.start5v5Match();
            window.cameraMode = 'cinematic';
            window.camera.position.set(0, 48, 85);
            window.camera.lookAt(0, 4, 0);
            window.camera.updateMatrixWorld(true);

            const results = [];
            const cam = window.camera;
            const stage = window.arenaGroup ? window.arenaGroup.children[0] : null;
            if (!stage) return JSON.stringify({ error: 'Stage not loaded' });
            const v = new THREE.Vector3();

            for (let i = 0; i < stage.children.length; i++) {
                const child = stage.children[i];
                const pos = child.geometry.attributes.position;
                let hasCenter = false;
                let hasLeftScreen = false;
                for (let j = 0; j < pos.count; j++) {
                    v.set(pos.getX(j), pos.getY(j), pos.getZ(j));
                    v.applyMatrix4(child.matrixWorld);
                    // dist from center
                    if (Math.hypot(v.x, v.z) < 15) {
                        hasCenter = true;
                    }
                    v.project(cam);
                    // Screen left: ndc.x between -1.0 and -0.7, ndc.y between -0.2 and 0.4
                    if (v.x < -0.7 && v.y > -0.2 && v.y < 0.4 && v.z > 0 && v.z < 1) {
                        hasLeftScreen = true;
                    }
                }
                if (hasCenter && hasLeftScreen) {
                    results.push({ index: i, name: window.stage3DData.meshes[i].name, tex: window.stage3DData.meshes[i].texture });
                }
            }
            return JSON.stringify(results);
        })()
        '''
        await ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get('id') == 2:
                print('DETECTED SPIKE MESHES:', json.dumps(r.get('result')))
                break
        await ws.close()
    finally:
        proc.kill()

asyncio.run(find_mesh())
