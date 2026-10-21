"""PV3.2-C — instrumentacao de diagnostico: expoe QUAL asset de arena foi
carregado (full vs variante mobile) e com quantas meshes. Aditivo, convencao do
repo de expor estado em window para E2E/probe.
Run: python tools/pv3_2_instrument_patch.py   (cwd = repo root)
"""
import shutil
import subprocess

GJ = 'public/game.js'
shutil.copy2(GJ, GJ + '.bak_pv32c')
g = open(GJ, 'r', encoding='utf-8', newline='').read()

anchor = """      if (res && res.meshes) {
        // PV-B.3: texturas da arena nova sao preservadas ao descartar o palco antigo"""
new = """      if (res && res.meshes) {
        // PV3.2: telemetria de qual variante entrou (full vs .mobile.json)
        window.__ARENA_LOADED = { asset: String(mapAsset), meshes: res.meshes.length,
          isMobile: !!(window.__DEVICE && window.__DEVICE.isMobile), at: performance.now() };
        // PV-B.3: texturas da arena nova sao preservadas ao descartar o palco antigo"""
assert g.count(anchor) == 1, f'ancora: {g.count(anchor)}'
g = g.replace(anchor, new, 1)
open(GJ, 'w', encoding='utf-8', newline='').write(g)

r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] window.__ARENA_LOADED instrumentado + node --check limpo')
