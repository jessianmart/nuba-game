
## §15 — Validação de Produção (GitHub + Vercel, 2026-10-20)

**Deploy público**: https://goofy-mendeleev.vercel.app
**Repo**: https://github.com/jessianmart/nuba-game (master)

Método: proxy reverso (`tools/prod_proxy.py`, `localhost:8080 → https://goofy-mendeleev.vercel.app`)
permite rodar a bateria determinística INALTERADA, com todos os bytes vindos do deploy público.

| Verificação | Resultado |
|---|---|
| verify_browser_runtime.py contra produção | ALL PASSED, zero console errors |
| test_e2e_suite.py contra produção | 38/38 Passed, Console Errors: 0 |

### Bugs de deploy achados e corrigidos pela bateria
1. **404 texturas de arena (50 arquivos)**: `public/assets/arena` é SYMLINK para
   `public/assets/stage/arena` localmente — o uploader do Vercel não segue symlinks.
   Fix: rewrite `/assets/arena/:path*` → `/assets/stage/arena/:path*` no vercel.json
   (commit e34ed50). Lição: manifest de runtime = o que o BROWSER pede, não o que o
   grep de código vê; refs vivem também dentro de JSONs de cena.
2. **Cache de 404s**: regra ampla `Cache-Control max-age=3600` em `(.*).(json|png|jpg)`
   aplicava-se também a respostas 404, preservando erros na edge. Regra removida;
   mantida apenas `decoded/*.ogg` immutable (arquivos confirmados presentes).
3. **Build cache stale**: `.vercel/build-output` local reusado entre deploys;
   `rm -rf .vercel/build-output` antes de redeploy crítico.
4. `.vercelignore` enxuta o deploy (541MB → ~150MB): fora `ui/raw`, `ui/_sheets`,
   `models/puppets`, banks de áudio brutos (`.xfbin/.acf/.nus3conf`) — todos com
   zero refs em runtime (auditados em código E JSONs).

## §16 — W1.2 Página de Ajustes (2026-10-21)

**5ª aba do lobby (AJUSTES)**: som (toggle sincronizado com perfil + volume das cues autênticas),
gráficos (pixel ratio low 0.75 / med 1.25 / high 1.75), game feel (master gate `JUICE.enabled`
nas 4 funções juice), controles (keymap real: Q/E/Espaço/R, C, H, TAB). Persistência em
`nuba.profile.v1` (campos aditivos: volume, quality, juice). Zero scroll na página.

| Verificação | Resultado |
|---|---|
| Smoke W1.2 (9 asserts, 2 probes c/ reload) | PASS — persistência restaurada após reload |
| verify_browser_runtime | ALL PASSED, zero console errors |
| test_e2e_suite | 38/38, Console Errors: 0 |

### Incidente W1.1 (2026-10-20 20:52): revert silencioso do working tree
Agentes paralelos (Antigravity) reverteram o game.js pós-W1.1: AUTH_SFX/SKILL_SFX_MAP sumiram
JUNTO com `bak_w11` e `tools/w11_*`; produção ficou sem áudio autêntico (a suite 38/38 não
cobre AUTH_SFX — só o smoke W1.1 cobre). Recuperação: patcher reconstituído do transcript
(session_search) + âncora level-up re-grepada (indent 4 espaços). Reaplicado, smoke 9/9,
bateria 38/38. **Lição: commit imediato após verde; checar marcadores de milestone antes de
qualquer trabalho novo no repo paralelo.**
