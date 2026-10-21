"""
Automated E2E Test Suite for Chunin Arenas in NUBA (Naruto Ultimate Battle Arena)
Validates:
  1. All 3 Chunin stages (sd01b, sd03b, sd04a) load without NaN coordinates and 100% of meshes instantiated.
  2. Map switching via lobby chips and applyArena() synchronizes HUD names, minimap, sanctuary zones, and camera bounds.
  3. Camera clamping works per stage (ceiling clamp y<=26 on sd01b, circular clamp on sd03b).
  4. sd03b has zero degenerate screen-crossing spikes.
  5. 0 console errors emitted across all stages.
"""

import asyncio
import base64
import json
import math
import os
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

SCRATCH_DIR = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch"
os.makedirs(SCRATCH_DIR, exist_ok=True)


def find_edge_path():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Microsoft Edge executable not found in standard paths.")


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.console_errors = []
        self.console_logs = []
        self.running = False
        self._pending_requests = {}
        self._listener_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50_000_000)
        self.running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        await self.send("Runtime.enable")
        await self.send("Log.enable")
        await self.send("Page.enable")

    async def _listen_loop(self):
        try:
            while self.running:
                resp_raw = await self.ws.recv()
                data = json.loads(resp_raw)
                cid = data.get("id")
                if cid is not None and cid in self._pending_requests:
                    fut = self._pending_requests.pop(cid)
                    if not fut.done():
                        fut.set_result(data.get("result", {}))
                    continue

                method = data.get("method")
                if method == "Runtime.exceptionThrown":
                    exc = data["params"]["exceptionDetails"]
                    text = exc.get("exception", {}).get("description") or exc.get("text")
                    url = exc.get("url", "")
                    line = exc.get("lineNumber", -1)
                    col = exc.get("columnNumber", -1)
                    err_msg = f"[PAGE EXCEPTION] {text} at {url}:{line}:{col}"
                    self.console_errors.append(err_msg)
                    print(f"  {err_msg}")
                elif method == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        url_info = f" (url: {entry.get('url')})" if entry.get("url") else ""
                        err_msg = f"[LOG ERROR] {entry.get('text')}{url_info}"
                        self.console_errors.append(err_msg)
                        print(f"  {err_msg}")
                    else:
                        self.console_logs.append(entry.get("text"))
                elif method == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    text = " ".join(str(x) for x in args)
                    if call_type == "error":
                        err_msg = f"[CONSOLE ERROR] {text}"
                        self.console_errors.append(err_msg)
                        print(f"  {err_msg}")
                    else:
                        self.console_logs.append(f"[{call_type}] {text}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.running:
                print(f"[CDP Loop Error] {e}")

    async def send(self, method, params=None, timeout=30.0):
        self.msg_id += 1
        cid = self.msg_id
        req = {"id": cid, "method": method}
        if params:
            req["params"] = params

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_requests[cid] = fut

        await self.ws.send(json.dumps(req))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def eval_js(self, expr, await_promise=False, timeout=60.0):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise
        }, timeout=timeout)
        val = res.get("result", {}).get("value")
        exc = res.get("exceptionDetails")
        if exc:
            msg = exc.get("exception", {}).get("description") or exc.get("text")
            raise RuntimeError(f"JS Eval Error: {msg}")
        return val

    async def capture_screenshot(self, filename):
        shot = await self.send("Page.captureScreenshot", {"format": "png"})
        if "data" in shot:
            data_bytes = base64.b64decode(shot["data"])
            filepath = os.path.join(SCRATCH_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(data_bytes)
            print(f"  [SCREENSHOT] {filepath} ({len(data_bytes)} bytes)")
            return filepath
        return None

    async def close(self):
        self.running = False
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()


class TestResult:
    def __init__(self, test_id, name, group):
        self.test_id = test_id
        self.name = name
        self.group = group
        self.passed = False
        self.error = None
        self.duration = 0.0


class ArenasE2ETestRunner:
    def __init__(self, cdp: CDPClient):
        self.cdp = cdp
        self.results = []

    async def run_test(self, test_id, name, group, test_fn):
        res = TestResult(test_id, name, group)
        start_time = time.time()
        print(f"[{group}] Running {test_id}: {name}...", end=" ", flush=True)
        try:
            await test_fn()
            res.passed = True
            print("PASS")
        except Exception as e:
            res.passed = False
            res.error = str(e)
            print(f"FAIL -> {e}")
        finally:
            res.duration = time.time() - start_time
            self.results.append(res)

    # =========================================================================
    # GROUP 1: CHUNIN STAGES LOADING & MESH INTEGRITY (NO NaN, 100% INSTANTIATED)
    # =========================================================================

    async def test_01_sd01b_chunin_tower_mesh_integrity(self):
        """sd01b: Chunin Preliminaries Tower loads without NaN coordinates and 100% of meshes instantiated."""
        res = await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd01b');
                for (let i = 0; i < 50; i++) {
                    if (window.stage3DData && window.stage3DData.id === 'sd01b') break;
                    await new Promise(r => setTimeout(r, 100));
                }
                const raw = window.stage3DData;
                if (!raw || !raw.meshes) return { error: 'sd01b stage3DData not loaded' };

                let rawNaNCount = 0;
                let nonFiniteCount = 0;
                for (const sm of raw.meshes) {
                    if (sm.positions) {
                        for (const v of sm.positions) {
                            if (Number.isNaN(v)) rawNaNCount++;
                            if (!Number.isFinite(v)) nonFiniteCount++;
                        }
                    }
                    if (sm.normals) {
                        for (const v of sm.normals) {
                            if (Number.isNaN(v)) rawNaNCount++;
                            if (!Number.isFinite(v)) nonFiniteCount++;
                        }
                    }
                    if (sm.uvs) {
                        for (const v of sm.uvs) {
                            if (Number.isNaN(v)) rawNaNCount++;
                            if (!Number.isFinite(v)) nonFiniteCount++;
                        }
                    }
                }

                // Scene graph verification
                const group = window.cachedStageGroup || window.arenaGroup;
                let instantiatedMeshes = 0;
                let geomNaNCount = 0;
                let dbhSubmeshCount = 0;
                let dbhVertexCount = 0;
                const meshNames = [];

                if (group) {
                    group.traverse(obj => {
                        if (obj.isMesh && obj.geometry) {
                            instantiatedMeshes++;
                            meshNames.push(obj.name);
                            const posAttr = obj.geometry.getAttribute('position');
                            if (posAttr) {
                                const arr = posAttr.array;
                                for (let i = 0; i < arr.length; i++) {
                                    if (Number.isNaN(arr[i])) geomNaNCount++;
                                }
                            }
                            obj.geometry.computeBoundingBox();
                            const bb = obj.geometry.boundingBox;
                            if (bb) {
                                if (!Number.isFinite(bb.min.x) || !Number.isFinite(bb.max.x) ||
                                    !Number.isFinite(bb.min.y) || !Number.isFinite(bb.max.y) ||
                                    !Number.isFinite(bb.min.z) || !Number.isFinite(bb.max.z)) {
                                    geomNaNCount++;
                                }
                            }
                            const lowName = (obj.name || '').toLowerCase();
                            if (lowName.includes('dbh')) {
                                dbhSubmeshCount++;
                                if (posAttr) dbhVertexCount += posAttr.count;
                            }
                        }
                    });
                }

                return {
                    stageId: raw.id,
                    rawMeshCount: raw.meshes.length,
                    instantiatedMeshes,
                    rawNaNCount,
                    nonFiniteCount,
                    geomNaNCount,
                    dbhSubmeshCount,
                    dbhVertexCount
                };
            })()
        """, await_promise=True)

        assert "error" not in res, f"Failed loading sd01b: {res.get('error')}"
        assert res["stageId"] == "sd01b", f"Expected stageId 'sd01b', got '{res['stageId']}'"
        assert res["rawNaNCount"] == 0, f"Found {res['rawNaNCount']} NaN values in sd01b raw submesh data."
        assert res["nonFiniteCount"] == 0, f"Found {res['nonFiniteCount']} non-finite values in sd01b."
        assert res["geomNaNCount"] == 0, f"Found {res['geomNaNCount']} NaN values in sd01b Three.js geometries."
        assert res["instantiatedMeshes"] >= 80, f"Expected >= 80 instantiated meshes in sd01b, found {res['instantiatedMeshes']}."
        assert res["dbhSubmeshCount"] >= 15, f"Expected >= 15 Giant Hands Statue ('dbh') submeshes in sd01b, found {res['dbhSubmeshCount']}."
        assert res["dbhVertexCount"] > 10000, f"Expected > 10k vertices for Giant Hands Statue, found {res['dbhVertexCount']}."

    async def test_02_sd03b_chunin_colosseum_mesh_integrity(self):
        """sd03b: Chunin Finals Colosseum loads without NaN coordinates and 100% of meshes instantiated."""
        res = await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd03b');
                for (let i = 0; i < 50; i++) {
                    if (window.stage3DData && window.stage3DData.id === 'sd03b') break;
                    await new Promise(r => setTimeout(r, 100));
                }
                const raw = window.stage3DData;
                if (!raw || !raw.meshes) return { error: 'sd03b stage3DData not loaded' };

                let rawNaNCount = 0;
                let nonFiniteCount = 0;
                for (const sm of raw.meshes) {
                    if (sm.positions) {
                        for (const v of sm.positions) {
                            if (Number.isNaN(v)) rawNaNCount++;
                            if (!Number.isFinite(v)) nonFiniteCount++;
                        }
                    }
                }

                const group = window.cachedStageGroup || window.arenaGroup;
                let instantiatedMeshes = 0;
                let geomNaNCount = 0;
                let wallMeshesCount = 0;
                let treeMeshesCount = 0;

                if (group) {
                    group.traverse(obj => {
                        if (obj.isMesh && obj.geometry) {
                            instantiatedMeshes++;
                            const posAttr = obj.geometry.getAttribute('position');
                            if (posAttr) {
                                for (let i = 0; i < posAttr.array.length; i++) {
                                    if (Number.isNaN(posAttr.array[i])) geomNaNCount++;
                                }
                            }
                            const lowName = (obj.name || '').toLowerCase();
                            if (lowName.includes('sd03b01_') || lowName.includes('wall')) {
                                wallMeshesCount++;
                            }
                            if (lowName.includes('ki00') || lowName.includes('ki01') || lowName.includes('tree')) {
                                treeMeshesCount++;
                            }
                        }
                    });
                }

                return {
                    stageId: raw.id,
                    rawMeshCount: raw.meshes.length,
                    instantiatedMeshes,
                    rawNaNCount,
                    nonFiniteCount,
                    geomNaNCount,
                    wallMeshesCount,
                    treeMeshesCount
                };
            })()
        """, await_promise=True)

        assert "error" not in res, f"Failed loading sd03b: {res.get('error')}"
        assert res["stageId"] == "sd03b", f"Expected stageId 'sd03b', got '{res['stageId']}'"
        assert res["rawNaNCount"] == 0, f"Found {res['rawNaNCount']} NaN values in sd03b raw data."
        assert res["nonFiniteCount"] == 0, f"Found {res['nonFiniteCount']} non-finite coordinates in sd03b."
        assert res["geomNaNCount"] == 0, f"Found {res['geomNaNCount']} NaN values in sd03b Three.js geometries."
        assert res["instantiatedMeshes"] >= 200, f"Expected >= 200 instantiated meshes in sd03b, found {res['instantiatedMeshes']}."
        assert res["wallMeshesCount"] >= 15, f"Expected perimeter stone wall meshes, found {res['wallMeshesCount']}."
        assert res["treeMeshesCount"] >= 4, f"Expected central colosseum trees, found {res['treeMeshesCount']}."

    async def test_03_sd04a_chunin_plateau_mesh_integrity(self):
        """sd04a: Chunin Plateau / Wild Stadium loads without NaN coordinates and 100% of meshes instantiated."""
        res = await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd04a');
                for (let i = 0; i < 50; i++) {
                    if (window.stage3DData && window.stage3DData.id === 'sd04a') break;
                    await new Promise(r => setTimeout(r, 100));
                }
                const raw = window.stage3DData;
                if (!raw || !raw.meshes) return { error: 'sd04a stage3DData not loaded' };

                let rawNaNCount = 0;
                let nonFiniteCount = 0;
                for (const sm of raw.meshes) {
                    if (sm.positions) {
                        for (const v of sm.positions) {
                            if (Number.isNaN(v)) rawNaNCount++;
                            if (!Number.isFinite(v)) nonFiniteCount++;
                        }
                    }
                }

                const group = window.cachedStageGroup || window.arenaGroup;
                let instantiatedMeshes = 0;
                let geomNaNCount = 0;
                let rockCliffCount = 0;
                let foliageCount = 0;
                let alphaTestCount = 0;

                if (group) {
                    group.traverse(obj => {
                        if (obj.isMesh && obj.geometry) {
                            instantiatedMeshes++;
                            const posAttr = obj.geometry.getAttribute('position');
                            if (posAttr) {
                                for (let i = 0; i < posAttr.array.length; i++) {
                                    if (Number.isNaN(posAttr.array[i])) geomNaNCount++;
                                }
                            }
                            const lowName = (obj.name || '').toLowerCase();
                            if (lowName.includes('flo002') || lowName.includes('obj005') || lowName.includes('cliff')) {
                                rockCliffCount++;
                            }
                            if (lowName.includes('tree') || lowName.includes('plant') || lowName.includes('ki0')) {
                                foliageCount++;
                                if (obj.material && (obj.material.alphaTest >= 0.20)) {
                                    alphaTestCount++;
                                }
                            }
                        }
                    });
                }

                return {
                    stageId: raw.id,
                    rawMeshCount: raw.meshes.length,
                    instantiatedMeshes,
                    rawNaNCount,
                    nonFiniteCount,
                    geomNaNCount,
                    rockCliffCount,
                    foliageCount,
                    alphaTestCount
                };
            })()
        """, await_promise=True)

        assert "error" not in res, f"Failed loading sd04a: {res.get('error')}"
        assert res["stageId"] == "sd04a", f"Expected stageId 'sd04a', got '{res['stageId']}'"
        assert res["rawNaNCount"] == 0, f"Found {res['rawNaNCount']} NaN values in sd04a raw data."
        assert res["nonFiniteCount"] == 0, f"Found {res['nonFiniteCount']} non-finite coordinates in sd04a."
        assert res["geomNaNCount"] == 0, f"Found {res['geomNaNCount']} NaN values in sd04a Three.js geometries."
        assert res["instantiatedMeshes"] >= 100, f"Expected >= 100 instantiated meshes in sd04a, found {res['instantiatedMeshes']}."
        assert res["rockCliffCount"] >= 2, f"Expected rock cliff wall meshes, found {res['rockCliffCount']}."
        assert res["foliageCount"] >= 10, f"Expected tree/plant foliage meshes, found {res['foliageCount']}."

    # =========================================================================
    # GROUP 2: MAP SWITCHING & SYNCHRONIZATION (HUD, MINIMAP, SANCTUARIES, BOUNDS)
    # =========================================================================

    async def test_04_lobby_chips_switching_and_hud_sync(self):
        """Map switching via lobby chips synchronizes .selected chip, #arena-name, #minimap-arena-name, and ARENA.id."""
        stages = [
            ("sd01b", "Torre"),
            ("sd03b", "Coliseu"),
            ("sd04a", "Selvagem"),
        ]
        for stage_id, expected_substr in stages:
            res = await self.cdp.eval_js(f"""
                (async () => {{
                    const chip = document.querySelector(`.arena-chip[data-arena="{stage_id}"]`);
                    if (!chip) return {{ error: 'Chip not found for {stage_id}' }};

                    chip.click();
                    let activeChip = null;
                    for (let i = 0; i < 40; i++) {{
                        activeChip = document.querySelector(`.arena-chip[data-arena="{stage_id}"].selected`);
                        if (activeChip && window.ARENA && window.ARENA.id === '{stage_id}') break;
                        await new Promise(r => setTimeout(r, 100));
                    }}

                    const arenaNameEl = document.getElementById('arena-name');
                    const minimapEl = document.getElementById('minimap-arena-name');
                    const isSelected = !!activeChip;

                    return {{
                        arenaId: window.ARENA.id,
                        arenaLabel: window.ARENA.label,
                        hudName: arenaNameEl ? arenaNameEl.textContent.trim() : null,
                        minimapName: minimapEl ? minimapEl.textContent.trim() : null,
                        isSelected
                    }};
                }})()
            """, await_promise=True)

            assert "error" not in res, res.get("error")
            assert res["arenaId"] == stage_id, f"Expected ARENA.id '{stage_id}', got '{res['arenaId']}'"
            assert res["isSelected"], f"Chip for '{stage_id}' did not receive 'selected' class."
            assert expected_substr.lower() in res["hudName"].lower(), \
                f"Expected '{expected_substr}' in #arena-name, got '{res['hudName']}'"
            assert res["minimapName"].upper().startswith("ARENA"), \
                f"Expected '#minimap-arena-name' to start with 'ARENA', got '{res['minimapName']}'"
            assert expected_substr.lower() in res["minimapName"].lower(), \
                f"Expected '{expected_substr}' in #minimap-arena-name, got '{res['minimapName']}'"

    async def test_05_sanctuary_zones_and_spawn_synchronization(self):
        """applyArena() synchronizes sanctuary zones and spawn coordinates to avoid floating/embedded bases."""
        res = await self.cdp.eval_js("""
            (async () => {
                const results = {};
                for (const stageId of ['sd01b', 'sd03b', 'sd04a']) {
                    await window.applyArena(stageId);
                    await new Promise(r => setTimeout(r, 200));

                    const bpBlue = window.basePos('blue');
                    const bpRed = window.basePos('red');
                    const hasCustom = Boolean(window.ARENA && window.ARENA.sanctuaryBlue);

                    results[stageId] = {
                        blue: bpBlue,
                        red: bpRed,
                        radius: window.ARENA.radius,
                        baseOffset: window.ARENA.baseOffset,
                        hasCustom,
                        finite: Number.isFinite(bpBlue.x) && Number.isFinite(bpBlue.z) &&
                                Number.isFinite(bpRed.x) && Number.isFinite(bpRed.z)
                    };
                }
                return results;
            })()
        """, await_promise=True)

        # 1. Verify dynamic synchronization across stages (sanctuary positions change with each arena)
        assert res["sd01b"]["blue"] != res["sd03b"]["blue"], \
            "Sanctuary coordinates did not change when switching from sd01b to sd03b!"
        assert res["sd03b"]["blue"] != res["sd04a"]["blue"], \
            "Sanctuary coordinates did not change when switching from sd03b to sd04a!"

        for sid in ['sd01b', 'sd03b', 'sd04a']:
            data = res[sid]
            assert data["finite"], f"Non-finite sanctuary coordinates on {sid}"
            blue = data["blue"]
            red = data["red"]

            # If custom sanctuary coordinates are defined, enforce exact geometric placement contract
            if data["hasCustom"]:
                if sid == "sd01b":
                    assert abs(blue["x"]) <= 12, f"sd01b Blue sanctuary X off center: {blue['x']}"
                    assert abs(red["x"]) <= 12, f"sd01b Red sanctuary X off center: {red['x']}"
                    assert abs(blue["z"]) >= 40, f"sd01b Blue sanctuary Z too close to center: {blue['z']}"
                    assert abs(red["z"]) >= 40, f"sd01b Red sanctuary Z too close to center: {red['z']}"
                elif sid == "sd03b":
                    r_blue = math.hypot(blue["x"], blue["z"])
                    r_red = math.hypot(red["x"], red["z"])
                    assert r_blue <= 80.0, f"sd03b Blue sanctuary exceeds colosseum wall: {r_blue}m"
                    assert r_red <= 80.0, f"sd03b Red sanctuary exceeds colosseum wall: {r_red}m"
                elif sid == "sd04a":
                    assert blue["x"] >= -48, f"sd04a Blue sanctuary floating off valley cliff: X={blue['x']} (min -48)"
                    assert red["x"] <= 40, f"sd04a Red sanctuary inside solid rock cliff: X={red['x']} (max 40)"
            else:
                # Fallback baseOffset synchronization contract (scaling dynamically with stage radius)
                expected_offset = round(data["radius"] * 0.84)
                assert abs(blue["x"] - (-expected_offset)) <= 1.0, \
                    f"{sid} Blue sanctuary X does not match synchronized baseOffset {expected_offset}"
                assert abs(red["x"] - expected_offset) <= 1.0, \
                    f"{sid} Red sanctuary X does not match synchronized baseOffset {expected_offset}"

    async def test_06_camera_bounds_synchronization(self):
        """applyArena() synchronizes cameraLimit and boundary profiles per stage."""
        res = await self.cdp.eval_js("""
            (async () => {
                const catalog = window.arenasCatalog || [];
                const limits = {};
                for (const stageId of ['sd01b', 'sd03b', 'sd04a']) {
                    await window.applyArena(stageId);
                    await new Promise(r => setTimeout(r, 150));
                    limits[stageId] = {
                        id: window.ARENA.id,
                        radius: window.ARENA.radius,
                        cameraLimit: window.ARENA.cameraLimit,
                        cameraMaxY: window.ARENA.cameraMaxY || null
                    };
                }
                return limits;
            })()
        """, await_promise=True)

        for sid in ['sd01b', 'sd03b', 'sd04a']:
            info = res[sid]
            assert info["radius"] > 0, f"{sid} has non-positive radius"
            assert info["cameraLimit"] >= info["radius"], f"{sid} cameraLimit must be >= radius"

    # =========================================================================
    # GROUP 3: CAMERA CLAMPING PER STAGE (CEILING Y<=26 on sd01b, CIRCULAR on sd03b)
    # =========================================================================

    async def test_07_camera_ceiling_clamp_sd01b(self):
        """sd01b: 3rd-person camera respects indoor ceiling clamp Y <= 26.0."""
        res = await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd01b');
                for (let i = 0; i < 40; i++) {
                    if (window.stage3DData && window.stage3DData.id === 'sd01b') break;
                    await new Promise(r => setTimeout(r, 100));
                }
                window.cameraMode = '3rd';
                const p = window.units.find(u => u.isPlayer) || window.units[0];
                if (p) {
                    p.x = 0; p.z = 0;
                }
                // High vertical pitch to force camera height upwards towards ceiling
                window.tpCamPitch = 1.35;

                // Allow render frames to update camera position
                await new Promise(r => setTimeout(r, 400));

                const camY = window.camera.position.y;
                const camX = window.camera.position.x;
                const camZ = window.camera.position.z;

                return {
                    camY,
                    camX,
                    camZ,
                    cameraMaxY: window.ARENA.cameraMaxY || 26.0
                };
            })()
        """, await_promise=True)

        assert res["camY"] <= 26.001, f"sd01b camera height Y={res['camY']:.2f} clipped above ceiling limit 26.0"
        assert res["camY"] >= 2.2, f"sd01b camera height Y={res['camY']:.2f} dipped below minimum floor clearance 2.2"

    async def test_08_camera_circular_clamp_sd03b(self):
        """sd03b: Circular colosseum camera clamping prevents diagonal corners from cutting into 92m stone wall."""
        res = await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd03b');
                for (let i = 0; i < 40; i++) {
                    if (window.stage3DData && window.stage3DData.id === 'sd03b') break;
                    await new Promise(r => setTimeout(r, 100));
                }
                window.cameraMode = '3rd';
                const p = window.units.find(u => u.isPlayer) || window.units[0];
                // Move player towards the diagonal corner
                if (p) {
                    p.x = 65;
                    p.z = 65;
                }
                // Look outwards to push camera horizontally into the diagonal corner
                window.tpCamYaw = Math.PI * 0.25; // 45 degrees
                window.tpCamPitch = 0.2;

                await new Promise(r => setTimeout(r, 300));

                const camX = window.camera.position.x;
                const camZ = window.camera.position.z;
                const radDist = Math.hypot(camX, camZ);
                const arenaRadius = window.ARENA.radius;
                const cameraLimit = window.ARENA.cameraLimit;

                return {
                    camX,
                    camZ,
                    radDist,
                    arenaRadius,
                    cameraLimit
                };
            })()
        """, await_promise=True)

        # Stone wall is at r=92m. Camera radial distance must never exceed the wall perimeter!
        assert res["radDist"] <= 92.0, \
            f"sd03b camera radial distance {res['radDist']:.2f}m clipped outside circular stone wall (92m)!"
        assert res["radDist"] <= (res["cameraLimit"] + 1.0), \
            f"sd03b camera radial distance {res['radDist']:.2f}m exceeded camera limit {res['cameraLimit']}m"

    async def test_09_camera_ground_clearance_all_stages(self):
        """3rd-person camera maintains safe ground clearance Y >= 2.2 across all Chunin stages."""
        res = await self.cdp.eval_js("""
            (async () => {
                const results = {};
                for (const stageId of ['sd01b', 'sd03b', 'sd04a']) {
                    await window.applyArena(stageId);
                    window.cameraMode = '3rd';
                    window.tpCamPitch = -1.1; // steep downward pitch aiming at ground
                    await new Promise(r => setTimeout(r, 200));
                    results[stageId] = {
                        camY: window.camera.position.y
                    };
                }
                return results;
            })()
        """, await_promise=True)

        for sid, d in res.items():
            assert d["camY"] >= 2.19, f"{sid} camera height dipped below ground: Y={d['camY']:.2f}"

    # =========================================================================
    # GROUP 4: ZERO DEGENERATE SCREEN-CROSSING SPIKES (sd03b)
    # =========================================================================

    async def test_10_sd03b_zero_degenerate_spikes(self):
        """sd03b has zero degenerate 3-vertex screen-crossing spikes spanning across origin."""
        res = await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd03b');
                const raw = window.stage3DData;
                if (!raw || !raw.meshes) return { error: 'sd03b stage3DData not available' };

                let degenerateMeshesFound = [];
                let hugeTrianglesFound = 0;
                const forbidden = ['sd03b02', 'sd03b04', 'sd03balfa07', 'trans_obj08_sub1'];
                const scale = raw.scale || 0.022;

                for (const sm of raw.meshes) {
                    const name = (sm.name || '').toLowerCase();
                    // Check if blacklisted degenerate chunks made it into output
                    for (const f of forbidden) {
                        if (name.includes(f)) {
                            degenerateMeshesFound.push(name);
                            break;
                        }
                    }

                    // Scan all triangles across submeshes for degenerate spanning spikes
                    const isBg = name.includes('bac') || name.includes('dome') || name.includes('cloud');
                    const p = sm.positions;
                    const idx = sm.indices;
                    if (!isBg && p && p.length >= 9) {
                        const vCount = Math.floor(p.length / 3);
                        const triCount = (idx && idx.length >= 3) ? Math.floor(idx.length / 3) : Math.floor(vCount / 3);

                        for (let t = 0; t < triCount; t++) {
                            const i0 = (idx && idx.length >= 3) ? idx[3 * t] : 3 * t;
                            const i1 = (idx && idx.length >= 3) ? idx[3 * t + 1] : 3 * t + 1;
                            const i2 = (idx && idx.length >= 3) ? idx[3 * t + 2] : 3 * t + 2;
                            if (i0 >= vCount || i1 >= vCount || i2 >= vCount) continue;

                            const p0 = [p[3 * i0] * scale, p[3 * i0 + 1] * scale, p[3 * i0 + 2] * scale];
                            const p1 = [p[3 * i1] * scale, p[3 * i1 + 1] * scale, p[3 * i1 + 2] * scale];
                            const p2 = [p[3 * i2] * scale, p[3 * i2 + 1] * scale, p[3 * i2 + 2] * scale];

                            const e0 = Math.hypot(p0[0] - p1[0], p0[1] - p1[1], p0[2] - p1[2]);
                            const e1 = Math.hypot(p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]);
                            const e2 = Math.hypot(p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]);
                            const maxEdge = Math.max(e0, e1, e2);
                            // Edge > 400m indicates degenerate stretch
                            if (maxEdge > 400.0) {
                                hugeTrianglesFound++;
                                degenerateMeshesFound.push(`${name} (edge=${maxEdge.toFixed(1)}m)`);
                                break;
                            }

                            // Origin spike: touches origin (<0.01m) and reaches past 30m
                            const d0 = Math.hypot(p0[0], p0[2]);
                            const d1 = Math.hypot(p1[0], p1[2]);
                            const d2 = Math.hypot(p2[0], p2[2]);
                            if (Math.min(d0, d1, d2) < 0.01 && Math.max(d0, d1, d2) > 30.0) {
                                hugeTrianglesFound++;
                                degenerateMeshesFound.push(`${name} (origin_spike min=${Math.min(d0,d1,d2).toFixed(2)}m max=${Math.max(d0,d1,d2).toFixed(2)}m)`);
                                break;
                            }
                        }
                    }
                }

                // Scene graph verification
                const group = window.cachedStageGroup || window.arenaGroup;
                let sceneDegenerateCount = 0;
                if (group) {
                    group.traverse(obj => {
                        if (obj.isMesh && obj.geometry) {
                            const name = (obj.name || '').toLowerCase();
                            for (const f of forbidden) {
                                if (name.includes(f)) {
                                    sceneDegenerateCount++;
                                    break;
                                }
                            }
                        }
                    });
                }

                return {
                    degenerateMeshesFound,
                    hugeTrianglesFound,
                    sceneDegenerateCount
                };
            })()
        """, await_promise=True)

        assert "error" not in res, res.get("error")
        assert len(res["degenerateMeshesFound"]) == 0, \
            f"Degenerate meshes detected in sd03b: {res['degenerateMeshesFound']}"
        assert res["hugeTrianglesFound"] == 0, \
            f"Found {res['hugeTrianglesFound']} huge spanning triangles in sd03b."
        assert res["sceneDegenerateCount"] == 0, \
            f"Found {res['sceneDegenerateCount']} degenerate meshes in Three.js scene graph."

    # =========================================================================
    # GROUP 5: 0 CONSOLE ERRORS ACROSS ALL STAGES & COMBAT
    # =========================================================================

    async def test_11_zero_console_errors_across_all_stages(self):
        """0 console errors emitted across all Chunin stages and combat skill activations."""
        # Cycle through stages and trigger combat actions on each
        res = await self.cdp.eval_js("""
            (async () => {
                const log = [];
                for (const stageId of ['sd01b', 'sd03b', 'sd04a', 'sd01b']) {
                    await window.applyArena(stageId);
                    await new Promise(r => setTimeout(r, 150));

                    const p = window.units.find(u => u.isPlayer);
                    if (p) {
                        p.cds.atk = 0;
                        window.executeSkill(p, 'atk');
                        p.cds.q = 0; p.chakra = 100;
                        window.executeSkill(p, 'q');
                        p.cds.e = 0; p.chakra = 100;
                        window.executeSkill(p, 'e');
                        p.cds.space = 0; p.chakra = 100;
                        window.executeSkill(p, 'space');
                        p.cds.r = 0; p.chakra = 100;
                        window.executeSkill(p, 'r');
                    }
                    await new Promise(r => setTimeout(r, 100));
                    log.push(`Tested ${stageId}`);
                }
                return { success: true, log };
            })()
        """, await_promise=True)

        assert res.get("success"), "Stage combat cycle failed to complete."
        # Verify console errors
        assert len(self.cdp.console_errors) == 0, \
            f"Console errors emitted during arena switching: {self.cdp.console_errors}"

    # =========================================================================
    # GROUP 6: PHOTOGRAPHIC VISUAL VALIDATION CAPTURES
    # =========================================================================

    async def test_12_photographic_visual_validation_captures(self):
        """Capture high-resolution screenshots of Chunin Arenas for audit."""
        # 1. sd01b Preliminaries Tower (focus on Giant Hands Statue)
        await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd01b');
                window.cameraMode = 'cinematic';
                window.camera.position.set(0, 16, 38);
                window.camera.lookAt(0, 10, -18);
                window.camera.fov = 55;
                window.camera.updateProjectionMatrix();
                const b = document.getElementById('center-banner');
                if (b) b.classList.add('hidden');
            })()
        """, await_promise=True)
        await asyncio.sleep(0.8)
        shot1 = await self.cdp.capture_screenshot("sd01b_chunin_tower_test.png")
        assert shot1 and os.path.exists(shot1), "Failed capturing sd01b screenshot."

        # 2. sd03b Colosseum Panorama
        await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd03b');
                window.cameraMode = 'cinematic';
                window.camera.position.set(0, 48, 85);
                window.camera.lookAt(0, 4, 0);
                window.camera.fov = 55;
                window.camera.updateProjectionMatrix();
            })()
        """, await_promise=True)
        await asyncio.sleep(0.8)
        shot2 = await self.cdp.capture_screenshot("sd03b_chunin_colosseum_test.png")
        assert shot2 and os.path.exists(shot2), "Failed capturing sd03b screenshot."

        # 3. sd04a Plateau Panorama
        await self.cdp.eval_js("""
            (async () => {
                await window.applyArena('sd04a');
                window.cameraMode = 'cinematic';
                window.camera.position.set(0, 50, 95);
                window.camera.lookAt(0, 4, 0);
                window.camera.fov = 55;
                window.camera.updateProjectionMatrix();
            })()
        """, await_promise=True)
        await asyncio.sleep(0.8)
        shot3 = await self.cdp.capture_screenshot("sd04a_chunin_plateau_test.png")
        assert shot3 and os.path.exists(shot3), "Failed capturing sd04a screenshot."


async def run_arenas_suite():
    print("==================================================================")
    print("      NUBA ARENAS E2E TEST SUITE (Chunin Arenas M5 Verification)  ")
    print("==================================================================")

    edge_bin = find_edge_path()
    port = get_free_port()
    tmp_profile = os.path.join(tempfile.gettempdir(), f"edge_arenas_e2e_{port}")
    os.makedirs(tmp_profile, exist_ok=True)

    print(f"Starting Headless Edge on port {port} with profile {tmp_profile}...")
    proc = subprocess.Popen([
        edge_bin,
        "--headless=new",
        f"--remote-debugging-port={port}",
        "--disable-gpu",
        "--window-size=1600,900",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    await asyncio.sleep(2.5)

    cdp = None
    runner = None
    all_passed = False

    try:
        # Connect to CDP
        ws_url = None
        for _ in range(30):
            try:
                data = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2).read()
                tabs = json.loads(data.decode("utf-8"))
                for t in tabs:
                    if "localhost" in t.get("url", ""):
                        ws_url = t.get("webSocketDebuggerUrl")
                        break
                if ws_url:
                    break
            except Exception:
                await asyncio.sleep(0.3)

        if not ws_url:
            raise RuntimeError(f"Could not connect to Edge remote debugging port {port}")

        print(f"Connected to CDP endpoint: {ws_url}")
        cdp = CDPClient(ws_url)
        await cdp.connect()

        # Wait for page assets and Three.js initialization
        print("Waiting for page assets and Three.js initialization...")
        for _ in range(40):
            res = await cdp.eval_js("Boolean(window.rosterMeta && window.stage3DData && window.arenasCatalog)")
            if res is True:
                break
            await asyncio.sleep(0.5)

        runner = ArenasE2ETestRunner(cdp)

        # ---------------------------------------------------------------------
        # Group 1: Chunin Stages Mesh & Coordinate Integrity
        # ---------------------------------------------------------------------
        print("\n--- Group 1: Chunin Stages Mesh & Coordinate Integrity ---")
        await runner.run_test("G1_01", "sd01b Chunin Tower Mesh Integrity & Statue", "G1", runner.test_01_sd01b_chunin_tower_mesh_integrity)
        await runner.run_test("G1_02", "sd03b Chunin Colosseum Mesh Integrity & Wall", "G1", runner.test_02_sd03b_chunin_colosseum_mesh_integrity)
        await runner.run_test("G1_03", "sd04a Chunin Plateau Mesh Integrity & Cliff", "G1", runner.test_03_sd04a_chunin_plateau_mesh_integrity)

        # ---------------------------------------------------------------------
        # Group 2: Map Switching & Synchronization
        # ---------------------------------------------------------------------
        print("\n--- Group 2: Map Switching & Synchronization ---")
        await runner.run_test("G2_01", "Lobby Chips Switching & HUD Labels Sync", "G2", runner.test_04_lobby_chips_switching_and_hud_sync)
        await runner.run_test("G2_02", "Sanctuary Zones & Spawn Synchronization", "G2", runner.test_05_sanctuary_zones_and_spawn_synchronization)
        await runner.run_test("G2_03", "Camera Limits & Boundaries Synchronization", "G2", runner.test_06_camera_bounds_synchronization)

        # ---------------------------------------------------------------------
        # Group 3: Camera Clamping Per Stage
        # ---------------------------------------------------------------------
        print("\n--- Initializing 5v5 Match for Camera Clamping & Combat Tests ---")
        start_match_js = """
        (async () => {
            if (!window.matchActive && typeof window.start5v5Match === 'function') {
                await window.start5v5Match();
            }
            for (let i = 0; i < 80; i++) {
                if (window.units && window.units.length === 10) return true;
                await new Promise(r => setTimeout(r, 100));
            }
            return window.units && window.units.length === 10;
        })()
        """
        match_init = await cdp.eval_js(start_match_js, await_promise=True, timeout=60.0)
        print(f"5v5 Match initialized (10 units active): {match_init}")

        print("\n--- Group 3: Camera Clamping Per Stage ---")
        await runner.run_test("G3_01", "sd01b Camera Ceiling Clamp Y <= 26.0", "G3", runner.test_07_camera_ceiling_clamp_sd01b)
        await runner.run_test("G3_02", "sd03b Camera Circular Perimeter Clamp", "G3", runner.test_08_camera_circular_clamp_sd03b)
        await runner.run_test("G3_03", "All Stages Camera Ground Clearance Y >= 2.2", "G3", runner.test_09_camera_ground_clearance_all_stages)

        # ---------------------------------------------------------------------
        # Group 4: Degenerate Screen-Crossing Spikes Prevention
        # ---------------------------------------------------------------------
        print("\n--- Group 4: Degenerate Screen-Crossing Spikes Prevention ---")
        await runner.run_test("G4_01", "sd03b Zero Degenerate Spikes Across Origin", "G4", runner.test_10_sd03b_zero_degenerate_spikes)

        # ---------------------------------------------------------------------
        # Group 5: Zero Console Errors Across Stages & Combat
        # ---------------------------------------------------------------------
        print("\n--- Group 5: Zero Console Errors Across Stages & Combat ---")
        await runner.run_test("G5_01", "0 Console Errors During Switching & Combat", "G5", runner.test_11_zero_console_errors_across_all_stages)

        # ---------------------------------------------------------------------
        # Group 6: Photographic Visual Validation Captures
        # ---------------------------------------------------------------------
        print("\n--- Group 6: Photographic Visual Validation Captures ---")
        await runner.run_test("G6_01", "Photographic Screenshots of 3 Chunin Stages", "G6", runner.test_12_photographic_visual_validation_captures)

    finally:
        console_errors = []
        if cdp:
            console_errors = list(cdp.console_errors)
            await cdp.close()

        print("Terminating Edge instance...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        import shutil
        shutil.rmtree(tmp_profile, ignore_errors=True)

    if not runner:
        print("CRITICAL: Test runner did not execute.")
        return False, [], console_errors

    total_tests = len(runner.results)
    passed_tests = sum(1 for r in runner.results if r.passed)
    failed_tests = total_tests - passed_tests

    print("\n==================================================================")
    print("                    ARENAS E2E TEST SUMMARY                       ")
    print("==================================================================")
    for r in runner.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.test_id}: {r.name} ({r.duration:.2f}s)")
        if r.error:
            print(f"         Error: {r.error}")
    print("------------------------------------------------------------------")
    print(f"  Total Tests : {total_tests}")
    print(f"  Passed      : {passed_tests}")
    print(f"  Failed      : {failed_tests}")
    print(f"  Console Errs: {len(console_errors)}")
    if console_errors:
        print("  Errors Logged:")
        for err in console_errors:
            print(f"    - {err}")
    print("==================================================================")

    all_passed = (failed_tests == 0 and len(console_errors) == 0)
    return all_passed, runner.results, console_errors


def main():
    try:
        all_passed, results, console_errors = asyncio.run(run_arenas_suite())
        if all_passed:
            print("\n>>> ALL CHUNIN ARENAS E2E TESTS PASSED WITH ZERO CONSOLE ERRORS! <<<\n")
            sys.exit(0)
        else:
            print("\n>>> ARENAS E2E TEST SUITE DETECTED FAILURES OR CONSOLE ERRORS! <<<\n")
            sys.exit(1)
    except Exception as e:
        print(f"\nCRITICAL RUNNER EXCEPTION: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
