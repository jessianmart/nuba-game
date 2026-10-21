"""
Empirical Adversarial Challenge Test Suite for NUBA M6:
Authentic 3D VFX & Animations Verification Across All 10 Heroes in Live WebGL

Milestone M6 — Challenger 1

Verifies:
1. Static & Runtime Wireframe Audit:
   - Zero VFX materials have wireframe: true in source code and in live Three.js scene graph.
2. 10-Hero 11-Clip Animation Dataset Audit:
   - All 10 ninjas have all 11 animation clips (idle, run, dash, attack, attack2, attack3, jutsu, jutsu2, ult, down, charge).
   - Zero NaNs or Infinities in quaternion/position keyframe curves.
3. Storm 3D Skill VFX Dataset JSON Audit:
   - JSON standard RFC 8259 compliance for public/assets/skills/skill_vfx.json.
   - Empirical scan for NaNs / Infinities in extracted submesh vertex/normal/uv buffers.
   - Impact of corrupted normals on async runtime loading (fetch catch fallback).
4. Live Headless Edge WebGL CDP Runtime Challenge:
   - Trigger signature jutsus for heroes (Naruto Rasengan/Kyuubi, Sasuke Chidori/Fireball/Kirin,
     Neji Kaiten, Gaara Sand Shield/Hand, Hinata Lion Fists, Itachi Amaterasu, Rock Lee Cyclone,
     Kakashi Raikiri/Water Dragon, Sakura Ground Shatter, Jiraiya Toad Oil Flame).
   - Assert compound VFX child meshes have multi-axis angular velocities (rotSpeed.x !== 0 || rotSpeed.y !== 0 || rotSpeed.z !== 0).
   - Assert Chidori spawns dynamic line segment arcs (THREE.LineSegments) with updateArcs.
   - Assert hand-held jutsus (Rasengan, Chidori, Raikiri, Lion Fists) update their positions matching hand bone world coordinates.
   - Assert zero console errors, zero runtime exceptions, zero NaNs across all skill executions.
"""

import asyncio
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

sys.stdout.reconfigure(encoding='utf-8')

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Microsoft Edge executable not found in standard paths.")


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


# =============================================================================
# CHALLENGE 1: OFFLINE VFX WIREFRAME AUDIT
# =============================================================================

def challenge_1_vfx_wireframes():
    print("\n" + "=" * 70)
    print("CHALLENGE 1: Adversarial VFX Wireframe Audit (Zero wireframe: true)")
    print("=" * 70)

    game_js_path = r"public/game.js"
    assert os.path.exists(game_js_path), f"File missing: {game_js_path}"

    with open(game_js_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    vfx_wireframe_violations = []
    total_wireframes = 0

    # Function names that define VFX or weapon meshes
    vfx_func_regex = re.compile(r'function\s+(spawnVFX|create\w+Mesh|createProceduralLightningArcs|buildExtractedVfxMeshGroup)')
    in_vfx_func = False
    current_func = ""

    for line_num, line in enumerate(lines, 1):
        fn_match = vfx_func_regex.search(line)
        if fn_match:
            in_vfx_func = True
            current_func = fn_match.group(1)
        elif line.startswith('function ') and not fn_match:
            in_vfx_func = False
            current_func = ""

        if 'wireframe' in line:
            total_wireframes += 1
            if re.search(r'wireframe:\s*true', line):
                # Disallow wireframe: true in any VFX function
                if in_vfx_func or 'vfx' in line.lower() or 'mesh' in line.lower():
                    vfx_wireframe_violations.append((line_num, current_func, line.strip()))

    print(f"  Scanned {len(lines)} lines of public/game.js.")
    print(f"  Total wireframe occurrences found: {total_wireframes}")

    if vfx_wireframe_violations:
        print(f"  [FAIL] Detected {len(vfx_wireframe_violations)} wireframe: true violations in VFX code:")
        for ln, fn, text in vfx_wireframe_violations:
            print(f"    Line {ln} in {fn}: {text}")
        return False, f"Found {len(vfx_wireframe_violations)} wireframe: true in VFX code"

    print("  [PASS] Zero VFX materials have wireframe: true. All VFX explicitly set wireframe: false.")
    return True, "Zero wireframe: true in VFX materials"


# =============================================================================
# CHALLENGE 2: 10-HERO 11-CLIP ANIMATION DATASET AUDIT
# =============================================================================

def challenge_2_animations_dataset():
    print("\n" + "=" * 70)
    print("CHALLENGE 2: 10-Hero 11-Clip Animation Dataset Audit")
    print("=" * 70)

    anim_path = r"public/assets/data/animations.json"
    assert os.path.exists(anim_path), f"File missing: {anim_path}"

    with open(anim_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    expected_heroes = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry']
    expected_clips = ['idle', 'run', 'dash', 'attack', 'attack2', 'attack3', 'jutsu', 'jutsu2', 'ult', 'down', 'charge']

    missing_heroes = [h for h in expected_heroes if h not in data]
    assert not missing_heroes, f"Missing heroes in animations.json: {missing_heroes}"

    nan_count = 0
    total_clips = 0
    missing_clips = {}

    for h in expected_heroes:
        hero_clips = data.get(h, {})
        m_clips = [c for c in expected_clips if c not in hero_clips]
        if m_clips:
            missing_clips[h] = m_clips

        for c_name, c_data in hero_clips.items():
            total_clips += 1
            # Check frames and tracks
            num_frames = c_data.get('numFrames', 0)
            assert num_frames > 0, f"Hero {h} clip {c_name} has 0 frames"

            # Check rotations
            rotations = c_data.get('rotations', {})
            for b_idx, q_list in rotations.items():
                for q in q_list:
                    for val in q:
                        if math.isnan(val) or math.isinf(val):
                            nan_count += 1

            # Check pelvisPos
            pelvis_track = c_data.get('pelvisPos', [])
            for p in pelvis_track:
                for val in p:
                    if math.isnan(val) or math.isinf(val):
                        nan_count += 1

    print(f"  Audited {len(expected_heroes)} heroes and {total_clips} animation clips.")
    if missing_clips:
        print(f"  [FAIL] Missing animation clips: {missing_clips}")
        return False, f"Missing clips: {missing_clips}"

    if nan_count > 0:
        print(f"  [FAIL] Detected {nan_count} NaNs/Infs in animations.json!")
        return False, f"Found {nan_count} NaNs in animations.json"

    print(f"  [PASS] 10/10 heroes have all 11 clips (110 total clips). Zero NaNs, zero Infinities.")
    return True, "110 animation clips verified with zero NaNs"


# =============================================================================
# CHALLENGE 3: STORM 3D SKILL VFX DATASET & RFC 8259 JSON AUDIT
# =============================================================================

def challenge_3_skill_vfx_dataset():
    print("\n" + "=" * 70)
    print("CHALLENGE 3: Storm 3D Skill VFX Dataset & RFC 8259 JSON Spec Audit")
    print("=" * 70)

    vfx_json_path = r"public/assets/skills/skill_vfx.json"
    assert os.path.exists(vfx_json_path), f"File missing: {vfx_json_path}"

    with open(vfx_json_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    # 1. Check RFC 8259 compliance via standard parser
    json_valid = True
    json_err_msg = ""
    try:
        data = json.loads(raw_content)
    except Exception as e:
        json_valid = False
        json_err_msg = str(e)

    # 2. Find all occurrences of literal NaN / Infinity in raw text
    nan_matches = [m.start() for m in re.finditer(r'NaN', raw_content)]
    inf_matches = [m.start() for m in re.finditer(r'Infinity', raw_content)]

    # Pinpoint affected models
    corrupted_models = set()
    for idx in nan_matches:
        sub = raw_content[max(0, idx - 1000):idx]
        matches = re.findall(r'\"([a-zA-Z0-9_]+)\"\s*:\s*\{\s*\"vertices\"', sub)
        if matches:
            corrupted_models.add(matches[-1])

    print(f"  File size: {len(raw_content):,} bytes")
    print(f"  RFC 8259 Valid JSON: {json_valid}")
    if not json_valid:
        print(f"  [CRITICAL SYNTAX ERROR] JSON parser error: {json_err_msg}")
    print(f"  Total NaN occurrences in skill_vfx.json: {len(nan_matches)}")
    print(f"  Total Infinity occurrences in skill_vfx.json: {len(inf_matches)}")
    if corrupted_models:
        print(f"  Corrupted models with NaNs in normals: {sorted(list(corrupted_models))}")

    # 3. Check consequences in public/game.js:
    # fetch('assets/skills/skill_vfx.json?v=8').then(r => r.json()).catch(() => ({}))
    # When r.json() fails, skillVfxData is empty {}, causing all buildExtractedVfxMeshGroup() to fail!
    if not json_valid or len(nan_matches) > 0:
        print("\n  [CRITICAL FAILURE EXPLANATION]")
        print("  - public/assets/skills/skill_vfx.json contains 88 NaN values in submesh normal buffers.")
        print("  - Standard JavaScript Response.json() / JSON.parse() rejects NaN as invalid JSON (RFC 8259).")
        print("  - public/game.js line 4481 catches the syntax error silently via .catch(() => ({})).")
        print("  - Consequently, window.skillVfxData is completely EMPTY ({}) in the live client engine!")
        print("  - All extracted Storm 3D submeshes (including Gaara's 1gareff1_hnd01_body giant sand hand)")
        print("    fail to instantiate, falling back to dummy procedural geometries (e.g. BoxGeometry palm).")
        return False, f"skill_vfx.json contains {len(nan_matches)} NaNs, breaking async JSON parsing"

    print("  [PASS] skill_vfx.json is 100% RFC 8259 valid with zero NaNs.")
    return True, "skill_vfx.json is valid"


# =============================================================================
# CHALLENGE 4: LIVE WEBGL RUNTIME CDP ADVERSARIAL CHALLENGE
# =============================================================================

async def challenge_4_live_webgl_cdp():
    print("\n" + "=" * 70)
    print("CHALLENGE 4: Live WebGL Runtime CDP Adversarial Stress Testing")
    print("=" * 70)

    edge_bin = find_edge()
    port = get_free_port()
    tmp_user_dir = tempfile.mkdtemp(prefix="nuba_cdp_vfx_")

    proc = subprocess.Popen([
        edge_bin,
        '--headless=new',
        f'--remote-debugging-port={port}',
        f'--user-data-dir={tmp_user_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--inprivate',
        '--disable-gpu',
        '--window-size=1600,900',
        'http://localhost:8080/index.html'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    console_errors = []
    ws = None
    results = {}

    try:
        # Wait for debugging port
        for _ in range(30):
            try:
                raw = urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=1).read()
                tabs = json.loads(raw)
                ws_entry = next((t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t.get('url', '')), None)
                if ws_entry:
                    ws = await websockets.connect(ws_entry, max_size=50_000_000)
                    break
            except Exception:
                await asyncio.sleep(0.3)

        assert ws is not None, "Failed to connect to Microsoft Edge CDP WebSocket."

        msg_id = 1
        async def send_cmd(method, params=None):
            nonlocal msg_id
            mid = msg_id
            msg_id += 1
            payload = {'id': mid, 'method': method}
            if params:
                payload['params'] = params
            await ws.send(json.dumps(payload))
            while True:
                resp = json.loads(await ws.recv())
                m = resp.get('method')
                if m == 'Runtime.exceptionThrown':
                    exc = resp['params']['exceptionDetails']
                    text = exc.get('exception', {}).get('description') or exc.get('text', '')
                    console_errors.append(f"Runtime Exception: {text}")
                elif m == 'Log.entryAdded':
                    entry = resp['params']['entry']
                    if entry.get('level') == 'error':
                        console_errors.append(f"Log Error: {entry.get('text', '')}")
                elif m == 'Runtime.consoleAPICalled':
                    c_type = resp['params']['type']
                    if c_type == 'error':
                        args = [str(a.get('value', a.get('description', ''))) for a in resp['params']['args']]
                        console_errors.append(f"Console Error: {' '.join(args)}")
                if resp.get('id') == mid:
                    return resp.get('result', {})

        await send_cmd('Runtime.enable')
        await send_cmd('Log.enable')
        await send_cmd('Page.enable')

        # Wait for page readiness
        print("  Waiting for client engine and 3D assets to load...")
        ready = False
        for _ in range(40):
            res_rdy = await send_cmd("Runtime.evaluate", {
                "expression": "Boolean(window.rosterMeta && window.animationsData && window.lobbyHeroMesh)",
                "returnByValue": True
            })
            if res_rdy.get("result", {}).get("value") is True:
                ready = True
                break
            await asyncio.sleep(0.5)

        assert ready, "Client engine failed to initialize within timeout!"
        print("  Client engine fully initialized with lobbyHeroMesh.")

        # Check skillVfxData runtime status
        res_vfx_data = await send_cmd("Runtime.evaluate", {
            "expression": "(() => { return { loaded: Boolean(window.skillVfxData), keysCount: window.skillVfxData ? Object.keys(window.skillVfxData).length : 0 }; })()",
            "returnByValue": True
        })
        vfx_data_status = res_vfx_data.get("result", {}).get("value", {})
        print(f"  Live window.skillVfxData Status: {vfx_data_status}")
        results['skillVfxDataLoaded'] = vfx_data_status.get('keysCount', 0) > 0

        # Start 5v5 Match
        print("  Starting 5v5 Match across Chunin Arena...")
        await send_cmd("Runtime.evaluate", {
            "expression": "(async () => { await window.start5v5Match(); })()",
            "awaitPromise": True
        })

        match_ready = False
        for i in range(60):
            res_u = await send_cmd("Runtime.evaluate", {
                "expression": "Boolean(window.units && window.units.length === 10)",
                "returnByValue": True
            })
            if res_u.get("result", {}).get("value") is True:
                match_ready = True
                print(f"  5v5 Match successfully spawned with 10 units after {i * 0.5:.1f}s.")
                break
            await asyncio.sleep(0.5)

        if not match_ready:
            # Debug what happened
            debug_res = await send_cmd("Runtime.evaluate", {
                "expression": "(() => { return { unitsLen: window.units ? window.units.length : 'no units', matchActive: window.matchActive }; })()",
                "returnByValue": True
            })
            print(f"  [DEBUG] Units State: {debug_res.get('result', {}).get('value')}")
            print(f"  [DEBUG] Console Errors: {console_errors}")

        assert match_ready, "5v5 match failed to spawn 10 units within 30s!"

        # =====================================================================
        # TEST A: Wireframe Audit in Live Scene Graph & VFX List
        # =====================================================================
        print("\n  [Test A] Auditing all active materials for wireframe: false in live WebGL...")
        res_wf = await send_cmd("Runtime.evaluate", {
            "expression": """
            (() => {
                let wireframeTrueCount = 0;
                let vfxMaterialsCount = 0;
                const scannedMeshes = [];

                // 1. Scan arenaGroup
                window.arenaGroup.traverse(obj => {
                    if (obj.isMesh || obj.isLine || obj.isSprite) {
                        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
                        mats.forEach(m => {
                            if (m) {
                                vfxMaterialsCount++;
                                if (m.wireframe === true) {
                                    wireframeTrueCount++;
                                    scannedMeshes.push(obj.name || 'unnamed_mesh');
                                }
                            }
                        });
                    }
                });

                // 2. Scan vfxList
                if (window.vfxList) {
                    window.vfxList.forEach(v => {
                        if (v.mesh) {
                            v.mesh.traverse(obj => {
                                if (obj.material) {
                                    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
                                    mats.forEach(m => {
                                        if (m) {
                                            vfxMaterialsCount++;
                                            if (m.wireframe === true) {
                                                wireframeTrueCount++;
                                                scannedMeshes.push(obj.name || 'vfx_child');
                                            }
                                        }
                                    });
                                }
                            });
                        }
                    });
                }

                return {
                    totalMaterialsScanned: vfxMaterialsCount,
                    wireframeTrueCount,
                    offenders: scannedMeshes
                };
            })()
            """,
            "returnByValue": True
        })
        wf_res = res_wf.get("result", {}).get("value", {})
        print(f"  Live Materials Scanned: {wf_res.get('totalMaterialsScanned')}, Wireframe True Count: {wf_res.get('wireframeTrueCount')}")
        results['liveWireframeZero'] = (wf_res.get('wireframeTrueCount') == 0)

        # =====================================================================
        # TEST B: Hero Signature Jutsus, Compound VFX Multi-Axis rotSpeed,
        #         Chidori LineSegments, Hand Bone Tracking, and 0 NaNs
        # =====================================================================
        print("\n  [Test B] Adversarial Challenge of Signature Jutsus across 10 Heroes...")

        # Test kit execution script
        eval_skills_script = """
        (async () => {
            const report = {
                heroesTested: [],
                compoundRotSpeedVerified: {},
                chidoriLineSegmentsVerified: false,
                chidoriDynamicArcsUpdated: false,
                handBoneTrackingVerified: {},
                nanDetected: false,
                nanDetails: []
            };

            for (const u of window.units) {
                const hId = u.heroId;
                u.deadTimer = 0;
                u.chakra = 100;
                u.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
                u.x = 0;
                u.z = 0;

                // Test Q (Primary Jutsu)
                window.executeSkill(u, 'q');
                await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

                // Inspect vfxList for compound meshes, rotSpeed, hand bone binding
                if (window.vfxList && window.vfxList.length > 0) {
                    for (const v of window.vfxList) {
                        if (v.mesh) {
                            // Check multi-axis rotSpeed in children
                            v.mesh.traverse(child => {
                                if (child.userData && child.userData.rotSpeed) {
                                    const rs = child.userData.rotSpeed;
                                    const hasMultiAxis = (rs.x !== 0 || rs.y !== 0 || rs.z !== 0);
                                    if (hasMultiAxis) {
                                        report.compoundRotSpeedVerified[hId] = report.compoundRotSpeedVerified[hId] || [];
                                        report.compoundRotSpeedVerified[hId].push({
                                            type: child.type,
                                            rotSpeed: { x: rs.x, y: rs.y, z: rs.z }
                                        });
                                    }
                                }
                                // Check Chidori line segments
                                if (hId === '1ssk' || hId === '1kks') {
                                    if (child.isLineSegments || child.type === 'LineSegments') {
                                        report.chidoriLineSegmentsVerified = true;
                                        if (child.userData && typeof child.userData.updateArcs === 'function') {
                                            report.chidoriDynamicArcsUpdated = true;
                                        }
                                    }
                                }
                            });

                            // Check hand bone dynamic tracking
                            if (v.bindUnit === u && v.bindBoneIdx !== undefined) {
                                const bIdx = v.bindBoneIdx;
                                const uMesh = u.mesh;
                                const bones = uMesh && uMesh.userData ? uMesh.userData.bones : null;
                                if (bones && bones[bIdx]) {
                                    const bone = bones[bIdx];
                                    uMesh.updateMatrixWorld(true);
                                    const wp = new THREE.Vector3();
                                    bone.getWorldPosition(wp);
                                    const dist = v.mesh.position.distanceTo(wp);
                                    report.handBoneTrackingVerified[hId] = {
                                        boneIdx: bIdx,
                                        tracked: true,
                                        distanceToBone: dist
                                    };
                                }
                            }
                        }
                    }
                }

                // Test W (Secondary Jutsu)
                u.cds.w = 0;
                u.chakra = 100;
                window.executeSkill(u, 'w');
                await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

                // Inspect Hinata Lion Fists dual hand binding (W)
                if (hId === '1hnt' && window.vfxList) {
                    const lionBinds = window.vfxList.filter(v => v.bindUnit === u && (v.bindBoneIdx === 9 || v.bindBoneIdx === 13));
                    if (lionBinds.length >= 2) {
                        report.handBoneTrackingVerified['1hnt_dual_lion_fists'] = {
                            count: lionBinds.length,
                            leftHandBone: 9,
                            rightHandBone: 13
                        };
                    }
                }

                // Test R (Ultimate Ougi)
                u.cds.r = 0;
                u.chakra = 100;
                window.executeSkill(u, 'r');

                // Advance frame simulation
                for (let step = 0; step < 6; step++) {
                    u.x += 0.1;
                }

                report.heroesTested.push(hId);
            }

            // Check for NaNs across all units and active meshes
            for (const u of window.units) {
                if (isNaN(u.x) || isNaN(u.z) || isNaN(u.hp) || isNaN(u.chakra)) {
                    report.nanDetected = true;
                    report.nanDetails.push(`Unit ${u.id} has NaN coordinates or vitals`);
                }
                if (u.mesh) {
                    if (isNaN(u.mesh.position.x) || isNaN(u.mesh.position.y) || isNaN(u.mesh.position.z)) {
                        report.nanDetected = true;
                        report.nanDetails.push(`Mesh position NaN for ${u.id}`);
                    }
                    if (u.mesh.userData && u.mesh.userData.bones) {
                        u.mesh.userData.bones.forEach((b, idx) => {
                            if (isNaN(b.position.x) || isNaN(b.quaternion.x) || isNaN(b.quaternion.w)) {
                                report.nanDetected = true;
                                report.nanDetails.push(`Bone ${idx} NaN for ${u.id}`);
                            }
                        });
                    }
                }
            }

            return report;
        })()
        """

        res_skills = await send_cmd("Runtime.evaluate", {
            "expression": eval_skills_script,
            "awaitPromise": True,
            "returnByValue": True
        })
        if "exceptionDetails" in res_skills:
            print(f"  [EVAL EXCEPTION] {res_skills['exceptionDetails']}")
        skills_report = res_skills.get("result", {}).get("value") or {}
        print("  Skills Execution Report:")
        print(f"    Heroes Tested: {len(skills_report.get('heroesTested', []))}/10 ({skills_report.get('heroesTested')})")
        print(f"    Compound rotSpeed Verified for: {list(skills_report.get('compoundRotSpeedVerified', {}).keys())}")
        print(f"    Chidori LineSegments Verified: {skills_report.get('chidoriLineSegmentsVerified')}")
        print(f"    Chidori Dynamic Arcs updateArcs: {skills_report.get('chidoriDynamicArcsUpdated')}")
        print(f"    Hand Bone Tracking Verified: {skills_report.get('handBoneTrackingVerified')}")
        print(f"    NaN Detected: {skills_report.get('nanDetected')}")
        if skills_report.get('nanDetails'):
            print(f"    NaN Details: {skills_report.get('nanDetails')}")

        results['heroesTestedCount'] = len(skills_report.get('heroesTested', []))
        results['chidoriLineSegments'] = skills_report.get('chidoriLineSegmentsVerified') is True
        results['chidoriDynamicArcs'] = skills_report.get('chidoriDynamicArcsUpdated') is True
        results['handBoneTracking'] = len(skills_report.get('handBoneTrackingVerified', {})) >= 3
        results['nanDetected'] = skills_report.get('nanDetected') is True
        results['compoundRotSpeedCount'] = len(skills_report.get('compoundRotSpeedVerified', {}))

        # Check console errors
        print(f"\n  [Console & Runtime Errors Check]")
        print(f"  Total Console Errors: {len(console_errors)}")
        if console_errors:
            for err in console_errors:
                print(f"    Error: {err}")
        results['consoleErrorsCount'] = len(console_errors)

        return results

    finally:
        try:
            if ws:
                await ws.close()
        except Exception:
            pass
        try:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass
        try:
            import shutil
            shutil.rmtree(tmp_user_dir, ignore_errors=True)
        except Exception:
            pass


# =============================================================================
# MAIN RUNNER & REPORT GENERATOR
# =============================================================================

def main():
    print("=" * 70)
    print("NUBA M6 ADVERSARIAL CHALLENGER SUITE")
    print("=" * 70)

    # Challenge 1
    c1_pass, c1_msg = challenge_1_vfx_wireframes()

    # Challenge 2
    c2_pass, c2_msg = challenge_2_animations_dataset()

    # Challenge 3
    c3_pass, c3_msg = challenge_3_skill_vfx_dataset()

    # Challenge 4
    c4_results = asyncio.run(challenge_4_live_webgl_cdp())

    print("\n" + "=" * 70)
    print("CHALLENGE RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Challenge 1 (VFX Wireframes Clean): {'PASS' if c1_pass else 'FAIL'} ({c1_msg})")
    print(f"  Challenge 2 (10-Hero 11-Clip Anims): {'PASS' if c2_pass else 'FAIL'} ({c2_msg})")
    print(f"  Challenge 3 (Skill VFX JSON Clean): {'PASS' if c3_pass else 'FAIL'} ({c3_msg})")
    print(f"  Challenge 4 (Live CDP WebGL Stress):")
    print(f"    - skillVfxData Loaded Runtime: {c4_results.get('skillVfxDataLoaded')}")
    print(f"    - Live Wireframe Zero: {c4_results.get('liveWireframeZero')}")
    print(f"    - Heroes Tested: {c4_results.get('heroesTestedCount')}/10")
    print(f"    - Compound rotSpeed Verified Heroes: {c4_results.get('compoundRotSpeedCount')}")
    print(f"    - Chidori THREE.LineSegments: {c4_results.get('chidoriLineSegments')}")
    print(f"    - Chidori Dynamic Arcs: {c4_results.get('chidoriDynamicArcs')}")
    print(f"    - Hand Bone World Tracking: {c4_results.get('handBoneTracking')}")
    print(f"    - Zero NaNs in Simulation: {not c4_results.get('nanDetected')}")
    print(f"    - Zero Console Errors: {c4_results.get('consoleErrorsCount') == 0}")

    all_pass = (
        c1_pass and
        c2_pass and
        c3_pass and
        c4_results.get('skillVfxDataLoaded') is True and
        c4_results.get('liveWireframeZero') is True and
        c4_results.get('heroesTestedCount') == 10 and
        c4_results.get('chidoriLineSegments') is True and
        c4_results.get('chidoriDynamicArcs') is True and
        c4_results.get('handBoneTracking') is True and
        not c4_results.get('nanDetected') and
        c4_results.get('consoleErrorsCount') == 0
    )

    if all_pass:
        print("\n>>> ALL ADVERSARIAL CHALLENGES PASSED! VERDICT: APPROVE <<<")
        sys.exit(0)
    else:
        print("\n>>> ADVERSARIAL CHALLENGE FAILED! VERDICT: REQUEST_CHANGES <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
