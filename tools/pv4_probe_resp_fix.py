"""PV4-FIX — probe_responsive.py pos-PV4.
Pre-PV4 exigia .team-group visivel; o PV4 esconde por design no touch.
Novo criterio: escondido = OK (design); se visivel, deve estar nos bounds.
 centro (timer/BR) DEVE estar visivel e nos bounds.
Run: python tools/pv4_probe_resp_fix.py   (cwd = repo root)
"""
import shutil

F = 'tools/probe_responsive.py'
shutil.copy2(F, F + '.bak_pv4')
s = open(F, 'r', encoding='utf-8', newline='').read()

old = """        checks = {
            'no-h-overflow': r['scrollW'] <= r['innerW'] + 1,
            'bar<52px': r['barH'] is not None and r['barH'] < 52,
            'overlay-hidden': r['overlayDisplay'] == 'none',
            'hud-in-bounds': all(
                r['rects'].get(k, {}).get('vis') and r['rects'][k]['r'] <= r['innerW'] + 1 and r['rects'][k]['l'] >= -1
                for k in ('grpB', 'grpR', 'ctr') if k in r['rects']),
"""

new = """        def _in(k):
            rr = r['rects'].get(k)
            return rr is not None and rr.get('vis') and rr['r'] <= r['innerW'] + 1 and rr['l'] >= -1
        checks = {
            'no-h-overflow': r['scrollW'] <= r['innerW'] + 1,
            'bar<52px': r['barH'] is not None and r['barH'] < 52,
            'overlay-hidden': r['overlayDisplay'] == 'none',
            # PV4: team-groups ficam ocultos por design no touch — escondido = OK;
            # se visiveis, precisam estar nos bounds. Centro (timer/BR) DEVE aparecer.
            'hud-hidden-or-bounded': all(
                (not r['rects'].get(k, {}).get('vis')) or (
                    r['rects'][k]['r'] <= r['innerW'] + 1 and r['rects'][k]['l'] >= -1)
                for k in ('grpB', 'grpR') if k in r['rects']),
            'center-timer-visible': _in('ctr'),
"""

assert s.count(old) == 1, f'anchor: {s.count(old)}'
s = s.replace(old, new, 1)
open(F, 'w', encoding='utf-8', newline='').write(s)
print('[ok] probe_responsive.py ajustado pos-PV4 (hidden-or-bounded + center-timer-visible)')
