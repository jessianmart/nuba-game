# APK_REVERSE — Engenharia reversa do APK de Naruto Ultimate Ninja Storm

Mapa do APK, formatos descobertos e o que foi extraído para o NUBA.
Tudo aqui foi feito com parsers Python próprios sobre o APK — **sem instalar
nenhuma ferramenta externa** (sem JADX, apktool, Ghidra ou REA).

- **Alvo**: `naruto-ultimate-ninja-storm-mod_129_working_1791703630.apk` (3.3 GB)
- **Extraído**: ~1.2 GB de artefatos + índices gerados
- **Namespace C++ do jogo**: `ns1` (CyberConnect2 / CRI)

---

## 1. Por que JADX não serviria

`classes.dex` (5.6 MB) e `classes2.dex` (2.9 KB) contêm **apenas** Google Play
Services, AndroidX, `play-core asset-delivery` e o SDK de anúncios. As 30
classes mais referenciadas são `com.google.*` e `androidx.*`. **Zero lógica de
jogo em Java.**

Toda a lógica está em `lib/arm64-v8a/libultimateninjastorm.so` (20.4 MB) e nos
assets `.awb`. Decompilar o DEX não produziria nada útil.

---

## 2. Estrutura do APK

| Caminho | Tamanho | Conteúdo |
|---|---:|---|
| `assets/data/**/*.awb` | 3.2 GB | 12 arquivos CPK (contenedores) |
| `lib/arm64-v8a/libultimateninjastorm.so` | 20.4 MB | Jogo completo (C++/NUCC) |
| `lib/arm64-v8a/libc++_shared.so` | 1.2 MB | runtime C++ |
| `classes.dex` + `classes2.dex` | 5.6 MB | Play Services / ads (não é o jogo) |
| `res/`, `resources.arsc` | 1 MB | recursos Android |

### Os 12 arquivos CPK

| Arquivo | Entradas | Conteúdo |
|---|---:|---|
| `assets/data/sim/data.awb` | 611 | corpos de personagens (`bod1`), params (`prm`), VFX (`eff1`), animações de skill (`skl1/2`) |
| `assets/data/sim/data2.awb` | 54 |cenas de home (`1nrtfig1`, 11 MB) |
| `assets/data/sim/stage1.awb` | 68 | **geometria dos palcos** (`sd00a`…`sd05b`), céu/nuvens, área de jogo |
| `assets/data/sim/stage2.awb` | 170 | cadeias de LOD (`sa00*lod0/1/2`) |
| `assets/data/sim/stream1.awb` | 113 | eventos 01–18 (`.strm`, `.xml`, `.lst`) |
| `assets/data/sim/stream2.awb` | 113 | eventos 18–36 |
| `assets/data/sim/installTime.awb` | 34 | subset instalável |
| `assets/data/sim/sound.awb` | 252 | **bancos de SFX** (`data/sound/Se/*.xfbin`) e voicebanks |
| `assets/data/disc/installTimeDisc.awb` | 406 | eventos de instalação/extra |
| `assets/data/disc/dataRegion.awb` | 1482 | **UI** (`interface/sel1`, `battle_mode`, `face`), retratos |
| `assets/data/disc/adx2.awb` | 88 | áudio aninhado (BGM 84 MB, voices JP/US) |
| `assets/data/disc/movie.awb` | 15 | cutscenes VP9 (`.usm`, 456 MB) |

**Conteúdo descomprimido total: 8.3 GB** (3165 `.xfbin`, 17 `.usm`, 88 `.awb` aninhados, 27 `.acb`).

---

## 3. Formatos (todos implementados em Python puro)

### CPK (`.awb`)
Contêiner de tabela CyberConnect.
- Cabeçalho com magic, `TocOffset` e `TocSize`.
- TOC em formato **UTFT** (tabela binária estilo Unity) → `tools/apk_inspect.py:parse_utf`.
- Cada entrada: `DirName`, `FileName`, `FileOffset`, `FileSize`, `ExtractSize`.

### CRILAYLA
Compressão própria (LZ variantes em backward stream). Implementado como reader
inverso bit-a-bit em `tools/apk_inspect.py:decompress_crilayla`. É aplicado
transparentemente — todo acesso passa por `tools/cpk_extract.py:read`.

### NUCC (`.xfbin`)
Contêiner de chunks: `nuccChunkNull`, `nuccChunkBinary`, `nuccChunkPage`,
`nuccChunkIndex`, `nuccChunkAnm`, `nuccChunkModel`, `nuccChunkTexture`,
`nuccChunkParticle`, `nuccChunkClump`, `nuccChunkCoord`…
Magic `NUCC` / `NUS3` (áudio).

### NTP3 / NDP3
Sub-formatos de textura e malha dentro dos chunks NUCC. Já decodificados pelo
`tools/extract_moba_assets.py` (`decode_ntp3_texture`, `decode_ndp3_mesh`).

### CRI ADX2 / HCA (áudio)
`data/sound/Se/*.xfbin` são contêineres ADX2 com streams **HCA**
(tags `ciph`, `comp`, `Wfmt`, `loop`; caminho fonte
`D:/msn_sound/CRI/NS1/PC/NS1/commse0.acb`).
> ⚠️ **HCA é codec proprietário.** Os 14 MB extraídos **não são reproduzíveis
> no navegador** sem um decodificador HCA (ex.: `ww2hca`, `hca-tools`).
> O Web Audio procedural atual do NUBA continua sendo a via prática.

---

## 4. O `.so` não está stripped — essa foi a maior descoberta

| Métrica | Valor |
|---|---:|
| Símbolos dinâmicos | 50.549 |
| Símbolos definidos | 50.061 |
| Funções | 45.876 |
| Objetos (dados) | 4.672 |
| Strings ASCII únicas (≥5) | 72.451 |
| **Classes reconstruídas** | **2.872** |

Seções relevantes: `.text` 9.9 MB, `.rodata` 834 KB, `.dynstr` 2.2 MB,
`.data` 494 KB, `.bss` 1.0 MB.

### Arquitetura real do jogo recuperada

| Classe | Métodos | Papel |
|---|---:|---|
| `ns1::ccPlayerLeader` | 240 | jogador humano: chakra, vida, tensão, awakening |
| `ns1::ccCpuPlayer` | 264 | **IA**: família `CheckReact*`, táticas, dodge timing |
| `ns1::ccPlayerRpg` | 182 | movimento/montaria (Brim), walls, floors, colisões |
| `ns1::ccPlayerPad` | 92 | input: `IsAttack`, `IsChakra`, `IsGuard`, `IsDash`, `IsFireArm` |
| `ns1::ccBaseStateAI` | 10 | máquina de estados da IA (`Think`, `RequestThinkSet`) |

APIs de balanceamento reais reveladas:

```cpp
ccPlayerLeader::AddChakra(float, unsigned)      // ganho de chakra
ccPlayerLeader::UseChakra(float)                // gasto
ccPlayerLeader::SetChakraDamage(float)          // dano de chakra
ccPlayerLeader::OnChakraMax()                   // chakra cheio → awakening
ccPlayerLeader::AddTension(float)               // "tensão" (guard-break)
ccRpgLifeGauge::SetChakraMax(float)
ccCpuPlayer::GetTactics()                       // escolha de tática
ccCpuPlayer::CheckEnemyAttackTiming(ccPlayer*, int)
ccCpuPlayer::SetDodgeTiming(int)
ccPlayerPad::IsSuccessTimingGuard(...)          // timing system
```

Sistema de **timing** existe de verdade: `DODGE_TIMING`, `IsSuccessTimingPush`,
`IsSuccessTimingGuard`, `FRAME_TO_TIMING_PUSH`.

Maquinas de estado (`CtrlAct_*` com `PL_ACT_STEP`):
`ATK`, `DMG`, `DMG_TO_DOWN`, `DMG_TO_FALL`, `GUARDHIT`, `DMG_GUARDBREAK`,
`DMG_FOLLOWATK`, `CHAKRA_CHARGE`, `AWAKE_BEGIN/CHARGE/END`, `DEAD_DUEL`,
`RECOVER_AIR`, `USE_ITEM_ATK`, `USE_ITEM_INSTANT`, `FALL`, `ENTRY`, `EXIT`,
`CTRL_1NRX_SLEEP`.

Projéteis/fábricas de jutsu reais (`ns1::ccEffectFireArm`):
`CreateChakraKunai`, `CreateChakraSyuriken`, `CreateChakraFuujiFuda`,
`CreateChakraTorikabuto`, `CreateChakraKunaiHitAir/Grand`, `CreateChakraSunaSyuriken`,
`CreateKunai_LW`.
`ns1::ccEffectHit`: `CreateHitChakraSlash`, `CreateHitChakraThrust`.

---

## 5. Tabelas de combate por personagem

De `data/spc/*prm.bin.xfbin` — 46 personagens, cada um com sub-tabelas
`mot` (motion), `skl` (skill), `etc`, `spl` (special).

A máquina de estados de animação real usa labels `PL_ANM_*` agrupadas em:

| Grupo | Exemplos | Significado |
|---|---|---|
| `combo` | `CMB00`…`CMB11` (até 20 estados) | **o combo de 3+ hits** |
| `rpg_skill` | `RPG00`…`RPG103` (até 144) | jutsus únicos do personagem |
| `airborne` | `FALL0`, `FALL1` | queda |
| `nutada` | `NUT` | rotação no ar (*taijutsu* classique) |
| `landing` | `LAN` | aterrissagem |
| `entrance` / `exit` | `ENTR`, `EXIT` | entradas |
| `run` / `turn` / `jump` | `RUN0`, `RUN1`, `TRN1`, `JMP0`, `JMP1`, `NXJ0` | locomoção |
| `reaction` | `RXN0` | reação a dano |

Exemplo (`1nrt` = Naruto): 20 estados de combo, 144 skills RPG, sub-tabelas
`etc`/`mot`/`skl`/`spl`.

> ⚠️ **Limite do RE:** os records de `*prm.bin` têm stride de 88 bytes com
> campos de `int32` misturados, mas o layout exato do struct não foi
> determined — sem os headers C++ isso exigiria análise do `.text`. As
> **strings simbólicas e a topologia** foram extraídas; os **valores numéricos**
> de balanceamento não. Estão disponíveis em `public/assets/data/spc/`.

---

## 6. O que foi extraído

### Fase 1 — alto ganho, baixo custo (41 MB)

| Lote | Arquivos | Destino |
|---|---:|---|
| Parâmetros de combate | 173 (26.1 MB) | `public/assets/data/spc/` |
| Bancos de SFX (ADX2/HCA) | 9 (14.4 MB) | `public/assets/audio/` |
| Meta de palco | 19 (0.4 MB) | `public/assets/data/stage_meta/` |

`stage_meta` inclui `StageAreaInfo.bin.xfbin` (147 KB) — **limites da arena e
pontos de spawn** — mais as curvas de câmera `CAMKonohaAct`, `GIMKonohaAct`,
`FLYKonohaAct`, `SCRKonohaAct`, `MAPKonohaAct` e `DMYKonohaAct`.

### Fase 2 — engenharia reversa (0 MB de assets)

| Artefato | Conteúdo |
|---|---|
| `data/so_strings.json` | 72.451 strings por domínio (chakra, damage, cooldown, ai…) |
| `data/so_constants.md` | relatório legível dos domínios |
| `data/so_symbols.json` | 45.876 funções + 4.672 objetos |
| `data/so_symbols.md` | símbolos por domínio |
| `data/so_class_index.json` / `.md` | **2.872 classes** com todos os métodos, agrupadas em 15 subsistemas |

Subsistemas recovered: `player` (31 classes), `skill` (275), `effect` (179),
`ui` (120), `item` (102), `collision` (87), `motion` (37), `sound` (19),
`stage` (13), `team` (12), `chakra` (9), `net` (4), `status` (2), `ai` (2).

### Fase 3 — expansão em massa (1.16 GB)

| Lote | Arquivos | MB | Observação |
|---|---:|---:|---|
| `models/puppets/` | 63 | 114.3 | todos os `data/puppet/pm*.xfbin` |
| `ui/raw/` | 342 | 149.7 | `sel1`, `battle_mode`, `face` (48 pulados no teto) |
| `stage/raw/` | 171 | 898.9 | `sd01a`…`sd05b` + LOD `sa0*` (12 pulados no teto) |

### Índices gerados

| Arquivo | Conteúdo |
|---|---|
| `data/combat_params.json` | 46 personagens → grupos de animação, sub-tabelas, asset ids |

---

## 7. Ferramentas criadas

| Script | Função |
|---|---|
| `tools/apk_inventory.py` | inventário streaming do APK (nada extraído) |
| `tools/cpk_extract.py` | lib de leitura/extração seletiva de CPK, com teto de disco |
| `tools/cpk_toc_list.py` | lista o TOC interno dos 12 `.awb` |
| `tools/cpk_find.py` | dry-run de tamanho antes de extrair |
| `tools/parse_nucc.py` | tabelas de strings de containers NUCC |
| `tools/build_combat_index.py` | índice por personagem → `combat_params.json` |
| `tools/so_strings.py` | extração de strings do binário nativo |
| `tools/so_symbols.py` | recuperação de símbolos ELF64 |
| `tools/demangle.py` | demangler Itanium ABI |
| `tools/build_symbol_index.py` | índice de classes → 2.872 classes |
| `tools/extract_fase1.py` / `extract_fase3.py` | lotes de extração orçados |

### Uso

```powershell
# Inventário do APK (não escreve nada)
python tools/apk_inventory.py inventory

# Procurar arquivos dentro dos CPKs
python tools/cpk_find.py "data/spc/" ".acb"

# Fase 1 (dry-run antes: acrescente --dry)
python tools/extract_fase1.py

# Índice nativo
python tools/so_symbols.py
python tools/build_symbol_index.py
```

Todo acesso passa por `tools/cpk_extract.py`, que valida espaço livre antes de
cada escrita (reserva de 3 GB).

---

## 8. Observações finais

- O `data/stream/*` contém `.xml` com a **narrativa e cutscenes** — 74 XMLs,
  1.1 MB. Fonte authoritative dos nomes de habilidade em japonês.
- Cinquenta e cinco personagens têm tabela de params completa; o roster do
  NUBA usa 10.
- **Ainda não resolvido**: schema binário exato dos structs de `*prm.bin`
  (valores de dano/cooldown), decodificação HCA, e formato dos `.usm`.