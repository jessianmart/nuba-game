"""
Milestone 1 (HUD) Empirical CDP Stress Testing Suite
Challenger: teamwork_preview_challenger_m1_2

Stress tests:
1. Action slot cooldown sweeps across all slots (atk, q, w, e, r):
   - Continuous transition from 100% to 0% as cooldown ticks down in real game loop.
   - Monotonic decrease of parsed conic-gradient percentage across time samples.
   - Proper reset to 'none' / display 'none' on completion.
   - Simultaneous all-slot cooldown stress.
2. Simulated click events on .moba-ability-btn elements:
   - CDP synthetic mouse events (Input.dispatchMouseEvent) at center coords of each button.
   - Verification of skill firing (atk, q, w, e, r, c): state change, chakra consumption, cooldown trigger.
   - Edge cases: click during cooldown, click with 0 chakra, click while dead (safe no-op, no errors).
3. Circular avatar geometric stability:
   - Aspect ratio exactly 1:1 and border-radius 50% under:
     * Standard viewports (1280x720, 800x600, 1920x1080, 640x480, 1024x1366).
     * Extreme container stress (flex compression, long text, sibling crowding).
4. Continuous console error & exception auditing throughout all operations.
"""

import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys
import os
import tempfile

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

async def run_stress_tests():
    tabs = None
    for _ in range(15):
        try:
            tabs_data = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5).read()
            tabs = json.loads(tabs_data)
            if tabs:
                break
        except Exception:
            time.sleep(0.5)

    if not tabs:
        print("ERROR: Could not connect to remote debugging port 9222!")
        return False, ["Could not connect to Edge 9222"]

    target_tab = None
    for t in tabs:
        if "localhost:8080" in t.get("url", ""):
            target_tab = t
            break

    if not target_tab:
        print("ERROR: Target tab not found! Available:", [t.get("url") for t in tabs])
        return False, ["Target tab not found"]

    ws_url = target_tab["webSocketDebuggerUrl"]
    print(f"Connecting to CDP at {ws_url}...")

    errors = []
    msg_id = 0

    async with websockets.connect(ws_url, max_size=25_000_000) as ws:
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
                    print(f"  [PAGE EXCEPTION] {text}")
                    errors.append(f"EXCEPTION: {text}")
                elif m == "Log.entryAdded":
                    entry = data["params"]["entry"]
                    if entry.get("level") == "error":
                        print(f"  [LOG ERROR] {json.dumps(entry)}")
                        errors.append(f"LOG: {entry.get('text')}")
                elif m == "Runtime.consoleAPICalled":
                    call_type = data["params"]["type"]
                    args = [a.get("value", a.get("description", "")) for a in data["params"]["args"]]
                    if call_type == "error":
                        msg = " ".join(str(x) for x in args)
                        print(f"  [CONSOLE ERROR] {msg}")
                        errors.append(f"CONSOLE: {msg}")

        await call_cdp("Runtime.enable")
        await call_cdp("Page.enable")
        await call_cdp("DOM.enable")

        print("Waiting for page load and engine initialization...")
        for _ in range(40):
            fn_check = await call_cdp("Runtime.evaluate", {
                "expression": "Boolean(window.rosterMeta && window.rosterMeta.length === 10 && typeof window.start5v5Match === 'function')",
                "returnByValue": True
            })
            if fn_check.get("result", {}).get("value") is True:
                break
            await asyncio.sleep(0.2)

        print("\n--- Initializing 5v5 Match for HUD Stress Testing ---")
        start_eval = """
        (async () => {
            if (!window.matchActive) {
                await window.start5v5Match();
            }
            for (let i = 0; i < 40; i++) {
                if (window.units && window.units.length === 10 && window.units.find(u => u.isPlayer)) break;
                await new Promise(r => setTimeout(r, 100));
            }
            const p = window.units ? window.units.find(u => u.isPlayer) : null;
            return {
                matchActive: window.matchActive,
                unitsCount: window.units ? window.units.length : 0,
                playerName: p ? p.name : null,
                playerKit: p && p.kit ? Object.keys(p.kit) : []
            };
        })()
        """
        match_init = await call_cdp("Runtime.evaluate", {"expression": start_eval, "awaitPromise": True, "returnByValue": True})
        print("RAW match_init:", match_init)
        init_val = match_init.get("result", {}).get("value", {})
        print("Match Initialization:", json.dumps(init_val, indent=2))
        assert init_val.get("matchActive") is True, f"Match failed to start! raw: {match_init}"
        assert init_val.get("unitsCount") == 10, f"Expected 10 units, got {init_val.get('unitsCount')}"

        await asyncio.sleep(1.0)

        results = {}

        # =========================================================================
        # TEST 1: COOLDOWN SWEEP CONTINUITY & MONOTONICITY ACROSS ALL SLOTS
        # =========================================================================
        print("\n=======================================================")
        print("TEST 1: STRESS-TESTING COOLDOWN SWEEPS ACROSS ALL SLOTS")
        print("=======================================================")

        # Helper to extract conic-gradient percentage
        sample_sweep_eval = """
        (() => {
            const slots = ['atk', 'q', 'w', 'e', 'r'];
            const res = {};
            const p = window.units.find(u => u.isPlayer);
            for (const s of slots) {
                const cdEl = document.getElementById(`cd-${s}`);
                const rem = p ? p.cds[s] : 0;
                const maxCd = (p && p.kit && p.kit[s] && p.kit[s].cd) ? p.kit[s].cd : 1;
                const bg = cdEl ? cdEl.style.background : '';
                const display = cdEl ? cdEl.style.display : '';
                const text = cdEl ? cdEl.textContent : '';
                let pct = null;
                const m = bg.match(/([0-9.]+)%/);
                if (m) pct = parseFloat(m[1]);
                res[s] = { rem, maxCd, pct, bg, display, text };
            }
            return res;
        })()
        """

        # 1A: Sequentially test each slot (atk, q, w, e, r)
        slot_sweep_results = {}
        slots_to_test = ['atk', 'q', 'w', 'e', 'r']

        for slot in slots_to_test:
            print(f"\n[Test 1.1] Testing slot '{slot}' Cooldown Sweep Continuity...")
            # Trigger cooldown for this slot
            sweep_eval = f"""
            (async () => {{
                const p = window.units.find(u => u.isPlayer);
                const cd = p.kit['{slot}'].cd || 1.0;
                p.cds['{slot}'] = cd;
                const samples = [];
                for (let i = 0; i < 8; i++) {{
                    await new Promise(r => requestAnimationFrame(r));
                    const cdEl = document.getElementById('cd-{slot}');
                    const rem = p.cds['{slot}'];
                    const maxCd = (p.kit && p.kit['{slot}'] && p.kit['{slot}'].cd) ? p.kit['{slot}'].cd : 1;
                    const bg = cdEl ? cdEl.style.background : '';
                    const display = cdEl ? cdEl.style.display : '';
                    const text = cdEl ? cdEl.textContent : '';
                    let pct = null;
                    const m = bg.match(/([0-9.]+)%/);
                    if (m) pct = parseFloat(m[1]);
                    samples.push({{ rem, maxCd, pct, bg, display, text }});
                }}
                return samples;
            }})()
            """
            sweep_res = await call_cdp("Runtime.evaluate", {"expression": sweep_eval, "awaitPromise": True, "returnByValue": True})
            samples = sweep_res.get("result", {}).get("value", [])
            pcts = [s["pct"] for s in samples if s.get("pct") is not None]
            print(f"  Slot '{slot}' Initial Samples PCTs: {pcts}")
            assert len(pcts) >= 4, f"Slot {slot} failed to generate conic-gradient percentage samples: {samples}"
            # Check monotonic decrease
            is_monotonic = all(pcts[i] >= pcts[i+1] - 0.1 for i in range(len(pcts)-1))
            assert is_monotonic, f"Slot {slot} cooldown percentage is not monotonically decreasing: {pcts}"

            # Now test transition down to completion (< 0.05s and 0s)
            complete_eval = f"""
            (() => {{
                const p = window.units.find(u => u.isPlayer);
                p.cds['{slot}'] = 0.08;
                return p.cds['{slot}'];
            }})()
            """
            await call_cdp("Runtime.evaluate", {"expression": complete_eval, "returnByValue": True})
            await asyncio.sleep(0.12)

            res_done = await call_cdp("Runtime.evaluate", {"expression": sample_sweep_eval, "returnByValue": True})
            final_data = res_done.get("result", {}).get("value", {}).get(slot, {})
            print(f"  Slot '{slot}' Post-Cooldown State: display='{final_data['display']}', bg='{final_data['bg']}', text='{final_data['text']}'")
            assert final_data["display"] in ["none", ""], f"Slot {slot} display should be 'none' when finished, got {final_data['display']}"
            assert final_data["bg"] in ["none", ""], f"Slot {slot} background should be cleared, got {final_data['bg']}"
            assert final_data["text"] == "", f"Slot {slot} text should be empty when finished, got {final_data['text']}"

            slot_sweep_results[slot] = {
                "monotonically_decreasing": is_monotonic,
                "conic_gradient_active": True,
                "cleanly_cleared_on_zero": True,
                "sample_pcts": pcts
            }

        # 1B: Simultaneous Multi-Slot Cooldown Stress Test
        print("\n[Test 1.2] Testing SIMULTANEOUS Cooldown Sweeps on ALL 5 SLOTS...")
        simul_eval = """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.cds.atk = p.kit.atk.cd;
            p.cds.q = p.kit.q.cd;
            p.cds.w = p.kit.w.cd;
            p.cds.e = p.kit.e.cd;
            p.cds.r = p.kit.r.cd;
            return {
                atk: p.cds.atk,
                q: p.cds.q,
                w: p.cds.w,
                e: p.cds.e,
                r: p.cds.r
            };
        })()
        """
        await call_cdp("Runtime.evaluate", {"expression": simul_eval, "returnByValue": True})
        await asyncio.sleep(0.06)
        simul_res = await call_cdp("Runtime.evaluate", {"expression": sample_sweep_eval, "returnByValue": True})
        simul_data = simul_res.get("result", {}).get("value", {})
        print("  All-slot Simultaneous Status:")
        for s, d in simul_data.items():
            print(f"    Slot '{s}': pct={d.get('pct')}%, display={d.get('display')}, text={d.get('text')}")
            assert d.get("display") == "flex", f"Slot {s} display should be 'flex', got {d.get('display')}"
            assert "conic-gradient" in d.get("bg", ""), f"Slot {s} missing conic-gradient in bg: {d.get('bg')}"
            assert d.get("pct") is not None and d.get("pct") > 60.0, f"Slot {s} initial pct should be > 60%, got {d.get('pct')}"

        # Clean up cooldowns
        await call_cdp("Runtime.evaluate", {"expression": """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            for (const s of ['atk', 'q', 'w', 'e', 'r']) p.cds[s] = 0;
        })()
        """})
        await asyncio.sleep(0.1)

        results["cooldown_sweeps"] = {
            "slots": slot_sweep_results,
            "simultaneous_all_slots_pass": True
        }

        # =========================================================================
        # TEST 2: SIMULATED CLICKS ON .moba-ability-btn ELEMENTS
        # =========================================================================
        print("\n=======================================================")
        print("TEST 2: STRESS-TESTING MOUSE CLICKS ON .moba-ability-btn")
        print("=======================================================")

        btn_coords_eval = """
        (() => {
            const btns = document.querySelectorAll('.moba-ability-btn');
            const data = {};
            btns.forEach(b => {
                const rect = b.getBoundingClientRect();
                data[b.id] = {
                    slot: b.dataset.slot,
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2,
                    width: rect.width,
                    height: rect.height,
                    visible: rect.width > 0 && rect.height > 0
                };
            });
            return data;
        })()
        """
        btn_res = await call_cdp("Runtime.evaluate", {"expression": btn_coords_eval, "returnByValue": True})
        btn_coords = btn_res.get("result", {}).get("value", {})
        print("Detected .moba-ability-btn elements and bounding boxes:")
        print(json.dumps(btn_coords, indent=2))
        assert len(btn_coords) >= 6, f"Expected at least 6 ability buttons, found {len(btn_coords)}"

        click_test_results = {}

        # Position player at arena center (0, 0) to avoid base sanctuary (+25/s) healing zone
        await call_cdp("Runtime.evaluate", {"expression": """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.x = 0;
            p.z = 0;
        })()
        """})

        # 2A: Test slot-atk click via CDP synthetic mouse events
        print("\n[Test 2.1] Simulating CDP Mouse Click on #slot-atk...")
        await call_cdp("Runtime.evaluate", {"expression": """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.cds.atk = 0;
            p.state = 'idle';
            p.comboStep = 0;
            p.comboResetTimer = 0;
        })()
        """})
        coords_atk = btn_coords["slot-atk"]
        await call_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": coords_atk["x"],
            "y": coords_atk["y"],
            "button": "left",
            "clickCount": 1
        })
        await call_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": coords_atk["x"],
            "y": coords_atk["y"],
            "button": "left",
            "clickCount": 1
        })
        await asyncio.sleep(0.08)

        atk_verify = await call_cdp("Runtime.evaluate", {"expression": """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            return {
                state: p.state,
                comboStep: p.comboStep,
                atkCd: p.cds.atk
            };
        })()
        """, "returnByValue": True})
        atk_val = atk_verify.get("result", {}).get("value", {})
        print("  Post-Click ATK State:", atk_val)
        assert atk_val.get("state") in ["attack", "attack2", "attack3"], f"Player did not enter attack state on click! {atk_val}"
        assert atk_val.get("comboStep") > 0, "Combo step did not increment!"
        click_test_results["slot-atk"] = {"passed": True, "state": atk_val.get("state")}

        # 2B: Test skill buttons (slot-q, slot-w, slot-e, slot-r) via CDP synthetic mouse
        skill_slots = [
            ("slot-q", "q", 25, 5.5),
            ("slot-w", "w", 20, 8.0),
            ("slot-e", "e", 15, 9.0),
            ("slot-r", "r", 50, 22.0)
        ]

        for btn_id, slot_key, expected_cost, expected_cd in skill_slots:
            print(f"\n[Test 2.2] Simulating CDP Mouse Click on #{btn_id} (Skill '{slot_key}')...")
            await call_cdp("Runtime.evaluate", {"expression": f"""
            (() => {{
                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds['{slot_key}'] = 0;
                p.deadTimer = 0;
                return p.chakra;
            }})()
            """})

            coords = btn_coords[btn_id]
            await call_cdp("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": coords["x"],
                "y": coords["y"],
                "button": "left",
                "clickCount": 1
            })
            await call_cdp("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": coords["x"],
                "y": coords["y"],
                "button": "left",
                "clickCount": 1
            })
            await asyncio.sleep(0.08)

            verify_res = await call_cdp("Runtime.evaluate", {"expression": f"""
            (() => {{
                const p = window.units.find(u => u.isPlayer);
                const cdEl = document.getElementById('cd-{slot_key}');
                return {{
                    remainingChakra: p.chakra,
                    cooldown: p.cds['{slot_key}'],
                    cdDisplay: cdEl ? cdEl.style.display : null,
                    cdBg: cdEl ? cdEl.style.background : null
                }};
            }})()
            """, "returnByValue": True})
            val = verify_res.get("result", {}).get("value", {})
            print(f"  Skill '{slot_key}' Result: chakra={val.get('remainingChakra')}, cd={val.get('cooldown')}, display={val.get('cdDisplay')}")
            expected_chakra = 100 - expected_cost
            # Account for ~5.5/s passive chakra regeneration during 80ms wait at center arena (~0.44 chakra)
            assert expected_chakra <= val.get("remainingChakra") <= (expected_chakra + 2.5), f"Chakra not deducted properly! Expected near {expected_chakra}, got {val.get('remainingChakra')}"
            assert val.get("cooldown") > 0, f"Cooldown not triggered for slot {slot_key}!"
            assert val.get("cdDisplay") == "flex", f"Cooldown overlay not displayed as flex!"
            assert "conic-gradient" in (val.get("cdBg") or ""), f"Missing conic-gradient in overlay bg: {val.get('cdBg')}"
            click_test_results[btn_id] = {"passed": True, "chakraSpent": 100 - val.get("remainingChakra"), "cdTriggered": val.get("cooldown")}

        # 2C: Test Chakra Button (#slot-c)
        print("\n[Test 2.3] Simulating CDP Mouse Click on #slot-c (Chakra Charge)...")
        await call_cdp("Runtime.evaluate", {"expression": """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            p.chakra = 40;
            return p.chakra;
        })()
        """})
        coords_c = btn_coords["slot-c"]
        await call_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": coords_c["x"],
            "y": coords_c["y"],
            "button": "left",
            "clickCount": 1
        })
        await call_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": coords_c["x"],
            "y": coords_c["y"],
            "button": "left",
            "clickCount": 1
        })
        await asyncio.sleep(0.08)

        chakra_res = await call_cdp("Runtime.evaluate", {"expression": """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            return p.chakra;
        })()
        """, "returnByValue": True})
        post_chakra = chakra_res.get("result", {}).get("value")
        print(f"  Post-Click Chakra: {post_chakra} (Expected ~65 with center arena passive regen)")
        assert 65.0 <= post_chakra <= 68.0, f"Expected chakra between 65 and 68 after click, got {post_chakra}"
        click_test_results["slot-c"] = {"passed": True, "chakraAfter": post_chakra}

        # 2D: Adversarial / Stress Clicking Scenarios
        print("\n[Test 2.4] Adversarial Click Scenarios (Cooldown Block, Zero Chakra, Dead Unit)...")
        adv_eval = """
        (() => {
            const p = window.units.find(u => u.isPlayer);
            const btnQ = document.getElementById('slot-q');

            // 1. Click while on cooldown
            p.chakra = 100;
            p.cds.q = 4.0;
            btnQ.click();
            const cdPrevented = (p.chakra === 100);

            // 2. Click with zero chakra
            p.cds.q = 0;
            p.chakra = 0;
            btnQ.click();
            const zeroChakraPrevented = (p.cds.q === 0 && p.chakra === 0);

            // 3. Click while dead
            p.chakra = 100;
            p.cds.q = 0;
            p.deadTimer = 5.0;
            btnQ.click();
            const deadPrevented = (p.cds.q === 0 && p.chakra === 100);

            // Restore player
            p.deadTimer = 0;
            p.chakra = 100;

            return { cdPrevented, zeroChakraPrevented, deadPrevented };
        })()
        """
        adv_res = await call_cdp("Runtime.evaluate", {"expression": adv_eval, "returnByValue": True})
        adv_val = adv_res.get("result", {}).get("value", {})
        print("  Adversarial Click Guards:", adv_val)
        assert adv_val.get("cdPrevented"), "Click while on cooldown should be a no-op!"
        assert adv_val.get("zeroChakraPrevented"), "Click with 0 chakra should be rejected without negative chakra!"
        assert adv_val.get("deadPrevented"), "Click while dead should be rejected!"

        results["click_interactions"] = {
            "button_results": click_test_results,
            "adversarial_guards": adv_val
        }

        # =========================================================================
        # TEST 3: CIRCULAR AVATAR GEOMETRIC STABILITY (1:1 ASPECT RATIO, 50% RADIUS)
        # =========================================================================
        print("\n=======================================================")
        print("TEST 3: STRESS-TESTING CIRCULAR AVATAR UNDER CONTAINER STATES")
        print("=======================================================")

        measure_avatar_eval = """
        (() => {
            const ring = document.querySelector('.player-avatar-ring');
            const img = document.getElementById('hud-player-portrait');
            if (!ring) return null;
            const ringRect = ring.getBoundingClientRect();
            const ringCs = window.getComputedStyle(ring);
            const imgRect = img ? img.getBoundingClientRect() : null;
            const imgCs = img ? window.getComputedStyle(img) : null;

            const ratio = ringRect.height > 0 ? (ringRect.width / ringRect.height) : 0;
            return {
                ringWidth: ringRect.width,
                ringHeight: ringRect.height,
                aspectRatio: Math.round(ratio * 1000) / 1000,
                isPerfectCircle: Math.abs(ratio - 1.0) < 0.01,
                borderRadius: ringCs.borderRadius,
                isBorderRadius50: ringCs.borderRadius.includes('50%') || (
                    parseFloat(ringCs.borderTopLeftRadius) > 0 &&
                    Math.abs(parseFloat(ringCs.borderTopLeftRadius) - ringRect.width / 2) < 1.0
                ),
                flexShrink: ringCs.flexShrink,
                imgWidth: imgRect ? imgRect.width : null,
                imgHeight: imgRect ? imgRect.height : null,
                imgObjectFit: imgCs ? imgCs.objectFit : null
            };
        })()
        """

        # 3A: Baseline Avatar Measurement
        base_res = await call_cdp("Runtime.evaluate", {"expression": measure_avatar_eval, "returnByValue": True})
        base_avatar = base_res.get("result", {}).get("value")
        print("  Baseline Avatar Measurements (1280x720):")
        print(json.dumps(base_avatar, indent=2))
        assert base_avatar["isPerfectCircle"], f"Avatar aspect ratio {base_avatar['aspectRatio']} is not 1:1!"
        assert base_avatar["isBorderRadius50"], f"Avatar border radius {base_avatar['borderRadius']} is not 50%!"
        assert base_avatar["flexShrink"] == "0", f"Avatar flexShrink is {base_avatar['flexShrink']}, expected '0' to prevent distortion!"

        # 3B: Viewport Resizing Matrix
        viewports = [
            (800, 600, "SVGA Compact"),
            (1920, 1080, "Full HD Wide"),
            (640, 480, "VGA Minimum"),
            (2560, 1440, "QHD 2K"),
            (1024, 1366, "Portrait Tablet")
        ]

        viewport_results = {}
        for w, h, label in viewports:
            print(f"\n[Test 3.1] Testing Viewport {w}x{h} ({label})...")
            await call_cdp("Emulation.setDeviceMetricsOverride", {
                "width": w,
                "height": h,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(0.15)

            v_res = await call_cdp("Runtime.evaluate", {"expression": measure_avatar_eval, "returnByValue": True})
            v_avatar = v_res.get("result", {}).get("value")
            print(f"    Width={v_avatar['ringWidth']}px, Height={v_avatar['ringHeight']}px, Ratio={v_avatar['aspectRatio']}, Radius={v_avatar['borderRadius']}")
            assert v_avatar["isPerfectCircle"], f"Avatar distorted under {label} {w}x{h}! Ratio: {v_avatar['aspectRatio']}"
            assert v_avatar["isBorderRadius50"], f"Avatar radius not 50% under {label} {w}x{h}!"
            viewport_results[f"{w}x{h}"] = v_avatar

        # Restore original viewport
        await call_cdp("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 720,
            "deviceScaleFactor": 1,
            "mobile": False
        })
        await asyncio.sleep(0.1)

        # 3C: Dynamic DOM Container Stress (Flex crowding & extreme text lengths)
        print("\n[Test 3.2] Testing Avatar under Container Flex Stress & Overflow...")
        stress_dom_eval = """
        (() => {
            const results = {};
            const deck = document.querySelector('.player-command-deck');
            const lvlChip = document.getElementById('hud-player-lvl');
            const hpText = document.getElementById('hud-hp-text');
            const ckText = document.getElementById('hud-ck-text');
            const vitalsStrip = document.querySelector('.vitals-strip');

            const origDeckWidth = deck.style.width;
            const origLvl = lvlChip.textContent;
            const origHp = hpText.textContent;

            // Scenario 1: Extreme compression on command deck
            deck.style.maxWidth = '300px';
            lvlChip.textContent = 'Lv.99999';
            hpText.textContent = 'HP 99999999 / 99999999 [CHAKRA SAGE MODE]';

            const ring = document.querySelector('.player-avatar-ring');
            const r1 = ring.getBoundingClientRect();
            const ratio1 = r1.width / r1.height;
            results.extreme_compression = {
                width: r1.width,
                height: r1.height,
                aspectRatio: Math.round(ratio1 * 1000) / 1000,
                isPerfectCircle: Math.abs(ratio1 - 1.0) < 0.01
            };

            // Scenario 2: Heavy sibling elements injected into vitals strip
            const junk1 = document.createElement('div');
            junk1.style.width = '300px';
            junk1.textContent = 'EXTRA_JUNK_ELEMENT_LONG_STRING';
            junk1.id = 'temp-junk-sibling';
            vitalsStrip.appendChild(junk1);

            const r2 = ring.getBoundingClientRect();
            const ratio2 = r2.width / r2.height;
            results.sibling_crowding = {
                width: r2.width,
                height: r2.height,
                aspectRatio: Math.round(ratio2 * 1000) / 1000,
                isPerfectCircle: Math.abs(ratio2 - 1.0) < 0.01
            };

            // Cleanup
            junk1.remove();
            deck.style.maxWidth = '';
            lvlChip.textContent = origLvl;
            hpText.textContent = origHp;

            return results;
        })()
        """
        stress_res = await call_cdp("Runtime.evaluate", {"expression": stress_dom_eval, "returnByValue": True})
        stress_val = stress_res.get("result", {}).get("value", {})
        print("  Container Stress Results:")
        print(json.dumps(stress_val, indent=2))
        assert stress_val["extreme_compression"]["isPerfectCircle"], f"Avatar squashed under extreme compression: {stress_val['extreme_compression']}"
        assert stress_val["sibling_crowding"]["isPerfectCircle"], f"Avatar squashed under sibling crowding: {stress_val['sibling_crowding']}"

        results["avatar_stability"] = {
            "baseline": base_avatar,
            "viewports": viewport_results,
            "container_stress": stress_val
        }

        # =========================================================================
        # TEST 4: CONSOLE ERROR AUDIT
        # =========================================================================
        print("\n=======================================================")
        print("TEST 4: CONSOLE ERRORS & RUNTIME EXCEPTION AUDIT")
        print("=======================================================")
        print(f"Total intercepted console errors / exceptions: {len(errors)}")
        if errors:
            for err in errors:
                print(f"  - {err}")
        assert len(errors) == 0, f"Encountered {len(errors)} runtime console errors!"

        return True, results

def main():
    import tempfile
    tmp_profile = tempfile.mkdtemp()
    print("Launching Headless Edge Browser on port 9222...")
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
    success = False
    details = None
    try:
        success, details = asyncio.run(run_stress_tests())
    except Exception as e:
        print(f"\nCRITICAL FAILURE IN STRESS TEST RUNNER: {e}")
        import traceback
        traceback.print_exc()
        success = False
    finally:
        print("Terminating Edge instance...")
        proc.terminate()
        proc.wait()

    if success:
        print("\n=======================================================")
        print(">>> EMPIRICAL STRESS TESTS COMPLETED SUCCESSFULLY! <<<")
        print("Verdict: APPROVE")
        print("=======================================================")
        sys.exit(0)
    else:
        print("\n=======================================================")
        print(">>> EMPIRICAL STRESS TESTS DETECTED FAILURES! <<<")
        print("Verdict: REQUEST_CHANGES")
        print("=======================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
