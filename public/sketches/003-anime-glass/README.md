# Variante 3: Anime Cinematic Glass

## Stance
O que o HUD atual QUERIA ser, executado com disciplina: glassmorphism ink + UM acento (chakra cyan), ouro reservado para momentos dramáticos (ult/despertar), cantos cortados diagonais (clip-path) pra energia anime.

## Escolhas-chave
- **Layout:** módulos flutuantes centrados (não full-width), cada painel com corte diagonal próprio; deck com clip-path duplo
- **Tipografia:** Barlow Condensed + Noto Sans JP para kanji de skill no kill-feed (螺旋丸) e banner de ougi (奥義・螺旋丸)
- **Cor:** cyan como sistema; dourado = drama (ult slot, chip de despertar, ougi banner)
- **Interação:** anel do avatar girando, shimmer na barra de chakra, slots com canto chanfrado, flare de ougi

## Trade-offs
- **Forte:** o mais "vivo" e cinematográfico; mistura os assets hero (crest, flare, ring) com CSS moderno sem brigar
- **FracO:** `backdrop-filter: blur` custa GPU em máquina fraca (precisa fallback); mais opinativo que o 2

## Melhor para
O momento " gameplay de anime" — clipes, kills montados, trailer. É o HUD que rende screenshot de Twitter.
