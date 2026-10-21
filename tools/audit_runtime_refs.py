"""audit_runtime_refs.py — guard de deploy do NUBA (PV-B.4).

Cruza as referencias de asset do CLIENTE (game.js / index.html / styles.css) e dos
JSONs de runtime (arenas.json, models/*.json, skill_vfx.json, stage_3d.json) com os
arquivos realmente presentes em public/, e reporta:

  1. assets referenciados e AUSENTES no disco (quebraria o runtime/producao)
  2. arquivos presentes e NAO referenciados (candidatos a exclusao do bundle)
  3. tamanho do que e realmente necessario vs. o que esta em public/

Uso:
  python tools/audit_runtime_refs.py            # relatorio
  python tools/audit_runtime_refs.py --json out.json
  python tools/audit_runtime_refs.py --unused   # so a lista de nao referenciados
"""

import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public')

CLIENT_FILES = ['public/game.js', 'public/index.html', 'public/styles.css']
RUNTIME_JSON = [
    'public/assets/data/arenas.json',
    'public/assets/data/roster_meta.json',
    'public/assets/skills/skill_vfx.json',
    'public/assets/stage/stage_3d.json',
]
RUNTIME_JSON_GLOBS = ['public/assets/models/*.json', 'public/assets/stage/arena/*.json']

ASSET_RE = re.compile(r"""assets/([A-Za-z0-9_\-./]+\.(?:png|webp|jpg|jpeg|json|ogg|mp3|wav|glb|gltf|bin))""")
# paths relativos dentro de JSONs de runtime (textures de arena/modelo, maps)
REL_ASSET_RE = re.compile(r"""["']([A-Za-z0-9_\-./]+\.(?:png|webp|jpg|jpeg|ogg|mp3|wav|json))["']""")


def collect_refs():
    refs = set()
    files = list(CLIENT_FILES) + RUNTIME_JSON
    for g in RUNTIME_JSON_GLOBS:
        files += glob.glob(os.path.join(ROOT, g))
    for rel in files:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        try:
            s = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for m in ASSET_RE.finditer(s):
            refs.add('assets/' + m.group(1))
        # JSONs de runtime: caminhos relativos de textura (ex.: 'arena/sd00a/x.png',
        # 'textures/1nrt_body.png') resolvem a partir de assets/
        if rel.endswith('.json'):
            for m in REL_ASSET_RE.finditer(s):
                p = m.group(1)
                if '/' in p:
                    refs.add(p if p.startswith('assets/') else 'assets/' + p)
    return refs


def disk_files():
    """Mapa relatorio a public/. O path 'assets/arena' e uma JUNCTION para
    'assets/stage/arena' (topologia de deploy) — normalizamos para a forma fisica
    e nao contamos a mesma textura duas vezes."""
    out = {}
    for base, _dirs, files in os.walk(PUB):
        rel_base = os.path.relpath(base, PUB).replace('\\', '/')
        if rel_base == 'assets/arena' or rel_base.startswith('assets/arena/'):
            continue  # junction -> ja contabilizado em assets/stage/arena
        for f in files:
            p = os.path.join(base, f)
            rel = os.path.relpath(p, PUB).replace('\\', '/')
            out[rel] = os.path.getsize(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=None)
    ap.add_argument('--unused', action='store_true')
    args = ap.parse_args()

    refs = collect_refs()
    disk = disk_files()

    def norm(p):
        # 'assets/arena/x' (path do cliente) -> 'assets/stage/arena/x' (path fisico)
        return p.replace('assets/arena/', 'assets/stage/arena/') if p.startswith('assets/arena/') else p

    missing = sorted(r for r in refs if norm(r) not in disk)
    # variantes webp: o cliente prefere .webp e cai para .png
    webp_equiv = sorted(r[:-4] + '.webp' for r in missing if r.endswith('.png') and r[:-4] + '.webp' in disk)
    missing = [r for r in missing if r not in webp_equiv]

    used = set()
    for r in refs:
        used.add(r)
        used.add(norm(r))
        if r.endswith('.png'):
            used.add(r[:-4] + '.webp')
            used.add(norm(r)[:-4] + '.webp')
    unused = {k: v for k, v in disk.items() if k not in used}

    used_bytes = sum(v for k, v in disk.items() if k in used)
    total_bytes = sum(disk.values())

    report = {
        'refs': len(refs),
        'diskFiles': len(disk),
        'missing': missing,
        'missingWithWebpEquivalent': webp_equiv,
        'unusedCount': len(unused),
        'unusedMb': round(sum(unused.values()) / 1048576, 2),
        'usedMb': round(used_bytes / 1048576, 2),
        'totalMb': round(total_bytes / 1048576, 2),
    }

    if args.unused:
        by_dir = {}
        for k, v in sorted(unused.items(), key=lambda kv: -kv[1]):
            d = os.path.dirname(k) or '.'
            by_dir.setdefault(d, [0, 0])
            by_dir[d][0] += 1
            by_dir[d][1] += v
        for d, (n, b) in sorted(by_dir.items(), key=lambda kv: -kv[1][1])[:30]:
            print('%-46s %6d arq %9.2f MB' % (d, n, b / 1048576))
        return

    print(json.dumps({k: v for k, v in report.items() if k != 'missingWithWebpEquivalent'},
                     indent=2, ensure_ascii=False))
    if webp_equiv:
        print('\nresolvidos por .webp (fallback .png nao existe, mas o webp sim): %d' % len(webp_equiv))
    if missing:
        print('\nREFERENCIADOS E AUSENTES (quebram runtime):')
        for m in missing[:40]:
            print('   ', m)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
