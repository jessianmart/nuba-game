"""PV4.2-race — blindar testes contra corridas de estado de meio de partida.

Bateria pos-PV4.2: verify 1 (labelHasTimer) + suite 45/47 (S04 morte, S05 ult).
Console errors 0; as 3 falhas sao LEITURAS SINCRONAS de estado que o combate
de bots (S01-S03 / AI) deixa sujo: vitima morta ha pouco (respawn/escudo),
caster em hitstun, awakening vencido, label de down pre-tick.

Fix (setup deterministico — assertions INALTERADAS, precedent skill §6.10):
  1. suite S04: vitima viva + spawnShield 0 + player sem hitstun/deadTimer.
  2. suite S05: caster limpo (deadTimer/hitstun/awakenedTimer 0) — o teste
     passa a medir ESTE cast, nao estado herdado.
  3. verify elim: spawnShield 0 na vitima + releitura do label APOS um frame
     (0.35s) via victimIdx — "Renascendo/⏳" e texto atualizado pelo frame loop.
Run: python tools/pv4_2_race_fix.py   (cwd = repo root)
"""
import py_compile
import shutil

SUITE = 'tools/test_e2e_suite.py'
VER = 'tools/verify_browser_runtime.py'
shutil.copy2(SUITE, SUITE + '.bak_pv42race')
shutil.copy2(VER, VER + '.bak_pv42race')

# ---------- 1+2: suite ----------
s = open(SUITE, encoding='utf-8', newline='').read()

a_s04 = """                enemy.x = player.x + 1.5;
                enemy.z = player.z;
                enemy.hp = 5;
                player.cds.atk = 0;"""
n_s04 = """                enemy.x = player.x + 1.5;
                enemy.z = player.z;
                enemy.hp = 5;
                player.cds.atk = 0;
                // PV4.2-race: estado deterministico (vitima viva/sem escudo, caster livre)
                enemy.deadTimer = 0;
                enemy.spawnShield = 0;
                player.deadTimer = 0;
                player.hitstun = 0;"""
assert s.count(a_s04) == 1, f'ancora S04: {s.count(a_s04)}'
s = s.replace(a_s04, n_s04, 1)
print('[ok] suite S04: vitima viva + sem escudo + caster limpo')

a_s05 = """                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.r = 0;"""
n_s05 = """                const p = window.units.find(u => u.isPlayer);
                p.chakra = 100;
                p.cds.r = 0;
                // PV4.2-race: caster vivo/limpo — o teste mede ESTE cast
                p.deadTimer = 0;
                p.hitstun = 0;
                p.awakenedTimer = 0;"""
assert s.count(a_s05) == 1, f'ancora S05: {s.count(a_s05)}'
s = s.replace(a_s05, n_s05, 1)
print('[ok] suite S05: caster limpo (awakening zerado)')

open(SUITE, 'w', encoding='utf-8', newline='').write(s)

# ---------- 3: verify ----------
v = open(VER, encoding='utf-8', newline='').read()

a_setup = """            enemy.deadTimer = 0;
            enemy.hp = 1000;
            enemy.mesh.visible = true;"""
n_setup = """            enemy.deadTimer = 0;
            enemy.hp = 1000;
            enemy.mesh.visible = true;
            enemy.spawnShield = 0; // PV4.2-race: escudo de respawn bloquearia dealDamage"""
assert v.count(a_setup) == 1, f'ancora elim setup: {v.count(a_setup)}'
v = v.replace(a_setup, n_setup, 1)

a_ret = """                hasVfxBursts,
                labelHasKO,
                labelHasTimer
            };"""
n_ret = """                hasVfxBursts,
                labelHasKO,
                labelHasTimer,
                victimIdx
            };"""
assert v.count(a_ret) == 1, f'ancora elim return: {v.count(a_ret)}'
v = v.replace(a_ret, n_ret, 1)

a_victim = """            // Test assist: ally damages enemy first"""
n_victim = """            const victimIdx = window.units.indexOf(enemy); // PV4.2-race: releitura do label pos-frame

            // Test assist: ally damages enemy first"""
assert v.count(a_victim) == 1, f'ancora victimIdx: {v.count(a_victim)}'
v = v.replace(a_victim, n_victim, 1)

a_eval = """        res_elim = await call_cdp("Runtime.evaluate", {"expression": elimination_test_script, "returnByValue": True})
        elim_val = res_elim.get("result", {}).get("value")
        print("Elimination & Downed Test Result:", json.dumps(elim_val, indent=2))"""
n_eval = """        res_elim = await call_cdp("Runtime.evaluate", {"expression": elimination_test_script, "returnByValue": True})
        elim_val = res_elim.get("result", {}).get("value")
        # PV4.2-race: o texto "Renascendo/⏳" do label e atualizado pelo frame loop —
        # reler APOS um tick (a leitura sincrona pegava o label pre-update as vezes).
        await asyncio.sleep(0.35)
        label_recheck_script = \"\"\"
        (() => {
            const enemy = window.units[VICTIM_IDX];
            if (!enemy || !enemy.labelEl) return { labelHasKO: false, labelHasTimer: false };
            const html = enemy.labelEl.innerHTML;
            return {
                labelHasKO: html.includes('K.O.'),
                labelHasTimer: html.includes('Renascendo') || html.includes('⏳')
            };
        })()
        \"\"\".replace("VICTIM_IDX", str((elim_val or {}).get("victimIdx", -1)))
        res_lbl = await call_cdp("Runtime.evaluate", {"expression": label_recheck_script, "returnByValue": True})
        lbl_val = res_lbl.get("result", {}).get("value") or {}
        if elim_val is not None:
            elim_val["labelHasKO"] = lbl_val.get("labelHasKO", elim_val.get("labelHasKO"))
            elim_val["labelHasTimer"] = lbl_val.get("labelHasTimer", elim_val.get("labelHasTimer"))
        print("Elimination & Downed Test Result:", json.dumps(elim_val, indent=2))"""
assert v.count(a_eval) == 1, f'ancora elim eval: {v.count(a_eval)}'
v = v.replace(a_eval, n_eval, 1)
open(VER, 'w', encoding='utf-8', newline='').write(v)
print('[ok] verify elim: spawnShield 0 + victimIdx + releitura pos-frame')

py_compile.compile(SUITE, doraise=True)
py_compile.compile(VER, doraise=True)
print('[ok] py_compile limpo (suite + verify)')
print('PV4.2 RACE FIX DONE')
