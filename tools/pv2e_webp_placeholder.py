"""PV2-E — placeholder 1x1 no fallback webp->png do loadTex.
BUG: entre o 404 do .webp e a chegada do .png, o renderer subia a textura com
imagem invalida -> THREE.WebGLState TypeError (texSubImage2D) no headless GPU-less.
FIX: no onError do webp, atribuir canvas 1x1 placeholder antes do load do png.
Run: python tools/pv2e_webp_placeholder.py   (cwd = repo root)
"""
import shutil
import subprocess

GJ = 'public/game.js'
shutil.copy2(GJ, GJ + '.bak_pv2e')
g = open(GJ, 'r', encoding='utf-8', newline='').read()

OLD = """    ? texLoader.load(webp, undefined, undefined, () => {
        texLoader.load(url, (img) => { t.image = img; t.needsUpdate = true; });
      })"""
NEW = """    ? texLoader.load(webp, undefined, undefined, () => {
        // PV2-E: placeholder 1x1 enquanto o .png carrega — evita upload de imagem invalida
        const _ph = document.createElement('canvas'); _ph.width = 1; _ph.height = 1;
        t.image = _ph; t.needsUpdate = true;
        texLoader.load(url, (img) => { t.image = img; t.needsUpdate = true; });
      })"""
n = g.count(OLD)
assert n == 1, f'ancora loadTex: {n} ocorrencias'
g = g.replace(OLD, NEW, 1)
open(GJ, 'w', encoding='utf-8', newline='').write(g)
r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] loadTex: placeholder 1x1 no fallback · node --check limpo')
print('PV2E PLACEHOLDER DONE')
