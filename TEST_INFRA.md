# E2E Test Infra: NUBA (Naruto Ultimate Battle Arena)

## Test Philosophy
- Opaque-box, requirement-driven. Tests are derived from `ORIGINAL_REQUEST.md` user requirements and Acceptance Criteria, not internal implementation quirks.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Workload Testing.
- Target Environment: Headless Microsoft Edge connected via Chrome DevTools Protocol (CDP) on port 9222.
- Clean Execution: 0 console errors, deterministic assertions, reliable timeouts.

## Feature Inventory & Test Coverage Goals
| # | Feature | Source (Requirement) | Tier 1 (Isolated) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---------|---------------------|:-----------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | Top Bar Height (<52px) | R1 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 2 | Mini-Portraits & Pulsing Dots | R1 | 5 | 5 | ✓ | ✓ |
| 3 | Numerical Respawn Countdown | R1 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 4 | Match Timer & Goal Display | R1 | 5 | 5 | ✓ | ✓ |
| 5 | Kill-Feed (Portraits & Fade) | R1 | 5 | 5 | ✓ | ✓ |
| 6 | Command Center (Avatar, Gauges) | R1 | 5 | 5 | ✓ | ✓ |
| 7 | Radial Cooldown Sweeps | R1 | 5 | 5 | ✓ | ✓ |
| 8 | Controls Drawer (Toggle 'H') | R1 | 5 | 5 | ✓ | ✓ |
| 9 | Free 'W' Key for Movement | R2 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 10 | Camera-Relative 3rd-Person Movement | R2 | 5 | 5 | ✓ | ✓ |
| 11 | Camera Stage Clamping (Y>=2.2, [-92, 92]) | R2 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 12 | Mouse Left Click Combo | R3 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 13 | Ninjutsu Primário [Q] | R3 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 14 | Ninjutsu Secundário [E] | R3 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 15 | Kawarimi / Substituição [ESPAÇO] | R3 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 16 | Ultimate Ougi & Despertar [R] | R3 / Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 17 | Concentrar Chakra [F] | R3 | 5 | 5 | ✓ | ✓ |
| 18 | Synchronized SFX & Audio | R3 | 5 | 5 | ✓ | ✓ |
| 19 | Cel-Shaded Hit Sparks | R3 | 5 | 5 | ✓ | ✓ |
| 20 | Awakening Ground Aura Rings | R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `tools/test_e2e_suite.py` executable via `python tools/test_e2e_suite.py`.
- Browser Runner: Automated via Chrome DevTools Protocol (`websockets` to `ws://127.0.0.1:9222/devtools/page/...`).
- Console Error Monitor: CDP `Log.entryAdded` and `Runtime.consoleAPICalled` listening throughout test lifecycle; any error level logs trigger test failure.
- Test Output: Emits structured test results (passed/failed, tier breakdown, assertions summary). When 100% complete, publishes `TEST_READY.md`.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Full Match Initiation & HUD Verification | F1, F2, F4, F6, F8 | Top bar rendered <52px, all 10 ninja icons present, controls drawer opens with 'H' and closes without blocking arena |
| 2 | 3rd-Person Boundary & Navigation Run | F9, F10, F11 | Player navigates arena in 3rd-person mode with WASD relative to camera; camera clamps properly at perimeter and above ground (Y>=2.2) |
| 3 | Combat Combo & Ability Cycling | F12, F13, F14, F15, F16, F17 | Left click 3-hit combo cycles cleanly, Q/E/Space/R fire intended skills with radial cooldown sweeps, F charges chakra |
| 4 | Kill & Respawn Cycle Verification | F3, F5, F2 | Enemy ninja eliminated; kill-feed renders killer/victim portraits and auto-fades; dead portrait displays numerical countdown timer |
| 5 | Awakening & Ultimate Clash | F16, F20, F18, F19 | Player activates Ultimate, awakening ground aura rings appear, SFX triggers, hit sparks render cleanly, 0 console errors |

## Coverage Thresholds
- Tier 1 (Feature Coverage): Basic positive verification for each feature.
- Tier 2 (Boundary & Corner Cases): Stress tests at stage perimeter, zero chakra, rapid clicks, edge inputs.
- Tier 3 (Cross-Feature Combinations): Movement while firing jutsu, toggling camera during combat, drawer toggle during respawn.
- Tier 4 (Real-World Application Scenarios): 5 multi-step end-to-end user gameplay sessions.
