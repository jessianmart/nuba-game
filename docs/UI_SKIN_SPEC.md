# UI_SKIN_SPEC — Skin de UI autêntica Storm (reskin do HUD MOBA)

> Documento de engenharia. O **contrato** (o que é obrigatório) está em
> `docs/UI_SKIN_CONTRACT.md`. Este arquivo explica *como*, *por quê* e *o que
> foi descartado*. Em caso de conflito, vale o contrato.

## 1. Objetivo

Clonar o padrão de UI do APK original (**Naruto Ultimate Ninja Storm**,
CyberConnect2 / Bandai Namco) e aplicar esse padrão no protótipo MOBA **NUBA**,
em estilo MOBA: HUD de 5v5 não obstrutivo, leitura instantânea de informação
(HP, chakra, cooldown, placar, tempo) com a mesma gramática visual do jogo de
luta — molduras 9-slice, algarismos desenhados, ícones de selo, faixas de Ougi.

Restrições de arte, herdadas do contrato:

- **Exclusividade de arte original de grandes estúdios** — todo pixel visual do
  HUD vem de recorte do APK. Nada de SVG desenhado à mão, nada de emoji no HUD.
- **Fontes e ícones premium** são o único complemento permitido (CDN de
  tipografia, ícones de terceiros), e apenas quando nenhum asset original
  servir. A tipografia já em uso no projeto (`Cinzel`, `Montserrat`,
  `Noto Sans JP`, via Google Fonts) se enquadra nessa exceção.
- Nenhuma lógica de combate, IA, câmera ou HUD sync é alterada pelo reskin. O
  DOM do HUD é **inviolável** — 34 testes E2E dependem dos IDs atuais
  (contrato §4).

## 2. Estado real em disco (verificado)

Verificado por inspeção de arquivo nesta árvore:

| Item | Caminho | Estado |
|---|---|---|
| Extração de atlas Battle | `tools/extract_ui_battle.py` | **existe** |
| Slicer de atlas | `tools/slice_ui_atlas.py` | **existe** |
| Contact sheets de revisão | `tools/make_review_sheets.py` | **existe** |
| PNGs Battle decodificados | `public/assets/ui/battle/` | **46 PNGs** |
| Slices recortados | `public/assets/ui/slices/` | **692 elementos** + `manifest.json` |
| Pacote curado de skin | `public/assets/ui/skin/` | **NÃO EXISTE** |
| Builder do pacote | `tools/build_ui_skin.py` | **NÃO EXISTE** |
| CSS da skin | `public/styles.css` | **sem** `--skin-*` e **sem** `border-image` (2031 linhas) |
| Motor da skin | `public/game.js` | **sem** `renderSkinDigits` / `showOugiBanner` / `flashKawarimi` / `loadSkinManifest` |
| Hooks de DOM | `public/index.html` | **presentes**: `#ougi-banner` (l. 167), `#kawarimi-flash` (l. 168), `data-digits` (l. 132/147), `data-skin-banner` (l. 164), `data-skin-frame` (l. 315) |

Ou seja: **etapas 1 e 2 concluídas, etapa 3 não iniciada, etapa 4 apenas com os
hooks de DOM**. O milestone M4 está **IN PROGRESS**.

## 3. Pipeline (4 etapas)

```
APK (CPK/CRILAYLA)  ->  battle/*.png (46)  ->  slices/ (692)  ->  skin/ + skin.json  ->  CSS/JS
        tools/extract_ui_battle.py     tools/slice_ui_atlas.py     tools/build_ui_skin.py   styles.css
                                                                                            index.html
                                                                                            game.js
```

### Etapa 1 — `tools/extract_ui_battle.py`

Decodifica, **em memória**, os três containers de UI de batalha que faltavam e
não estavam cobertos por `tools/extract_all_ui_from_apk.py`:

| Grupo | Entrada no CPK `installTimeDisc.awb` |
|---|---|
| `battle` | `data/interface/battle/eng/ANDROID/battle.xfbin` |
| `bigbat` | `data/interface/battle/eng/ANDROID/bigbat.xfbin` |
| `startmenu` | `data/interface/battle/eng/ANDROID/xbattle_startmenu.xfbin` |

Como funciona: `tools.cpk_extract.read_by_name` faz streaming do container CPK
(transparente à descompressão CRILAYLA) **sem escrever o `.xfbin` em disco**;
`parse_nucc_chunks` percorre os chunks NUCC e, para cada `nuccChunkTexture`,
`decode_ntp3_texture` reconstrói o PNG RGBA. Entrada ~22 MB, saída
`public/assets/ui/battle/`, nome de arquivo `<grupo>_<chunk>.png`
(ex.: `battle_xbattle_ougi00_01.png`).

Por que as variantes **ANDROID**: é o layout em retrato, o mesmo formato do
HUD MOBA (o jogo de luta é 4:3/portrait; o MOBA é widescreen e precisa de
recortes separáveis). Também grava `public/assets/ui/battle/battle_sources.json`
com a proveniência de cada PNG.

Teto de decodificação: `MAX_DIM = 1024` — ver §8 (Limitações).

### Etapa 2 — `tools/slice_ui_atlas.py`

**Por que recortar?** Cada textura NTP3 decodificada é um *atlas*: várias peças
de UI coladas no mesmo PNG (molduras de barra, orbes, asas, botões, algarismos).
Consumir o atlas inteiro com `background-position` seria frágil e ilegível; o
HUD precisa de arquivos individuais com **tamanho nativo** conhecido.

Algoritmo (segmentação por alpha, sem modelo semântico):

1. `mask = alpha > 8` (`ALPHA_MIN`);
2. `scipy.ndimage.label` → componentes conexas;
3. `ndimage.find_objects` → bbox por componente;
4. área do componente calculada de verdade (`(sub == lab).sum()`) e **descartada
   se < `MIN_AREA = 400 px²`** — é o filtro de ruído;
5. recorte com folga `PAD = 2 px` em volta do bbox;
6. nome `slices/<grupo>/<atlas>_<NN>.png` (`NN` = índice na ordem
   `(y0, x0)`), e entrada em `manifest.json` com `file`, `atlas`, `box`, `w`, `h`,
   `area`.

Entradas: todos os `public/assets/ui/battle/*.png` (grupo `battle`) e todos os
`public/assets/ui/*.png` (grupo `core`). Resultado medido em disco:
**269 slices de `battle` + 423 de `core` = 692 elementos**.

`--contact-sheet` gera `public/assets/ui/_sheets/{battle,core}.png`;
`tools/make_review_sheets.py` gera as folhas temática `rev_deck`, `rev_fx`,
`rev_chrome` e as folhas `pick_*` — é por elas que cada chave da skin foi
escolhida visualmente em vez de por nome de arquivo (o nome do chunk não diz o
que o elemento é).

### Etapa 3 — `tools/build_ui_skin.py` *(ainda não escrito)*

Lê a tabela de chaves do contrato §2.1, copia o recorte correspondente de
`slices/` para `public/assets/ui/skin/<chave>.png` (trim de alpha já aplicado
pelo slicer) e grava o índice:

```json
{ "<chave>": { "file": "<chave>.png", "w": 123, "h": 45, "src": "core/xbattle_x_00.png" } }
```

É a etapa que falta hoje: `tools/build_ui_skin.py` e `public/assets/ui/skin/`
não existem.

### Etapa 4 — aplicação (`styles.css`, `index.html`, `game.js`)

- **`styles.css`**: todas as variáveis `--skin-*` no `:root` (contrato §3) e
  aplicação via `border-image` / `background-image`. **Estado atual: não
  aplicado.**
- **`index.html`**: apenas *hooks* aditivos — `#ougi-banner`,
  `#kawarimi-flash`, `data-digits="true"` nos placares, `data-skin-banner`,
  `data-skin-frame`. Já presentes. Nenhum ID existente pode ser tocado.
- **`game.js`**: `renderSkinDigits`, `showOugiBanner`, `flashKawarimi`,
  `loadSkinManifest` (contrato §5). **Estado atual: ausentes.**

## 4. Mapa de equivalência: HUD MOBA ↔ elemento Storm

Tamanhos nativos medidos em `public/assets/ui/slices/manifest.json`.

| Slot da UI MOBA (DOM) | Chave da skin | Origem em `slices/` | Nativo | Observação |
|---|---|---|---|---|
| Top strip do HUD (`.hud-top-bar`) | `panel_silver` | `core/xcmn_base_04` | 64x74 | tile 9-slice da moldura da faixa |
| Time azul (faixa + placar) | `panel_blue` | `core/xcmn_base_02` | 64x74 | tile 9-slice, variante azul |
| Time vermelho (faixa + placar) | `panel_red` | `core/xcmn_base_01` | 64x74 | tile 9-slice, variante vermelha |
| Destaque / Awakening | `panel_orange` | `core/xcmn_base_05` | 64x74 | mesma família, tom quente |
| Modal (placar TAB, morte) | `panel_white` | `core/xcmn_base_06` | 64x74 | painel neutro claro |
| Mini-índices (`#hud-blue-icons`, `#hud-red-icons`) | `nameplate` | `core/xbattle_namebase_01` | 255x50 | barra de nome sob o retrato |
| Relógio (`#match-timer`, `#sb-clock`) | `digit_0..digit_9` + `digit_inf` | `core/xbattle_count_{00..09}`, `count_10` | 47–65 x 78–84 / 125x77 | `:` e `/` ficam como texto |
| Placar (`#score-blue`, `#score-red`, `#sb-score-*`) | `digit_0..digit_9` | idem | idem | mesma fonte de algarismos |
| Kill feed (`#kill-feed`) | `nameplate_alt` | `core/xbattle_namebase_00` | 255x49 | pastilha da linha de abate |
| Avatar do jogador (`#hud-player-portrait`) | `ring_avatar` | `core/xbattle_newgauge_08` | 74x74 | anel ao redor do retrato |
| Orbe de chakra (`#hud-ck-fill`) | `orb_dark` | `core/xbattle_newgauge_09` | 54x53 | cápsula do medidor |
| Barra de HP (`#hud-hp-fill`) | `bar_frame` + `bar_fill_hp` | `core/xbattle_newgauge_03` + `core/xbattle_gauge05_00` | 242x55 + **58x53** (ver §6) | moldura + preenchimento |
| Barra de chakra (`#hud-ck-fill`) | `bar_thin` | `core/xbattle_newgauge_02` | 63x31 | versão compacta da moldura |
| Slot Taijutsu (`#slot-atk`) | `icon_atk` | `core/xbattle_pad01_06` | 77x77 | exibido a 48px |
| Slot Ninjutsu primário (`#slot-q`) | `icon_q` | `core/xbattle_pad01_07` | 76x77 | selo de mão |
| Slot Ninjutsu secundário (`#slot-w`) | `icon_w` | `core/xbattle_pad01_03` | 77x77 | chama |
| Slot Kawarimi (`#slot-e`) | `icon_e` | `core/xbattle_pad01_01` | 77x77 | rolo/kunai |
| Slot Ougi (`#slot-r`) | `icon_r` | `core/xbattle_pad01_k_01` | 192x192 | soco vermelho, maior de todos |
| Slot Concentração (`#slot-c`) | `icon_c` | `core/xbattle_pad01_05` | 93x83 | selo hexagonal |
| Estado desabilitado / runa | `icon_rune` | `core/xbattle_pad01_g_00` | 148x148 | runa de despertar |
| Badges de botão dos slots | `btn_face_b/a/y/x` | `battle/battle_cmn_button00_00..03` | 71x71 | badges de face de botão |
| Selo "1P" (você é quem joga) | `badge_1p` | `battle/battle_xcmn_playere_fd_00` | 42x67 | mesmo prefixo de nome do asset descartado §5 — ver nota |
| Banner de centro (`#center-banner`) | `banner_combat` / `banner_tie` / `banner_win` / `banner_lose` | `core/xbattle_signal_fd00_00/01/06/07` | 175x72 / 176x73 / 85x88 / 84x85 | faixas "DÉBUT COMBAT", "ÉGALITÉ", "VICTOIRE", "DÉFAITE" |
| Card de morte (`#player-death-overlay`) | `panel_white` + `digit_*` | idem + `count_*` | 64x74 | painel + `#death-timer-num` vira dígitos |
| Scoreboard TAB (`#scoreboard-tab-overlay`) | `result_frame` | `core/xbattle_win00_03` | 497x94 | moldura do placar; `data-skin-frame="result"` já no DOM |
| Botão de sair/vitória do placar | `result_btn_red` | `core/xbattle_win00_00` | 128x79 | botão vítreo vermelho |
| Drawer de controles (`#controls-drawer`) | `panel_silver` + `result_btn_red` | `core/xcmn_base_04` + `core/xbattle_win00_00` | 64x74 + 128x79 | folha de teclas |
| Faixa de Ougi (`#ougi-banner`) | `ougi_bar` + `ougi_flare` | `battle/battle_xbattle_ougi00_01` + `..._05` | 159x60 + 240x72 | clarão por cima da faixa |
| Aura de despertar (`#hud-awakening-state`) | `flame_aura` | `core/xbattle_newgauge_06` | 249x107 | aura de fogo |
| Flash de Kawarimi (`#kawarimi-flash`) | `flame_aura` (recorte) + `swirl` | `core/xbattle_newgauge_06` + `core/xbattle_newgauge_04` | 249x107 + 55x58 | overlay de tela ~320ms |
| Contador de combo | `combo_digit_0..4` | `battle/battle_xbattle_combo00_00..09` | 68–85 x 104–112 | 10 recortes, ciano→vermelho |
| Botão de pausa | `btn_pause` | `core/xbattle_pad05_00` | 200x108 | |
| Anel de chakra | `aura_ring` | `core/xbattle_pad07_00` | 250x249 | |
| Cursor de alvo | `cursor` | `core/xbattle_cursor_00` | 44x44 | |
| Ícones de status (kill feed) | `status_*` | `core/xbattle_sicon00_*`, `xbattle_sicon01_*` | variável | soco, fogo, zzz, seta |

**Nota sobre `badge_1p`:** `core/xcmn_playere_fd_00` (63x47, cinzas de
dublagem) **não** é a origem. A origem é `battle/battle_xcmn_playere_fd_00`
(42x67), que vem do container `battle.xfbin` e é o selo "1P" desenhado. São
arquivos com nomes parecidos em origens diferentes — confundi-los é o erro
mais provável ao montar a tabela do builder.

## 5. Convenções de aplicação

### 5.1 `border-image` nos tiles 64x74

`xcmn_base_00..06` são **tiles de moldura de 64x74**, não painéis de tamanho
fixo. Aplicar como `background-size: 100% 100%` estica a arte e destrói os
detalhes de canto. O padrão correto é 9-slice:

```css
--skin-panel-blue: url("assets/ui/skin/panel_blue.png");
.hud-top-bar {
  border-image: var(--skin-panel-blue) 16 fill stretch;  /* 16 = ~25% de 64 */
  border-width: 16px;
}
```

O valor de `border-image-slice` sai da largura do tile (64 px de lado, 74 de
altura). O `fill` é obrigatório: sem ele só aparece a moldura, sem o miolo
transparente do painel. Contrato §3 proíbe `backdrop-filter`/blur em elemento
que tenha asset de moldura — a moldura original já carrega o vidro e a sombra.

### 5.2 Barras: moldura + preenchimento

Duas camadas, não uma imagem:

- **Moldura** = `border-image` de `bar_frame` (242x55) — o chanfro, os
  rebites, a sombra externa. Estática.
- **Preenchimento** = `background-image: var(--skin-bar-fill-hp)` com
  `background-size: 100% 100%`; a cor de time entra como `background-color`
  por baixo, sob o filtro. O JS continua mexendo só em `style.width`, o que o
  contrato §4 exige.

Isso mantém a barra legível em qualquer largura sem redesenhar nada.

### 5.3 Algarismos viram `<img>` por dígito

`xbattle_count_*` é um atlas com os algarismos desenhados do jogo, cada um com
peso e sombra próprios — não é fonte de texto. `renderSkinDigits(el, text)`
(contrato §5.1) troca `textContent` por uma sequência de
`<img class="skin-digit" src="assets/ui/skin/digit_N.png">`, deixando `:` e `/`
como texto. Alvos: `#match-timer`, `#score-blue`, `#score-red`,
`#sb-score-blue`, `#sb-score-red`, `#sb-clock`, `#death-timer-num` e
`#respawn-cd-${id}`.

Motivo prático: `textContent` numérico é lido por
`tools/test_e2e_suite.py`. Se o teste compara string, a substituição por `<img>`
pode quebrar a asserção — a implementação precisa manter o valor textual
acessível (`.alt`, `aria-label`, ou um nó de texto por dígito). **Não foi
verificado** qual dos dois o suíte exige; é o primeiro ponto a checar quando
`renderSkinDigits` for implementado.

### 5.4 Efeitos ligados: Ougi e Kawarimi

Dois hooks foram adicionados ao DOM e aguardam o motor:

| Hook | Efeito | Asset | Tempo |
|---|---|---|---|
| `#ougi-banner` | faixa + clarão de Ougi | `ougi_bar` + `ougi_flare` | ~1.4 s, em `executeSkill(..., 'r')` e ao entrar em awakening |
| `#kawarimi-flash` | overlay de tela com aura de fogo | `flame_aura` (+ `swirl`) | ~320 ms, em `executeSkill(..., 'e')` |

Ambos são puramente decorativos e não tocam em cooldown, dano ou IA.

### 5.5 Por que o atlas foi recortado

Repetindo o motivo da etapa 2 porque é a decisão de arquitetura central do
reskin: no APK, um PNG de UI carrega **várias texturas semeadas juntas** —
`xbattle_count.png` tem os 11 algarismos; `xbattle_pad01.png` tem todos os
ícones de slot; `xcmn_base.png` tem as 7 variantes de painel. Não existe
sprite-rect table legível para o navegador. Recortar gera arquivos com nome
semântico, tamanho nativo e bbox registrado, que é o que o CSS precisa.

## 6. Divergência detectada entre contrato e disco

O contrato §2.1 registra `bar_fill_hp` como `core/xbattle_gauge05_00` com
**156x18**. O slice real em `slices/manifest.json` é **58x53** (área 1162 px²) —
ou seja, `xbattle_gauge05` não é uma barra horizontal, e o preenchimento de HP
ainda **não tem origem confirmada**. Enquanto isso não for resolvido, ou o
builder aponta `bar_fill_hp` para outro recorte de `xbattle_newgauge_*`, ou a
barra de HP usa só a moldura + `background-color`. Registrado aqui como ponto
aberto, não como fato resolvido.

Os demais tamanhos da tabela do contrato conferem com o `manifest.json` medido.

## 7. Assets deliberadamente descartados

| Asset | O que é | Por que foi descartado |
|---|---|---|
| `battle/bigbat_xbattle_action00_fd_00` (256x73), `_01` (490x33) | prompt de console com a palavra **"ESCAPE"** | Texto de debug/console do jogo de luta. Não pertence a uma HUD de MOBA e nem é rádio para o jogador ler |
| `core/xcmn_choicebar00_00/01` (125x56, 125x98) | atlas de barra de escolha | Codifica opções de menu de seleção de personagem (1P/2P/CPU), sem equivalente no fluxo MOBA |
| `core/xcmn_hwindow00_00` (125x79) | janela de help/modal com padding | Padding/ruído de layout do menu; o miolo é quase todo transparente |
| `core/xadv_gauge_action*_fd_*` (17 recortes) | prompts de ação **em francês** | String de locale errada para o produto. `xadv_*` é o HUD de *advantage/online*, não o de battle 5v5 |
| `core/xbattle_spoiuchi_*` (2) e `battle/battle_xbattle_spoiuchi_00..20` (21) | cinzas de dublagem /Speak (falas dos ninjas) | Sprite de retrato de fala sem uso no HUD; ocupa o atlas e confunde a revisão visual |
| `core/xcmn_playere_fd_00..02` (3) | cinzas de dublagem do *core* | Idem — e tem o mesmo nome do asset que **é** usado (`battle/battle_xcmn_playere_fd_00`), ver §4 |
| `core/xbattle_combo00_00` (125x768) | atlas de combo do core | Recorte único, muito alto: indica atlas empacotado verticalmente que o slicer não separou em dígitos. Os dígitos de combo vêm de `battle/battle_xbattle_combo00_*` |
| Tudo que o filtro de área removeu | Componentes < 400 px² | Ruído de alpha, sujeira de descompressão NTP3 e respingo de borda |

## 8. Limitações conhecidas

1. **Recorte automático pode colar vizinhos.** A segmentação é por alpha e
   conectividade: se dois elementos do atlas se tocam ou se há um halo
   translúcido entre eles, eles viram um componente só.
   *Mitigação*: filtro `MIN_AREA = 400 px²` descarta a maioria do ruído, e a
   revisão visual via `tools/make_review_sheets.py` + `--contact-sheet` é
   obrigatória antes de fechar a tabela de chaves. Não há detecção automática de
   "elemento colado" — é inspeção manual.
2. **Sem sprite-rect table no chunk NUCC.** O chunk `nuccChunkTexture` traz a
   textura inteira; a posição de cada sub-elemento não está em campo legível.
   Portanto o recorte é **geométrico** (bbox por alpha), não semântico. O nome
   do chunk não descreve a peça — daí a revisão visual.
3. **Assets decodificados em 512/1024 px.** `extract_moba_assets.decode_ntp3_texture`
   recebe `max_dim` e as texturas grandes são reduzidas (`extract_ui_battle.py`
   usa `MAX_DIM = 1024`). Ícones exibidos acima do nativo ficam borrados. A
   política do contrato é exibir a 48 px justamente para caber dentro do nativo
   da maioria dos ícones — mas `icon_r` (192x192) e `flame_aura` (249x107) têm
   resolução de origem desconhecida após o teto.
4. **HCA ainda não é decodificável.** Os bancos de SFX do APK são ADX2 com
   streams HCA (codec proprietário, tags `ciph`/`comp`/`Wfmt`/`loop`). Não há
   decodificador no repositório, então o reskin **não toca em áudio**: o Web
   Audio procedural de `game.js` continua sendo a via prática. Um "soco Ougi com
   som do APK" está bloqueado por isso.
5. **Texturas com alpha parcial.** `ALPHA_MIN = 8` define opaco; bordas com
   alpha entre 1 e 7 são cortadas e depois o `PAD = 2 px` tenta recuperar. Em
   bordas com halo suave isso produz um leve recorte. Não medido: o quão
   visível isso é no HUD final.
6. **Colisão de nomes entre `core/` e `battle/`.** `xcmn_playere_fd`,
   `xbattle_spoiuchi` e `xbattle_combo00` existem nos dois grupos. A tabela de
   chaves do builder precisa sempre dizer o grupo, senão pega a origem errada.

## 9. Como rodar

```powershell
# Etapa 1 — decodifica battle.xfbin, bigbat.xfbin e xbattle_startmenu.xfbin
python tools/extract_ui_battle.py

# Etapa 2 — recorta os atlas em 692 elementos e grava manifest.json
python tools/slice_ui_atlas.py
python tools/slice_ui_atlas.py --contact-sheet     # contact sheets p/ revisão
python tools/slice_ui_atlas.py --only newgauge     # debug: só um atlas

# Revisão visual obrigatória antes de escolher chaves
python tools/make_review_sheets.py                 # -> public/assets/ui/_sheets/

# Etapa 3 — pacote curado (AINDA NÃO ESCRITO)
python tools/build_ui_skin.py

# Etapa 4 — servidor local
python tools/server.py
```

## 10. Como validar

```powershell
# 0 erros de console no boot
python tools/verify_browser_runtime.py

# 34/34 testes E2E (o contrato §4 é inviolável por causa disto)
python tools/test_e2e_suite.py
```

Ordem obrigatória: um `verify_browser_runtime.py` limpo **antes** do suíte,
porque falha de carregamento de asset (`skin.json`/PNG 404) só aparece no log de
console.

Checklist manual do reskin, além do automatizado:

- [ ] `public/assets/ui/skin/skin.json` existe e o console loga a contagem
- [ ] nenhum recorte colou vizinho (comparar com `_sheets/rev_*.png`)
- [ ] `.hud-top-bar` continua com altura computada < 52 px **com** a moldura
- [ ] `#cd-${slot}` continua recebendo o `conic-gradient` original
- [ ] kill feed continua com `.fade-out` aos 4.2 s e remoção aos 4.7 s
- [ ] `#death-timer-num` e `#respawn-cd-*` legíveis (ver §5.3)

## 11. Referências

| Documento | Conteúdo |
|---|---|
| `docs/UI_SKIN_CONTRACT.md` | contrato do reskin — fonte de verdade |
| `APK_REVERSE.md` §3 | formatos CPK / CRILAYLA / NUCC / NTP3 / HCA |
| `public/assets/ui/slices/manifest.json` | índice autoritativo de bbox e tamanho nativo |
| `public/assets/ui/_sheets/*.png` | folhas de revisão visual |