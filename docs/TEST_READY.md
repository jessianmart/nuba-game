
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
