"""Monta o pacote de skin da UI a partir dos recortes em slices/.

  python tools/build_ui_skin.py

Copia cada recorte da tabela SKIN para public/assets/ui/skin/<chave>.png,
grava public/assets/ui/skin/skin.json e uma contact sheet de conferencia
(_skin_sheet.png). Falha com exit != 0 se algum recorte nao existir no manifest.
"""

import json
import os
import sys

from PIL import Image, ImageDraw

SLICE_DIR = os.path.join("public", "assets", "ui", "slices")
SKIN_DIR = os.path.join("public", "assets", "ui", "skin")
SHEET_PATH = os.path.join(SKIN_DIR, "_skin_sheet.png")

SKIN = {
    # 2.1 - contrato
    "panel_blue": ("core/xcmn_base_02", "painel de time azul / moldura 9-slice"),
    "panel_red": ("core/xcmn_base_01", "painel de time vermelho"),
    "panel_silver": ("core/xcmn_base_04", "painel neutro do deck"),
    "panel_white": ("core/xcmn_base_06", "painel de modal (placar, morte)"),
    "panel_orange": ("core/xcmn_base_05", "destaque / awakening"),
    "nameplate": ("core/xbattle_namebase_01", "barra de nome dos mini-indices"),
    "nameplate_alt": ("core/xbattle_namebase_00", "variante de nome"),
    "digit_0": ("core/xbattle_count_01", "algarismo 0"),
    "digit_1": ("core/xbattle_count_02", "algarismo 1"),
    "digit_2": ("core/xbattle_count_03", "algarismo 2"),
    "digit_3": ("core/xbattle_count_04", "algarismo 3"),
    "digit_4": ("core/xbattle_count_00", "algarismo 4"),
    "digit_5": ("core/xbattle_count_08", "algarismo 5"),
    "digit_6": ("core/xbattle_count_05", "algarismo 6"),
    "digit_7": ("core/xbattle_count_09", "algarismo 7"),
    "digit_8": ("core/xbattle_count_06", "algarismo 8"),
    "digit_9": ("core/xbattle_count_07", "algarismo 9"),
    "digit_inf": ("core/xbattle_count_10", "simbolo infinito"),
    "icon_atk": ("core/xbattle_pad01_00", "Taijutsu (soco)"),
    "icon_q": ("core/xbattle_pad01_07", "Ninjutsu primario (selo de mao)"),
    "icon_w": ("core/xbattle_pad01_03", "Ninjutsu secundario (chama)"),
    "icon_e": ("core/xbattle_pad01_06", "Kawarimi (rolo/kunai scroll)"),
    "icon_r": ("core/xbattle_pad01_k_01", "Ougi ultimate (soco vermelho)"),
    "icon_c": ("core/xbattle_pad01_05", "Concentracao de chakra (selo hexagonal)"),
    "icon_rune": ("core/xbattle_pad01_g_00", "runa de despertar / desabilitado"),
    "ring_avatar": ("core/xbattle_newgauge_08", "anel do avatar do jogador"),
    "orb_dark": ("core/xbattle_newgauge_09", "orbe de chakra"),
    "bar_frame": ("core/xbattle_newgauge_03", "moldura da barra de vitais"),
    "bar_thin": ("core/xbattle_newgauge_02", "barra compacta (secundaria)"),
    "flame_aura": ("core/xbattle_newgauge_06", "aura de despertar"),
    "swirl": ("core/xbattle_newgauge_05", "voluta ornamental"),
    "bar_fill_hp": ("core/xadv_gauge00_07", "preenchimento de barra"),
    "ougi_bar": ("battle/battle_xbattle_ougi00_01", "faixa de Ougi"),
    "ougi_flare": ("battle/battle_xbattle_ougi00_05", "clarao de Ougi"),
    "btn_face_b": ("battle/battle_cmn_button00_00", "badge de botao B"),
    "btn_face_a": ("battle/battle_cmn_button00_01", "badge de botao A"),
    "btn_face_y": ("battle/battle_cmn_button00_02", "badge de botao Y"),
    "btn_face_x": ("battle/battle_cmn_button00_03", "badge de botao X"),
    "badge_1p": ("battle/battle_xcmn_playere_fd_00", 'selo "1P" (voce)'),
    "combo_digit_0": ("battle/battle_xbattle_combo00_08", "combo: algarismo 0"),
    "combo_digit_1": ("battle/battle_xbattle_combo00_01", "combo: algarismo 1"),
    "combo_digit_2": ("battle/battle_xbattle_combo00_02", "combo: algarismo 2"),
    "combo_digit_3": ("battle/battle_xbattle_combo00_03", "combo: algarismo 3"),
    "combo_digit_4": ("battle/battle_xbattle_combo00_04", "combo: algarismo 4"),

    # 2.2 - confirmadas visualmente em _sheets/
    "banner_combat": ("core/xbattle_win00_03", "faixa de abertura de combate"),
    "banner_tie": ("core/xbattle_signal_fd00_05", 'faixa "EGALITE"'),
    "banner_win": ("core/xbattle_win01_00", 'faixa de vitoria "GANADOR"'),
    "banner_lose": ("core/xcmn_result_fd00_02", 'faixa de derrota "VERSAGT"'),
    "result_frame": ("core/xcmn_result_fd00_00", "painel de resultado"),
    "result_btn_red": ("battle/battle_cmn_button00_08", "botao vermelho de resultado"),
    "status_fist": ("core/xbattle_sicon00_03", "status: soco"),
    "status_flame": ("core/xbattle_sicon00_01", "status: fogo"),
    "status_stun": ("core/xbattle_sicon00_00", "status: atordoado"),
    "status_boost": ("core/xbattle_sicon00_04", "status: seta de buff"),
    "cursor": ("core/xbattle_cursor_00", "cursor de alvo"),
    "btn_pause": ("core/xbattle_pad05_00", "botao de pausa"),
    "aura_ring": ("core/xbattle_pad07_00", "anel de chakra"),
}


def load_manifest():
    with open(os.path.join(SLICE_DIR, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    return {e["file"]: e for group in manifest.values() for e in group}


def fail(missing):
    print("ERRO: recortes ausentes no manifest.json:", file=sys.stderr)
    for key, src in missing:
        print(f"  chave '{key}' -> '{src}'", file=sys.stderr)
    sys.exit(1)


def build_sheet(skin, cols=6, cell=140):
    keys = list(skin)
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + 16)), (18, 20, 28, 255))
    draw = ImageDraw.Draw(sheet)
    for i, key in enumerate(keys):
        x, y = (i % cols) * cell, (i // cols) * (cell + 16)
        draw.rectangle([x, y, x + cell - 2, y + cell + 14], outline=(64, 76, 104, 255))
        draw.text((x + 4, y + cell + 2), key[:26], fill=(205, 215, 235, 255))
        art = Image.open(os.path.join(SKIN_DIR, f"{key}.png")).convert("RGBA")
        art.thumbnail((cell - 12, cell - 12), Image.LANCZOS)
        sheet.alpha_composite(art, (x + (cell - art.width) // 2, y + (cell - art.height) // 2))
    sheet.save(SHEET_PATH)


def main():
    entries = load_manifest()
    missing = [
        (key, f"{src}.png")
        for key, (src, _) in SKIN.items()
        if f"{src}.png" not in entries
    ]
    if missing:
        fail(missing)

    seen = {}
    for key, (src, _) in SKIN.items():
        if src in seen:
            print(f"ERRO: recorte '{src}' duplicado em '{seen[src]}' e '{key}'", file=sys.stderr)
            sys.exit(1)
        seen[src] = key

    os.makedirs(SKIN_DIR, exist_ok=True)
    for stale in os.listdir(SKIN_DIR):
        if stale.endswith(".png") and stale[:-4] not in SKIN:
            os.remove(os.path.join(SKIN_DIR, stale))

    skin = {}
    for key, (src, use) in SKIN.items():
        out = os.path.join(SKIN_DIR, f"{key}.png")
        Image.open(os.path.join(SLICE_DIR, f"{src}.png")).convert("RGBA").save(out)
        with Image.open(out) as im:
            w, h = im.size
        skin[key] = {"file": f"{key}.png", "w": w, "h": h, "src": f"{src}.png", "use": use}

    with open(os.path.join(SKIN_DIR, "skin.json"), "w", encoding="utf-8") as fh:
        json.dump(skin, fh, indent=2, ensure_ascii=False, sort_keys=True)

    build_sheet(skin)
    total = sum(
        os.path.getsize(os.path.join(SKIN_DIR, f)) for f in os.listdir(SKIN_DIR)
    )
    print(f"{len(skin)} chaves -> {SKIN_DIR}")
    print(f"pacote: {total / 1024:.1f} KB | contact sheet: {SHEET_PATH}")


if __name__ == "__main__":
    main()