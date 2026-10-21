"""Recover exported/imported symbol names from the unstripped native library.

The Storm library keeps .dynsym and .dynstr intact, so the game's own function
names survive. Pure Python ELF64 reader -- no disassembler required.
"""

import json
import os
import struct
import sys
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.apk_inspect import APK_PATH  # noqa: E402

SO = "lib/arm64-v8a/libultimateninjastorm.so"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "public/assets/data/so_symbols.json")
OUT_MD = os.path.join(ROOT, "public/assets/data/so_symbols.md")

STT = {0: "NOTYPE", 1: "OBJECT", 2: "FUNC", 3: "SECTION", 4: "FILE"}
BIND = {0: "LOCAL", 1: "GLOBAL", 2: "WEAK"}

DOMAINS = {
    "chakra": r"chakra|chakra_",
    "damage": r"damage|dmg|atk|attack",
    "defense": r"guard|defen|block|dmgcut",
    "cooldown": r"cool|recover|casttime|interval|timing",
    "skill": r"skill|skl|ninjutsu|jutsu|secret|ultimate|ougi|awaken|wakeup",
    "status": r"status|poison|confus|stun|slow|down|seal|trap|dizzy",
    "motion": r"motion|anim|cmb|combo",
    "item": r"item|equip|weapon|costume|consum|accessor",
    "stage": r"stage|arena|spawn|checkpoint|battlefield",
    "team": r"team|counter|score|kill|death|respawn|revive|point",
    "ai": r"^ai|_ai|ai_|personality|behaviou?r|aggress|tactics",
    "effect": r"effect|eff_|vfx|particle|impact|hitstop",
    "ui": r"hud|ui|interface|menu|gauge|icon",
    "net": r"net|packet|lobby|online|multiplayer|photon",
}


def load():
    with zipfile.ZipFile(APK_PATH) as z:
        return z.read(SO)


def sections(d):
    e_shoff, = struct.unpack_from("<Q", d, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", d, 0x3A)
    out = []
    for i in range(e_shnum):
        o = e_shoff + i * e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size = struct.unpack_from(
            "<IIQQQQ", d, o)
        out.append({"name_off": sh_name, "type": sh_type, "addr": sh_addr,
                    "offset": sh_offset, "size": sh_size})
    stro = out[e_shstrndx]["offset"]
    for s in out:
        p = stro + s["name_off"]
        e = d.find(b"\x00", p)
        s["name"] = d[p:e].decode("latin1") if e > 0 else ""
    return out


def symbols(d, secs):
    dynsym = next(s for s in secs if s["type"] == 11)  # SHT_DYNSYM
    dynstr = next(s for s in secs if s["name"] == ".dynstr")
    base, size = dynstr["offset"], dynstr["size"]
    end = base + size
    out = []
    for o in range(dynsym["offset"], dynsym["offset"] + dynsym["size"], 24):
        st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from(
            "<IBBHQQ", d, o)
        p = base + st_name
        if not (base <= p < end):
            continue
        e = d.find(b"\x00", p)
        if e < 0 or e > end:
            continue
        name = d[p:e].decode("latin1")
        if not name:
            continue
        out.append({
            "name": name,
            "type": STT.get(st_info & 0xF, str(st_info & 0xF)),
            "bind": BIND.get(st_info >> 4, str(st_info >> 4)),
            "value": st_value,
            "size": st_size,
            "defined": st_shndx != 0,
        })
    return out


def main():
    d = load()
    secs = sections(d)
    syms = symbols(d, secs)
    defined = [s for s in syms if s["defined"]]
    print(f"{SO}: {len(d)} bytes, {len(syms)} symbols ({len(defined)} defined), "
          f"{len(secs)} sections")
    print("types:", Counter(s["type"] for s in syms))

    buckets = defaultdict(list)
    for s in syms:
        low = s["name"].lower()
        for dom, pat in DOMAINS.items():
            import re
            if re.search(pat, low):
                buckets[dom].append(s["name"])

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "library": SO,
            "size_bytes": len(d),
            "symbol_count": len(syms),
            "defined_count": len(defined),
            "functions": sorted({s["name"] for s in syms if s["type"] == "FUNC"}),
            "domains": {k: sorted(set(v)) for k, v in buckets.items()},
        }, f, indent=1)

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# Symbols in `{SO}`\n\n")
        f.write(f"- {len(syms)} dynamic symbols, {len(defined)} defined\n")
        f.write(f"- {len([s for s in syms if s['type'] == 'FUNC'])} functions\n")
        f.write(f"- {len([s for s in syms if s['type'] == 'OBJECT'])} objects\n\n")
        f.write("| Domain | Symbols |\n|---|---:|\n")
        for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            f.write(f"| {k} | {len(set(v))} |\n")
        for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            u = sorted(set(v))
            f.write(f"\n## {k} ({len(u)})\n\n```\n")
            f.write("\n".join(u[:300]))
            f.write("\n```\n")
    print(f"-> {OUT_JSON}\n-> {OUT_MD}")
    for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:9s} {len(set(v))}")


if __name__ == "__main__":
    main()