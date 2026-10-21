"""Fix santuarios sa00z: dentro do contorno real da vila (raycast polar 72 angulos).
Blue (-40,-30) / Red (45,30) — r~50 nos angulos 216/34 (contorno r 60-70).
Run: python tools/fix_sa00z_sanctuaries.py   (cwd = repo root)
"""
import json
import shutil

AJ = 'public/assets/data/arenas.json'
shutil.copy2(AJ, AJ + '.bak_sanct')
s = open(AJ, 'r', encoding='utf-8', newline='').read()

OLD_BLUE = '   "sanctuaryBlue": {\r\n    "x": -95,\r\n    "z": -95\r\n   },\r\n   "sanctuaryRed": {\r\n    "x": 95,\r\n    "z": 95\r\n   },'
NEW_BLUE = '   "sanctuaryBlue": {\r\n    "x": -40,\r\n    "z": -30\r\n   },\r\n   "sanctuaryRed": {\r\n    "x": 45,\r\n    "z": 30\r\n   },'
assert s.count(OLD_BLUE) == 1, 'ancora santuarios sa00z'
s = s.replace(OLD_BLUE, NEW_BLUE, 1)
open(AJ, 'w', encoding='utf-8', newline='').write(s)

d = json.load(open(AJ, encoding='utf-8'))
e = next(a for a in d['arenas'] if a['id'] == 'sa00z')
assert e['sanctuaryBlue'] == {'x': -40, 'z': -30} and e['sanctuaryRed'] == {'x': 45, 'z': 30}
print('[ok] santuarios sa00z dentro da vila: blue (-40,-30) / red (45,30)')
