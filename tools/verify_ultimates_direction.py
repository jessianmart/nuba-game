import asyncio
import json
import urllib.request
import websockets
import subprocess
import os
import base64
import math

EDGE_PATHS = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]

def get_edge():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Edge not found")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'visual_tests')
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def run_visual_verification():
    edge_bin = get_edge()
    port = 9345
    temp_dir = 'C:/temp/edge_ult_direction_test'
    proc = subprocess.Popen([
        edge_bin, '--headless=new', f'--remote-debugging-port={port}',
        f'--user-data-dir={temp_dir}', '--no-first-run', '--no-default-browser-check',
        '--inprivate', '--window-size=1600,900', 'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        await asyncio.sleep(2.5)
        raw = urllib.request.urlopen(f'http://127.0.0.1:{port}/json').read()
        tabs = json.loads(raw)
        ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0]
        ws = await websockets.connect(ws_url, max_size=50_000_000)
        await ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
        await ws.send(json.dumps({'id': 2, 'method': 'Runtime.enable'}))

        req_id = 100
        async def eval_js(expr):
            nonlocal req_id
            req_id += 1
            cid = req_id
            await ws.send(json.dumps({'id': cid, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == cid:
                    res = r.get('result', {})
                    if 'exceptionDetails' in res:
                        raise RuntimeError(f"JS Error: {res['exceptionDetails']}")
                    return res.get('result', {}).get('value')

        async def snap(filename):
            nonlocal req_id
            req_id += 1
            cid = req_id
            await ws.send(json.dumps({'id': cid, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == cid:
                    data = base64.b64decode(r['result']['data'])
                    path = os.path.join(OUTPUT_DIR, filename)
                    with open(path, 'wb') as f:
                        f.write(data)
                    print(f"  [SCREENSHOT] {filename} saved ({len(data)} bytes)")
                    return path

        print("=== NUBA ULTIMATE & DIRECTIONAL SKILL VERIFICATION ===")
        # Start match
        init_res = await eval_js('''
        (async () => {
            for (let w = 0; w < 40; w++) {
                if (window.start5v5Match && window.units && window.units.length > 0) break;
                await new Promise(r => setTimeout(r, 100));
            }
            if (!window.matchActive) {
                await window.start5v5Match();
            }
            const b = document.getElementById('center-banner');
            if (b) b.style.display = 'none';
            return { unitsCount: window.units ? window.units.length : 0 };
        })()
        ''')
        print(f"Match started with {init_res['unitsCount']} units.")
        await asyncio.sleep(0.5)

        # Move other units far away so player's rotY is pure facing East
        await eval_js('''
        (() => {
            const p = window.units.find(u => u.isPlayer);
            for (const u of window.units) {
                if (!u.isPlayer) {
                    u.x = 200; u.z = 200; // Park bots away during direct orientation tests
                }
            }
        })()
        ''')

        heroes = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry']
        
        for hid in heroes:
            test_res = await eval_js(f'''
            (() => {{
                const p = window.units.find(u => u.isPlayer);
                p.heroId = '{hid}';
                p.x = 0; p.z = 0;
                p.rotY = Math.PI / 2; // Facing East (+X direction)
                const dirX = Math.sin(p.rotY); // 1.0
                const dirZ = Math.cos(p.rotY); // 0.0
                p.chakra = 100;
                p.cds.r = 0;
                
                // Clear active VFX to measure this cast
                window.vfxList.length = 0;
                window.arenaGroup.clear();

                window.executeSkill(p, 'r');

                const vfx = window.vfxList;
                const compoundVfx = vfx.filter(v => v.style === 'compound');
                const compoundMeshes = compoundVfx.map(v => v.mesh);

                let info = {{
                    heroId: '{hid}',
                    rotY: p.rotY,
                    dirX, dirZ,
                    compoundCount: compoundMeshes.length,
                    positions: compoundMeshes.map(m => ({{
                        x: Math.round(m.position.x * 100) / 100,
                        y: Math.round(m.position.y * 100) / 100,
                        z: Math.round(m.position.z * 100) / 100,
                        rotY: Math.round(m.rotation.y * 100) / 100
                    }}))
                }};

                if ('{hid}' === '1gar') {{
                    // Shield must be centered on Gaara (p.x, p.z)
                    // Colossal hand must be forward with rotation matching p.rotY
                    const shield = compoundMeshes[0];
                    const hand = compoundMeshes[1];
                    info.shieldOnGaara = Math.hypot(shield.position.x - p.x, shield.position.z - p.z) < 0.1;
                    info.handForward = Math.hypot(hand.position.x - p.x, hand.position.z - p.z) > 5.0;
                    info.handRotMatches = Math.abs(hand.rotation.y - p.rotY) < 0.05;
                }} else if ('{hid}' === '1nej') {{
                    // Kaiten must be centered ON NEJI (p.x, p.z)
                    const kaiten = compoundMeshes[0];
                    info.kaitenOnNeji = Math.hypot(kaiten.position.x - p.x, kaiten.position.z - p.z) < 0.1;
                }} else if ('{hid}' === '1hnt') {{
                    // Hinata twin lion fists must be perpendicular to dir
                    const lf1 = compoundMeshes[0];
                    const lf2 = compoundMeshes[1];
                    info.lf1RotMatches = Math.abs(lf1.rotation.y - p.rotY) < 0.05;
                    info.lf2RotMatches = Math.abs(lf2.rotation.y - p.rotY) < 0.05;
                    const sep = Math.hypot(lf1.position.x - lf2.position.x, lf1.position.z - lf2.position.z);
                    info.perpSeparation = Math.abs(sep - 3.6) < 0.2;
                    info.forwardDist = Math.hypot((lf1.position.x + lf2.position.x)/2 - p.x, (lf1.position.z + lf2.position.z)/2 - p.z) > 5.0;
                }} else if ('{hid}' === '1ssk') {{
                    const kirin = compoundMeshes[0];
                    info.kirinRotMatches = Math.abs(kirin.rotation.y - p.rotY) < 0.05;
                    info.kirinForward = Math.hypot(kirin.position.x - p.x, kirin.position.z - p.z) > 5.0;
                }} else if ('{hid}' === '1kks') {{
                    const rk = compoundMeshes[0];
                    const wd = compoundMeshes[1];
                    const targetRkX = p.x + Math.sin(p.rotY) * 1.5;
                    const targetRkZ = p.z + Math.cos(p.rotY) * 1.5;
                    info.raikiriAtKakashi = Math.hypot(rk.position.x - targetRkX, rk.position.z - targetRkZ) < 0.1;
                    info.dragonForward = Math.hypot(wd.position.x - p.x, wd.position.z - p.z) > 5.0;
                    info.dragonRotMatches = Math.abs(wd.rotation.y - p.rotY) < 0.05;
                }} else if ('{hid}' === '1skr') {{
                    const shatter = compoundMeshes[0];
                    info.shatterForward = Math.hypot(shatter.position.x - p.x, shatter.position.z - p.z) > 5.0;
                    info.shatterRotMatches = Math.abs(shatter.rotation.y - p.rotY) < 0.05;
                }} else if ('{hid}' === '1roc') {{
                    const tornado = compoundMeshes[0];
                    info.tornadoForward = Math.hypot(tornado.position.x - p.x, tornado.position.z - p.z) > 5.0;
                    info.tornadoRotMatches = Math.abs(tornado.rotation.y - p.rotY) < 0.05;
                }} else if ('{hid}' === '1itc') {{
                    const amat = compoundMeshes[0];
                    info.amatForward = Math.hypot(amat.position.x - p.x, amat.position.z - p.z) > 5.0;
                    info.amatRotMatches = Math.abs(amat.rotation.y - p.rotY) < 0.05;
                }} else if ('{hid}' === '1nrt') {{
                    const giantRas = compoundMeshes[0];
                    const shockRing = compoundMeshes[1];
                    info.rasForward = Math.hypot(giantRas.position.x - p.x, giantRas.position.z - p.z) > 5.0;
                    info.shockRingForward = Math.hypot(shockRing.position.x - p.x, shockRing.position.z - p.z) > 5.0;
                }}

                return info;
            }})()
            ''')
            print(f"\n[Hero {hid} Ultimate Test Result]:")
            for k, v in test_res.items():
                if k != 'positions':
                    print(f"  {k}: {v}")
                    if isinstance(v, bool):
                        assert v is True, f"Hero {hid} assertion failed for {k}"
            print(f"  positions: {test_res['positions']}")
            await snap(f"ultimate_dir_{hid}.png")

        # Now test secondary directional skills
        print("\n--- Testing Directional Secondary Skills ---")
        sec_res = await eval_js('''
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.x = 0; p.z = 0;
            p.rotY = Math.PI / 4; // 45 degrees
            window.projectiles.length = 0;
            window.vfxList.length = 0;
            window.arenaGroup.clear();

            // 1. Kakashi W (Water Dragon)
            p.heroId = '1kks';
            p.cds.w = 0; p.chakra = 100;
            window.executeSkill(p, 'w');
            const pWd = window.projectiles[window.projectiles.length - 1];

            // 2. Jiraiya Q (Toad Oil Flame)
            p.heroId = '1jry';
            p.cds.q = 0; p.chakra = 100;
            window.executeSkill(p, 'q');
            const pToad = window.projectiles[window.projectiles.length - 1];

            // 3. Neji W (Air Palm)
            p.heroId = '1nej';
            p.cds.w = 0; p.chakra = 100;
            window.executeSkill(p, 'w');
            const pAir = window.projectiles[window.projectiles.length - 1];

            // 4. Gaara Q (Sand Hand)
            p.heroId = '1gar';
            p.cds.q = 0; p.chakra = 100;
            window.executeSkill(p, 'q');
            const handVfx = window.vfxList.find(v => v.style === 'compound');

            return {
                kakashiW_rotMatches: Math.abs(pWd.mesh.rotation.y - p.rotY) < 0.01,
                kakashiW_isDirectional: pWd.directional === true,
                jiraiyaQ_rotMatches: Math.abs(pToad.mesh.rotation.y - p.rotY) < 0.01,
                jiraiyaQ_isDirectional: pToad.directional === true,
                nejiW_rotMatches: Math.abs(pAir.mesh.rotation.y - p.rotY) < 0.01,
                nejiW_isDirectional: pAir.directional === true,
                gaaraQ_rotMatches: Math.abs(handVfx.mesh.rotation.y - p.rotY) < 0.01
            };
        })()
        ''')
        print("Secondary Skills Directional Check:")
        for k, v in sec_res.items():
            print(f"  {k}: {v}")
            assert v is True, f"Failed assertion for {k}: expected True, got {v}"

        await snap("secondary_skills_directional.png")
        print("\n>>> ALL VISUAL AND DIRECTIONAL CHECKS PASSED! <<<")

    finally:
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(run_visual_verification())
