"""PV2-D (v2) — filtro de ruído 404 .webp nos coletores (design PV-B.2).
Loader webp-first tenta <tex>.webp e cai no .png quando o par nao existe
(conversao rejeitada pelo QA — ganho nulo em .png <2KB). 404 e' RUÍDO do design,
nao regressao: nao contaminar o criterio "zero console errors".
Ancoras: linha unica por arquivo (robusto a indentacao).
Run: python tools/pv2d_webp_noise_filter_v2.py   (cwd = repo root)
"""
import shutil
import subprocess

LINHA = '                    if entry.get("level") == "error":'
FILTRO = ('                    # PV2-D: 404 .webp sem par = ruído do loader webp-first (design)\n'
          '                    _pv2d_url = (entry.get("url") or "")\n'
          '                    if entry.get("level") == "error" and not _pv2d_url.endswith(".webp"):')

for path in ['tools/test_e2e_suite.py', 'tools/verify_browser_runtime.py']:
    shutil.copy2(path, path + '.bak_pv2d')
    src = open(path, 'r', encoding='utf-8').read()
    n = src.count(LINHA)
    assert n == 1, f'{path}: {n} ocorrencias da âncora'
    open(path, 'w', encoding='utf-8').write(src.replace(LINHA, FILTRO, 1))
    r = subprocess.run(['python', '-m', 'py_compile', path], capture_output=True, text=True)
    assert r.returncode == 0, f'{path}: {r.stderr}'
    print(f'[ok] {path}')
print('PV2D NOISE FILTER DONE')
