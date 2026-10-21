import asyncio, json, urllib.request, websockets, subprocess, os

async def check_console():
    EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if not os.path.exists(EDGE_PATH):
        EDGE_PATH = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    proc = subprocess.Popen([
        EDGE_PATH, '--headless=new', '--remote-debugging-port=9291',
        '--user-data-dir=C:/temp/edge_sd01a_logs', '--no-first-run', '--no-default-browser-check',
        '--inprivate', 'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(2.5)
        raw = urllib.request.urlopen('http://127.0.0.1:9291/json').read()
        tabs = json.loads(raw)
        ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0]
        ws = await websockets.connect(ws_url, max_size=50_000_000)
        await ws.send(json.dumps({'id': 1, 'method': 'Log.enable'}))
        await ws.send(json.dumps({'id': 2, 'method': 'Runtime.enable'}))

        expr = '''
        (async () => {
            for (let w = 0; w < 40; w++) {
                if (window.applyArena && window.start5v5Match) break;
                await new Promise(r => setTimeout(r, 200));
            }
            try {
                console.log("Applying sd01a...");
                await window.applyArena('sd01a');
                console.log("applyArena finished!");
                await window.start5v5Match();
                console.log("start5v5Match finished! ArenaGroup visible:", window.arenaGroup.visible, "children:", window.arenaGroup.children.length);
                const stg = window.cachedStageGroup;
                console.log("cachedStageGroup:", !!stg, "stg children:", stg ? stg.children.length : 0);
                if (stg) {
                    console.log("First 3 mesh names:", stg.children.slice(0, 3).map(c => c.geometry ? c.geometry.attributes.position.count : 0));
                }
                return "SUCCESS";
            } catch(e) {
                console.error("SD01A LOAD ERROR:", e.message, e.stack);
                return "ERROR: " + e.message;
            }
        })()
        '''
        await ws.send(json.dumps({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))

        for _ in range(30):
            r = json.loads(await ws.recv())
            if r.get('method') == 'Runtime.consoleAPICalled':
                print('CONSOLE:', r['params']['type'], [arg.get('value') for arg in r['params']['args']])
            if r.get('id') == 3:
                print('EVAL RESULT:', r.get('result', {}).get('result', {}).get('value'))
                break
        await ws.close()
    finally:
        proc.kill()

asyncio.run(check_console())
