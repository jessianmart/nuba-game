# -*- coding: utf-8 -*-
"""Integrador serial W2: Tsunade (1tnd, heroi #11) + Orochimaru (1orc, heroi #12).
Le w22_out/ (Orochimaru, validado) e w23_out/ (Tsunade, extraida pelo subagente),
copia assets com diff por bytes, mergeia animations.json, patcha 5 maps do game.js
e appenda 2 fichas em roster_meta.json. DECISAO DO USUARIO: Tsunade entra no lugar
da Temari (w21 descartado/inexistente).

Regras (skill 6.8): dry-run valida TODAS as ancoras ANTES de gravar qualquer arquivo;
toda gravacao deixa .bak_w2int; ancoras ASCII-only; aborta se w23 (Tsunade) ausente."""
import io, json, os, re, shutil, sys

REPO = r"C:\Users\jessi\Documents\antigravity\goofy-mendeleev"
GAME = os.path.join(REPO, "public", "game.js")
RANIM = os.path.join(REPO, "public", "assets", "data", "animations.json")
RMETA = os.path.join(REPO, "public", "assets", "data", "roster_meta.json")
BAK = ".bak_w2int"

# ---- design dos kits (PT-BR, tema Storm) — constantes de ficha ----
KITS = {
 "1tnd": """  '1tnd': {
    atk: { name: 'Taijutsu com Selo de Chakra', desc: 'Socos devastadores que canalizam chakra concentrado no ponto de impacto', cd: 0.40, cost: 0 },
    q:   { name: 'Rakanken (Punho Sismico)', desc: 'Punho de chakra que racha o chao e arremessa inimigos na area', cd: 5.5, cost: 25, dmg: 240, color: 0x22c55e, type: 'dash_aoe' },
    w:   { name: 'Shosen Jutsu (Chakra Medico)', desc: 'Espirais de chakra verde ferem inimigos e recompõem o vigor da Hokage', cd: 8.0, cost: 20, dmg: 120, color: 0x14b8a6, type: 'spin_aoe' },
    e:   { name: 'Kawarimi da Quinta', desc: 'Substituicao ninja deixando um tronco selado', cd: 9.0, cost: 15, dmg: 0, color: 0x4ade80, type: 'kawarimi' },
    r:   { name: 'Byakugo: Sozo Saisei (Renascimento da Criacao)', desc: 'O Selo da Centopeia libera forca sobre-humana e regeneracao total', cd: 24.0, cost: 50, dmg: 460, color: 0x10b981, type: 'ultimate' }
  }""",
 "1orc": """  '1orc': {
    atk: { name: 'Kusanagi: Lamina Serpente', desc: 'Estocadas rapidas da espada amaldicoada com alcance serpenteante', cd: 0.42, cost: 0 },
    q:   { name: "Sen'nejashu (Cobras Ocultas)", desc: 'Multiplicas cobras explode dos bracos e cacam o inimigo mais proximo', cd: 5.0, cost: 25, dmg: 200, color: 0x84cc16, type: 'fireball' },
    w:   { name: 'Kusanagi no Tsurugi (Estocada Longa)', desc: 'Avanco perfurante da lamina que atravessa a defesa', cd: 7.5, cost: 20, dmg: 180, color: 0xa3e635, type: 'dash_aoe' },
    e:   { name: 'Kawarimi de Cobra', desc: 'Substituicao deixando uma cobra de cobertura', cd: 9.0, cost: 15, dmg: 0, color: 0x4ade80, type: 'kawarimi' },
    r:   { name: 'Yamata no Jutsu (Hydra de Oito Cabecas)', desc: 'A serpente de oito cabecas domina a arena com presas venenosas', cd: 25.0, cost: 50, dmg: 470, color: 0x65a30d, type: 'ultimate' }
  }""",
}
SFX = {
 "1tnd": "  '1tnd': { q: 'punch_hit', w: 'chakura_use', e: 'shunshin', r: 'oogi' }",
 "1orc": "  '1orc': { q: 'genjyutu', w: 'sword_hit', e: 'shunshin', r: 'oogi' }",
}
VFX = {  # q/w preenchidos em runtime p/ 1tnd (procura 1tnd_*.png especifico); 1orc confirmado do w22_out
 "1tnd": ["__TBD__", "1efc_chakra00", "1efc_log01", "1efc_nor_dst01"],
 "1orc": ["1orc_1orceff1_01", "1efc_strk01", "1efc_log01", "1efc_nor_rpl02"],
}
VANIM = {
 "1tnd": "  '1tnd': { q: 'thrust', w: 'pulse', e: 'rise',  r: 'spin' }",
 "1orc": "  '1orc': { q: 'rise',   w: 'thrust', e: 'rise', r: 'pulse' }",
}
STATS = {
 "1tnd": "  '1tnd': { hp: 1150, spd: 0.98, dr: 1.05, reg: 1.45 }, // Hokage medica: sustain maximo",
 "1orc": "  '1orc': { hp: 1000, spd: 1.02, dr: 1.00, reg: 1.10 }, // Sannin versatil",
}
FICHA = {
 "1tnd": {"name": "Tsunade", "title": "Quinta Hokage • Sannin Lendária", "role": "Bruiser Sustentado / Cura",
          "color": "#22c55e", "jp": "綱手", "clan": "Sannin", "atk": 5.0, "def": 4.0, "spd": 3.5, "ck": 5.0,
          "dif": "Médio", "heightCm": 163.0,
          "desc": "Quinta Hokage e a maior ninja médica da história: punhos sísmicos, chakra curativo e regeneração absoluta."},
 "1orc": {"name": "Orochimaru", "title": "Serpente Sannin • Renegado", "role": "Assassino à Distância / Veneno",
          "color": "#84cc16", "jp": "大蛇丸", "clan": "Sannin", "atk": 4.5, "def": 3.5, "spd": 4.0, "ck": 5.0,
          "dif": "Difícil", "heightCm": 179.4,
          "desc": "Sannin serpente exilado de Konoha: cobras dos braços, a lâmina Kusanagi e a Hydra de oito cabeças."},
}

def read_txt(p):
    return io.open(p, "r", encoding="utf-8", newline="").read()

def write_txt(p, content, eol):
    shutil.copyfile(p, p + BAK)
    body = eol.join(content.split("\n")) if eol == "\r\n" else content
    io.open(p, "w", encoding="utf-8", newline="").write(body)

def count_model(p):
    """Conta verts/tris recursivamente (arrays 'positions' e 'indices')."""
    verts = tris = 0
    def walk(o):
        nonlocal verts, tris
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "positions" and isinstance(v, list) and v and isinstance(v[0], (int, float)):
                    verts += len(v) // 3
                elif k == "indices" and isinstance(v, list) and v and isinstance(v[0], (int, float)):
                    tris += len(v) // 3
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o: walk(x)
    walk(json.load(io.open(p, "r", encoding="utf-8")))
    return verts, tris

def diff_copy(src_dir, dst_dir, only_prefix=None):
    n = 0
    for root, _, files in os.walk(src_dir):
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, src_dir)
            if only_prefix and not rel.startswith(only_prefix):
                continue
            dst = os.path.join(dst_dir, rel)
            need = True
            if os.path.exists(dst):
                need = os.path.getsize(src) != os.path.getsize(dst)
            if need:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst); n += 1
    return n

def main():
    # (0) pre-requisitos: reports dos 2 herois
    missing = [h for h in ("w22_out", "w23_out") if not os.path.isdir(os.path.join(REPO, h))]
    if missing:
        print("ABORTADO — pastas ausentes no repo:", missing); return 1
    reps = {}
    for h in ("w22_out", "w23_out"):
        rp = os.path.join(REPO, h, "report.json")
        if not os.path.isfile(rp):
            print(f"ABORTADO — {h}/report.json ausente"); return 1
        reps[h] = json.load(io.open(rp, "r", encoding="utf-8"))
    hid = {reps["w22_out"].get("hero_id") or reps["w22_out"].get("heroId"): "w22_out",
           reps["w23_out"].get("hero_id") or reps["w23_out"].get("heroId"): "w23_out"}
    if "1orc" not in hid or "1tnd" not in hid:
        print("ABORTADO — hero_ids inesperados:", hid); return 1
    print("[0] reports OK:", {k: v.get("hero_id") for k, v in reps.items()})

    # (1) VFX da Tsunade: procura PNG especifico 1tnd_* em w23 skills
    tnd_skills = os.path.join(REPO, "w23_out", "assets", "skills")
    tnd_pngs = sorted([f for f in os.listdir(tnd_skills) if f.lower().startswith("1tnd")], key=lambda f: -os.path.getsize(os.path.join(tnd_skills, f))) if os.path.isdir(tnd_skills) else []
    if tnd_pngs:
        VFX["1tnd"][0] = tnd_pngs[0][:-4]  # q = maior PNG especifico
        if len(tnd_pngs) > 1: VFX["1tnd"][1] = tnd_pngs[1][:-4]
    else:
        VFX["1tnd"][0] = "1efc_chakra04"  # fallback: pool comum (impacto de chakra)
    print("[1] VFX 1tnd:", VFX["1tnd"])

    # (2) DRY-RUN: valida TODAS as ancoras antes de gravar
    g = read_txt(GAME)
    eol = "\r\n" if "\r\n" in g else "\n"
    anchors = {
        "kits":   "'1jry': {",
        "sfx":    "'1jry': { q: 'goheki'",
        "vfx":    "'1jry': { q: 'toad_fire'",
        "vanim":  "'1jry': { q: 'thrust'",
        "stats":  "'1jry': { hp: 1150",
    }
    pos = {k: g.find(v) for k, v in anchors.items()}
    if any(p == -1 for p in pos.values()) or len(set(pos.values())) != len(pos):
        print("ABORTADO — ancora faltando/ambigua:", pos); return 1
    close_kits = g.find("\n  }\n};", pos["kits"])
    if close_kits == -1:
        print("ABORTADO — fechamento de HERO_KITS nao encontrado"); return 1
    print("[2] dry-run ancoras OK:", {k: v for k, v in pos.items()})

    # (3) copia assets com diff (models/textures/skills) — idempotente
    n = 0
    for h in ("w22_out", "w23_out"):
        a = os.path.join(REPO, h, "assets")
        n += diff_copy(os.path.join(a, "models"), os.path.join(REPO, "public", "assets", "models"))
        n += diff_copy(os.path.join(a, "textures"), os.path.join(REPO, "public", "assets", "textures"))
        n += diff_copy(os.path.join(a, "skills"), os.path.join(REPO, "public", "assets", "skills"))
    print(f"[3] assets copiados/atualizados: {n} arquivos")

    # (4) animations.json — merge por heroi (só as keys que faltam)
    an = read_txt(RANIM)
    a_eol = "\r\n" if "\r\n" in an else "\n"
    an_data = json.loads(an)
    added = []
    for h, hid_v in (("w22_out", "1orc"), ("w23_out", "1tnd")):
        src_an = os.path.join(REPO, h, "assets", "data", "animations.json")
        if os.path.isfile(src_an):
            src = json.load(io.open(src_an, "r", encoding="utf-8"))
            for k, v in src.items():
                if k not in an_data:
                    an_data[k] = v; added.append(k)
                else:
                    an_data[k] = v  # herois novos nao existem; safe overwrite
    write_txt(RANIM, json.dumps(an_data, ensure_ascii=False), a_eol)
    print(f"[4] animations.json: keys adicionadas: {added} (total {len(an_data)})")

    # (5) game.js — 5 patchs
    def after_line(content, anchor, new_lines):
        i = content.find(anchor)
        j = content.find("\n", i)
        line_end = content[i:j]
        comma = "," if not line_end.rstrip().endswith(",") else ""
        return content[:j] + comma + "\n" + "\n".join(new_lines) + content[j:]

    g = after_line(g, "'1jry': { q: 'goheki'", [SFX["1tnd"], SFX["1orc"]])
    vfx_t = f"  '1tnd': {{ q: '{VFX['1tnd'][0]}', w: '{VFX['1tnd'][1]}', e: '{VFX['1tnd'][2]}', r: '{VFX['1tnd'][3]}' }}"
    vfx_o = f"  '1orc': {{ q: '{VFX['1orc'][0]}', w: '{VFX['1orc'][1]}', e: '{VFX['1orc'][2]}', r: '{VFX['1orc'][3]}' }}"
    g = after_line(g, "'1jry': { q: 'toad_fire'", [vfx_t, vfx_o])
    g = after_line(g, "'1jry': { q: 'thrust'", [VANIM["1tnd"], VANIM["1orc"]])
    g = after_line(g, "'1jry': { hp: 1150", [STATS["1tnd"], STATS["1orc"]])
    ins = close_kits + len("\n  }")  # pos fechamento do bloco 1jry (recalcula apos edits anteriores nao afetam antes disso)
    ins = g.find("\n  }\n};", g.find("'1jry': {")) + len("\n  }")
    blocks = "," + "\n" + KITS["1tnd"] + ",\n" + KITS["1orc"]
    g = g[:ins] + blocks + g[ins:]
    write_txt(GAME, g, eol)
    print("[5] game.js: 5 maps patchados (KITS, SFX, VFX, VANIM, STATS)")

    # (6) roster_meta.json — append 2 fichas
    rm = json.loads(read_txt(RMETA))
    ids = [x["id"] for x in rm["roster"]]
    for hid_v, wdir in (("1tnd", "w23_out"), ("1orc", "w22_out")):
        if hid_v in ids:
            print(f"  [skip] {hid_v} ja no roster"); continue
        f = FICHA[hid_v]
        mpath = os.path.join(REPO, "w" + ("23" if hid_v == "1tnd" else "22") + "_out", "assets", "models", hid_v + ".json")
        verts, tris = count_model(mpath)
        texs = sorted(os.listdir(os.path.join(REPO, wdir, "assets", "textures"))) if os.path.isdir(os.path.join(REPO, wdir, "assets", "textures")) else []
        an_keys = list(an_data.get(hid_v, {}).keys())
        an_list = sorted(an_keys)  # mapa simples das anims disponiveis
        entry = {
            "id": hid_v, "name": f["name"], "title": f["title"], "role": f["role"], "color": f["color"],
            "portrait": f"assets/portraits/{hid_v}.png", "model": f"assets/models/{hid_v}.json",
            "textures": [f"textures/{t}" for t in texs if t.lower().endswith(".png")],
            "verts": verts, "tris": tris,
            "apkSource": reps[wdir].get("apk_source", f"assets/data/sim/data.awb -> {hid_v}bod1.xfbin"),
            "animations": an_list, "heightCm": f["heightCm"],
            "worldHeight": round(f["heightCm"] * 0.03333, 3),
            "jp": f["jp"], "clan": f["clan"], "atk": f["atk"], "def": f["def"], "spd": f["spd"],
            "ck": f["ck"], "dif": f["dif"], "desc": f["desc"],
        }
        rm["roster"].append(entry)
        print(f"  [+] {hid_v}: {verts}v/{tris}t, {len(entry['textures'])} tex, {len(an_list)} anims")
    r_eol = "\r\n" if "\r\n" in read_txt(RMETA) else "\n"
    write_txt(RMETA, json.dumps(rm, ensure_ascii=False, indent=1), r_eol)
    print(f"[6] roster_meta: {len(rm['roster'])} herois")
    print("W2 INTEGRATE: APLICADO (rollback: arquivos *" + BAK + ")")
    return 0

if __name__ == "__main__":
    sys.exit(main())
