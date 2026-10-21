# -*- coding: utf-8 -*-
"""LOBBY FIT: heroi 3D visivel no centro (bg opaco removido) + ZERO rolagem em qualquer
tela (6x overflow-y:auto -> hidden, compactacao do painel de detalhes, lobby-main flex).
Rollback: *.bak_lobbyfit"""
import io, re, sys, shutil

def apply(path, patches):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        c = s.count(old)
        if c != 1:
            print(f'ANCHOR FAIL [{path}:{name}]: {c} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {name}')
    for name, pat, new, expect in patches_re(path):
        s2, n = re.subn(pat, new, s)
        if n != expect:
            print(f'REGEX FAIL [{path}:{name}]: {n} != {expect}'); return False
        s = s2
        print(f'  [OK] {name} (x{expect})')
    shutil.copyfile(path, path + '.bak_lobbyfit')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

def patches_re(path):
    if path == 'public/styles.css':
        return [('overflow-y auto -> hidden (zero rolagem)', r'overflow-y: auto;', 'overflow: hidden;', 6)]
    return []

ok = True
ok &= apply('public/index.html', [
    ('cache-bust styles v22', 'styles.css?v=21', 'styles.css?v=22'),
    ('cache-bust game v28', 'game.js?v=27', 'game.js?v=28'),
])
ok &= apply('public/game.js', [
    ('anm tags 16 -> 6 (cabe sem scroll)', "(hero.animations || []).slice(0, 16)", "(hero.animations || []).slice(0, 6)"),
])
ok &= apply('public/styles.css', [
    ('lobby bg transparente (heroi 3D visivel)',
     '  background:\n    radial-gradient(circle at 50% 42%, rgba(201, 162, 39, 0.05) 0%, transparent 55%),\n    radial-gradient(circle at 50% 45%, rgba(0, 0, 0, 0.25) 0%, rgba(6, 7, 12, 0.9) 78%),\n    linear-gradient(180deg, #0c0d15 0%, #12141c 55%, #08090e 100%);',
     '  background:\n    radial-gradient(circle at 50% 42%, rgba(201, 162, 39, 0.05) 0%, transparent 55%),\n    radial-gradient(circle at 50% 45%, rgba(0, 0, 0, 0.30) 0%, rgba(6, 7, 12, 0.72) 78%);\n  /* LOBBY FIT: camada opaca removida — heroi 3D e palco visiveis no centro */'),
    ('lobby-main flexivel (cabe exato)',
     '  height: calc(100vh - 120px);\n  margin-top: 14px;',
     '  flex: 1 1 auto;\n  min-height: 0;\n  height: auto;\n  margin-top: 10px;\n  /* LOBBY FIT: preenche o espaco restante — nunca transborda */'),
])

# bloco de compactacao no fim do styles.css
FIT = """
/* ==================== LOBBY FIT: compactacao (nenhuma tela rola) ==================== */
.screen { overflow: hidden; } /* garantia: nenhuma tela gera rolagem */
.hero-details-panel { padding: 10px; gap: 8px; }
.hero-details-panel .hero-header-card { padding: 8px; gap: 10px; }
.hero-details-panel #detail-portrait { width: 54px; height: 54px; }
.hero-details-panel .skill-card { padding: 4px 8px; }
.hero-details-panel .skill-name-txt { font-size: 12px; }
.hero-details-panel .skill-desc-txt {
  font-size: 9.5px; line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.hero-details-panel .skill-cd-badge { font-size: 9px; }
.hero-details-panel .anm-tags { max-height: 40px; }
.roster-grid { max-height: 460px; }
"""
if ok:
    src = io.open('public/styles.css', 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n').rstrip('\n') + '\n' + FIT
    io.open('public/styles.css', 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    print('  [OK] bloco FIT appended')
    print('LOBBY FIT: APLICADO')
else:
    print('LOBBY FIT: ABORTADO'); sys.exit(1)
