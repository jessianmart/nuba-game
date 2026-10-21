"""
Adversarial Empirical Stress Test Suite for Milestone 2:
Responsive Movement, Camera Clamping, and Authentic Controls

Verifies:
1. 'W' Key isolation: strictly forward movement, zero chakra deduction, zero jutsu trigger.
2. Camera-relative movement: pressing 'W' at 8 camera yaw angles moves player along horizontal view vector.
3. Real-time walking to all 4 arena corners in 3rd-person mode while continuously checking camera coordinates.
4. Arena boundary & corner stress testing: player at (+92,+92), (-92,+92), (-92,-92), (+92,-92) and 14 perimeter coordinates.
5. Camera stage clamping: camera X/Z in [-92, 92], height Y >= 2.2 under 360-degree yaw sweeps and negative pitch angles.
6. Zero console errors throughout execution.
"""

import asyncio
import base64
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SCRATCH_DIR = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch"

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.pending = {}
        self.errors = []
        self.logs = []
        self._listener_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=30_000_000)
        self._listener_task = asyncio.create_task(self._listen())
        await self.send("Runtime.enable")
        await self.send("Log.enable")
        await self.send("Page.enable")

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()

    async def _listen(self):
        try:
            while True:
                raw = await self.ws.recv()
                data = json.loads(raw)
                cid = data.get("id")
                if cid is not None and cid in self.pending:
                    fut = self.pending.pop(cid)
                    if not fut.done():
                        fut.set_result(data)

                m = data.get("method")
                if m == "Runtime.exceptionThrown":
                    exc = data["params"]["exceptionDetails"]
                    desc = exc.get("exception", {}).get("description") or exc.get("text")
                    print(f"  [PAGE EXCEPTION] {desc}")
                    self.errors.append(desc)
                elif m == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        print(f"  [LOG ERROR] {entry.get('text')}")
                        self.errors.append(entry.get("text"))
                    else:
                        self.logs.append(entry.get("text"))
                elif m == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    text = " ".join(str(x) for x in args)
                    if call_type == "error":
                        print(f"  [CONSOLE ERROR] {text}")
                        self.errors.append(text)
                    else:
                        self.logs.append(f"[{call_type}] {text}")
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Listen loop error: {e}")

    async def send(self, method, params=None):
        self.msg_id += 1
        cid = self.msg_id
        payload = {"id": cid, "method": method}
        if params:
            payload["params"] = params
        fut = asyncio.get_event_loop().create_future()
        self.pending[cid] = fut
        await self.ws.send(json.dumps(payload))
        data = await asyncio.wait_for(fut, timeout=30.0)
        if "error" in data:
            raise RuntimeError(f"CDP error on {method}: {data['error']}")
        return data.get("result", {})

    async def eval_js(self, expression, await_promise=False):
        res = await self.send("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True
        })
        exc = res.get("exceptionDetails")
        if exc:
            msg = exc.get("exception", {}).get("description") or exc.get("text")
            raise RuntimeError(f"JS Eval Error: {msg}")
        return res.get("result", {}).get("value")

    async def key_down(self, code, key=""):
        await self.send("Input.dispatchKeyEvent", {
            "type": "rawKeyDown",
            "code": code,
            "key": key,
            "windowsVirtualKeyCode": 87 if code == "KeyW" else 0
        })

    async def key_up(self, code, key=""):
        await self.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "code": code,
            "key": key,
            "windowsVirtualKeyCode": 87 if code == "KeyW" else 0
        })

    async def save_screenshot(self, filename):
        os.makedirs(SCRATCH_DIR, exist_ok=True)
        shot = await self.send("Page.captureScreenshot", {"format": "png"})
        if "data" in shot:
            out_path = os.path.join(SCRATCH_DIR, filename)
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(shot["data"]))
            print(f"  [SCREENSHOT] Saved: {out_path}")
            return out_path
        return None


async def run_stress_test_suite():
    print("=" * 70)
    print("  EMPIRICAL CHALLENGER: MILESTONE 2 COMPREHENSIVE STRESS TEST")
    print("=" * 70)

    # 1. Connect to CDP with retry loop
    tabs = None
    for attempt in range(15):
        try:
            tabs_data = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3).read()
            tabs = json.loads(tabs_data)
            if tabs:
                break
        except Exception:
            time.sleep(0.8)

    if not tabs:
        raise RuntimeError("Could not connect to Edge CDP remote debugging port 9222!")

    target_tab = next((t for t in tabs if "localhost:8080" in t.get("url", "")), None)
    if not target_tab:
        raise RuntimeError(f"Target tab not found! Tabs: {[t.get('url') for t in tabs]}")

    cdp = CDPClient(target_tab["webSocketDebuggerUrl"])
    await cdp.connect()
    print("Connected to CDP websocket successfully.")

    # 2. Wait for page assets and start 5v5 match
    print("\n[INIT] Waiting for page assets and Three.js initialization...")
    await asyncio.sleep(3.5)
    match_ready = await cdp.eval_js("""
        (async () => {
            if (!window.matchActive && typeof window.start5v5Match === 'function') {
                await window.start5v5Match();
            }
            for (let i = 0; i < 60; i++) {
                if (window.units && window.units.length === 10) return true;
                await new Promise(r => setTimeout(r, 100));
            }
            return false;
        })()
    """, await_promise=True)
    assert match_ready, "5v5 match failed to initialize with 10 units!"
    print("Match successfully active with 10 units.")

    # Ensure 3rd-person camera mode & invulnerable testing sandbox
    await cdp.eval_js("""
        (() => {
            window.cameraMode = 'thirdperson';
            const p = window.units.find(u => u.isPlayer);
            if (p) {
                p.hp = 999999;
                p.maxHp = 999999;
                p.deadTimer = 0;
            }
            // Park AI bots away from center arena so they don't interfere with movement tests
            window.units.filter(u => !u.isPlayer).forEach((u, i) => {
                u.hp = 99999;
                u.x = (u.team === 'blue' ? -70 : 70) + (i % 3) * 2;
                u.z = (u.team === 'blue' ? -70 : 70) + Math.floor(i / 3) * 2;
            });
        })()
    """)
    await asyncio.sleep(0.5)

    failures = []
    test_results = {}

    # =========================================================================
    # TEST 1: 'W' KEY ISOLATION & CHAKRA INVARIANCE
    # =========================================================================
    print("\n--- TEST 1: 'W' Key Isolation & Chakra Invariance ---")
    try:
        baseline = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 75.0;
                p.state = 'idle';
                p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
                return {
                    chakra: p.chakra,
                    cds: { ...p.cds },
                    state: p.state,
                    projCount: window.projectiles ? window.projectiles.length : 0
                };
            })()
        """)

        # Press W multiple times (single taps)
        for _ in range(5):
            await cdp.key_down("KeyW", "w")
            await asyncio.sleep(0.06)
            await cdp.key_up("KeyW", "w")
            await asyncio.sleep(0.04)

        # Hold W for sustained run
        await cdp.key_down("KeyW", "w")
        await asyncio.sleep(0.6)
        await cdp.key_up("KeyW", "w")
        await asyncio.sleep(0.1)

        after_w = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    chakra: p.chakra,
                    cds: { ...p.cds },
                    state: p.state,
                    projCount: window.projectiles ? window.projectiles.length : 0
                };
            })()
        """)

        # Press Alt+W to confirm legacy shortcut is dead
        await cdp.send("Input.dispatchKeyEvent", {
            "type": "rawKeyDown",
            "code": "KeyW",
            "key": "w",
            "modifiers": 1 # Alt
        })
        await asyncio.sleep(0.2)
        await cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "code": "KeyW",
            "key": "w",
            "modifiers": 1
        })
        await asyncio.sleep(0.1)

        after_alt_w = await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                return {
                    chakra: p.chakra,
                    cds: { ...p.cds },
                    state: p.state,
                    projCount: window.projectiles ? window.projectiles.length : 0
                };
            })()
        """)

        assert after_w["chakra"] >= baseline["chakra"] - 0.001, (
            f"Chakra was deducted! Before: {baseline['chakra']}, After W: {after_w['chakra']}"
        )
        assert after_alt_w["chakra"] >= baseline["chakra"] - 0.001, (
            f"Alt+W deducted chakra! Before: {baseline['chakra']}, After Alt+W: {after_alt_w['chakra']}"
        )
        for slot in ["atk", "q", "w", "e", "r"]:
            assert after_w["cds"][slot] == 0, f"Skill {slot} went on cooldown from 'W': {after_w['cds'][slot]}"
            assert after_alt_w["cds"][slot] == 0, f"Skill {slot} went on cooldown from Alt+'W': {after_alt_w['cds'][slot]}"
        assert after_w["projCount"] == baseline["projCount"], (
            f"Jutsu projectiles spawned from 'W'! Before: {baseline['projCount']}, After: {after_w['projCount']}"
        )

        print("  [PASS] 'W' key strictly moves player without deducting chakra or triggering jutsu.")
        test_results["test_1_w_isolation"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] Test 1 failed: {e}")
        failures.append(f"Test 1: {e}")
        test_results["test_1_w_isolation"] = f"FAIL: {e}"

    # =========================================================================
    # TEST 2: CAMERA-RELATIVE MOVEMENT ALONG HORIZONTAL VIEW VECTOR (8 ANGLES)
    # =========================================================================
    print("\n--- TEST 2: Camera-Relative Movement Across 8 Orientations ---")
    yaw_angles = [
        (0.0, "North (+Z)"),
        (math.pi / 4, "North-East (+X, +Z)"),
        (math.pi / 2, "East (+X)"),
        (3 * math.pi / 4, "South-East (+X, -Z)"),
        (math.pi, "South (-Z)"),
        (5 * math.pi / 4, "South-West (-X, -Z)"),
        (3 * math.pi / 2, "West (-X)"),
        (7 * math.pi / 4, "North-West (-X, +Z)")
    ]

    angle_results = []
    try:
        for yaw, label in yaw_angles:
            # Setup player at origin and set camera yaw
            await cdp.eval_js(f"""
                (() => {{
                    const p = window.units.find(u => u.isPlayer);
                    p.x = 0; p.z = 0;
                    p.animTimer = 0;
                    p.deadTimer = 0;
                    window.cameraMode = 'thirdperson';
                    window.tpCamYaw = {yaw};
                    p.rotY = {yaw};
                }})()
            """)
            await asyncio.sleep(0.08)

            # Get camera forward vector
            cam_data = await cdp.eval_js("""
                (() => {
                    const cam = window.camera;
                    const dir = cam.getWorldDirection(cam.position.clone());
                    const fLen = Math.hypot(dir.x, dir.z) || 1;
                    const p = window.units.find(u => u.isPlayer);
                    return {
                        fwdX: dir.x / fLen,
                        fwdZ: dir.z / fLen,
                        startX: p.x,
                        startZ: p.z
                    };
                })()
            """)

            # Press W for 350ms to let physics update
            await cdp.key_down("KeyW", "w")
            await asyncio.sleep(0.35)
            await cdp.key_up("KeyW", "w")
            await asyncio.sleep(0.05)

            end_pos = await cdp.eval_js("""
                (() => {
                    const p = window.units.find(u => u.isPlayer);
                    return { endX: p.x, endZ: p.z };
                })()
            """)

            dx = end_pos["endX"] - cam_data["startX"]
            dz = end_pos["endZ"] - cam_data["startZ"]
            disp_len = math.hypot(dx, dz)

            assert disp_len > 0.8, f"Player barely moved at yaw {yaw:.2f} ({label}): displacement = {disp_len:.3f}"
            unit_dx = dx / disp_len
            unit_dz = dz / disp_len

            # Cosine similarity with camera forward vector
            cos_sim = unit_dx * cam_data["fwdX"] + unit_dz * cam_data["fwdZ"]
            print(f"  Yaw {yaw:5.2f} rad ({label:22s}): disp=({dx:5.2f}, {dz:5.2f}), len={disp_len:4.2f}, cos_sim={cos_sim:6.4f}")
            assert cos_sim >= 0.95, (
                f"Movement not aligned with camera forward! Expected ({cam_data['fwdX']:.2f}, {cam_data['fwdZ']:.2f}), "
                f"Got ({unit_dx:.2f}, {unit_dz:.2f}), Cosine Similarity = {cos_sim:.4f}"
            )
            angle_results.append({
                "yaw": yaw,
                "label": label,
                "cos_sim": cos_sim,
                "disp_len": disp_len
            })

        # Also test dynamic curve: Hold W while continuously sweeping camera yaw
        print("  Testing continuous camera yaw sweep while holding 'W'...")
        await cdp.eval_js("""
            (() => {
                const p = window.units.find(u => u.isPlayer);
                p.x = 0; p.z = 0;
                window.tpCamYaw = 0;
                p.rotY = 0;
            })()
        """)
        await asyncio.sleep(0.05)
        await cdp.key_down("KeyW", "w")
        curve_pts = []
        for step in range(15):
            await cdp.eval_js("window.tpCamYaw += 0.1;")
            await asyncio.sleep(0.05)
            pos = await cdp.eval_js("""
                (() => {
                    const p = window.units.find(u => u.isPlayer);
                    return { x: p.x, z: p.z, yaw: window.tpCamYaw };
                })()
            """)
            curve_pts.append(pos)
        await cdp.key_up("KeyW", "w")
        await asyncio.sleep(0.05)

        total_curve_dist = math.hypot(curve_pts[-1]["x"] - curve_pts[0]["x"], curve_pts[-1]["z"] - curve_pts[0]["z"])
        assert total_curve_dist > 2.0, f"Curved motion displacement too small: {total_curve_dist}"
        print(f"  [PASS] Dynamic curve traversed {total_curve_dist:.2f} units along rotating camera.")

        print("  [PASS] Camera-relative movement verified across all 8 cardinal/diagonal angles and dynamic sweeps.")
        test_results["test_2_camera_relative_movement"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] Test 2 failed: {e}")
        failures.append(f"Test 2: {e}")
        test_results["test_2_camera_relative_movement"] = f"FAIL: {e}"

    # =========================================================================
    # TEST 3: REAL-TIME WALKING TO ALL 4 ARENA CORNERS
    # =========================================================================
    print("\n--- TEST 3: Real-Time Walking to All 4 Arena Corners in 3rd-Person Mode ---")
    corners = [
        {"name": "Corner 1 (NE: +88, +88)", "targetX": 88, "targetZ": 88},
        {"name": "Corner 2 (NW: -88, +88)", "targetX": -88, "targetZ": 88},
        {"name": "Corner 3 (SW: -88, -88)", "targetX": -88, "targetZ": -88},
        {"name": "Corner 4 (SE: +88, -88)", "targetX": 88, "targetZ": -88}
    ]

    corner_walk_results = []
    try:
        for c in corners:
            tx, tz = c["targetX"], c["targetZ"]
            walk_data = await cdp.eval_js(f"""
                (async () => {{
                    window.cameraMode = 'thirdperson';
                    const p = window.units.find(u => u.isPlayer);
                    p.x = 0; p.z = 0;
                    p.deadTimer = 0;
                    p.animTimer = 0;
                    const origSpeed = p.speed;
                    p.speed = 70; // Set speed for corner transit
                    const targetYaw = Math.atan2({tx}, {tz});
                    window.tpCamYaw = targetYaw;
                    p.rotY = targetYaw;

                    const camCoords = [];
                    // Walk until corner reached (clamped at [-88, 88]) or max 100 frames
                    for (let step = 0; step < 100; step++) {{
                        window.keys['KeyW'] = true;
                        await new Promise(r => requestAnimationFrame(r));
                        const cam = window.camera;
                        camCoords.push({{
                            cx: cam.position.x,
                            cy: cam.position.y,
                            cz: cam.position.z,
                            px: p.x,
                            pz: p.z
                        }});
                        // Check if reached corner clamp
                        if (Math.abs(p.x - {tx}) <= 0.5 && Math.abs(p.z - {tz}) <= 0.5) {{
                            // Hold against wall for 15 more frames to stress clamping while pressed into corner
                            for (let h = 0; h < 15; h++) {{
                                await new Promise(r => requestAnimationFrame(r));
                                camCoords.push({{
                                    cx: cam.position.x,
                                    cy: cam.position.y,
                                    cz: cam.position.z,
                                    px: p.x,
                                    pz: p.z
                                }});
                            }}
                            break;
                        }}
                    }}
                    window.keys['KeyW'] = false;
                    p.speed = origSpeed;
                    return {{
                        finalP: {{ x: p.x, z: p.z }},
                        camSamples: camCoords
                    }};
                }})()
            """, await_promise=True)

            final_p = walk_data["finalP"]
            cam_samples = walk_data["camSamples"]
            print(f"  Reached {c['name']}: Player=({final_p['x']:.2f}, {final_p['z']:.2f}), Samples={len(cam_samples)}")

            # Assert player actually reached the corner
            dist_to_corner = math.hypot(final_p["x"] - tx, final_p["z"] - tz)
            assert dist_to_corner <= 1.0, f"Player did not reach corner {c['name']}: dist={dist_to_corner:.2f}"

            # Check all camera samples during walk
            min_y = min(s["cy"] for s in cam_samples)
            max_x = max(abs(s["cx"]) for s in cam_samples)
            max_z = max(abs(s["cz"]) for s in cam_samples)

            assert max_x <= 92.0001, f"Camera X exceeded 92: {max_x} at {c['name']}"
            assert max_z <= 92.0001, f"Camera Z exceeded 92: {max_z} at {c['name']}"
            assert min_y >= 2.1999, f"Camera Y dropped below 2.2: {min_y} at {c['name']}"

            corner_walk_results.append({
                "corner": c["name"],
                "final_pos": final_p,
                "min_cam_y": min_y,
                "max_cam_x": max_x,
                "max_cam_z": max_z
            })

        print("  [PASS] Walking to all 4 corners completed with player reaching boundary and zero camera clamping violations.")
        test_results["test_3_corner_walk"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] Test 3 failed: {e}")
        failures.append(f"Test 3: {e}")
        test_results["test_3_corner_walk"] = f"FAIL: {e}"

    # =========================================================================
    # TEST 4: EXTREME BOUNDARY & 360-DEGREE CAMERA CLAMPING STRESS
    # =========================================================================
    print("\n--- TEST 4: Boundary & 360-Degree Camera Clamping Stress (14 Perimeter Coordinates) ---")
    perimeter_coords = [
        # 4 Arena Corners at normal player boundary (88, 88)
        (88, 88, "Corner (+88, +88)"),
        (-88, 88, "Corner (-88, +88)"),
        (-88, -88, "Corner (-88, -88)"),
        (88, -88, "Corner (+88, -88)"),
        # 4 Arena Outer Stage Limits (92, 92)
        (92, 92, "Outer Limit (+92, +92)"),
        (-92, 92, "Outer Limit (-92, +92)"),
        (-92, -92, "Outer Limit (-92, -92)"),
        (92, -92, "Outer Limit (+92, -92)"),
        # 4 Cardinal Edges
        (0, 92, "North Edge (0, +92)"),
        (92, 0, "East Edge (+92, 0)"),
        (0, -92, "South Edge (0, -92)"),
        (-92, 0, "West Edge (-92, 0)"),
        # 2 Extreme Knockback Overrun Points (95, 95)
        (95, 95, "Overrun (+95, +95)"),
        (-95, -95, "Overrun (-95, -95)")
    ]

    total_samples = 0
    clamping_violations = []
    global_min_y = float("inf")
    global_max_x = float("-inf")
    global_min_x = float("inf")
    global_max_z = float("-inf")
    global_min_z = float("inf")

    try:
        for px, pz, label in perimeter_coords:
            eval_stress = f"""
                (async () => {{
                    window.cameraMode = 'thirdperson';
                    const p = window.units.find(u => u.isPlayer);
                    p.x = {px}; p.z = {pz};

                    const results = [];
                    // Test 24 yaw steps around 360 degrees
                    for (let yStep = 0; yStep < 24; yStep++) {{
                        const yaw = (yStep / 24) * Math.PI * 2;
                        window.tpCamYaw = yaw;

                        // Test 3 pitch angles: default (0.32), extreme low looking up (-0.5), high looking down (0.8)
                        for (const pitch of [0.32, -0.5, 0.8]) {{
                            window.tpCamPitch = pitch;
                            // Wait 1 render frame
                            await new Promise(r => requestAnimationFrame(r));
                            const cam = window.camera;
                            results.push({{
                                yaw,
                                pitch,
                                cx: cam.position.x,
                                cy: cam.position.y,
                                cz: cam.position.z,
                                nan: isNaN(cam.position.x) || isNaN(cam.position.y) || isNaN(cam.position.z)
                            }});
                        }}
                    }}
                    return results;
                }})()
            """
            samples = await cdp.eval_js(eval_stress, await_promise=True)
            for s in samples:
                total_samples += 1
                cx, cy, cz = s["cx"], s["cy"], s["cz"]
                global_min_y = min(global_min_y, cy)
                global_max_x = max(global_max_x, cx)
                global_min_x = min(global_min_x, cx)
                global_max_z = max(global_max_z, cz)
                global_min_z = min(global_min_z, cz)

                if s["nan"]:
                    clamping_violations.append(f"NaN camera coordinate at {label}, yaw={s['yaw']:.2f}")
                if cx < -92.0001 or cx > 92.0001:
                    clamping_violations.append(f"Camera X out of bounds ({cx:.3f}) at {label}, yaw={s['yaw']:.2f}")
                if cz < -92.0001 or cz > 92.0001:
                    clamping_violations.append(f"Camera Z out of bounds ({cz:.3f}) at {label}, yaw={s['yaw']:.2f}")
                if cy < 2.1999:
                    clamping_violations.append(f"Camera Y below minimum clearance ({cy:.3f} < 2.2) at {label}, pitch={s['pitch']:.2f}")

        print(f"  Stress tested {len(perimeter_coords)} coordinates x 72 configurations = {total_samples} samples.")
        print(f"  Global Camera Range observed:")
        print(f"    X: [{global_min_x:.3f}, {global_max_x:.3f}] (limit: [-92.0, 92.0])")
        print(f"    Y: [{global_min_y:.3f}] (minimum floor: 2.200)")
        print(f"    Z: [{global_min_z:.3f}, {global_max_z:.3f}] (limit: [-92.0, 92.0])")

        assert len(clamping_violations) == 0, f"Found {len(clamping_violations)} clamping violations:\n" + "\n".join(clamping_violations[:10])
        print("  [PASS] Zero camera boundary, height or NaN violations across all perimeter stress positions.")
        test_results["test_4_perimeter_clamping"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] Test 4 failed: {e}")
        failures.append(f"Test 4: {e}")
        test_results["test_4_perimeter_clamping"] = f"FAIL: {e}"

    # Capture screenshots of corner viewports
    print("\nCapturing visual evidence screenshots...")
    # Corner 1 view
    await cdp.eval_js("""
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.x = 88; p.z = 88;
            window.tpCamYaw = Math.PI * 1.25;
            window.tpCamPitch = 0.32;
        })()
    """)
    await asyncio.sleep(0.3)
    await cdp.save_screenshot("m2_challenger_corner_ne.png")

    # Corner 3 view
    await cdp.eval_js("""
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.x = -88; p.z = -88;
            window.tpCamYaw = Math.PI * 0.25;
            window.tpCamPitch = 0.32;
        })()
    """)
    await asyncio.sleep(0.3)
    await cdp.save_screenshot("m2_challenger_corner_sw.png")

    # =========================================================================
    # TEST 5: CONSOLE & ERROR AUDIT
    # =========================================================================
    print("\n--- TEST 5: Console & Runtime Error Audit ---")
    await asyncio.sleep(0.5)
    console_errs = list(cdp.errors)
    print(f"  Total console/page errors detected: {len(console_errs)}")
    if console_errs:
        for err in console_errs:
            print(f"    - {err}")
        failures.append(f"Console errors detected: {len(console_errs)}")
        test_results["test_5_console_errors"] = f"FAIL ({len(console_errs)} errors)"
    else:
        print("  [PASS] Clean runtime with 0 console errors or unhandled exceptions.")
        test_results["test_5_console_errors"] = "PASS"

    await cdp.close()

    print("\n" + "=" * 70)
    print("                EMPIRICAL CHALLENGER VERDICT")
    print("=" * 70)
    for t_name, t_res in test_results.items():
        print(f"  {t_name:35s}: {t_res}")
    print("=" * 70)

    if failures:
        print(f"\nOVERALL RESULT: FAILED ({len(failures)} failures)")
        return False, test_results, failures, {
            "min_y": global_min_y,
            "max_x": global_max_x,
            "min_x": global_min_x,
            "max_z": global_max_z,
            "min_z": global_min_z,
            "samples": total_samples
        }
    else:
        print("\nOVERALL RESULT: 100% PASSED - ALL EMPIRICAL VERIFICATIONS SATISFIED!")
        return True, test_results, [], {
            "min_y": global_min_y,
            "max_x": global_max_x,
            "min_x": global_min_x,
            "max_z": global_max_z,
            "min_z": global_min_z,
            "samples": total_samples
        }


def main():
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

    try:
        success, results, errs, stats = asyncio.run(run_stress_test_suite())
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nCRITICAL HARNESS EXCEPTION: {e}")
        success = False
        results = {}
        errs = [str(e)]
        stats = {}
    finally:
        proc.terminate()
        proc.wait()
        import shutil
        shutil.rmtree(tmp_profile, ignore_errors=True)

    # Save empirical summary to json for handoff
    summary_path = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\.agents\teamwork\teamwork_preview_challenger_m2_1\test_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "success": success,
            "results": results,
            "errors": errs,
            "stats": stats,
            "timestamp": time.time()
        }, f, indent=2)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
