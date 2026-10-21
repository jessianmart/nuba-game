# -*- coding: utf-8 -*-
"""Extrai portraits de selecao (dataRegion.awb: msel1_<id>.tex.xfbin -> NTP3 -> PNG)
para public/assets/portraits/. Uso: python tools/extract_portraits.py 1tnd 1orc"""
import sys, os, importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = r"C:\Users\jessi\Documents\antigravity\nuba-android\app\src\main\assets\assets\data\disc\dataRegion.awb"

sys.path.insert(0, REPO)  # extract_moba_assets faz 'from tools.apk_inspect import ...'
spec = importlib.util.spec_from_file_location("ema", os.path.join(REPO, "tools", "extract_moba_assets.py"))
ema = importlib.util.module_from_spec(spec)
sys.modules["ema"] = ema
spec.loader.exec_module(ema)

def main(ids):
    out = os.path.join(REPO, "public", "assets", "portraits")
    os.makedirs(out, exist_ok=True)
    ok, miss = [], []
    import zipfile, io as _io
    with zipfile.ZipFile(ema.APK_PATH) as z:
        f = _io.BytesIO(z.read("assets/data/disc/dataRegion.awb"))
        cpk = ema.parse_utf(f.read(64 * 1024), 16)[0]
        f.seek(cpk["TocOffset"])
        toc = ema.parse_utf(f.read(cpk["TocSize"]), 16)
        toc_map = {r["FileName"].lower(): r for r in toc}
        for cid in ids:
            fname = f"msel1_{cid}.tex.xfbin"
            if fname not in toc_map:
                miss.append(cid); continue
            r = toc_map[fname]
            f.seek(cpk["TocOffset"] + r["FileOffset"])
            raw = f.read(r["FileSize"])
            if raw[:8] == b"CRILAYLA":
                raw = ema.decompress_crilayla(raw)
            p_off = raw.find(b"NTP3")
            if p_off == -1:
                miss.append(cid); continue
            pw, ph, prgba, _ = ema.decode_ntp3_texture(raw, p_off + 16, max_dim=256)
            ema.write_png_rgba(os.path.join(out, f"{cid}.png"), pw, ph, prgba)
            ok.append((cid, pw, ph, os.path.getsize(os.path.join(out, f"{cid}.png"))))
    for cid, w, h, b in ok:
        print(f"  [OK] {cid}.png {w}x{h} {b}B")
    for cid in miss:
        print(f"  [MISS] {cid}: msel1_{cid}.tex.xfbin ausente no dataRegion.awb")
    return 0 if len(miss) == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["1tnd", "1orc"]))
