# LIFELINE — lifeline

> An append-only chain of *whys*. The project records *why* it is what it is, and any mind that
> connects inherits that why instantly — with no one re-explaining.
>
> **This file is GENERATED** from the ledger (in `.lifeline/`), which is the source of truth.
> Do NOT hand-edit — append with `lifeline log` and it regenerates.
>
> **Start at #0001.** It's the whole project in human language.

## Protocol

1. **Append-only.** Never edit entries; a correction is a new entry (`kind: correction`) that
   references in `parents` the `id` it corrects — superseding it in the current truth.
2. **One entry per unit of work with meaning.** Not per file, not per tool call. The *why*
   outweighs the *what* (Law #5).
3. **Content-addressed identity (Law #3):** `id = sha256(kind, author, agent, provider, model,
   summary, body, sorted-parents)`. `ts` and `dedup_key` stay OUT of the hash — the same content
   yields the same `id` on any machine. `parents` form the causal DAG; there is no prev_hash (the
   ledger is a graph, not a list).
4. **Integrity:** `lifeline verify` checks that every `id` matches its content.
5. **Append:** `lifeline log --kind … --summary … --body …`. To see the assembled context an AI
   would receive: `lifeline context`.

## Project laws (the constitution)

1. **No memory without an immutable anchor.** Every context item carries the hash of its source
   event. The anti-hallucination spine.
2. **Append-only.** Corrections are new entries referencing the prior id.
3. **Deterministic content-addressing.** Same content + parents → same id, on any node.
4. **Provider-agnostic storage; deliver in the provider's format.**
5. **The *why* outweighs the *what*.**
6. **Budget is first-class.** Context fits the window; truncation is explicit, never silent.
7. **MCP-native.** The AI's interface is the product surface, not an appendix.

**Non-goals (law by omission):** Lifeline is NOT a cognitive OS, NOT an MMU, NOT an agent
orchestrator/sandbox, NOT a workflow engine, does NOT replace git, is NOT an executor/curator
(self-healing) or a trainer (fine-tuning/DL). It records reasoning.

---

## Entries

### #0001 — 2026-10-21T11:42:33.619673+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: NUBA publicado: GitHub + Vercel validados via proxy (38/38, 0 console errors)
- **parents**: —
- **id**: 93a6692ac04e2937adbae4c6e3707da09826e7e43257c6ab0e476ec0e9ccb89e

**Body**:
Meta do usuário: entregar tudo validado e publicar GitHub+Vercel inicialmente. Executado: repo github.com/jessianmart/nuba-game (master, 1858+ arquivos, ~541MB assets, sem files >100MB); deploy https://goofy-mendeleev.vercel.app com .vercelignore enxuto (541MB->~150MB, exclui ui/raw, ui/_sheets, models/puppets, banks de audio brutos). Validação: tools/prod_proxy.py (reverse proxy localhost:8080 -> URL Vercel) permitiu rodar verify_browser_runtime.py + test_e2e_suite.py INALTERADOS contra bytes de produção: 38/38, zero console errors. Bugs de deploy corrigidos pela bateria: (1) public/assets/arena é symlink -> stage/arena e o uploader Vercel não segue symlinks (50 texturas 404) — fix via rewrites /assets/arena/:path* -> /assets/stage/arena/:path*; (2) regra ampla de Cache-Control cacheava 404s na edge — removida; (3) .vercel/build-output stale entre deploys — rm antes de redeploy. W2.1 discovery (Temari 1tmr model+anims+vfx extraídos e validados estruturalmente) permanece em w21_out/ aguardando integração serial. Próximos passos: W1.2 Settings, W1.3 Tutorial, integração Temari, fan-out roster.

<!-- lifeline:end -->
