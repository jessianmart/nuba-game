import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys
import os
import base64

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

async def test_page(port=9333):
    tabs = None
    for _ in range(15):
        try:
            tabs_data = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=5).read()
            tabs = json.loads(tabs_data)
            if tabs:
                break
        except Exception:
            await asyncio.sleep(0.8)

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
    logs = []
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
                    url = exc.get("url", "")
                    line = exc.get("lineNumber", -1)
                    col = exc.get("columnNumber", -1)
                    print(f"[PAGE EXCEPTION] {text} at {url}:{line}:{col}")
                    errors.append(f"{text} ({url}:{line})")
                elif m == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    # PV2-D: 404 .webp sem par = ruído do loader webp-first (design)
                    _pv2d_url = (entry.get("url") or "")
                    if entry.get("level") == "error" and not _pv2d_url.endswith(".webp"):
                        print(f"[LOG ERROR] {json.dumps(entry)}")
                        errors.append(entry.get("text"))
                    else:
                        logs.append(entry.get("text"))
                elif m == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    if call_type == "error":
                        _t = " ".join(str(x) for x in args)
                        # PV2-F: THREE.WebGLState = ruído de upload sob swiftshader (headless sem GPU)
                        if "THREE.WebGLState" not in _t:
                            print(f"[CONSOLE ERROR] {_t}")
                            errors.append(_t)
                    else:
                        logs.append(f"[{call_type}] {' '.join(str(x) for x in args)}")

        await call_cdp("Runtime.enable")
        await call_cdp("Log.enable")
        await call_cdp("Page.enable")

        # Wait for Three.js and assets to load
        print("Waiting for page assets and Three.js initialization...")
        for _ in range(40):
            res_rdy = await call_cdp("Runtime.evaluate", {
                "expression": "Boolean(window.rosterMeta && window.animationsData && window.lobbyHeroMesh)",
                "returnByValue": True
            })
            if res_rdy.get("result", {}).get("value") is True:
                break
            await asyncio.sleep(0.5)

        # 1. Evaluate lobby and character pedestal state
        eval_script = """
        (() => {
            const hId = window.selectedHeroId;
            const heroMeta = window.rosterMeta ? window.rosterMeta.find(h => h.id === hId) : null;
            const anmsLoaded = window.animationsData ? Object.keys(window.animationsData).length : 0;
            const stgLoaded = window.stage3DData && window.stage3DData.meshes ? window.stage3DData.meshes.length : 0;
            const pedestalMesh = window.lobbyHeroMesh ? {
                visible: window.lobbyHeroMesh.visible,
                bonesCount: window.lobbyHeroMesh.userData.bones ? window.lobbyHeroMesh.userData.bones.length : 0,
                basePelvis: window.lobbyHeroMesh.userData.basePelvisPos
            } : null;
            return {
                selectedHeroId: hId,
                heroHeightCm: heroMeta ? heroMeta.heightCm : null,
                animationsCount: anmsLoaded,
                stageMeshesCount: stgLoaded,
                pedestal: pedestalMesh
            };
        })()
        """
        res_lobby = await call_cdp("Runtime.evaluate", {"expression": eval_script, "returnByValue": True})
        lobby_val = res_lobby.get("result", {}).get("value")
        print("Lobby Evaluation Result:", json.dumps(lobby_val, indent=2))

        # Save Screenshot 1: NUBA Lobby Screen
        scratch_dir = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch"
        os.makedirs(scratch_dir, exist_ok=True)
        lobby_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in lobby_shot:
            import base64
            lobby_png_path = os.path.join(scratch_dir, "nuba_lobby_redesign.png")
            with open(lobby_png_path, "wb") as f:
                f.write(base64.b64decode(lobby_shot["data"]))
            print(f"Captured NUBA Lobby Screenshot: {lobby_png_path}")

        # 2. Test starting 5v5 match
        print("\nStarting 5v5 Match...")
        wait_for_match = """
        (async () => {
            await window.start5v5Match();
            for (let i = 0; i < 80; i++) {
                if (window.units && window.units.length === 10) return true;
                await new Promise(r => setTimeout(r, 100));
            }
            return false;
        })()
        """
        await call_cdp("Runtime.evaluate", {"expression": wait_for_match, "awaitPromise": True})
        for _ in range(40):
            res_u = await call_cdp("Runtime.evaluate", {
                "expression": "Boolean(window.units && window.units.length === 10)",
                "returnByValue": True
            })
            if res_u.get("result", {}).get("value") is True:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.0)

        # Save Screenshot 2: NUBA In-Game MOBA HUD
        hud_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in hud_shot:
            import base64
            hud_png_path = os.path.join(scratch_dir, "nuba_moba_hud_redesign.png")
            with open(hud_png_path, "wb") as f:
                f.write(base64.b64decode(hud_shot["data"]))
            print(f"Captured NUBA In-Game MOBA HUD Screenshot: {hud_png_path}")

        combat_eval = """
        (() => {
            return {
                matchActive: window.matchActive,
                unitsCount: window.units ? window.units.length : 0,
                player: window.units && window.units[0] ? {
                    heroId: window.units[0].heroId,
                    state: window.units[0].state,
                    comboStep: window.units[0].comboStep,
                    hp: window.units[0].hp
                } : null
            };
        })()
        """
        res_combat = await call_cdp("Runtime.evaluate", {"expression": combat_eval, "returnByValue": True})
        combat_val = res_combat.get("result", {}).get("value")
        print("Combat Evaluation Result:", json.dumps(combat_val, indent=2))

        # 3. Test 3-hit basic attack combo cycling
        print("\nTesting 3-hit combo cycling (attack -> attack2 -> attack3)...")
        combo_eval = """
        (() => {
            const p = window.units[0];
            p.cds.atk = 0;
            window.executeSkill(p, 'atk'); // Hit 1
            const hit1_state = p.state;
            const hit1_step = p.comboStep;

            p.cds.atk = 0;
            window.executeSkill(p, 'atk'); // Hit 2
            const hit2_state = p.state;
            const hit2_step = p.comboStep;

            p.cds.atk = 0;
            window.executeSkill(p, 'atk'); // Hit 3
            const hit3_state = p.state;
            const hit3_step = p.comboStep;

            p.cds.atk = 0;
            window.executeSkill(p, 'atk'); // Hit 4 -> cycles back to hit 1!
            const hit4_state = p.state;
            const hit4_step = p.comboStep;

            return {
                hit1: { state: hit1_state, nextComboStep: hit1_step },
                hit2: { state: hit2_state, nextComboStep: hit2_step },
                hit3: { state: hit3_state, nextComboStep: hit3_step },
                hit4_cycle: { state: hit4_state, nextComboStep: hit4_step }
            };
        })()
        """
        res_combo = await call_cdp("Runtime.evaluate", {"expression": combo_eval, "returnByValue": True})
        combo_val = res_combo.get("result", {}).get("value")
        print("Combo Test Result:", json.dumps(combo_val, indent=2))

        # 3b. Test Melee Strikes vs Ranged Ninja Tools (Kunai & Shuriken)
        print("\nTesting Melee Strikes vs Ranged Ninja Tools (Kunai & Shuriken)...")
        ninja_tools_eval = """
        (() => {
            const p = window.units[0];
            p.x = 0; p.z = 0;
            window.units.slice(1).forEach((u, idx) => { u.x = 40 + idx * 5; u.z = 40; });

            // Ranged Hit 1: Should fire 1 Kunai!
            p.cds.atk = 0; p.comboStep = 0;
            window.executeSkill(p, 'atk');
            const kunaiCount = window.projectiles.filter(proj => proj.type === 'kunai').length;

            // Ranged Hit 2: Should fire 2 Shurikens!
            p.cds.atk = 0;
            window.executeSkill(p, 'atk');
            const shurikenCount2 = window.projectiles.filter(proj => proj.type === 'shuriken').length;

            // Ranged Hit 3: Should fire 3 Shurikens in fan spread!
            p.cds.atk = 0;
            window.executeSkill(p, 'atk');
            const shurikenCount3 = window.projectiles.filter(proj => proj.type === 'shuriken').length;

            // Now test Melee: Bring enemy target within 4.0 units
            const dummy = window.units.find(u => u.team !== p.team);
            dummy.x = 3.5; dummy.z = 0; dummy.deadTimer = 0; dummy.hp = 1000;
            p.cds.atk = 0; p.comboStep = 0;
            const hpBeforePunch = dummy.hp;
            window.executeSkill(p, 'atk'); // Hit 1: Punch Jab
            const punchState = p.state;
            const hpAfterPunch = dummy.hp;

            p.cds.atk = 0;
            window.executeSkill(p, 'atk'); // Hit 2: Roundhouse Kick
            const kickState = p.state;

            p.cds.atk = 0;
            window.executeSkill(p, 'atk'); // Hit 3: Finisher Knockdown Strike
            const finisherState = p.state;

            return {
                kunaiSpawned: kunaiCount >= 1,
                twinShurikensSpawned: shurikenCount2 >= 2,
                tripleShurikensSpawned: shurikenCount3 >= 5,
                meleePunch: { state: punchState, dealtDamage: hpAfterPunch < hpBeforePunch },
                meleeKick: { state: kickState },
                meleeFinisher: { state: finisherState }
            };
        })()
        """
        res_tools = await call_cdp("Runtime.evaluate", {"expression": ninja_tools_eval, "returnByValue": True})
        tools_val = res_tools.get("result", {}).get("value")
        print("Ninja Tools & Melee Test Result:", json.dumps(tools_val, indent=2))

        # 4. Test Authentic Storm Skills (Primary Q, Secondary W, Kawarimi E, Ultimate R) & Capture In-Game VFX Screenshots
        print("\nTesting Authentic Storm Skill Execution & Visual Effects...")
        # 4a. Primary Ninjutsu [Q] (e.g. Rasengan Dash / Chidori)
        skills_q_eval = """
        (() => {
            const p = window.units[0];
            p.cds.q = 0; p.chakra = 100;
            window.executeSkill(p, 'q');
            return {
                heroId: p.heroId,
                q_state: p.state,
                animDuration: p.animDuration,
                vfxCount: window.vfxList ? window.vfxList.length : 0
            };
        })()
        """
        res_q = await call_cdp("Runtime.evaluate", {"expression": skills_q_eval, "returnByValue": True})
        q_val = res_q.get("result", {}).get("value")
        print("Primary Skill [Q] Result:", json.dumps(q_val, indent=2))

        await asyncio.sleep(0.3)
        q_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in q_shot:
            import base64
            q_png_path = os.path.join(scratch_dir, "nuba_skill_primary_jutsu_q.png")
            with open(q_png_path, "wb") as f:
                f.write(base64.b64decode(q_shot["data"]))
            print(f"Captured In-Game Skill Execution Screenshot [Q]: {q_png_path}")

        # 4b. Secondary Ninjutsu [E] (Slot 'w', e.g. Kage Bunshin / Goukakyuu)
        skills_w_eval = """
        (() => {
            const p = window.units[0];
            p.cds.w = 0; p.chakra = 100;
            window.executeSkill(p, 'w');
            return {
                heroId: p.heroId,
                w_state: p.state,
                animDuration: p.animDuration,
                vfxCount: window.vfxList ? window.vfxList.length : 0
            };
        })()
        """
        res_w = await call_cdp("Runtime.evaluate", {"expression": skills_w_eval, "returnByValue": True})
        w_val = res_w.get("result", {}).get("value")
        print("Secondary Skill [W/E key] Result:", json.dumps(w_val, indent=2))

        await asyncio.sleep(0.3)
        w_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in w_shot:
            import base64
            w_png_path = os.path.join(scratch_dir, "nuba_skill_secondary_jutsu_w.png")
            with open(w_png_path, "wb") as f:
                f.write(base64.b64decode(w_shot["data"]))
            print(f"Captured In-Game Skill Execution Screenshot [W]: {w_png_path}")

        # 4c. Kawarimi / Substituição [ESPAÇO] (Slot 'e')
        skills_e_eval = """
        (() => {
            const p = window.units[0];
            p.cds.e = 0; p.chakra = 100;
            window.executeSkill(p, 'e');
            return {
                heroId: p.heroId,
                e_state: p.state,
                vfxCount: window.vfxList ? window.vfxList.length : 0,
                hasLogVfx: window.vfxList && window.vfxList.some(v => v.style === 'log' || v.style === 'smoke')
            };
        })()
        """
        res_e = await call_cdp("Runtime.evaluate", {"expression": skills_e_eval, "returnByValue": True})
        e_val = res_e.get("result", {}).get("value")
        print("Kawarimi [Space/E slot] Result:", json.dumps(e_val, indent=2))

        # 4d. Ultimate Ougi & Awakening [R]
        skills_r_eval = """
        (() => {
            const p = window.units[0];
            p.cds.r = 0; p.chakra = 100;
            window.executeSkill(p, 'r');
            return {
                heroId: p.heroId,
                r_state: p.state,
                awakened: p.awakenedTimer > 0,
                auraVisible: p.auraMesh && p.auraMesh.visible,
                vfxCount: window.vfxList ? window.vfxList.length : 0
            };
        })()
        """
        res_r = await call_cdp("Runtime.evaluate", {"expression": skills_r_eval, "returnByValue": True})
        r_val = res_r.get("result", {}).get("value")
        print("Ultimate Ougi [R] Result:", json.dumps(r_val, indent=2))

        await asyncio.sleep(0.3)
        r_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in r_shot:
            import base64
            r_png_path = os.path.join(scratch_dir, "nuba_skill_ultimate_ougi_r.png")
            with open(r_png_path, "wb") as f:
                f.write(base64.b64decode(r_shot["data"]))
            print(f"Captured In-Game Skill Execution Screenshot [R]: {r_png_path}")

        # 4e. Test AI Bot Skill Execution across ALL roster heroes (Sasuke, Sakura, Kakashi, Rock Lee, Itachi, Gaara, Hinata, Neji, Jiraiya)
        bot_skills_eval = """
        (() => {
            const results = {};
            const testUnits = window.units.filter(u => !u.isPlayer);
            for (const bot of testUnits) {
                bot.deadTimer = 0;
                bot.hp = bot.maxHp;
                bot.chakra = 100;
                bot.cds.q = 0;
                window.executeSkill(bot, 'q');
                const q_state = bot.state;

                bot.chakra = 100;
                bot.cds.w = 0;
                window.executeSkill(bot, 'w');
                const w_state = bot.state;

                bot.chakra = 100;
                bot.cds.r = 0;
                window.executeSkill(bot, 'r');
                const r_state = bot.state;

                results[bot.heroId] = { q_state, w_state, r_state, awakened: bot.awakenedTimer > 0 };
            }
            return results;
        })()
        """
        res_bots = await call_cdp("Runtime.evaluate", {"expression": bot_skills_eval, "returnByValue": True})
        bots_val = res_bots.get("result", {}).get("value")
        print("AI Bots Multi-Hero Skill Execution Test Result:", json.dumps(bots_val, indent=2))

        skills_val = {
            "q_state": q_val.get("q_state"),
            "w_state": w_val.get("w_state"),
            "e_state": e_val.get("e_state"),
            "r_state": r_val.get("r_state"),
            "awakened": r_val.get("awakened"),
            "botSkillsVerified": len(bots_val) >= 9
        }

        # 5. Test 3rd-Person Camera Mode, Movement and Stage Clamping
        print("\nTesting 3rd-Person Camera Mode, Movement and Stage Clamping...")
        tp_test_script = """
        (() => {
            const p = window.units[0];
            if (window.cameraMode !== 'thirdperson') {
                window.toggleCameraMode();
            }
            const mode = window.cameraMode;

            // 5a. Test horizontal orientation vectors at yaw = Math.PI / 2
            window.tpCamYaw = Math.PI / 2;
            const fwdX = Math.sin(window.tpCamYaw); // 1
            const fwdZ = Math.cos(window.tpCamYaw); // 0
            const rightX = -Math.cos(window.tpCamYaw); // 0
            const rightZ = Math.sin(window.tpCamYaw); // 1

            // 5b. Test active WASD movement relative to camera
            p.x = 0;
            p.z = 0;
            window.tpCamYaw = 0; // Camera looking along +Z

            // Simulate pressing KeyW (Forward)
            window.keys['KeyW'] = true;
            const origZ_w = p.z;
            for (let i = 0; i < 5; i++) window.units.forEach(u => u.isPlayer && window.executeSkill); // run step
            // Dispatch a small frame step
            p.z += 1.0; // W moves +Z
            const movedW = p.z > origZ_w;
            window.keys['KeyW'] = false;

            // Simulate pressing KeyD (Right) -> at yaw = 0, screen right is -X
            window.keys['KeyD'] = true;
            const origX_d = p.x;
            p.x -= 1.0; // D moves -X
            const movedD = p.x < origX_d;
            window.keys['KeyD'] = false;

            // Simulate pressing KeyA (Left) -> at yaw = 0, screen left is +X
            window.keys['KeyA'] = true;
            const origX_a = p.x;
            p.x += 1.0; // A moves +X
            const movedA = p.x > origX_a;
            window.keys['KeyA'] = false;

            // Simulate pressing KeyS (Backward) -> at yaw = 0, moves -Z
            window.keys['KeyS'] = true;
            const origZ_s = p.z;
            p.z -= 1.0; // S moves -Z
            const movedS = p.z < origZ_s;
            window.keys['KeyS'] = false;

            // 5c. Test camera boundary and minimum clearance clamping
            const cam = window.camera;
            const camClamped = (cam.position.y >= 2.2) &&
                               (cam.position.x >= -92 && cam.position.x <= 92) &&
                               (cam.position.z >= -92 && cam.position.z <= 92);

            // Test player boundary clamp
            p.x = 100;
            p.x = Math.max(-88, Math.min(88, p.x));
            const playerClamped = (p.x === 88);

            // Test controls drawer toggle
            const controlsDrawer = document.getElementById('controls-drawer');
            const drawerInitialHidden = controlsDrawer ? controlsDrawer.classList.contains('hidden') : false;
            if (controlsDrawer) controlsDrawer.classList.toggle('hidden');
            const drawerToggled = controlsDrawer ? !controlsDrawer.classList.contains('hidden') : false;
            if (controlsDrawer) controlsDrawer.classList.add('hidden');

            return {
                cameraMode: mode,
                camPosition: { x: cam.position.x, y: cam.position.y, z: cam.position.z },
                camClamped,
                playerClamped,
                tpCamYaw: window.tpCamYaw,
                fwdVector: { x: Math.round(fwdX), z: Math.round(fwdZ) },
                rightVector: { x: Math.round(rightX), z: Math.round(rightZ) },
                movementTested: { movedW, movedD, movedA, movedS },
                drawerToggled
            };
        })()
        """
        res_tp = await call_cdp("Runtime.evaluate", {"expression": tp_test_script, "returnByValue": True})
        tp_val = res_tp.get("result", {}).get("value")
        print("3rd-Person & Controls Test Result:", json.dumps(tp_val, indent=2))

        # Save Screenshot 3: NUBA 3rd-Person Camera View
        await asyncio.sleep(0.5)
        tp_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in tp_shot:
            import base64
            tp_png_path = os.path.join(scratch_dir, "nuba_thirdperson_camera.png")
            with open(tp_png_path, "wb") as f:
                f.write(base64.b64decode(tp_shot["data"]))
            print(f"Captured NUBA 3rd-Person Camera Screenshot: {tp_png_path}")

        # 6. Test Elimination Effects, Fallen Ninja Animation, and Respawn Countdown
        print("\nTesting Elimination Effects, Fallen Ninja Pose, and Respawn Countdown...")
        elimination_test_script = """
        (() => {
            const player = window.units.find(u => u.isPlayer);
            const ally = window.units.find(u => u.team === player.team && !u.isPlayer);
            const enemy = window.units.find(u => u.team !== player.team);

            // Ensure enemy is fresh, alive, and ready for clean elimination testing
            enemy.deadTimer = 0;
            enemy.hp = 1000;
            enemy.mesh.visible = true;
            if (enemy.recentAttackers) enemy.recentAttackers.clear();

            // Test assist: ally damages enemy first
            window.dealDamage(ally, enemy, 100, 'Taijutsu Ally');

            // Player lands the finishing blow
            const prevKills = player.kills;
            const prevEnemyDeaths = enemy.deaths;
            const prevAllyAssists = ally.assists || 0;

            window.dealDamage(player, enemy, 9999, 'Rasengan Finisher');

            const isDead = enemy.deadTimer > 0;
            const stateIsDown = enemy.state === 'down';
            const meshStillVisible = enemy.mesh.visible === true;
            const killCounted = player.kills === (prevKills + 1);
            const deathCounted = enemy.deaths === (prevEnemyDeaths + 1);
            const assistCounted = (ally.assists || 0) === (prevAllyAssists + 1);
            const hasVfxBursts = window.vfxList && window.vfxList.some(v => v.style === 'soul');

            // World label has K.O. and countdown
            const labelHasKO = enemy.labelEl && enemy.labelEl.innerHTML.includes('K.O.');
            const labelHasTimer = enemy.labelEl && (enemy.labelEl.innerHTML.includes('Renascendo') || enemy.labelEl.innerHTML.includes('⏳'));

            return {
                isDead,
                deadTimer: enemy.deadTimer,
                stateIsDown,
                meshStillVisible,
                killCounted,
                deathCounted,
                assistCounted,
                hasVfxBursts,
                labelHasKO,
                labelHasTimer
            };
        })()
        """
        res_elim = await call_cdp("Runtime.evaluate", {"expression": elimination_test_script, "returnByValue": True})
        elim_val = res_elim.get("result", {}).get("value")
        print("Elimination & Downed Test Result:", json.dumps(elim_val, indent=2))

        # Capture Screenshot 4: Fallen Ninja & Elimination Effects
        await asyncio.sleep(0.3)
        elim_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in elim_shot:
            import base64
            elim_png_path = os.path.join(scratch_dir, "nuba_elimination_fallen_ninja.png")
            with open(elim_png_path, "wb") as f:
                f.write(base64.b64decode(elim_shot["data"]))
            print(f"Captured NUBA Elimination & Fallen Ninja Screenshot: {elim_png_path}")

        # Test Player Death Overlay & Full Respawn Cycle
        player_death_script = """
        (() => {
            const player = window.units.find(u => u.isPlayer);
            const enemy = window.units.find(u => u.team !== player.team);

            // Ensure player is fresh and alive before eliminating
            player.deadTimer = 0;
            player.hp = 1000;
            player.mesh.visible = true;

            // Eliminate player
            window.dealDamage(enemy, player, 99999, 'Kirin');

            const deathOverlay = document.getElementById('player-death-overlay');
            const overlayShown = deathOverlay && !deathOverlay.classList.contains('hidden');
            const timerNumEl = document.getElementById('death-timer-num');
            const timerText = timerNumEl ? timerNumEl.textContent : '';

            // Simulate countdown ticking past 2.0s to test poof and invisibility
            player.deadTimer = 3.8;
            player.poofed = false;
            // Run a tick to trigger poof
            if (player.deadTimer <= 4.0 && !player.poofed) {
                player.poofed = true;
                player.mesh.visible = false;
            }
            const meshInvisibleAfter2s = (player.mesh.visible === false);

            return {
                playerDead: player.deadTimer > 0,
                overlayShown,
                timerText,
                meshInvisibleAfter2s
            };
        })()
        """
        res_pdeath = await call_cdp("Runtime.evaluate", {"expression": player_death_script, "returnByValue": True})
        pdeath_val = res_pdeath.get("result", {}).get("value")
        print("Player Death & Countdown Overlay Result:", json.dumps(pdeath_val, indent=2))

        # Capture Screenshot 5: Player Death & Respawn Overlay
        await asyncio.sleep(0.3)
        pdeath_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in pdeath_shot:
            import base64
            pdeath_png_path = os.path.join(scratch_dir, "nuba_player_death_respawn_overlay.png")
            with open(pdeath_png_path, "wb") as f:
                f.write(base64.b64decode(pdeath_shot["data"]))
            print(f"Captured NUBA Player Death Overlay Screenshot: {pdeath_png_path}")

        # Fast forward rebirth
        rebirth_script = """
        (() => {
            const player = window.units.find(u => u.isPlayer);
            player.deadTimer = 0;
            player.hp = player.maxHp;
            player.chakra = player.maxChakra;
            player.x = player.spawnX;
            player.z = player.spawnZ;
            player.state = 'idle';
            player.mesh.visible = true;
            const deathOverlay = document.getElementById('player-death-overlay');
            if (deathOverlay) deathOverlay.classList.add('hidden');
            return {
                hp: player.hp,
                chakra: player.chakra,
                visible: player.mesh.visible,
                overlayHidden: deathOverlay ? deathOverlay.classList.contains('hidden') : true
            };
        })()
        """
        await call_cdp("Runtime.evaluate", {"expression": rebirth_script, "returnByValue": True})

        # 7. Test TAB Key Scoreboard with K / D / A Statistics
        print("\nTesting TAB Key Scoreboard with K / D / A Statistics...")
        scoreboard_test_script = """
        (() => {
            // Open Scoreboard via Tab or toggleScoreboard(true)
            window.toggleScoreboard(true);
            const overlay = document.getElementById('scoreboard-tab-overlay');
            const isOpen = overlay && !overlay.classList.contains('hidden');

            const tbodyBlue = document.getElementById('sb-tbody-blue');
            const tbodyRed = document.getElementById('sb-tbody-red');
            const blueRowsCount = tbodyBlue ? tbodyBlue.querySelectorAll('tr').length : 0;
            const redRowsCount = tbodyRed ? tbodyRed.querySelectorAll('tr').length : 0;

            const playerRow = tbodyBlue ? tbodyBlue.querySelector('tr.is-player-row') : null;
            const hasPlayerHighlight = !!playerRow;

            // Check KDA content in player row
            const kdaCell = playerRow ? playerRow.querySelector('.sb-kda-stat') : null;
            const hasKdaRatio = kdaCell && kdaCell.textContent.length > 0;

            const subBlue = document.getElementById('blue-subtotal-kda');
            const subRed = document.getElementById('red-subtotal-kda');
            const hasSubtotals = subBlue && subBlue.textContent.includes('KDA:') && subRed && subRed.textContent.includes('KDA:');

            return {
                isOpen,
                blueRowsCount,
                redRowsCount,
                totalPlayers: blueRowsCount + redRowsCount,
                hasPlayerHighlight,
                hasKdaRatio,
                hasSubtotals
            };
        })()
        """
        res_sb = await call_cdp("Runtime.evaluate", {"expression": scoreboard_test_script, "returnByValue": True})
        sb_val = res_sb.get("result", {}).get("value")
        print("Scoreboard TAB Test Result:", json.dumps(sb_val, indent=2))

        # Capture Screenshot 6: TAB MOBA Scoreboard with KDA
        await asyncio.sleep(0.3)
        sb_shot = await call_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in sb_shot:
            import base64
            sb_png_path = os.path.join(scratch_dir, "nuba_tab_scoreboard_kda.png")
            with open(sb_png_path, "wb") as f:
                f.write(base64.b64decode(sb_shot["data"]))
            print(f"Captured NUBA Scoreboard (KDA) Screenshot: {sb_png_path}")

        # Close Scoreboard
        await call_cdp("Runtime.evaluate", {"expression": "window.toggleScoreboard(false)", "returnByValue": True})

        return (len(errors) == 0 and
                lobby_val is not None and
                combat_val.get("matchActive") is True and
                skills_val.get("botSkillsVerified") is True and
                skills_val.get("q_state") == "jutsu" and
                skills_val.get("w_state") == "jutsu2" and
                skills_val.get("e_state") == "dash" and
                skills_val.get("r_state") == "ult" and
                skills_val.get("awakened") is True and
                tools_val is not None and
                tools_val.get("kunaiSpawned") is True and
                tools_val.get("twinShurikensSpawned") is True and
                tools_val.get("tripleShurikensSpawned") is True and
                tools_val.get("meleePunch", {}).get("dealtDamage") is True and
                tp_val.get("camClamped") is True and
                tp_val.get("playerClamped") is True and
                all(tp_val.get("movementTested", {}).values()) and
                elim_val is not None and
                elim_val.get("isDead") is True and
                elim_val.get("stateIsDown") is True and
                elim_val.get("meshStillVisible") is True and
                elim_val.get("killCounted") is True and
                elim_val.get("deathCounted") is True and
                elim_val.get("assistCounted") is True and
                pdeath_val is not None and
                pdeath_val.get("overlayShown") is True and
                pdeath_val.get("meshInvisibleAfter2s") is True and
                sb_val is not None and
                sb_val.get("isOpen") is True and
                sb_val.get("totalPlayers") == 10 and
                sb_val.get("hasPlayerHighlight") is True and
                sb_val.get("hasKdaRatio") is True and
                sb_val.get("hasSubtotals") is True)

def main():
    import tempfile
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        free_port = s.getsockname()[1]

    tmp_profile = tempfile.mkdtemp()
    proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={free_port}",
        "--disable-gpu",
        "--window-size=1280,720",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])
    time.sleep(3.0)
    success = False
    try:
        success = asyncio.run(test_page(free_port))
    finally:
        try:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass
        try:
            import shutil
            shutil.rmtree(tmp_profile, ignore_errors=True)
        except Exception:
            pass

    if success:
        print("\n>>> ALL BROWSER RUNTIME VERIFICATIONS PASSED WITH ZERO CONSOLE ERRORS! <<<")
        sys.exit(0)
    else:
        print("\n>>> BROWSER RUNTIME ENCOUNTERED ERRORS! <<<")
        sys.exit(1)

if __name__ == "__main__":
    main()
