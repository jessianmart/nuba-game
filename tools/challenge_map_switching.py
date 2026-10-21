"""
Adversarial Stress Test Suite: Map Switching & Runtime Memory (Milestone M5 Challenge 2)

Empirically stress-tests:
1. Rapid stage cycling: sd01b -> sd03b -> sd04a -> sd00a (multiple sequential loops).
2. Proper geometry & material disposal (geometry.dispose(), material.dispose()).
3. WebGL context stability (zero webglcontextlost events, bounded scene memory).
4. Concurrent / unawaited fire-and-forget switching race conditions.
5. Stage switching during active 5v5 MOBA match with live AI bots & combat.
6. Execution of Taijutsu, Q, E, Space, R combat actions across all 4 stages.
7. Verification of 0 console errors, 0 runtime exceptions, 0 HTTP 404s.
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

class AdversarialCDPHarness:
    def __init__(self, port):
        self.port = port
        self.ws = None
        self.msg_id = 0
        self.pending = {}
        self.console_errors = []
        self.runtime_exceptions = []
        self.network_404s = []
        self.all_network_errors = []
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
        await self.send("Network.enable")

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
                    if entry.get("level") == "error":
                        self.console_errors.append(entry.get("text", ""))
                        print(f"  [LOG ERROR] {entry.get('text')}", flush=True)
                elif method == "Runtime.consoleAPICalled":
                    if params.get("type") == "error":
                        args = [str(a.get("value", a.get("description", ""))) for a in params.get("args", [])]
                        err_str = " ".join(args)
                        self.console_errors.append(err_str)
                        print(f"  [CONSOLE ERROR] {err_str}", flush=True)
                elif method == "Network.responseReceived":
                    resp = params.get("response", {})
                    url = resp.get("url", "")
                    status = resp.get("status", 200)
                    if status == 404:
                        self.network_404s.append(f"404: {url}")
                        print(f"  [NETWORK 404] {url}", flush=True)
                    elif status >= 400:
                        self.all_network_errors.append(f"{status}: {url}")
                        print(f"  [NETWORK ERROR {status}] {url}", flush=True)
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

async def run_stress_test():
    print("=" * 78)
    print("M5 CHALLENGE 2: EMPIRICAL MAP SWITCHING & MEMORY STRESS HARNESS")
    print("=" * 78)

    edge_bin = find_edge()
    port = get_free_port()
    tmp_profile = tempfile.mkdtemp()
    print(f"[*] Launching Headless Edge on port {port} with profile {tmp_profile}")

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

    await asyncio.sleep(2.5)
    cdp = AdversarialCDPHarness(port)
    results = {}

    try:
        await cdp.connect()
        print("[+] CDP connected and event listeners active.")

        # Wait for page readiness
        print("[*] Waiting for initial page readiness...")
        for _ in range(40):
            ready = await cdp.eval("Boolean(window.rosterMeta && window.applyArena && window.start5v5Match)")
            if ready:
                break
            await asyncio.sleep(0.4)

        if not ready:
            raise RuntimeError("Engine failed to initialize within timeout.")
        print("[+] Engine initialized successfully.")

        # ---------------------------------------------------------------------
        # INSTRUMENTATION
        # ---------------------------------------------------------------------
        print("[*] Injecting memory, disposal, and WebGL context instrumentation...")
        await cdp.eval("""
        (() => {
          window.__stress = {
            geomDisposeCalls: 0,
            matDisposeCalls: 0,
            texDisposeCalls: 0,
            contextLostCount: 0,
            contextRestoredCount: 0
          };

          const origGeomDispose = THREE.BufferGeometry.prototype.dispose;
          THREE.BufferGeometry.prototype.dispose = function() {
            window.__stress.geomDisposeCalls++;
            return origGeomDispose.apply(this, arguments);
          };

          const origMatDispose = THREE.Material.prototype.dispose;
          THREE.Material.prototype.dispose = function() {
            window.__stress.matDisposeCalls++;
            return origMatDispose.apply(this, arguments);
          };

          const origTexDispose = THREE.Texture.prototype.dispose;
          THREE.Texture.prototype.dispose = function() {
            window.__stress.texDisposeCalls++;
            return origTexDispose.apply(this, arguments);
          };

          const cvs = document.getElementById('game-canvas');
          if (cvs) {
            cvs.addEventListener('webglcontextlost', (e) => {
              window.__stress.contextLostCount++;
              console.warn('[STRESS] WebGL Context Lost!');
            });
            cvs.addEventListener('webglcontextrestored', (e) => {
              window.__stress.contextRestoredCount++;
              console.info('[STRESS] WebGL Context Restored.');
            });
          }
        })();
        """)

        await asyncio.sleep(0.3)
        print("[+] Instrumentation attached successfully.")

        # Helper to query scene memory metrics
        async def get_scene_metrics():
            return await cdp.eval("""
            (() => {
              const geos = new Set();
              const mats = new Set();
              let meshCount = 0;
              window.scene.traverse(o => {
                if (o.isMesh) meshCount++;
                if (o.geometry) geos.add(o.geometry.id);
                if (o.material) {
                  const arr = Array.isArray(o.material) ? o.material : [o.material];
                  arr.forEach(m => { if (m) mats.add(m.id); });
                }
              });
              let arenaMeshCount = 0;
              window.arenaGroup.traverse(o => { if (o.isMesh) arenaMeshCount++; });
              const cvs = document.getElementById('game-canvas');
              const gl = cvs ? (cvs.getContext('webgl2') || cvs.getContext('webgl')) : null;
              return {
                sceneMeshes: meshCount,
                arenaMeshes: arenaMeshCount,
                uniqueGeometries: geos.size,
                uniqueMaterials: mats.size,
                contextLost: gl ? gl.isContextLost() : false
              };
            })()
            """)

        # ---------------------------------------------------------------------
        # TEST 1: Rapid Sequential Stage Switching in Lobby
        # ---------------------------------------------------------------------
        print("\n" + "-" * 60)
        print("TEST 1: Rapid Sequential Stage Switching (3 full cycles = 12 switches)")
        print("-" * 60)

        stages = ["sd01b", "sd03b", "sd04a", "sd00a"]
        t1_details = []
        cycle_count = 3
        switches_done = 0

        for cycle in range(cycle_count):
            for stage_id in stages:
                pre_disposes = await cdp.eval("window.__stress.geomDisposeCalls")
                pre_mat_disposes = await cdp.eval("window.__stress.matDisposeCalls")

                switch_start = time.time()
                await cdp.eval(f"window.applyArena('{stage_id}')")
                duration = time.time() - switch_start

                await asyncio.sleep(0.05)

                post_disposes = await cdp.eval("window.__stress.geomDisposeCalls")
                post_mat_disposes = await cdp.eval("window.__stress.matDisposeCalls")
                cur_arena_id = await cdp.eval("window.selectedArenaId")
                arena_obj_id = await cdp.eval("window.ARENA.id")
                metrics = await get_scene_metrics()

                switches_done += 1
                disp_delta = post_disposes - pre_disposes
                mat_disp_delta = post_mat_disposes - pre_mat_disposes

                log_entry = {
                    "switch": switches_done,
                    "target": stage_id,
                    "current": cur_arena_id,
                    "arena_id": arena_obj_id,
                    "duration_ms": round(duration * 1000, 1),
                    "geom_disposed_delta": disp_delta,
                    "mat_disposed_delta": mat_disp_delta,
                    "arena_meshes": metrics["arenaMeshes"],
                    "scene_geometries": metrics["uniqueGeometries"],
                    "context_lost": metrics["contextLost"]
                }
                t1_details.append(log_entry)
                print(f"  Switch #{switches_done:02d} -> {stage_id} in {log_entry['duration_ms']}ms | "
                      f"GeomDisposed: +{disp_delta} | MatDisposed: +{mat_disp_delta} | "
                      f"ArenaMeshes: {metrics['arenaMeshes']} | SceneGeos: {metrics['uniqueGeometries']}")

        # Verification of Test 1:
        # Every switch (after switch 1) MUST call geometry.dispose() on the previous arena
        nonzero_disposals = [e for e in t1_details[1:] if e["geom_disposed_delta"] > 0]
        t1_all_disposed = len(nonzero_disposals) == len(t1_details) - 1
        # Without disposal, scene geometries would accumulate > 1500; bounded is < 500
        t1_memory_bounded = t1_details[-1]["scene_geometries"] < 500
        t1_no_context_loss = all(not e["context_lost"] for e in t1_details)

        results["test1_sequential_switching"] = {
            "pass": t1_all_disposed and t1_memory_bounded and t1_no_context_loss,
            "switches_executed": switches_done,
            "all_switches_disposed_prior_geometry": t1_all_disposed,
            "memory_bounded": t1_memory_bounded,
            "final_scene_geometries": t1_details[-1]["scene_geometries"],
            "total_geom_disposes": await cdp.eval("window.__stress.geomDisposeCalls"),
            "total_mat_disposes": await cdp.eval("window.__stress.matDisposeCalls"),
            "context_stable": t1_no_context_loss
        }
        print(f"[+] TEST 1 RESULT: {'PASS' if results['test1_sequential_switching']['pass'] else 'FAIL'} "
              f"(Disposal verified on {len(nonzero_disposals)}/{len(t1_details)-1} switches)")

        # ---------------------------------------------------------------------
        # TEST 2: Concurrent / Unawaited Rapid Fire-and-Forget Switching
        # ---------------------------------------------------------------------
        print("\n" + "-" * 60)
        print("TEST 2: Adversarial Concurrent Fire-and-Forget Switching")
        print("-" * 60)

        # Trigger 4 rapid unawaited calls back-to-back with zero delay
        t2_res = await cdp.eval("""
        (async () => {
          const promises = [
            window.applyArena('sd01b'),
            window.applyArena('sd03b'),
            window.applyArena('sd04a'),
            window.applyArena('sd00a')
          ];
          await Promise.all(promises);
          return {
            selectedArenaId: window.selectedArenaId,
            arenaId: window.ARENA.id,
            arenaRadius: window.ARENA.radius
          };
        })()
        """)
        await asyncio.sleep(0.5)

        t2_metrics = await get_scene_metrics()

        # Check for duplicate extracted stages
        t2_stage_groups = await cdp.eval("""
        (() => {
          let stageGroupCount = 0;
          window.arenaGroup.children.forEach(c => {
            if (c.children && c.children.length > 30 && c.children[0] && c.children[0].userData && c.children[0].userData.texture) {
              stageGroupCount++;
            }
          });
          return stageGroupCount;
        })()
        """)

        t2_pass = (
            t2_stage_groups == 1 and
            t2_res["selectedArenaId"] == t2_res["arenaId"] and
            not t2_metrics["contextLost"]
        )

        results["test2_concurrent_switching"] = {
            "pass": t2_pass,
            "final_selected": t2_res["selectedArenaId"],
            "arena_id": t2_res["arenaId"],
            "stage_group_count": t2_stage_groups,
            "arena_meshes": t2_metrics["arenaMeshes"],
            "scene_geometries": t2_metrics["uniqueGeometries"],
            "context_stable": not t2_metrics["contextLost"]
        }
        print(f"[+] TEST 2 RESULT: {'PASS' if t2_pass else 'FAIL'} "
              f"(Stage groups: {t2_stage_groups}, Meshes: {t2_metrics['arenaMeshes']}, "
              f"Selected: {t2_res['selectedArenaId']}, Arena: {t2_res['arenaId']})")

        # ---------------------------------------------------------------------
        # TEST 3: Switching During Active Match & Combat Validation on Each Stage
        # ---------------------------------------------------------------------
        print("\n" + "-" * 60)
        print("TEST 3: Arena Switching During 5v5 Match + Combat Execution on All Stages")
        print("-" * 60)

        # Start match
        await cdp.eval("window.start5v5Match()")
        await asyncio.sleep(1.0)
        match_active = await cdp.eval("window.matchActive")
        print(f"[*] 5v5 Match active: {match_active}")

        t3_stages_results = {}
        combat_stages = [
            ("sd01b", "Torre Preliminar (Exame Chunin)", 62, "box"),
            ("sd03b", "Coliseu (Exame Chunin)", 78, "circle"),
            ("sd04a", "Estadio Selvagem (Plato)", 75, "box"),
            ("sd00a", "Campo de Treinamento (Konoha)", 88, "box")
        ]

        for s_id, s_name, s_radius, s_shape in combat_stages:
            print(f"\n  [*] Switching live match to {s_id} ({s_name})...")
            await cdp.eval(f"window.applyArena('{s_id}')")
            await asyncio.sleep(0.4)

            # 1. Assert arena parameters match catalog
            stg_info = await cdp.eval("""
            (() => {
              const u = window.units.find(x => x.isPlayer);
              const bB = window.basePos('blue');
              const bR = window.basePos('red');
              return {
                id: window.ARENA.id,
                radius: window.ARENA.radius,
                shape: window.ARENA.shape,
                playerX: u ? u.x : 0,
                playerZ: u ? u.z : 0,
                cameraY: window.camera ? window.camera.position.y : 0,
                cameraMaxY: window.ARENA.cameraMaxY,
                blueBase: bB,
                redBase: bR,
                unitCount: window.units.length
              };
            })()
            """)

            # 2. Assert unit positions are within bounds and not NaN
            bounds_ok = await cdp.eval("""
            (() => {
              for (const u of window.units) {
                if (isNaN(u.x) || isNaN(u.z) || isNaN(u.hp)) return false;
                if (window.ARENA.shape === 'circle') {
                  const dist = Math.hypot(u.x, u.z);
                  if (dist > window.ARENA.playerLimit + 5) return false;
                } else if (window.ARENA.bounds) {
                  const b = window.ARENA.bounds;
                  if (u.x < b.minX - 5 || u.x > b.maxX + 5 || u.z < b.minZ - 5 || u.z > b.maxZ + 5) return false;
                }
              }
              return true;
            })()
            """)

            # 3. Assert camera ceiling clamp for sd01b and circular clamp for sd03b in thirdperson mode
            cam_clamp_ok = await cdp.eval("""
            (() => {
              const origMode = window.cameraMode;
              window.cameraMode = 'thirdperson';
              const p = window.units.find(u => u.isPlayer);
              const camY = window.camera.position.y;
              let ok = true;
              if (window.ARENA.id === 'sd01b') {
                ok = camY <= 26.5;
              } else if (window.ARENA.shape === 'circle') {
                const hyp = Math.hypot(window.camera.position.x, window.camera.position.z);
                ok = hyp <= (window.ARENA.cameraLimit || 82) + 5;
              }
              window.cameraMode = origMode;
              return ok;
            })()
            """)

            # 4. Fire combat actions on this stage
            # - Taijutsu Combo (3 hits)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) {
                p.chakra = 100;
                window.executeSkill(p, 'basic');
              }
            })()
            """)
            await asyncio.sleep(0.15)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) window.executeSkill(p, 'basic');
            })()
            """)
            await asyncio.sleep(0.15)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) window.executeSkill(p, 'basic');
            })()
            """)
            await asyncio.sleep(0.2)

            # - Primary Ninjutsu (Q)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) {
                p.chakra = 100;
                p.cooldownQ = 0;
                window.executeSkill(p, 'q');
              }
            })()
            """)
            await asyncio.sleep(0.2)

            # - Secondary Ninjutsu (E -> slot w)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) {
                p.chakra = 100;
                p.cooldownW = 0;
                window.executeSkill(p, 'w');
              }
            })()
            """)
            await asyncio.sleep(0.2)

            # - Kawarimi (Space -> slot e)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) {
                p.chakra = 100;
                p.cooldownE = 0;
                window.executeSkill(p, 'e');
              }
            })()
            """)
            await asyncio.sleep(0.2)

            # - Ultimate Ougi (R -> slot r)
            await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              if (p) {
                p.chakra = 100;
                p.cooldownR = 0;
                window.executeSkill(p, 'r');
              }
            })()
            """)
            await asyncio.sleep(0.3)

            # Check combat state
            combat_state = await cdp.eval("""
            (() => {
              const p = window.units.find(u => u.isPlayer);
              return {
                playerAlive: p ? (p.deadTimer <= 0) : false,
                playerHp: p ? p.hp : 0,
                playerState: p ? p.state : null,
                projectilesActive: window.projectiles ? window.projectiles.length : 0,
                vfxActive: window.vfxList ? window.vfxList.length : 0,
                isAwakened: p ? (p.awakenedTimer > 0) : false
              };
            })()
            """)

            stage_pass = (
                stg_info["id"] == s_id and
                stg_info["radius"] == s_radius and
                stg_info["shape"] == s_shape and
                stg_info["unitCount"] == 10 and
                bounds_ok and
                cam_clamp_ok and
                bool(combat_state and combat_state.get("playerAlive"))
            )

            t3_stages_results[s_id] = {
                "pass": stage_pass,
                "info": stg_info,
                "bounds_ok": bounds_ok,
                "cam_clamp_ok": cam_clamp_ok,
                "combat": combat_state
            }
            print(f"  [+] Stage {s_id}: {'PASS' if stage_pass else 'FAIL'} | "
                  f"Units: {stg_info['unitCount']} | Bounds: {bounds_ok} | "
                  f"CamClamp: {cam_clamp_ok} | Awakened: {combat_state.get('isAwakened')} | "
                  f"VFX: {combat_state.get('vfxActive')}")

        t3_all_pass = all(v["pass"] for v in t3_stages_results.values())
        results["test3_match_combat"] = {
            "pass": t3_all_pass,
            "stages": t3_stages_results
        }
        print(f"\n[+] TEST 3 RESULT: {'PASS' if t3_all_pass else 'FAIL'}")

        # ---------------------------------------------------------------------
        # TEST 4: High-Frequency 20-Switch Memory Leak & WebGL Context Stress
        # ---------------------------------------------------------------------
        print("\n" + "-" * 60)
        print("TEST 4: High-Frequency 20-Switch Memory Leak & Context Loss Stress")
        print("-" * 60)

        initial_metrics = await get_scene_metrics()
        initial_disposes = await cdp.eval("window.__stress.geomDisposeCalls")

        stress_stages = ["sd01b", "sd03b", "sd04a", "sd00a"] * 5  # 20 switches
        stress_t0 = time.time()

        for idx, sid in enumerate(stress_stages):
            await cdp.eval(f"window.applyArena('{sid}')")
            await asyncio.sleep(0.04)

        stress_duration = time.time() - stress_t0
        await asyncio.sleep(0.5)

        final_metrics = await get_scene_metrics()
        final_disposes = await cdp.eval("window.__stress.geomDisposeCalls")
        context_losses = await cdp.eval("window.__stress.contextLostCount")
        webgl_context_active = await cdp.eval("""
        (() => {
          const cvs = document.getElementById('game-canvas');
          const gl = cvs.getContext('webgl2') || cvs.getContext('webgl');
          return gl ? !gl.isContextLost() : false;
        })()
        """)

        added_geos = final_metrics["uniqueGeometries"] - initial_metrics["uniqueGeometries"]
        disposes_during_stress = final_disposes - initial_disposes

        print(f"  Switches completed: 20 in {stress_duration:.2f}s ({(stress_duration/20)*1000:.1f}ms/switch)")
        print(f"  Geometry disposals during stress: {disposes_during_stress}")
        print(f"  Scene Geometries: {initial_metrics['uniqueGeometries']} -> {final_metrics['uniqueGeometries']} (delta: {added_geos})")
        print(f"  Scene Materials: {initial_metrics['uniqueMaterials']} -> {final_metrics['uniqueMaterials']}")
        print(f"  Context losses detected: {context_losses}")
        print(f"  WebGL context active: {webgl_context_active}")

        # Memory leak condition:
        # If geometries were not disposed, 20 switches would add > 2,000 geometries.
        # With disposal, the net increase across 20 cycles should be near 0 (delta < 50).
        memory_stable = added_geos < 50
        context_stable = (context_losses == 0) and webgl_context_active

        results["test4_memory_leak_stress"] = {
            "pass": memory_stable and context_stable and disposes_during_stress > 1000,
            "switches": 20,
            "duration_s": round(stress_duration, 2),
            "initial_geometries": initial_metrics["uniqueGeometries"],
            "final_geometries": final_metrics["uniqueGeometries"],
            "delta_geometries": added_geos,
            "disposals_count": disposes_during_stress,
            "context_losses": context_losses,
            "context_active": webgl_context_active,
            "memory_stable": memory_stable
        }
        print(f"[+] TEST 4 RESULT: {'PASS' if results['test4_memory_leak_stress']['pass'] else 'FAIL'}")

        # ---------------------------------------------------------------------
        # TEST 5: Console Errors, Runtime Exceptions & 404 Auditing
        # ---------------------------------------------------------------------
        print("\n" + "-" * 60)
        print("TEST 5: Console Errors, Runtime Exceptions & 404 Auditing")
        print("-" * 60)

        print(f"  Total Console Errors: {len(cdp.console_errors)}")
        print(f"  Total Runtime Exceptions: {len(cdp.runtime_exceptions)}")
        print(f"  Total Network 404s: {len(cdp.network_404s)}")
        print(f"  Total Network >=400 Errors: {len(cdp.all_network_errors)}")

        for err in cdp.console_errors:
            print(f"    [ERR] {err}")
        for exc in cdp.runtime_exceptions:
            print(f"    [EXC] {exc}")
        for n404 in cdp.network_404s:
            print(f"    [404] {n404}")

        t5_pass = (
            len(cdp.console_errors) == 0 and
            len(cdp.runtime_exceptions) == 0 and
            len(cdp.network_404s) == 0
        )
        results["test5_zero_errors_and_404s"] = {
            "pass": t5_pass,
            "console_errors": cdp.console_errors,
            "runtime_exceptions": cdp.runtime_exceptions,
            "network_404s": cdp.network_404s
        }
        print(f"[+] TEST 5 RESULT: {'PASS' if t5_pass else 'FAIL'}")

        # ---------------------------------------------------------------------
        # OVERALL VERDICT
        # ---------------------------------------------------------------------
        all_passed = all(r.get("pass", False) for r in results.values())
        print("\n" + "=" * 78)
        print(f"OVERALL STRESS TEST VERDICT: {'APPROVE' if all_passed else 'REQUEST_CHANGES'}")
        print("=" * 78)

        results["overall_verdict"] = "APPROVE" if all_passed else "REQUEST_CHANGES"

    finally:
        await cdp.close()
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

    # Save results to JSON file for verification
    output_path = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\.agents\teamwork\teamwork_preview_challenger_m5_2\stress_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Detailed results written to {output_path}")

    return all_passed

if __name__ == "__main__":
    success = asyncio.run(run_stress_test())
    sys.exit(0 if success else 1)
