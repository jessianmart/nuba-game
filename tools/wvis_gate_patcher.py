# -*- coding: utf-8 -*-
"""W-VIS-GATE: conserta o verify EXIT 1 (causa raiz: hitstun do W-HS bloqueia
os casts em sequencia do verify numa partida viva — bots acertam o player
entre casts -> w_state 'idle' stale -> compositor silencioso reprova).
Fix:
  V1-V4: zero hitstun do PLAYER antes de cada cast forçado (q/w/e/r)
  V5: zero hitstun do BOT no loop de skills multi-hero
  V6: compositor vira dict _checks com print "VERIFY FAILURE DETAIL"
      (debug permanente — a classe de falha silenciosa morre aqui)
Idempotente, dry-run valida todas as ancoras antes de gravar.
Rollback: tools/verify_browser_runtime.py.bak_wvis
"""
import io, shutil, sys

P = 'tools/verify_browser_runtime.py'
raw = io.open(P, 'rb').read()
eol = '\r\n' if b'\r\n' in raw else '\n'
src = raw.decode('utf-8').replace('\r\n', '\n')

if 'VERIFY FAILURE DETAIL' in src:
    print('W-VIS-GATE ja aplicado — nada a fazer'); sys.exit(0)

CASTS = [
    ('            p.cds.q = 0; p.chakra = 100;', '            p.hitstun = 0; p.cds.q = 0; p.chakra = 100;'),
    ('            p.cds.w = 0; p.chakra = 100;', '            p.hitstun = 0; p.cds.w = 0; p.chakra = 100;'),
    ('            p.cds.e = 0; p.chakra = 100;', '            p.hitstun = 0; p.cds.e = 0; p.chakra = 100;'),
    ('            p.cds.r = 0; p.chakra = 100;', '            p.hitstun = 0; p.cds.r = 0; p.chakra = 100;'),
    ('                bot.deadTimer = 0;', '                bot.deadTimer = 0; bot.hitstun = 0;'),
]

RETURN_ANC = """        return (len(errors) == 0 and
                assets_val is not None and
                assets_val.get("vfxKeys", 0) >= 11 and
                assets_val.get("rosterLen", 0) >= 12 and
                assets_val.get("animKeys", 0) >= 12 and
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
                sb_val.get("hasSubtotals") is True)"""

RETURN_NEW = """        # W-VIS-GATE: compositor com diagnostico — imprime EXATAMENTE o que falhou
        _checks = {
            "errors_empty": len(errors) == 0,
            "assets_sanity": assets_val is not None and assets_val.get("vfxKeys", 0) >= 11 and assets_val.get("rosterLen", 0) >= 12 and assets_val.get("animKeys", 0) >= 12,
            "lobby": lobby_val is not None,
            "match_active": combat_val.get("matchActive") is True,
            "bot_skills": skills_val.get("botSkillsVerified") is True,
            "q_jutsu": skills_val.get("q_state") == "jutsu",
            "w_jutsu2": skills_val.get("w_state") == "jutsu2",
            "e_dash": skills_val.get("e_state") == "dash",
            "r_ult": skills_val.get("r_state") == "ult",
            "awakened": skills_val.get("awakened") is True,
            "tools": tools_val is not None and tools_val.get("kunaiSpawned") is True and tools_val.get("twinShurikensSpawned") is True and tools_val.get("tripleShurikensSpawned") is True and tools_val.get("meleePunch", {}).get("dealtDamage") is True,
            "tp_clamps": tp_val.get("camClamped") is True and tp_val.get("playerClamped") is True and all(tp_val.get("movementTested", {}).values()),
            "elim": elim_val is not None and elim_val.get("isDead") is True and elim_val.get("stateIsDown") is True and elim_val.get("meshStillVisible") is True and elim_val.get("killCounted") is True and elim_val.get("deathCounted") is True and elim_val.get("assistCounted") is True,
            "pdeath": pdeath_val is not None and pdeath_val.get("overlayShown") is True and pdeath_val.get("meshInvisibleAfter2s") is True,
            "scoreboard": sb_val is not None and sb_val.get("isOpen") is True and sb_val.get("totalPlayers") == 10 and sb_val.get("hasPlayerHighlight") is True and sb_val.get("hasKdaRatio") is True and sb_val.get("hasSubtotals") is True,
        }
        _failed = sorted(k for k, v in _checks.items() if not v)
        if _failed:
            print("VERIFY FAILURE DETAIL:", __import__("json").dumps(_failed))
        return len(_failed) == 0"""

fails = []
for i, (anc, _) in enumerate(CASTS, 1):
    n = src.count(anc)
    if n != 1:
        fails.append(f'  V{i} count={n} (esperado 1)')
rn = src.count(RETURN_ANC)
if rn != 1:
    fails.append(f'  V6 return count={rn} (esperado 1)')
if fails:
    print('DRY-RUN ABORTADO:'); print('\n'.join(fails)); sys.exit(1)
print('dry-run OK: 5 casts + compositor')

out = src
for anc, new in CASTS:
    out = out.replace(anc, new)
out = out.replace(RETURN_ANC, RETURN_NEW)
assert out.count('p.hitstun = 0;') == 4 and out.count('bot.hitstun = 0;') == 1
assert out.count('VERIFY FAILURE DETAIL') == 1

shutil.copyfile(P, P + '.bak_wvis')
data = out.replace('\n', eol).encode('utf-8') if eol == '\r\n' else out.encode('utf-8')
io.open(P, 'wb').write(data)
print('W-VIS-GATE APLICADO: casts immune a hitstun + diagnostico de falha no compositor')
