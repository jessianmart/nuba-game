"""Static string extraction from the native game library inside the APK.

Pure-Python ELF string-table reader. No disassembler, no installation.
"""

import os
import re
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.apk_inspect import APK_PATH  # noqa: E402

SO = "lib/arm64-v8a/libultimateninjastorm.so"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(ROOT, "public/assets/data/so_constants.md")
OUT_JSON = os.path.join(ROOT, "public/assets/data/so_strings.json")

DOMAINS = {
    "chakra": r"chakra|chakara|chakra_|_chakra|chakraCost|chakra_nut",
    "damage": r"damage|atkPower|attack_power|dmg|attackRate|atk_rate|hitDamage",
    "defense": r"defen|guard|blockRate|dmgCut|damageCut|armor",
    "cooldown": r"cool_?time|cooldown|recover|castTime|cast_time|interval",
    "ninjutsu": r"skill|skl|ninjutsu|jutsu|secret|ultimate|ougi|wakeup|awaken|despertar",
    "status": r"status|poison|confus|stun|slow|down|guardBreak|seal|trap",
    "motion": r"motion|anim|PL_ANM|cmb|combo|rpg[0-9]",
    "item": r"item|equip|weapon|costume|accessory|consum",
    "stage": r"stage|arena|battlefield|spawn|checkpoint",
    "team": r"team|counter|point|score|kill|death|respawn|revive",
    "ai": r"\bai\b|ai_|behavior|personality|aggressive|reaction",
    "effect": r"effect|eff_|vfx|particle|impact|hitstop",
}

STR_RE = re.compile(rb"[\x20-\x7e]{5,}")


def load():
    with zipfile.ZipFile(APK_PATH) as z:
        return z.read(SO)


def all_strings(data):
    seen = {}
    for m in STR_RE.finditer(data):
        s = m.group().decode()
        seen[s] = seen.get(s, 0) + 1
    return seen


def elf_sections(data):
    """Walk the ELF64 section headers to recover .rodata / .dynstr ranges."""
    if data[:4] != b"\x7fELF":
        return []
    e_shoff, = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    if not e_shoff or not e_shnum:
        return []
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if off + 64 > len(data):
            break
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size = struct.unpack_from(
            "<IIQQQQ", data, off)
        secs.append({"name_off": sh_name, "type": sh_type, "offset": sh_offset,
                     "size": sh_size, "flags": sh_flags})
    strtab = secs[e_shstrndx] if e_shstrndx < len(secs) else None
    for s in secs:
        if strtab:
            p = strtab["offset"] + s["name_off"]
            s["name"] = data[p:data.index(b"\x00", p)].decode("latin1")
        else:
            s["name"] = ""
    return secs


def main():
    data = load()
    print(f"{SO}: {len(data)} bytes, magic={data[:4]!r}")
    secs = elf_sections(data)
    print(f"ELF sections: {len(secs)}")
    for s in secs:
        if s["size"] > 4096:
            print(f"  {s['name']:20s} off={s['offset']:#010x} size={s['size'] / 1024:.0f}KB")

    strings = all_strings(data)
    print(f"\nASCII strings (>=5 chars): {len(strings)} unique")

    buckets = {k: [] for k in DOMAINS}
    for s, n in strings.items():
        low = s.lower()
        for dom, pat in DOMAINS.items():
            if re.search(pat, low):
                buckets[dom].append(s)

    json_out = {d: sorted(v)[:4000] for d, v in buckets.items()}
    json_out["_meta"] = {
        "library": SO,
        "size_bytes": len(data),
        "unique_strings": len(strings),
        "sections": [{"name": s.get("name"), "offset": s["offset"], "size": s["size"]}
                     for s in secs],
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        import json
        json.dump(json_out, f, indent=1, ensure_ascii=False)

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# libultimateninjastorm.so — static string survey\n\n")
        f.write(f"- Library: `{SO}` ({len(data) / 1024 / 1024:.1f} MB, AArch64)\n")
        f.write(f"- Unique ASCII strings (>=5 chars): **{len(strings)}**\n")
        f.write(f"- ELF sections: {len(secs)}\n\n")
        f.write("| Section | Offset | Size |\n|---|---:|---:|\n")
        for s in secs:
            f.write(f"| `{s.get('name','')}` | {s['offset']:#x} | {s['size']} |\n")
        f.write("\n## Symbolic domains\n\n")
        f.write("| Domain | Matching strings |\n|---|---:|\n")
        for d, v in buckets.items():
            f.write(f"| {d} | {len(v)} |\n")
        for d, v in buckets.items():
            f.write(f"\n## {d} ({len(v)} strings, showing 200)\n\n```\n")
            for s in sorted(v)[:200]:
                f.write(s + "\n")
            f.write("```\n")

    print(f"\n-> {OUT_JSON}")
    print(f"-> {OUT_MD}")
    for d, v in buckets.items():
        print(f"  {d:9s} {len(v)}")


if __name__ == "__main__":
    main()