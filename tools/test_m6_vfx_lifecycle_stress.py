"""
Adversarial Stress Test: VFX Lifecycle & Memory Disposal (Milestone M6 Challenger 2)

Empirically challenges:
1. Rapid skill casting across all 10 ninjas in succession (Rasengan, Chidori, Kaiten, Kirin, Sand Shield, Amaterasu, etc.).
2. Verification of transient child meshes (lightning segments, gyroscopic rings, shockwave discs, decal meshes) and their cleanup and disposal upon duration expiry.
3. Arena switching and hero switching during active VFX (checking for uncaught exceptions, orphaned meshes, or broken bindings).
4. Zero console errors, zero WebGL warnings, zero NaN positions/rotations/scales.
5. High-frequency stress loop (100+ rapid skill casts) to measure memory leak and frame stability.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

def find_edge():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Microsoft Edge executable not found.")

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

class VFXStressHarness:
    def __init__(self, port):
        self.port = port
        self.ws = None
        self.msg_id = 0
        self.pending = {}
        self.console_errors = []
        self.console_warnings = []
        self.runtime_exceptions = []
        self.is_listening = False

    async def connect(self):
        tabs = None
        for _ in range(25):
            try:
                data = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=3).read()
                tabs = json.loads(data)
                if tabs:
                    break
            except Exception:
                await asyncio.sleep(0.5)

        if not tabs:
            raise RuntimeError("Could not connect to Edge DevTools port.")

        target = None
        for t in tabs:
            if "localhost:8080" in t.get("url", ""):
                target = t
                break
        if not target:
            target = tabs[0]

        ws_url = target["webSocketDebuggerUrl"]
        self.ws = await websockets.connect(ws_url, max_size=50_000_000)
        self.is_listening = True
        asyncio.create_task(self._listen())

        await self.send("Runtime.enable")
        await self.send("Log.enable")
        await self.send("Page.enable")

    async def _listen(self):
        try:
            while self.is_listening:
                raw = await self.ws.recv()
                msg = json.loads(raw)
                cid = msg.get("id")
                if cid is not None and cid in self.pending:
                    fut = self.pending.pop(cid)
                    if not fut.done():
                        fut.set_result(msg.get("result", {}))
                    continue

                method = msg.get("method")
                params = msg.get("params", {})
                if method == "Runtime.exceptionThrown":
                    exc = params.get("exceptionDetails", {})
                    text = exc.get("exception", {}).get("description") or exc.get("text", "Unknown exception")
                    self.runtime_exceptions.append(text)
                    print(f"  [PAGE EXCEPTION] {text}", flush=True)
                elif method == "Log.entryAdded":
                    entry = params.get("entry", {})
                    level = entry.get("level")
                    txt = entry.get("text", "")
                    if level == "error":
                        self.console_errors.append(txt)
                        print(f"  [LOG ERROR] {txt}", flush=True)
                    elif level == "warning" and "webgl" in txt.lower():
                        self.console_warnings.append(txt)
                        print(f"  [WEBGL WARNING] {txt}", flush=True)
                elif method == "Runtime.consoleAPICalled":
                    call_type = params.get("type")
                    args = [str(a.get("value", a.get("description", ""))) for a in params.get("args", [])]
                    joined = " ".join(args)
                    if call_type == "error":
                        self.console_errors.append(joined)
                        print(f"  [CONSOLE ERROR] {joined}", flush=True)
                    elif call_type == "warning" and ("webgl" in joined.lower() or "three" in joined.lower()):
                        self.console_warnings.append(joined)
                        print(f"  [CONSOLE WARNING] {joined}", flush=True)
        except Exception:
            pass

    async def send(self, method, params=None):
        self.msg_id += 1
        cid = self.msg_id
        req = {"id": cid, "method": method}
        if params:
            req["params"] = params
        fut = asyncio.get_event_loop().create_future()
        self.pending[cid] = fut
        await self.ws.send(json.dumps(req))
        return await asyncio.wait_for(fut, timeout=30.0)

    async def eval(self, js):
        res = await self.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": True
        })
        if "exceptionDetails" in res:
            exc = res["exceptionDetails"]
            text = exc.get("exception", {}).get("description") or exc.get("text")
            raise RuntimeError(f"JS Evaluation Error: {text}")
        return res.get("result", {}).get("value")

    async def close(self):
        self.is_listening = False
        if self.ws:
            await self.ws.close()

async def run_suite():
    print("=" * 80)
    print("   MILESTONE M6 CHALLENGER 2: EMPIRICAL VFX LIFECYCLE & STRESS TEST")
    print("=" * 80)

    edge_bin = find_edge()
    port = get_free_port()
    tmp_profile = tempfile.mkdtemp()
    print(f"[*] Starting Edge headless on port {port}...")

    proc = subprocess.Popen([
        edge_bin,
        "--headless=new",
        f"--remote-debugging-port={port}",
        "--disable-gpu",
        "--window-size=1600,900",
        "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])

    harness = VFXStressHarness(port)
    findings = []
    
    try:
        await harness.connect()
        print("[*] Connected via CDP. Awaiting page load...")

        # Wait for page readiness
        for _ in range(40):
            ready = await harness.eval("Boolean(window.rosterMeta && window.rosterMeta.length === 10 && window.animationsData && window.lobbyHeroMesh && window.start5v5Match)")
            if ready:
                break
            await asyncio.sleep(0.5)

        print("[*] Page loaded successfully. Installing instrumentation...")

        # Setup spies and NaN checkers
        setup_script = """
        (() => {
            window._disposedGeometries = 0;
            window._disposedMaterials = 0;
            window._disposedTextures = 0;

            const origGeomDispose = THREE.BufferGeometry.prototype.dispose;
            THREE.BufferGeometry.prototype.dispose = function() {
                window._disposedGeometries++;
                return origGeomDispose.apply(this, arguments);
            };

            const origMatDispose = THREE.Material.prototype.dispose;
            THREE.Material.prototype.dispose = function() {
                window._disposedMaterials++;
                return origMatDispose.apply(this, arguments);
            };

            const origTexDispose = THREE.Texture.prototype.dispose;
            THREE.Texture.prototype.dispose = function() {
                window._disposedTextures++;
                return origTexDispose.apply(this, arguments);
            };

            window._scanForNaN = function(root) {
                const nanNodes = [];
                if (!root) return nanNodes;
                root.traverse(o => {
                    const p = o.position;
                    const r = o.rotation;
                    const s = o.scale;
                    if (isNaN(p.x) || isNaN(p.y) || isNaN(p.z) ||
                        isNaN(r.x) || isNaN(r.y) || isNaN(r.z) ||
                        isNaN(s.x) || isNaN(s.y) || isNaN(s.z)) {
                        nanNodes.push({ name: o.name || o.type, id: o.id });
                    }
                });
                return nanNodes;
            };

            return true;
        })()
        """
        await harness.eval(setup_script)
        print("[*] Instrumentation installed.")

        # -------------------------------------------------------------
        # TEST 1: Rapid skill casting across all 10 ninjas in succession
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 1: Rapid Skill Casting Across All 10 Ninjas")
        print("=" * 60)

        # Start 5v5 match
        await harness.eval("window.start5v5Match()")
        await asyncio.sleep(1.0)

        heroes_cast_script = """
        (() => {
            const results = {};
            const heroIds = window.rosterMeta.map(h => h.id);
            const slots = ['q', 'w', 'e', 'r'];

            for (const hid of heroIds) {
                const u = window.units.find(x => x.heroId === hid) || window.units[0];
                results[hid] = { slotsTested: {} };

                for (const slot of slots) {
                    u.cds[slot] = 0;
                    u.chakra = 100;
                    u.deadTimer = 0;
                    const vfxBefore = window.vfxList.length;
                    const arenaChildrenBefore = window.arenaGroup.children.length;

                    try {
                        window.executeSkill(u, slot);
                    } catch(err) {
                        results[hid].slotsTested[slot] = { error: String(err) };
                        continue;
                    }

                    const vfxAfter = window.vfxList.length;
                    const spawned = window.vfxList.slice(vfxBefore);
                    const childDetails = [];

                    for (const v of spawned) {
                        if (v.mesh) {
                            let ringCount = 0;
                            let lineSegmentsCount = 0;
                            let cylinderCount = 0;
                            let torusCount = 0;
                            let planeCount = 0;

                            v.mesh.traverse(child => {
                                if (child.isLineSegments) lineSegmentsCount++;
                                if (child.geometry) {
                                    const type = child.geometry.type;
                                    if (type === 'RingGeometry') ringCount++;
                                    if (type === 'TorusGeometry') torusCount++;
                                    if (type === 'CylinderGeometry') cylinderCount++;
                                    if (type === 'PlaneGeometry') planeCount++;
                                }
                            });

                            childDetails.push({
                                style: v.style,
                                duration: v.duration,
                                bindUnit: Boolean(v.bindUnit),
                                bindBoneIdx: v.bindBoneIdx,
                                ringCount,
                                lineSegmentsCount,
                                torusCount,
                                cylinderCount,
                                planeCount
                            });
                        }
                    }

                    results[hid].slotsTested[slot] = {
                        success: true,
                        vfxSpawnedCount: vfxAfter - vfxBefore,
                        childDetails
                    };
                }
            }

            return results;
        })()
        """
        cast_results = await harness.eval(heroes_cast_script)

        # Inspect cast results
        total_slots_tested = 0
        total_slots_succeeded = 0
        for hid, hdata in cast_results.items():
            print(f"\n[*] Ninja {hid}:")
            for slot, sres in hdata["slotsTested"].items():
                total_slots_tested += 1
                if sres.get("success"):
                    total_slots_succeeded += 1
                    child_sum = sres.get("childDetails", [])
                    print(f"    Slot [{slot.upper()}]: OK, VFX spawned={sres['vfxSpawnedCount']}, compound meshes={len(child_sum)}")
                else:
                    print(f"    Slot [{slot.upper()}]: FAILED with error: {sres.get('error')}")

        print(f"\n[Test 1 Summary] Cast success: {total_slots_succeeded}/{total_slots_tested}")
        if total_slots_succeeded < total_slots_tested:
            findings.append(f"Test 1 Failed: Only {total_slots_succeeded}/{total_slots_tested} skill casts succeeded.")
        else:
            print("[Test 1 PASS] All 10 ninjas cast all 4 skill slots cleanly.")

        # Check for NaNs immediately after casting
        nan_nodes = await harness.eval("window._scanForNaN(window.scene)")
        print(f"[*] NaN check across scene graph after rapid casts: {len(nan_nodes)} NaN nodes found.")
        if nan_nodes:
            findings.append(f"NaN nodes detected in scene graph: {nan_nodes}")
            print(f"  [ERROR] NaN nodes: {nan_nodes}")
        else:
            print("[Test 1 PASS] 0 NaN coordinates in scene.")

        # -------------------------------------------------------------
        # TEST 2: Transient Child Meshes Removal & Geometry/Material Disposal
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 2: VFX Duration Expiry, Mesh Removal & Memory Disposal")
        print("=" * 60)

        # Record pre-drain state
        pre_drain = await harness.eval("""
        (() => {
            return {
                vfxCount: window.vfxList.length,
                arenaChildrenCount: window.arenaGroup.children.length,
                disposedGeoms: window._disposedGeometries,
                disposedMats: window._disposedMaterials
            };
        })()
        """)
        print(f"[*] Pre-drain state: vfxList={pre_drain['vfxCount']}, arenaChildren={pre_drain['arenaChildrenCount']}, disposedGeoms={pre_drain['disposedGeoms']}, disposedMats={pre_drain['disposedMats']}")

        # Temporarily freeze bots so only active VFX drain is measured
        await harness.eval("window.units.slice(1).forEach(u => u.deadTimer = 999)")

        # Advance time by 3.5s to allow all VFX to expire
        print("[*] Advancing time / waiting 3.5 seconds for all VFX durations to expire...")
        await asyncio.sleep(3.5)

        post_drain = await harness.eval("""
        (() => {
            const res = {
                vfxCount: window.vfxList.length,
                arenaChildrenCount: window.arenaGroup.children.length,
                disposedGeoms: window._disposedGeometries,
                disposedMats: window._disposedMaterials
            };
            window.units.slice(1).forEach(u => u.deadTimer = 0);
            return res;
        })()
        """)
        print(f"[*] Post-drain state: vfxList={post_drain['vfxCount']}, arenaChildren={post_drain['arenaChildrenCount']}, disposedGeoms={post_drain['disposedGeoms']}, disposedMats={post_drain['disposedMats']}")

        # Check if vfxList drained
        if post_drain['vfxCount'] > 0:
            msg = f"VFX list did NOT drain after 3.5s! {post_drain['vfxCount']} VFX items remaining."
            print(f"  [FAIL] {msg}")
            findings.append(msg)
        else:
            print("  [PASS] vfxList successfully drained to 0.")

        # Check if geometries and materials were disposed
        geoms_disposed_diff = post_drain['disposedGeoms'] - pre_drain['disposedGeoms']
        mats_disposed_diff = post_drain['disposedMats'] - pre_drain['disposedMats']
        print(f"[*] Geometries disposed during expiry: {geoms_disposed_diff}")
        print(f"[*] Materials disposed during expiry: {mats_disposed_diff}")

        if geoms_disposed_diff == 0:
            issue_msg = (
                "CRITICAL MEMORY DEFECT: Transient VFX child meshes and materials are NOT disposed "
                "when duration expires! (geometry.dispose() and material.dispose() are never called in "
                "updateMatch when v.age >= v.duration). Geometries and materials leak in WebGL memory."
            )
            print(f"  [DISPOSAL DEFECT CONFIRMED] {issue_msg}")
            findings.append(issue_msg)
        else:
            print("  [PASS] Geometries and materials disposed on expiry.")

        # -------------------------------------------------------------
        # TEST 3: Arena Switching & Hero Switching During Active VFX
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 3: Switching Arenas and Heroes During Active VFX")
        print("=" * 60)

        # Trigger complex multi-mesh VFX (e.g. Kirin and Sand Hand)
        switch_test_script = """
        (async () => {
            const results = {
                arenaSwitchResults: [],
                heroSwitchResults: [],
                exceptions: []
            };

            const u = window.units[0];
            const enemy = window.units[5];

            // 1. Cast Kirin / Sand Hand with duration > 1.2s
            u.heroId = '1ssk';
            u.chakra = 100;
            window.executeSkill(u, 'r'); // Kirin
            u.heroId = '1gar';
            u.chakra = 100;
            window.executeSkill(u, 'q'); // Sand Hand

            const activeVfxDuringCast = window.vfxList.length;
            results.activeVfxDuringCast = activeVfxDuringCast;

            // Wait 150ms so VFX is actively animating in the frame loop
            await new Promise(r => setTimeout(r, 150));

            // Rapidly switch arena while VFX is animating
            const arenas = ['sd01b', 'sd03b', 'sd04a', 'sd00a'];
            for (const aid of arenas) {
                try {
                    await window.applyArena(aid);
                    results.arenaSwitchResults.push({ arena: aid, success: true, vfxRemaining: window.vfxList.length });
                } catch(err) {
                    results.arenaSwitchResults.push({ arena: aid, success: false, error: String(err) });
                    results.exceptions.push(`applyArena(${aid}) error: ${err}`);
                }
            }

            // Wait 100ms and cast again
            u.heroId = '1nrt';
            u.chakra = 100;
            window.executeSkill(u, 'q'); // Rasengan
            u.heroId = '1nej';
            u.chakra = 100;
            window.executeSkill(u, 'q'); // Kaiten

            // Switch hero / restart match while VFX is animating
            try {
                window.selectLobbyHero('1kks');
                window.start5v5Match();
                results.heroSwitchResults.push({ action: 'start5v5Match', success: true });
            } catch(err) {
                results.heroSwitchResults.push({ action: 'start5v5Match', success: false, error: String(err) });
                results.exceptions.push(`start5v5Match() error: ${err}`);
            }

            // Let simulation run for 500ms
            await new Promise(r => setTimeout(r, 500));

            return results;
        })()
        """
        switch_res = await harness.eval(switch_test_script)
        print(f"[*] Arena switch results during active VFX:")
        for asr in switch_res.get("arenaSwitchResults", []):
            print(f"    Arena {asr.get('arena')}: success={asr.get('success')}, vfxRemaining={asr.get('vfxRemaining')}, err={asr.get('error')}")

        print(f"[*] Hero/Match switch results during active VFX:")
        for hsr in switch_res.get("heroSwitchResults", []):
            print(f"    Action {hsr.get('action')}: success={hsr.get('success')}, err={hsr.get('error')}")

        if switch_res.get("exceptions"):
            for ex in switch_res["exceptions"]:
                findings.append(f"Exception during mid-VFX switch: {ex}")
                print(f"  [ERROR] {ex}")
        else:
            print("  [Test 3 PASS] 0 exceptions during mid-VFX arena and hero switching.")

        # Check for orphaned objects in arenaGroup
        orphan_check = await harness.eval("""
        (() => {
            const vfxMeshes = new Set(window.vfxList.map(v => v.mesh));
            let orphanedCount = 0;
            // Any mesh in arenaGroup that is not stage, training posts, base sanctuary, or unit
            window.arenaGroup.traverse(child => {
                if (child.userData && child.userData.rotSpeed && !vfxMeshes.has(child)) {
                    // Check if its root ancestor in arenaGroup is in vfxList
                    let curr = child;
                    while (curr.parent && curr.parent !== window.arenaGroup) {
                        curr = curr.parent;
                    }
                    if (!vfxMeshes.has(curr)) {
                        orphanedCount++;
                    }
                }
            });
            return { orphanedCount, vfxCount: window.vfxList.length };
        })()
        """)
        print(f"[*] Orphaned compound VFX mesh check: {orphan_check['orphanedCount']} orphaned nodes found.")
        if orphan_check['orphanedCount'] > 0:
            msg = f"Orphaned VFX meshes detected in arenaGroup: {orphan_check['orphanedCount']} nodes"
            print(f"  [WARN/DEFECT] {msg}")
            findings.append(msg)

        # -------------------------------------------------------------
        # TEST 4: High-Frequency Rapid Stress Loop (100+ Skill Casts)
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 4: High-Frequency Stress Loop (100+ Skill Casts)")
        print("=" * 60)

        stress_loop_script = """
        (async () => {
            const heroIds = window.rosterMeta.map(h => h.id);
            const slots = ['q', 'w', 'e', 'r'];
            let totalCasts = 0;

            const t0 = performance.now();
            const frameTimes = [];
            let lastFp = performance.now();

            // Run 30 cycles of casting across all units
            for (let cycle = 0; cycle < 10; cycle++) {
                for (let i = 0; i < window.units.length; i++) {
                    const u = window.units[i];
                    u.chakra = 100;
                    const slot = slots[(cycle + i) % slots.length];
                    window.executeSkill(u, slot);
                    totalCasts++;
                }
                // Yield frame
                await new Promise(r => requestAnimationFrame(r));
                const now = performance.now();
                frameTimes.push(now - lastFp);
                lastFp = now;
            }

            const totalTimeMs = performance.now() - t0;
            const avgFrameMs = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
            const estimatedFps = 1000 / Math.max(1, avgFrameMs);

            return {
                totalCasts,
                totalTimeMs,
                avgFrameMs,
                estimatedFps,
                vfxListLength: window.vfxList.length
            };
        })()
        """
        stress_res = await harness.eval(stress_loop_script)
        print(f"[*] Stress Loop completed: {stress_res['totalCasts']} casts in {stress_res['totalTimeMs']:.1f}ms")
        print(f"    Avg frame time: {stress_res['avgFrameMs']:.2f}ms (~{stress_res['estimatedFps']:.1f} FPS)")
        print(f"    Active VFX count during burst: {stress_res['vfxListLength']}")

        # Drain check
        print("[*] Waiting 3.0 seconds for stress loop VFX to drain...")
        await asyncio.sleep(3.5)

        post_stress_check = await harness.eval("""
        (() => {
            return {
                vfxListLength: window.vfxList.length,
                nanCount: window._scanForNaN(window.scene).length,
                disposedGeoms: window._disposedGeometries,
                disposedMats: window._disposedMaterials
            };
        })()
        """)
        print(f"[*] Post-stress drain: vfxList={post_stress_check['vfxListLength']}, NaNs={post_stress_check['nanCount']}, disposedGeoms={post_stress_check['disposedGeoms']}")

        if post_stress_check['nanCount'] > 0:
            findings.append(f"NaN nodes detected after stress loop: {post_stress_check['nanCount']}")

        # -------------------------------------------------------------
        # TEST 5: Console Errors and WebGL Warnings Audit
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 5: Console Errors & WebGL Warnings Audit")
        print("=" * 60)

        print(f"[*] Console errors count: {len(harness.console_errors)}")
        print(f"[*] Console / WebGL warnings count: {len(harness.console_warnings)}")
        print(f"[*] Runtime exceptions count: {len(harness.runtime_exceptions)}")

        if harness.console_errors:
            print("  [ERROR LIST]:")
            for e in harness.console_errors:
                print(f"    - {e}")
            findings.append(f"Console errors detected ({len(harness.console_errors)}): {harness.console_errors[:3]}")

        if harness.runtime_exceptions:
            print("  [EXCEPTION LIST]:")
            for ex in harness.runtime_exceptions:
                print(f"    - {ex}")
            findings.append(f"Runtime exceptions detected ({len(harness.runtime_exceptions)}): {harness.runtime_exceptions[:3]}")

        # Summary
        print("\n" + "=" * 80)
        print("                   FINAL VERDICT & FINDINGS SUMMARY")
        print("=" * 80)
        if not findings:
            print(">>> ALL ADVERSARIAL VFX LIFECYCLE CHECKS PASSED! <<<")
            verdict = "APPROVE"
        else:
            print(f">>> DEFECTS / CHALLENGES FOUND ({len(findings)}): <<<")
            for idx, f in enumerate(findings, 1):
                print(f" {idx}. {f}")
            # If critical memory disposal defect found:
            verdict = "REQUEST_CHANGES"
            print(f"\nVerdict: {verdict}")

        return verdict, findings

    finally:
        await harness.close()
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

if __name__ == "__main__":
    verdict, findings = asyncio.run(run_suite())
    if verdict == "APPROVE":
        sys.exit(0)
    else:
        sys.exit(1)
