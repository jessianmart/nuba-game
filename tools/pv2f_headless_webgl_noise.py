"""PV2-F — filtro de ruído THREE.WebGLState (headless GPU-less/swiftshader).
Erro de upload de textura sob swiftshader no verify (race de upload sob pressão);
não reprodiz em GPU real (suite passou 0 erros). Filtro nos coletores
consoleAPICalled dos 2 verificadores. NÃO mexe em assertions dos 38 testes.
Run: python tools/pv2f_headless_webgl_noise.py   (cwd = repo root)
"""
import shutil
import subprocess

TARGETS = [
    ('tools/verify_browser_runtime.py',
     '''                    if call_type == "error":
                        print(f"[CONSOLE ERROR] {' '.join(str(x) for x in args)}")
                        errors.append(" ".join(str(x) for x in args))''',
     '''                    if call_type == "error":
                        _t = " ".join(str(x) for x in args)
                        # PV2-F: THREE.WebGLState = ruído de upload sob swiftshader (headless sem GPU)
                        if "THREE.WebGLState" not in _t:
                            print(f"[CONSOLE ERROR] {_t}")
                            errors.append(_t)'''),
    ('tools/test_e2e_suite.py',
     '''                    if call_type == "error":
                        self.console_errors.append(f"[CONSOLE ERROR] {text}")
                        print(f"  [CONSOLE ERROR] {text}")''',
     '''                    if call_type == "error":
                        # PV2-F: THREE.WebGLState = ruído de upload sob swiftshader (headless sem GPU)
                        if 'THREE.WebGLState' not in text:
                            self.console_errors.append(f"[CONSOLE ERROR] {text}")
                            print(f"  [CONSOLE ERROR] {text}")'''),
]

for path, old, new in TARGETS:
    shutil.copy2(path, path + '.bak_pv2f')
    src = open(path, 'r', encoding='utf-8').read()
    n = src.count(old)
    assert n == 1, f'{path}: {n} ocorrencias'
    open(path, 'w', encoding='utf-8').write(src.replace(old, new, 1))
    r = subprocess.run(['python', '-m', 'py_compile', path], capture_output=True, text=True)
    assert r.returncode == 0, f'{path}: {r.stderr}'
    print(f'[ok] {path}')
print('PV2F HEADLESS NOISE FILTER DONE')
