# -*- coding: utf-8 -*-
"""PV-B.6: assert de sanidade de ASSETS no verify_browser_runtime.py.
Pega a classe de bug: JSON de asset corrompido (ex.: skill_vfx.json com NaN) ->
r.json() rejeita -> .catch(() => ({})) engole -> VFX morre SEM console error.
Rollback: tools/verify_browser_runtime.py.bak_pvb6
"""
import io, shutil, sys

P = 'tools/verify_browser_runtime.py'
raw = io.open(P, 'rb').read()
eol = '\r\n' if b'\r\n' in raw else '\n'
src = raw.decode('utf-8').replace('\r\n', '\n')

ANCHOR = "        return (len(errors) == 0 and\n"
NEW_RET = ("        return (len(errors) == 0 and\n"
           "                assets_val is not None and\n"
           '                assets_val.get("vfxKeys", 0) >= 11 and\n'
           '                assets_val.get("rosterLen", 0) >= 12 and\n'
           '                assets_val.get("animKeys", 0) >= 12 and\n')

BLOCK = '''        # PV-B.6: sanidade de ASSETS carregados — pega corrupcao silenciosa de JSON
        # (ex.: skill_vfx.json com NaN -> r.json() falha -> catch {} mata os VFX
        #  extraidos sem nenhum console error; mesmo padrao do revert W1.1)
        assets_probe = """
        (() => ({
          vfxKeys: Object.keys(window.skillVfxData || {}).length,
          rosterLen: (window.rosterMeta || []).length,
          animKeys: Object.keys(window.animationsData || {}).length
        }))()
        """
        res_as = await call_cdp("Runtime.evaluate", {"expression": assets_probe, "returnByValue": True})
        assets_val = res_as.get("result", {}).get("value")
        print("Assets Sanity Result:", json.dumps(assets_val))

'''

if 'assets_val' in src:
    print('ja aplicado'); sys.exit(0)
if src.count(ANCHOR) != 1:
    print('ABORTADO: ancora do return nao encontrada/ambigua (count=%d)' % src.count(ANCHOR)); sys.exit(1)

out = src.replace(ANCHOR, BLOCK + NEW_RET)
shutil.copyfile(P, P + '.bak_pvb6')
io.open(P, 'wb').write(out.replace('\n', eol).encode('utf-8') if eol == '\r\n' else out.encode('utf-8'))
print('patch PV-B.6 aplicado no verify_browser_runtime.py')
