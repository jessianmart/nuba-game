import zipfile
import os
import struct
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import (
    OUT_DIR,
    parse_nucc_chunks,
    decode_ntp3_texture,
    write_png_rgba,
)

UI_DIR = os.path.join(OUT_DIR, "ui")
os.makedirs(UI_DIR, exist_ok=True)

TARGET_UI_XFBINS = [
    "xbattle_gauge.xfbin",
    "xbattle_win.xfbin",
    "xbattle_sicon.xfbin",
    "xbattle_pad.xfbin",
    "xcmn_mobile.xfbin",
    "xadv_gauge.xfbin",
    "cmn_battleload00.xfbin",
    "cmn_result.xfbin",
    "xbattle_ninka.xfbin",
    "xbattle_signal.xfbin",
    "cmn_player.xfbin",
]

def extract_all_ui():
    print(f"Extracting maximum UI visuals from APK: {APK_PATH}...")
    extracted_count = 0

    with zipfile.ZipFile(APK_PATH, "r") as z:
        # Check installTimeDisc.awb
        with z.open("assets/data/disc/installTimeDisc.awb") as f_awb:
            cpk = parse_utf(f_awb.read(65536), 16)[0]
            f_awb.seek(cpk["TocOffset"])
            toc = parse_utf(f_awb.read(cpk["TocSize"]), 16)
            toc_map = {}
            for r in toc:
                name = r["FileName"].lower()
                if name not in toc_map:
                    toc_map[name] = []
                toc_map[name].append(r)

            for target in TARGET_UI_XFBINS:
                matches = toc_map.get(target.lower(), [])
                if not matches:
                    continue
                # Pick the latest/largest match
                r = max(matches, key=lambda x: x["FileSize"])
                f_awb.seek(cpk["TocOffset"] + r["FileOffset"])
                raw_bytes = f_awb.read(r["FileSize"])
                if raw_bytes.startswith(b"CRILAYLA"):
                    raw = decompress_crilayla(raw_bytes)
                else:
                    raw = raw_bytes

                try:
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkTexture":
                            t_pos = pay.find(b"NTP3")
                            if t_pos != -1:
                                decoded = decode_ntp3_texture(pay, t_pos + 16, max_dim=512)
                                if decoded:
                                    w, h, rgba, _ = decoded
                                    clean_name = ch_name.replace("/", "_").replace("\\", "_")
                                    out_path = os.path.join(UI_DIR, f"{clean_name}.png")
                                    write_png_rgba(out_path, w, h, rgba)
                                    extracted_count += 1
                                    print(f"  [UI] Extracted {clean_name}.png ({w}x{h}) from {target}")
                except Exception as ex:
                    print(f"  [ERR] Failed parsing {target}: {ex}")

    print(f"\nSuccessfully extracted {extracted_count} authentic Storm UI interface assets into {UI_DIR}!")

if __name__ == "__main__":
    extract_all_ui()
