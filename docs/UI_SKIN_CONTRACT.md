# UI_SKIN_CONTRACT — contrato de reskin Storm (fonte de verdade)

Todos os agentes deste reskin implementam **contra este arquivo**. Se algo não
está aqui, não improvise: acrescente aqui primeiro.

## 1. Regra de origem

- **Pixels visuais** vêm exclusivamente de recortes dos atlas já decodificados em
  `public/assets/ui/slices/` (origem: APK `installTimeDisc.awb`,
  `data/interface/battle/**`, decodificados por `tools/extract_ui_battle.py` +
  `tools/slice_ui_atlas.py`).
- CSS posiciona e dimensiona; nada de desenho, SVG ou emoji inventado no HUD.
- Liberado para complementar: tipografia premium via CDN (política já usada para
  o three.js) e ícones de terceiros — **apenas** se nenhum asset original servir.

## 2. Pacote de skin

`tools/build_ui_skin.py` lê a tabela abaixo, copia cada recorte para
`public/assets/ui/skin/<chave>.png` (trim alpha já aplicado pelo slicer) e grava
`public/assets/ui/skin/skin.json`:

```json
{ "<chave>": { "file": "<chave>.png", "w": 123, "h": 45, "src": "core/xbattle_x_00.png" } }
```

### 2.1 Tabela de chaves (chave → recorte em `slices/`)

Todas **verificadas visualmente** em `public/assets/ui/_sheets/`:

| chave | recorte | px | uso |
|---|---|---|---|
| `panel_blue` | `core/xcmn_base_02` | 64x74 | painel de time azul / moldura 9-slice |
| `panel_red` | `core/xcmn_base_01` | 64x74 | painel de time vermelho |
| `panel_silver` | `core/xcmn_base_04` | 64x74 | painel neutro do deck |
| `panel_white` | `core/xcmn_base_06` | 64x74 | painel de modal (placar, morte) |
| `panel_orange` | `core/xcmn_base_05` | 64x74 | destaque / awakening |
| `nameplate` | `core/xbattle_namebase_01` | 255x50 | barra de nome dos mini-índices |
| `nameplate_alt` | `core/xbattle_namebase_00` | 255x49 | variante de nome |
| `digit_0..digit_9` | `core/xbattle_count_{01,02,03,04,00,08,05,09,06,07}` | var. | algarismos do placar/relógio |
| `digit_inf` | `core/xbattle_count_10` | 125x77 | símbolo infinito |
| `icon_atk` | `core/xbattle_pad01_06` | 77x77 | Taijutsu (soco) |
| `icon_q` | `core/xbattle_pad01_07` | 76x77 | Ninjutsu primário (selo de mão) |
| `icon_w` | `core/xbattle_pad01_03` | 77x77 | Ninjutsu secundário (chama) |
| `icon_e` | `core/xbattle_pad01_01` | 77x77 | Kawarimi (rolo/kunai scroll) |
| `icon_r` | `core/xbattle_pad01_k_01` | 192x192 | Ougi ultimate (soco vermelho) |
| `icon_c` | `core/xbattle_pad01_05` | 93x83 | Concentração de chakra (selo hexagonal) |
| `icon_rune` | `core/xbattle_pad01_g_00` | 148x148 | runa de despertar / desabilitado |
| `ring_avatar` | `core/xbattle_newgauge_08` | 74x74 | anel do avatar do jogador |
| `orb_dark` | `core/xbattle_newgauge_09` | 54x53 | orbe de chakra |
| `bar_frame` | `core/xbattle_newgauge_03` | 242x55 | moldura da barra de vitais |
| `bar_thin` | `core/xbattle_newgauge_02` | 63x31 | barra compacta (secundária) |
| `flame_aura` | `core/xbattle_newgauge_06` | 249x107 | aura de despertar |
| `swirl` | `core/xbattle_newgauge_04` | 55x58 | voluta ornamental |
| `bar_fill_hp` | `core/xbattle_gauge05_00` | 156x18 | preenchimento de barra (texturiz. auth.) |
| `ougi_bar` | `battle/battle_xbattle_ougi00_01` | 159x60 | faixa de Ougi |
| `ougi_flare` | `battle/battle_xbattle_ougi00_05` | 240x72 | clarão de Ougi |
| `btn_face_b/a/y/x` | `battle/battle_cmn_button00_00..03` | 71x71 | badges de botão (mapeia slots) |
| `badge_1p` | `battle/battle_xcmn_playere_fd_00` | 42x67 | selo "1P" (você) |
| `combo_digit_0..4` | `battle/battle_xbattle_combo00_00..09` | var. | contador de combo (ciano→vermelho) |

### 2.2 Chaves verificadas por `tools/build_ui_skin.py`

Confirmadas visualmente em `public/assets/ui/skin/_skin_sheet.png` (57 chaves no
pacote). As candidatas da versão anterior desta seção estavam erradas: os recortes
`_00/_01/_06/_07` de `xbattle_signal_fd00` são **fragmentos de palavra**
("DÉBUT", "COMBA", "O", "K"), não faixas; `xbattle_win00_00` é uma nuvem
ornamental, não um botão.

| chave | recorte final | px | o que é |
|---|---|---|---|
| `banner_combat` | `core/xbattle_win00_03` | 497x94 | faixa de energia azul (abertura de combate) |
| `banner_tie` | `core/xbattle_signal_fd00_05` | 155x41 | faixa "ÉGALITÉ" (verde) |
| `banner_win` | `core/xbattle_win01_00` | 512x128 | faixa "GANADOR" |
| `banner_lose` | `core/xcmn_result_fd00_02` | 408x100 | faixa "VERSAGT" em moldura ciano |
| `result_frame` | `core/xcmn_result_fd00_00` | 504x100 | painel de resultado em moldura laranja |
| `result_btn_red` | `battle/battle_cmn_button00_08` | 69x68 | botão/badge vermelho |
| `status_fist` | `core/xbattle_sicon00_03` | 49x41 | status: soco |
| `status_flame` | `core/xbattle_sicon00_01` | 48x48 | status: fogo |
| `status_stun` | `core/xbattle_sicon00_00` | 48x48 | status: atordoado (fumaça) |
| `status_boost` | `core/xbattle_sicon00_04` | 48x36 | status: seta de buff |
| `cursor` | `core/xbattle_cursor_00` | 44x44 | cursor de alvo |
| `btn_pause` | `core/xbattle_pad05_00` | 200x108 | botão de pausa |
| `aura_ring` | `core/xbattle_pad07_00` | 250x249 | anel de chakra |

Correções aplicadas na 2.1 durante a conferência da `_skin_sheet.png` (as
linhas da 2.1 devem ser lidas com estas substituições):

- `swirl`: `core/xbattle_newgauge_04` (círculo branco liso, indecifável)
  → `core/xbattle_newgauge_05` (voluta dourada, 47x36).
- `bar_fill_hp`: `core/xbattle_gauge05_00` (faisca de fogo)
  → `core/xadv_gauge00_07` (barra horizontal 300x70, textura de preenchimento).
- `icon_atk` ⇄ `icon_e`: `icon_atk` passa a `core/xbattle_pad01_00` (soco /
  Taijutsu, 97x97) e `icon_e` passa a `core/xbattle_pad01_06` (rolo/kunai,
  77x77). Antes os dois estavam trocados.

Limitações conhecidas do atlas (não há recorte melhor):

- `combo_digit_1` aponta para `battle/battle_xbattle_combo00_01`, que é um "7":
  nenhum dos atlases `battle_xbattle_combo00..04` possui o algarismo "1".
  Se o contador mostrar valor 1, reaproveitar `digit_1`.
- `badge_1p` é o glifo "1" de `battle_xcmn_playere_fd_00` (não "1P").
- `bar_thin` é um rolo ornamental dourado (63x31), não uma barra preenchível.
- `result_btn_red` e `btn_face_b` são visualmente parecidos (69x68 vs 71x71),
  arquivos distintos.

## 3. Contrato CSS (custom properties em `:root`)

`styles.css` deve declarar, no topo, todas as variáveis:

```css
:root{
  --skin-url: "assets/ui/skin/";
  --skin-panel-blue:   var(--skin-url) panel_blue.png;
  --skin-panel-red:    var(--skin-url) panel_red.png;
  --skin-panel-silver: var(--skin-url) panel_silver.png;
  --skin-panel-white:  var(--skin-url) panel_white.png;
  --skin-panel-orange: var(--skin-url) panel_orange.png;
  --skin-nameplate:    var(--skin-url) nameplate.png;
  --skin-bar-frame:    var(--skin-url) bar_frame.png;
  --skin-bar-thin:     var(--skin-url) bar_thin.png;
  --skin-bar-fill-hp:  var(--skin-url) bar_fill_hp.png;
  --skin-ring-avatar:  var(--skin-url) ring_avatar.png;
  --skin-orb-dark:     var(--skin-url) orb_dark.png;
  --skin-flame-aura:   var(--skin-url) flame_aura.png;
  --skin-ougi-bar:     var(--skin-url) ougi_bar.png;
  --skin-ougi-flare:   var(--skin-url) ougi_flare.png;
  --skin-swirl:        var(--skin-url) swirl.png;
}
```

Regras de aplicação:

- Painéis/molduras usam `border-image` com `fill` (`border-image-slice` a partir
  da largura do tile, ver §2.1) — nunca `background` esticado sem `slice`.
- Barras de vitais: moldura = `border-image` de `bar_frame`; preenchimento =
  `background-image: var(--skin-bar-fill-hp)` com `background-size: 100% 100%`
  e cor de team aplicada como `background-color` sob o filtro.
- Ícones de habilidade: `<img class="ability-icon">` com `image-rendering:auto`,
  tamanho exibido **48px** (matem 1:1 do nativo quando possível).
- Proibido `backdrop-filter`/blur em elementos que tenham asset de moldura.

## 4. Contrato DOM (inviolável — 34 testes E2E dependem disso)

**IDs existentes não podem ser removidos, renomeados nem reordenados**:
`#game-canvas`, `#lobby-screen`, `#hud-screen`, `#roster-grid`,
`#lobby-blue-team`, `#lobby-red-team`, `#detail-portrait`, `#detail-name`,
`#detail-role`, `#detail-title`, `#detail-apk-meta`, `#detail-stats-deck`,
`#detail-skills`, `#detail-anms`, `#btn-start-match`, `#btn-open-studio`,
`#btn-toggle-wireframe`, `#btn-toggle-pose`, `.hud-top-bar`, `#score-blue`,
`#score-red`, `#hud-blue-icons`, `#hud-red-icons`, `#match-timer`,
`#kill-feed`, `#center-banner`, `#world-labels`, `#minimap-canvas`,
`#hud-player-portrait`, `#hud-player-lvl`, `#hud-hp-fill`, `#hud-hp-text`,
`#hud-ck-fill`, `#hud-ck-text`, `#hud-kda`, `#hud-awakening-state`,
`#slot-atk|#slot-q|#slot-w|#slot-e|#slot-r|#slot-c`,
`#cd-atk|#cd-q|#cd-w|#cd-e|#cd-r`, `#controls-drawer`, `#btn-help-controls`,
`#btn-close-controls`, `#btn-cam-mode`, `#btn-toggle-scoreboard`,
`#btn-back-lobby`, `#player-death-overlay`, `#death-timer-num`,
`#death-progress-fill`, `#scoreboard-tab-overlay`, `#sb-tbody-blue`,
`#sb-tbody-red`, `#sb-score-blue`, `#sb-score-red`, `#sb-clock`,
`#studio-modal`, `#btn-close-studio`.

Invariantes visuais mantidas:
- `.hud-top-bar` com altura computada **< 52px**.
- `#top-icon-${id}` continua contendo `.alive-dot` e `.respawn-countdown#respawn-cd-${id}`.
- `#cd-${slot}` continua recebendo `conic-gradient(rgba(0,0,0,0.78) ${pct}%, transparent 0%)`.
- `#kill-feed` recebe `.fade-out` aos 4.2s e é removido aos 4.7s.
- `.moba-ability-btn` continua com `data-slot` e clique → `executeSkill`.
- `#controls-drawer` alterna `.hidden`.

Novos hooks permitidos (aditivos): `.skin-digits`, `#ougi-banner`,
`#kawarimi-flash`, `data-skin` em qualquer elemento.

## 5. Contrato de motor (`game.js`)

Adições, sem alterar comportamento existente:

1. `renderSkinDigits(el, text)` — substitui o `textContent` numérico por
   `<img class="skin-digit" src="assets/ui/skin/digit_N.png">` por caractere
   (`:` e `/` ficam como texto). Usar em `#match-timer`, `#score-blue`,
   `#score-red`, `#sb-score-blue`, `#sb-score-red`, `#sb-clock`,
   `#death-timer-num` e em `#respawn-cd-${id}`.
2. `showOugiBanner()` — `#ougi-banner` fica visível ~1.4s com
   `background-image: var(--skin-ougi-bar)` + `var(--skin-ougi-flare)`;
   dispara em `executeSkill(..., 'r')` e ao entrar em awakening.
3. `flashKawarimi()` — `#kawarimi-flash` (overlay de tela com
   `var(--skin-flame-aura)`) por ~320ms em `executeSkill(..., 'e')`.
4. `loadSkinManifest()` — `fetch('assets/ui/skin/skin.json')` no boot; injeta
   `--skin-has-manifest: 1` no `:root` e loga contagem. Falha silenciosa.

Todo o resto do `game.js` (IA, movimento, câmera, combate, HUD sync) permanece
intacto.

## 6. Definição de pronto

```powershell
python tools/build_ui_skin.py          # gera skin/ + skin.json
python tools/verify_browser_runtime.py # 0 erros de console
python tools/test_e2e_suite.py         # 34/34
```
