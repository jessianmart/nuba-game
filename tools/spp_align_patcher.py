# -*- coding: utf-8 -*-
"""SPP ALIGN: recentra geometria VFX no proprio centroide (Blender audit: fireball/
amaterasu/toad_fire ~144u off-origin giravam como braco de catapulta no facing).
Rollback: *.bak_sppalign"""
import io, sys, shutil

path = 'public/game.js'
src = io.open(path, 'r', encoding='utf-8', newline='').read()
eol = '\r\n' if '\r\n' in src else '\n'
s = src.replace('\r\n', '\n')
old = "  for (const sm of meshesToUse) {\n    const geom = new THREE.BufferGeometry();\n    geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(sm.positions), 3));"
new = old + """
    // SPP ALIGN: recentra no proprio centroide — modelos extraidos off-origin
    // (fireball/amaterasu/toad_fire ~144u — Blender audit) giravam como braco de
    // catapulta na rotacao de facing; recentrados, o facing aponta a ponta pro alvo
    const _pa = geom.getAttribute('position');
    if (_pa && _pa.count > 3) {
      let _cx = 0, _cy = 0, _cz = 0;
      for (let _i = 0; _i < _pa.count; _i++) { _cx += _pa.getX(_i); _cy += _pa.getY(_i); _cz += _pa.getZ(_i); }
      _cx /= _pa.count; _cy /= _pa.count; _cz /= _pa.count;
      if (Math.hypot(_cx, _cy, _cz) > 0.5) { // so mexe nos realmente off-origin
        for (let _i = 0; _i < _pa.count; _i++) { _pa.setXYZ(_i, _pa.getX(_i) - _cx, _pa.getY(_i) - _cy, _pa.getZ(_i) - _cz); }
        _pa.needsUpdate = true;
      }
    }"""
c = s.count(old)
if c != 1:
    print(f'ANCHOR FAIL: {c} occ'); sys.exit(1)
s = s.replace(old, new, 1)
shutil.copyfile(path, path + '.bak_sppalign')
io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
print('[OK] SPP ALIGN: recentragem aplicada')
sys.exit(0)
