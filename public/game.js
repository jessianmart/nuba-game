import * as THREE from 'three';
window.THREE = THREE;

// ============================================================================
// PV0.2 DEVICE DETECTION + PV0.3 INPUT STATE (Mobile Foundation — docs/PIVOT_MOBILE.md)
// ============================================================================
window.__DEVICE = {
  isTouch: ('ontouchstart' in window) || (navigator.maxTouchPoints || 0) > 0,
  isMobile: /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) ||
            ((navigator.maxTouchPoints || 0) > 0 && Math.min(screen.width, screen.height) < 820),
  dpr: window.devicePixelRatio || 1
};
if (window.__DEVICE.isTouch) document.body.classList.add('touch');

// PV0.3: estado unico de input analogico — teclado E touch escrevem aqui (§2.4 do plano)
window.INPUT = {
  moveX: 0, moveZ: 0,                 // joystick analogico -1..1 (moveZ +1 = frente)
  aimX: 0, aimZ: 0, aimActive: false, // drag-aim manual (vetor unitario)
  fire: false,                        // botao ATK touch segurado
  chakra: false                       // botao de concentrar chakra segurado (PV1.4)
};

// ============================================================================
// PV-A PERF INSTRUMENTATION (docs/PIVOT_MOBILE.md v2 §PV-A) — régua de perf
// Aditivo: nao altera DOM, nao altera combate, nao toca no contrato E2E.
// Uso: window.__PERF.snapshot() -> { fps:{avg,min,p5,frames}, drawCalls, ... }
// ============================================================================
const PERF = {
  frames: 0, fpsWindow: [], lastSample: performance.now(),
  worstFrameMs: 0, lastFrameMs: 0, frameRing: [],
  payloadBytes: 0, payloadEntries: 0
};
window.__PERF = {
  enabled: true,
  get fps() { return PERF.fpsWindow.length ? PERF.fpsWindow[PERF.fpsWindow.length - 1] : 0; },
  snapshot() {
    const w = PERF.fpsWindow.slice().sort((a, b) => a - b);
    const info = (typeof renderer !== 'undefined' && renderer.info) ? renderer.info : null;
    const mem = info ? info.memory : null;
    const rend = info ? info.render : null;
    return {
      ts: Date.now(),
      matchActive: (typeof matchActive !== 'undefined') ? matchActive : false,
      fps: {
        samples: w.length,
        avg: w.length ? +(w.reduce((s, v) => s + v, 0) / w.length).toFixed(1) : 0,
        min: w.length ? w[0] : 0,
        p5: w.length ? w[Math.max(0, Math.floor(w.length * 0.05))] : 0,
        max: w.length ? w[w.length - 1] : 0
      },
      frameMs: (() => {
        const r = PERF.frameRing.slice().sort((a, b) => a - b);
        return {
          worst: +PERF.worstFrameMs.toFixed(2),
          last: +PERF.lastFrameMs.toFixed(2),
          avg: r.length ? +(r.reduce((s, v) => s + v, 0) / r.length).toFixed(2) : 0,
          p95: r.length ? +r[Math.min(r.length - 1, Math.floor(r.length * 0.95))].toFixed(2) : 0,
          samples: r.length
        };
      })(),
      drawCalls: rend ? rend.calls : null,
      triangles: rend ? rend.triangles : null,
      geometries: mem ? mem.geometries : null,
      textures: mem ? mem.textures : null,
      programs: (info && info.programs) ? info.programs.length : null,
      pixelRatio: (typeof renderer !== 'undefined') ? renderer.getPixelRatio() : null,
      drawBuffer: (typeof renderer !== 'undefined') ? [renderer.domElement.width, renderer.domElement.height] : null,
      units: (typeof units !== 'undefined' && Array.isArray(units)) ? units.length : 0,
      vfx: (typeof vfxList !== 'undefined' && Array.isArray(vfxList)) ? vfxList.length : 0,
      projectiles: (typeof projectiles !== 'undefined' && Array.isArray(projectiles)) ? projectiles.length : 0,
      payload: { bytes: PERF.payloadBytes, entries: PERF.payloadEntries, mb: +(PERF.payloadBytes / 1048576).toFixed(2) },
      device: window.__DEVICE || null,
      viewport: { w: window.innerWidth, h: window.innerHeight }
    };
  },
  reset() { PERF.fpsWindow.length = 0; PERF.worstFrameMs = 0; PERF.frames = 0; }
};
// payload de rede (bytes transferidos) — medido pelo Resource Timing API
try {
  const res = performance.getEntriesByType('resource');
  PERF.payloadEntries = res.length;
  PERF.payloadBytes = res.reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0);
} catch (err) { /* Resource Timing indisponivel */ }

// ============================================================================
// PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) — joystick + cluster
// ============================================================================
window.__cameraMode = () => cameraMode; // PV1.5a: leitura E2E do modo de câmera
// CHARACTER SKILL KITS (Authentic Naruto Ultimate Ninja Storm Movesets)
// ============================================================================
const HERO_KITS = {
  '1nrt': {
    atk: { name: 'Combo Uzumaki + Kunai', desc: 'Sequência de 4 golpes Taijutsu + arremesso de Kunai', cd: 0.42, cost: 0 },
    q:   { name: 'Rasengan!', desc: 'Avança com esfera espiral de chakra causando alto dano e knockback', cd: 6.0, cost: 25, dmg: 250, color: 0x00d4ff, type: 'dash_aoe' },
    w:   { name: 'Kage Bunshin no Jutsu', desc: 'Invoca Clones das Sombras que atacam inimigos próximos', cd: 8.0, cost: 20, dmg: 160, color: 0xff9900, type: 'clone_burst' },
    e:   { name: 'Kawarimi (Substituição)', desc: 'Troca de lugar com um tronco e teleporta atrás do alvo', cd: 10.0, cost: 15, dmg: 0, color: 0xa3e635, type: 'kawarimi' },
    r:   { name: 'Oodama Rasengan + Kyuubi', desc: 'Explosão massiva de Chakra da Raposa de 9 Caudas + Despertar', cd: 22.0, cost: 50, dmg: 480, color: 0xff3b00, type: 'ultimate' }
  },
  '1ssk': {
    atk: { name: 'Uchiha Taijutsu + Shuriken', desc: 'Golpes velozes com arremesso triplo de Shuriken', cd: 0.38, cost: 0 },
    q:   { name: 'Chidori (Mil Pássaros)', desc: 'Investida relâmpago perfurante de altíssima velocidade', cd: 4.8, cost: 25, dmg: 235, color: 0x60a5fa, type: 'dash_aoe' },
    w:   { name: 'Katon: Gokakyu no Jutsu', desc: 'Dispara uma imensa Bola de Fogo explosiva à distância', cd: 6.5, cost: 20, dmg: 220, color: 0xff5500, type: 'fireball' },
    e:   { name: 'Sharingan Kawarimi', desc: 'Evade o ataque com Sharingan e contra-ataca pelas costas', cd: 8.5, cost: 15, dmg: 70, color: 0xef4444, type: 'kawarimi' },
    r:   { name: 'Kirin + Marca da Maldição', desc: 'Invoca relâmpago celestial em área + Despertar Nível 2', cd: 20.0, cost: 50, dmg: 470, color: 0x818cf8, type: 'ultimate' }
  },
  '1skr': {
    atk: { name: 'Punho de Chakra Concentrado', desc: 'Golpes pesados com impacto sísmico', cd: 0.44, cost: 0 },
    q:   { name: 'Oukahou (Impacto da Flor)', desc: 'Salta e esmaga o solo, lançando inimigos ao ar (Stun)', cd: 6.5, cost: 25, dmg: 205, color: 0xff5c8a, type: 'slam_aoe' },
    w:   { name: 'Ninjutsu Médico (Cura em Área)', desc: 'Restaura HP seu e de todos os aliados próximos', cd: 11.0, cost: 30, dmg: 300, color: 0x4ade80, type: 'heal_aoe' },
    e:   { name: 'Kawarimi no Jutsu', desc: 'Substituição ninja rápida com impulso de velocidade', cd: 8.5, cost: 15, dmg: 0, color: 0xa3e635, type: 'kawarimi' },
    r:   { name: 'Força de Uma Centena (Byakugou)', desc: 'Terremoto devastador em área + Regeneração Suprema', cd: 22.0, cost: 50, dmg: 400, color: 0xf43f5e, type: 'ultimate' }
  },
  '1kks': {
    atk: { name: 'Kunai Relâmpago + Taijutsu', desc: 'Cortes precisos de Jonin com Kunai eletrificada', cd: 0.38, cost: 0 },
    q:   { name: 'Raikiri (Corte Relâmpago)', desc: 'Atravessa inimigos em linha reta com lâmina elétrica', cd: 6.0, cost: 25, dmg: 265, color: 0x38bdf8, type: 'dash_aoe' },
    w:   { name: 'Suiton: Suiryudan no Jutsu', desc: 'Dispara um Dragão de Água teleguiado que empurra rivais', cd: 7.0, cost: 20, dmg: 200, color: 0x0ea5e9, type: 'fireball' },
    e:   { name: 'Raiton Kage Bunshin', desc: 'Substituição com clone elétrico que paralisa quem estiver perto', cd: 9.0, cost: 15, dmg: 90, color: 0x60a5fa, type: 'kawarimi' },
    r:   { name: 'Kamui (Mangekyo Sharingan)', desc: 'Distorção espacial que suga e explode inimigos na área', cd: 22.0, cost: 50, dmg: 460, color: 0xa855f7, type: 'ultimate' }
  },
  '1roc': {
    atk: { name: 'Punho Forte Acelerado', desc: 'Velocidade extrema de chutes e socos corpo-a-corpo', cd: 0.28, cost: 0 },
    q:   { name: 'Konoha Senpuu (Furacão da Folha)', desc: 'Chute giratório ciclônico que atinge todos ao redor', cd: 3.8, cost: 20, dmg: 135, color: 0x22c55e, type: 'spin_aoe' },
    w:   { name: 'Omote Renge (Lótus Primária)', desc: 'Investida ultrarrápida com impacto meteórico no chão', cd: 5.5, cost: 20, dmg: 180, color: 0x4ade80, type: 'dash_aoe' },
    e:   { name: 'Retirada Pesos de Treino', desc: 'Teleporta em velocidade pura deixando pós-imagem', cd: 7.5, cost: 15, dmg: 0, color: 0x86efac, type: 'kawarimi' },
    r:   { name: 'Ura Renge (Oito Portões Internos)', desc: 'Abre os Portões de Chakra: velocidade e dano absurdos', cd: 20.0, cost: 50, dmg: 470, color: 0xef4444, type: 'ultimate' }
  },
  '1itc': {
    atk: { name: 'Shuriken Uchiha + Corvos', desc: 'Ataques elegantes intercalados com ilusões de corvos', cd: 0.38, cost: 0 },
    q:   { name: 'Amaterasu (Chamas Negras)', desc: 'Incendeia a área alvo com chamas negras inapagáveis', cd: 7.0, cost: 30, dmg: 300, color: 0x991b1b, type: 'slam_aoe' },
    w:   { name: 'Katon: Gokakyu + Clone Explosivo', desc: 'Dispara fogo e explode clones em área', cd: 8.0, cost: 25, dmg: 170, color: 0xef4444, type: 'fireball' },
    e:   { name: 'Genjutsu de Corvos', desc: 'Desfaz o corpo em uma revoada de corvos e reaparece atrás', cd: 9.0, cost: 15, dmg: 60, color: 0xa855f7, type: 'kawarimi' },
    r:   { name: 'Tsukuyomi + Susanoo', desc: 'Prende todos os rivais próximos em Genjutsu letal', cd: 24.0, cost: 50, dmg: 500, color: 0xdc2626, type: 'ultimate' }
  },
  '1gar': {
    atk: { name: 'Rajada de Areia', desc: 'Ondas de areia que atacam à meia distância', cd: 0.45, cost: 0 },
    q:   { name: 'Sabaku Kyuu (Caixão de Areia)', desc: 'Prende e esmaga inimigos na área com areia implacável', cd: 7.0, cost: 25, dmg: 190, color: 0xd97706, type: 'slam_aoe' },
    w:   { name: 'Suna no Tate (Escudo Absoluto)', desc: 'Cria barreira de areia que absorve dano e explode', cd: 10.0, cost: 25, dmg: 80, color: 0xf59e0b, type: 'spin_aoe' },
    e:   { name: 'Substituição de Areia', desc: 'Desmancha em areia e emerge em posição segura', cd: 9.0, cost: 15, dmg: 0, color: 0xfbbf24, type: 'kawarimi' },
    r:   { name: 'Sabaku Taisou + Shukaku', desc: 'Tsunami gigante de areia que devasta toda a arena central', cd: 24.0, cost: 50, dmg: 430, color: 0xb45309, type: 'ultimate' }
  },
  '1hnt': {
    atk: { name: 'Punho Gentil (Juken)', desc: 'Golpes de palma que drenam Chakra do oponente', cd: 0.36, cost: 0 },
    q:   { name: 'Shugohakke Rokujuyonsho', desc: 'Dança de lâminas de chakra em 360 graus ao redor de Hinata', cd: 5.0, cost: 25, dmg: 140, color: 0xa78bfa, type: 'spin_aoe' },
    w:   { name: 'Punho dos Leões Gêmeos', desc: 'Avança com leões de chakra azul/roxo nos punhos', cd: 8.0, cost: 20, dmg: 165, color: 0x8b5cf6, type: 'dash_aoe' },
    e:   { name: 'Byakugan Kawarimi', desc: 'Visão de 360° antecipa o golpe e reposiciona instantaneamente', cd: 8.0, cost: 15, dmg: 0, color: 0xc4b5fd, type: 'kawarimi' },
    r:   { name: 'Oito Trigramas: Leões Gêmeos Supremos', desc: 'Explosão de chakra puro que zera a defesa inimiga', cd: 22.0, cost: 50, dmg: 440, color: 0x7c3aed, type: 'ultimate' }
  },
  '1nej': {
    atk: { name: 'Juken: Golpe de Tenketsu', desc: 'Ataques cirúrgicos nos pontos de chakra', cd: 0.35, cost: 0 },
    q:   { name: 'Hakkeshō Kaiten (Rotação)', desc: 'Gira em alta velocidade repelindo projéteis e causando dano', cd: 5.2, cost: 25, dmg: 135, color: 0x60a5fa, type: 'spin_aoe' },
    w:   { name: 'Hakke Kuusho (Palma de Ar)', desc: 'Dispara um canhão de vácuo comprimido à distância', cd: 6.0, cost: 20, dmg: 150, color: 0x38bdf8, type: 'fireball' },
    e:   { name: 'Byakugan Evasão', desc: 'Teleporta para as costas do inimigo vulnerável', cd: 8.0, cost: 15, dmg: 0, color: 0x818cf8, type: 'kawarimi' },
    r:   { name: 'Oito Trigramas: 64 Golpes', desc: 'Domo dos Oito Trigramas que desfere 64 golpes fatais', cd: 22.0, cost: 50, dmg: 450, color: 0x3b82f6, type: 'ultimate' }
  },
  '1jry': {
    atk: { name: 'Taijutsu Eremita dos Sapos', desc: 'Golpes pesados de longo alcance e cabeleira de agulhas', cd: 0.44, cost: 0 },
    q:   { name: 'Katon: Gamayu Endan', desc: 'Sopro gigantesco de óleo de sapo em chamas em cone', cd: 6.5, cost: 25, dmg: 210, color: 0xf97316, type: 'fireball' },
    w:   { name: 'Hari Jizo (Escudo de Espinhos)', desc: 'Cabelo endurecido envolve Jiraiya e perfura quem encostar', cd: 9.0, cost: 25, dmg: 150, color: 0xf43f5e, type: 'spin_aoe' },
    e:   { name: 'Kawarimi do Sapo', desc: 'Substituição ninja deixando um sapo invocador', cd: 9.0, cost: 15, dmg: 0, color: 0x4ade80, type: 'kawarimi' },
    r:   { name: 'Chou Oodama Rasengan + Modo Sennin', desc: 'Esfera colossal de Rasengan Eremita que varre a arena', cd: 23.0, cost: 50, dmg: 490, color: 0xef4444, type: 'ultimate' }
  },
  '1tnd': {
    atk: { name: 'Taijutsu com Selo de Chakra', desc: 'Socos devastadores que canalizam chakra concentrado no ponto de impacto', cd: 0.40, cost: 0 },
    q:   { name: 'Rakanken (Punho Sismico)', desc: 'Punho de chakra que racha o chao e arremessa inimigos na area', cd: 5.5, cost: 25, dmg: 240, color: 0x22c55e, type: 'dash_aoe' },
    w:   { name: 'Shosen Jutsu (Chakra Medico)', desc: 'Espirais de chakra verde ferem inimigos e recompõem o vigor da Hokage', cd: 8.0, cost: 20, dmg: 120, color: 0x14b8a6, type: 'spin_aoe' },
    e:   { name: 'Kawarimi da Quinta', desc: 'Substituicao ninja deixando um tronco selado', cd: 9.0, cost: 15, dmg: 0, color: 0x4ade80, type: 'kawarimi' },
    r:   { name: 'Byakugo: Sozo Saisei (Renascimento da Criacao)', desc: 'O Selo da Centopeia libera forca sobre-humana e regeneracao total', cd: 24.0, cost: 50, dmg: 460, color: 0x10b981, type: 'ultimate' }
  },
  '1orc': {
    atk: { name: 'Kusanagi: Lamina Serpente', desc: 'Estocadas rapidas da espada amaldicoada com alcance serpenteante', cd: 0.42, cost: 0 },
    q:   { name: "Sen'nejashu (Cobras Ocultas)", desc: 'Multiplicas cobras explode dos bracos e cacam o inimigo mais proximo', cd: 5.0, cost: 25, dmg: 200, color: 0x84cc16, type: 'fireball' },
    w:   { name: 'Kusanagi no Tsurugi (Estocada Longa)', desc: 'Avanco perfurante da lamina que atravessa a defesa', cd: 7.5, cost: 20, dmg: 180, color: 0xa3e635, type: 'dash_aoe' },
    e:   { name: 'Kawarimi de Cobra', desc: 'Substituicao deixando uma cobra de cobertura', cd: 9.0, cost: 15, dmg: 0, color: 0x4ade80, type: 'kawarimi' },
    r:   { name: 'Yamata no Jutsu (Hydra de Oito Cabecas)', desc: 'A serpente de oito cabecas domina a arena com presas venenosas', cd: 25.0, cost: 50, dmg: 470, color: 0x65a30d, type: 'ultimate' }
  }
};

// ============================================================================
// LIGHTWEIGHT PROCEDURAL WEB AUDIO SYNTHESIZER
// ============================================================================
class SoundFX {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }
  init() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) this.ctx = new AC();
    }
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
  }
  playTone(freqStart, freqEnd, dur = 0.15, type = 'sawtooth', gainVal = 0.08) {
    if (!this.ctx || this.enabled === false) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freqStart, now);
    osc.frequency.exponentialRampToValueAtTime(Math.max(20, freqEnd), now + dur);
    gain.gain.setValueAtTime(gainVal, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + dur);
    osc.connect(gain).connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + dur);
  }
  hit() { this.playTone(220, 55, 0.09, 'triangle', 0.1); }
  click() { this.playTone(980, 640, 0.045, 'square', 0.05); }
  kick() { this.playTone(170, 40, 0.12, 'triangle', 0.12); }
  shuriken() { this.playTone(920, 280, 0.07, 'sawtooth', 0.07); }
  clink() { this.playTone(1350, 480, 0.06, 'sine', 0.09); }
  jutsu() {
    this.playTone(320, 880, 0.22, 'sawtooth', 0.09);
    setTimeout(() => this.playTone(640, 180, 0.25, 'sine', 0.09), 90);
  }
  kawarimi() {
    this.playTone(520, 260, 0.08, 'square', 0.08);
    setTimeout(() => this.playTone(160, 80, 0.12, 'triangle', 0.09), 60);
  }
  ultimate() {
    this.playTone(180, 960, 0.45, 'sawtooth', 0.12);
    setTimeout(() => this.playTone(960, 90, 0.55, 'sawtooth', 0.12), 200);
  }
  ko() {
    this.playTone(160, 35, 0.45, 'sawtooth', 0.16);
    setTimeout(() => this.playTone(85, 20, 0.65, 'triangle', 0.18), 120);
  }
  resurrect() {
    this.playTone(260, 880, 0.45, 'sine', 0.14);
    setTimeout(() => this.playTone(520, 1400, 0.55, 'sawtooth', 0.12), 150);
  }
}
const sfx = new SoundFX();

// ==================== W1.1 ÁUDIO AUTÊNTICO (banks CRIWARE ACB do Storm) ====================
// 48 cues extraídas com tools/extract_audio.py -> public/assets/audio/decoded/*.ogg
const SKILL_SFX_MAP = {
  '1nrt': { q: 'rasen', w: 'zanei_open', e: 'shunshin', r: 'oogi' },
  '1ssk': { q: 'chidori', w: 'goukakyu', e: 'shunshin', r: 'oogi' },
  '1skr': { q: 'senpu', w: 'sabaku', e: 'shunshin', r: 'oogi' },
  '1kks': { q: 'raikiri', w: 'goheki', e: 'shunshin', r: 'oogi' },
  '1roc': { q: 'reppu', w: 'senpu', e: 'shunshin', r: 'oogi' },
  '1itc': { q: 'genjyutu', w: 'crow1', e: 'itachi_eye', r: 'oogi' },
  '1gar': { q: 'sabaku', w: 'gaara_sandhit', e: 'sabaku', r: 'oogi' },
  '1hnt': { q: 'housenka', w: 'byakugan', e: 'housenka', r: 'oogi' },
  '1nej': { q: 'kaiten', w: 'hakke_hit', e: 'kaiten', r: 'oogi' },
  '1jry': { q: 'goheki', w: 'fire_lp', e: 'shunshin', r: 'oogi' },
  '1tnd': { q: 'punch_hit', w: 'chakura_use', e: 'shunshin', r: 'oogi' },
  '1orc': { q: 'genjyutu', w: 'sword_hit', e: 'shunshin', r: 'oogi' }
};
const AUTH_SFX = {
  bank: {}, log: [], volume: 0.85, _last: {},
  THROTTLE: { ko: 450, down: 250, dash: 220, hit_s: 90, punch_hit: 110, kick_hit: 110, menu_slct: 60, kunai_swing: 90, shuriken: 110, kunai_hit: 60, ground_hit: 240, box_open: 1200, awake_off: 1500 },
  preload(name) {
    if (this.bank[name]) return this.bank[name];
    try { const a = new Audio('assets/audio/decoded/' + name + '.ogg'); a.preload = 'auto'; this.bank[name] = a; } catch (e) {}
    return this.bank[name] || null;
  },
  play(name, opts) {
    if (sfx.enabled === false) return false;
    const now = performance.now();
    const min = (opts && opts.min) || this.THROTTLE[name] || 70;
    if (this._last[name] && now - this._last[name] < min) return false;
    const a = this.preload(name);
    if (!a) return false;
    try { a.currentTime = 0; a.volume = this.volume * ((opts && opts.vol) || 1); const p = a.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
    this._last[name] = now;
    this.log.push(name); if (this.log.length > 14) this.log.shift();
    return true;
  },
  playAt(name, x, z, opts) { // W5: SFX autêntico posicionado — volume obedece à distância da câmera
    const cam = window.__camera;
    if (!cam) return this.play(name, opts);
    const d = Math.hypot(cam.position.x - (x || 0), cam.position.z - (z || 0));
    const base = (opts && opts.vol) || 1;
    const v = Math.pow(1 - Math.min(d / 60, 1), 1.2) * 1.4 * base;
    if (v < 0.06) return false;
    const played = this.play(name, { vol: Math.min(v, 1), min: opts && opts.min });
    if (played) { this.lastPlays = this.lastPlays || []; this.lastPlays.push({ n: name, v: Math.round(Math.min(v, 1) * 100) / 100, d: Math.round(d) }); if (this.lastPlays.length > 60) this.lastPlays.shift(); }
    return played;
  },
  pick(a, b) { this._alt = this._alt || {}; this._alt[a] = !this._alt[a]; return this._alt[a] ? a : b; } // W5: variação hit1/hit2
};
window.AUTH_SFX = AUTH_SFX; // W1.1: validação E2E
window.SKILL_SFX_MAP = SKILL_SFX_MAP;
// W6: música de fundo autêntica (bgm.awb do APK — modeslct no lobby, stage00
// leve na batalha). Settings FUNCIONAIS no painel PREFERÊNCIAS (toggle música,
// volume música, volume SFX) persistidos no perfil. Autoplay policy: o play()
// sem gesto é engolido; o unlock no primeiro pointerdown/keydown retoma.
const MUSIC = {
  el: null, track: null,
  baseVol: { menu: 0.7, battle: 0.38 },
  settings() {
    try {
      const d = loadProfileData();
      return { on: d.music !== false, vol: d.musicVol != null ? d.musicVol : 0.55 };
    } catch (e) { return { on: true, vol: 0.55 }; }
  },
  file(track) { return 'assets/audio/music/' + (track === 'battle' ? 'battle_stage00' : 'menu_modeslct') + '.ogg'; },
  play(track) {
    this.track = track;
    const s = this.settings();
    if (!s.on) { this.stop(); return false; }
    if (!this.el) { this.el = new Audio(); this.el.loop = true; }
    if (this.el.dataset.track !== track) { this.el.src = this.file(track); this.el.dataset.track = track; }
    const base = this.baseVol[track] != null ? this.baseVol[track] : 0.6;
    this.el.volume = Math.max(0, Math.min(1, base * s.vol));
    const p = this.el.play(); if (p && p.catch) p.catch(function () {});
    return true;
  },
  applySettings() {
    const s = this.settings();
    if (!s.on) { this.stop(); return; }
    if (!this.track) return;
    if (!this.el) { this.play(this.track); return; }
    const base = this.baseVol[this.track] != null ? this.baseVol[this.track] : 0.6;
    this.el.volume = Math.max(0, Math.min(1, base * s.vol));
    if (this.el.paused) { const p = this.el.play(); if (p && p.catch) p.catch(function () {}); }
  },
  stop() { if (this.el) { try { this.el.pause(); } catch (e) {} } }
};
window.MUSIC = MUSIC;
(function () { // W6: unlock da autoplay policy — retoma a música no 1º gesto
  const unlock = () => { MUSIC.applySettings(); window.removeEventListener('pointerdown', unlock); window.removeEventListener('keydown', unlock); };
  window.addEventListener('pointerdown', unlock);
  window.addEventListener('keydown', unlock);
})();
MUSIC.play('menu'); // W6: trilha do lobby (modeslct)

// ==================== TITLE SCREEN (W-MENU T1) ====================
// Ritual de entrada: o jogo abre na tela-titulo; o 1o clique/Enter atravessa pra Home.
function isTitleActive() {
  const t = document.getElementById('title-screen');
  return !!t && t.classList.contains('active');
}
function dismissTitle() {
  if (!isTitleActive()) return false;
  const t = document.getElementById('title-screen');
  t.classList.remove('active');
  document.getElementById('lobby-screen').classList.add('active');
  if (typeof setLobbyPage === 'function') setLobbyPage('play');
  try { sfx.init(); } catch (e) {}
  try { AUTH_SFX.play('menu_slct', { vol: 0.65 }); } catch (e) {}
  window.__TITLE_DISMISSED = performance.now();
  return true;
}
window.dismissTitle = dismissTitle; // EXPORT E2E
(function initTitleScreen() {
  const t = document.getElementById('title-screen');
  if (!t || t.dataset.wired) return;
  t.dataset.wired = '1';
  t.addEventListener('click', () => dismissTitle());
  window.addEventListener('keydown', (e) => {
    if (!isTitleActive()) return;
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); dismissTitle(); }
  });
})();


// W7: Framer Motion vanilla (dom/+esm vendored em assets/vendor) — spring
// física para os HUDs. Import dinâmico: se falhar, GSAP/CSS seguram o fallback.
let MOTION = null;
import('./assets/vendor/motion.esm.js')
  .then((m) => { MOTION = m; window.MOTION = m; })
  .catch(() => {});
function w7Spring(el, props, opts) {
  if (MOTION && MOTION.animate) {
    try {
      return MOTION.animate(el, props, Object.assign({ type: 'spring', stiffness: 420, damping: 30 }, opts || {}));
    } catch (e) { /* fallback abaixo */ }
  }
  if (window.gsap) {
    try {
      window.gsap.fromTo(el, { scale: 0.9, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.3, ease: 'back.out(1.8)', overwrite: 'auto' });
    } catch (e) { /* seco */ }
  }
  return null;
}
window.w7Spring = w7Spring;

// W5-F2: vozes de batalha POR HERÓI — bancos PL_1XXX do APK (21 cues/ninja:
// dano leve/médio/pesado, ataque leve/médio/ult, combo, despertar). Gate por
// unidade (1 voz/1.7s padrão), bots 45% mais esparsos, volume pelo playAt.
const VOICE_CUE_SETS = {
  dmg_s: ['S_PL_DmgS1', 'S_PL_DmgS2', 'S_PL_DmgS3'],
  dmg_m: ['S_PL_DmgM1', 'S_PL_DmgM2'],
  dmg_l: ['S_PL_DmgL1', 'S_PL_DmgL2'],
  atk_s: ['S_PL_AtkS1', 'S_PL_AtkS2', 'S_PL_AtkS3'],
  atk_m: ['S_PL_AtkM1', 'S_PL_AtkM2'],
  atk_l: ['S_PL_AtkL1', 'S_PL_AtkL2'],
  combo: ['S_PL_Combo1', 'S_PL_Combo2', 'S_PL_Combo3'],
  awake: ['S_PL_Awake'],
  catch: ['S_PL_Catch'],
  grdb: ['S_PL_GrdBrk1', 'S_PL_GrdBrk2'],
};
window.HERO_VOICE_MAP = {};
['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc'].forEach(function (id) { window.HERO_VOICE_MAP[id] = VOICE_CUE_SETS; });
window._voiceGate = {};
window.unitVoice = function (u, kind, opts) {
  if (!u || !u.heroId || !window.HERO_VOICE_MAP[u.heroId]) return false;
  if (!u.isPlayer && Math.random() < 0.45) return false;
  const set = window.HERO_VOICE_MAP[u.heroId][kind];
  if (!set || !set.length) return false;
  const now = performance.now();
  const min = (opts && opts.min !== undefined) ? opts.min : 1700;
  const key = u.id || u.heroId;
  if (window._voiceGate[key] && now - window._voiceGate[key] < min) return false;
  AUTH_SFX._vAlt = (AUTH_SFX._vAlt || 0) + 1;
  const cue = set[AUTH_SFX._vAlt % set.length];
  const played = AUTH_SFX.playAt('voice/' + u.heroId + '/' + cue, u.x, u.z, { vol: (opts && opts.vol) || 0.95 });
  if (played) window._voiceGate[key] = now;
  return played;
}; // W5-F2
(function () { const _cl = sfx.clink.bind(sfx); sfx.clink = function () { AUTH_SFX.play('menu_slct', { vol: 0.65 }); _cl(); }; })(); // W1.1: cliques de UI

// ============================================================================
// GLOBAL STATE & THREE.JS SCENE SETUP
// ============================================================================
const canvas = document.getElementById('game-canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
// PV3.1: quality governor automatico. Mobile tem dpr cap 1.25 e teto de 24 VFX
// (GPU fraca, tela pequena); desktop mantem 1.75. A preferencia do perfil manda
// ATE o cap — 'high' em mobile ainda vale 1.25, nunca 1.75.
window.__GOV = (function () {
  let pref = 'high';
  try {
    const d = loadProfileData();
    if (d && typeof d.quality === 'string') pref = d.quality;
  } catch (e) {}
  const mob = !!(window.__DEVICE && window.__DEVICE.isMobile);
  const CAPS = { low: 0.75, med: 1.25, high: 1.75 };
  const cap = mob ? Math.min(CAPS[pref] || 1.25, 1.25) : (CAPS[pref] || 1.75);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, cap));
  return { mobile: mob, pref: pref, dprCap: cap, vfxCap: mob ? 24 : Infinity };
})();
window.__renderer = renderer; // W1.2: validação E2E de qualidade
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c1626);
scene.fog = new THREE.FogExp2(0x0c1626, 0.0016);

const camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.5, 4000);
window.__camera = camera; // PV4.2: telemetria E2E da distancia da camera

// Lighting (Anime Cel-Shade bright sun + warm ambient fill)
const hemiLight = new THREE.HemisphereLight(0xfffaed, 0x334155, 1.35);
scene.add(hemiLight);
const dirLight = new THREE.DirectionalLight(0xfff7ed, 1.65);
dirLight.position.set(60, 140, 80);
scene.add(dirLight);
const ambLight = new THREE.AmbientLight(0xffffff, 0.35);
scene.add(ambLight);

const texLoader = new THREE.TextureLoader();
const modelCache = new Map();
const textureCache = new Map();

let rosterMeta = [];
let animationsData = {};
let skillVfxData = {};
let stage3DData = null;
let cachedStageGroup = null;

let selectedHeroId = '1nrt';
let isWireframe = false;
let lobbyPreviewPose = 'idle';
let lobbyPedestalGroup = new THREE.Group();
let lobbyHeroMesh = null;
scene.add(lobbyPedestalGroup);

let matchActive = false;
let matchEnding = false; // M5: guarda contra duplo disparo do fim de partida
let cameraMode = 'moba'; // 'moba' or 'thirdperson'
let tpCamYaw = 0;
let tpCamPitch = 0.32;
let arenaGroup = new THREE.Group();
scene.add(arenaGroup);

// ============================================================================
// ARENA CONFIG
// The Konoha training field (sd00a) values below are the ones the E2E suite
// asserts on, so they stay byte-for-byte identical. Other arenas override them
// from public/assets/data/arenas.json (built by tools/build_arenas_catalog.py,
// which reads the game's own StageAreaInfo table).
// ============================================================================
const ARENA_DEFAULTS = {
  id: 'sd00a',
  label: 'Campo de Treinamento',
  radius: 88,      // unit movement + knockback clamp
  cameraLimit: 92, // camera clamp (E2E: [-92, 92], Y >= 2.2)
  playerLimit: 93, // player sprint clamp
  pushLimit: 95,   // separation / knockback push clamp
  baseOffset: 74   // distance from centre to each team's sanctuary
};
let ARENA = Object.assign({}, ARENA_DEFAULTS);
let arenasCatalog = [];
let selectedArenaId = ARENA_DEFAULTS.id;

const clampArena = v => THREE.MathUtils.clamp(v, -ARENA.radius, ARENA.radius);
const clampPlayer = v => THREE.MathUtils.clamp(v, -ARENA.playerLimit, ARENA.playerLimit);
const clampPush = v => THREE.MathUtils.clamp(v, -ARENA.pushLimit, ARENA.pushLimit);
const clampCamera = v => THREE.MathUtils.clamp(v, -ARENA.cameraLimit, ARENA.cameraLimit);
const basePos = team => {
  if (team === 'blue' && ARENA.sanctuaryBlue) return { x: ARENA.sanctuaryBlue.x, z: ARENA.sanctuaryBlue.z };
  if (team === 'red' && ARENA.sanctuaryRed) return { x: ARENA.sanctuaryRed.x, z: ARENA.sanctuaryRed.z };
  const o = ARENA.baseOffset;
  return team === 'blue' ? { x: -o, z: -o } : { x: o, z: o };
};

const TARGET_KILLS = 30;

// ============================================================================
// PV1.1 MATCH CONFIGS (docs/PIVOT_MOBILE.md §2.2 — decisao #1: dm_3v3 e' o default)
// ============================================================================
const MATCH_CONFIGS = {
  dm_3v3:        { label: 'COMBATE 3v3', teamSize: 3, killTarget: 15, time: 180, respawn: 5,  overtime: 30, mode: 'dm' },
  dm_legacy_5v5: { label: 'COMBATE 5v5', teamSize: 5, killTarget: 30, time: 300, respawn: 6,  overtime: 60, mode: 'dm' },
  br_vila:       { label: 'REALEZA NA VILA', mode: 'br', arena: 'sa00z', players: 10, squad: 1, teamSize: 5, killTarget: null, time: 180, respawn: null, overtime: 0, zoneStart: 65, zoneMin: 6, zonePhases: 6, phaseTime: 25 }, // PV2 (§2.3) — layout real via br_vila_layout.json
  training:       { label: 'TREINO · CAMPO 3', mode: 'training', arena: 'sd00a', teamSize: 1, killTarget: null, time: null, respawn: 3, overtime: 0 }, // W-TRN: campo dos troncos — dano, skills, combos e Teste dos Sinos
};
let activeMatchCfg = MATCH_CONFIGS.dm_legacy_5v5;   // modo atual (global — playMatchIntro/tick leem)
let lastMatchConfigId = 'dm_legacy_5v5';           // revanche reusa o modo da partida anterior
let selectedModeId = 'dm_3v3';                      // default do lobby (decisao #1 do plano)
let brState = null;                                 // PV2: estado do BR (zona 結界/baús/vivos) — null fora do modo

// ============================================================================
// W-TRN TREINO · CAMPO DE TREINAMENTO (modo training) — arena sd00a, os tres
// troncos do Campo 3. Bonecos de treino (dummies) sem IA, medição de dano
// (números flutuantes + DPS + combos) e o TESTE DOS SINOS do Kakashi:
// 2 sinos antes do meio-dia (cada queda do Kakashi rende 1 sino — ele
// escapa com kawarimi e volta com HP cheio).
// ============================================================================
const TRN = {
  active: false,
  last: 0, total: 0, hits: 0, dps: 0,
  combo: 0, comboDmg: 0, bestCombo: 0, bestComboDmg: 0,
  firstHitAt: 0, lastHitAt: 0, bySkill: {},
  bells: 0,
  bell: { active: false, time: 0, limit: 180, dummy: null, startedAt: 0, bestSecs: null },
  dummies: [], _hudT: 0, hudDirty: true,
  DUMMY_HP: 12000, KAKASHI_HP: 2600, COMBO_WINDOW: 3.0,

  reset(announce) {
    this.last = 0; this.total = 0; this.hits = 0; this.dps = 0;
    this.combo = 0; this.comboDmg = 0; this.bestCombo = 0; this.bestComboDmg = 0;
    this.firstHitAt = 0; this.lastHitAt = 0; this.bySkill = {};
    const p = units.find(u => u.isPlayer);
    if (p) {
      p.hp = p.maxHp; p.chakra = p.maxChakra; p.hitstun = 0; p.deadTimer = 0; p.comboStep = 0;
      for (const k of Object.keys(p.cds)) p.cds[k] = 0;
    }
    if (announce) showBanner('TREINO RESETADO — CHAKRA E RECARGAS RESTAURADOS', 1500);
    this.hudDirty = true;
  },

  recordHit(attacker, target, dmg, skillName) {
    const now = performance.now();
    this.last = dmg; this.total += dmg; this.hits++;
    if (!this.firstHitAt) this.firstHitAt = now;
    if (now - (this.lastHitAt || 0) > this.COMBO_WINDOW * 1000) { this.combo = 0; this.comboDmg = 0; }
    this.combo++; this.comboDmg += dmg;
    if (this.combo > this.bestCombo) { this.bestCombo = this.combo; this.bestComboDmg = this.comboDmg; }
    this.lastHitAt = now;
    const key = (skillName || 'golpe').replace(/\s*\[.*\]\s*$/, '');
    const agg = this.bySkill[key] || (this.bySkill[key] = { n: 0, dmg: 0 });
    agg.n++; agg.dmg += dmg;
    if (target && !target.isPlayer) this.spawnFloat(target, dmg);
    this.hudDirty = true;
  },

  spawnFloat(target, dmg) {
    const layer = document.getElementById('dmg-float-layer');
    if (!layer || !camera) return;
    const v = new THREE.Vector3(target.x, 4.9, target.z).project(camera);
    if (v.z > 1) return;
    const sx = (v.x * (window.innerWidth / 2)) + (window.innerWidth / 2);
    const sy = -(v.y * (window.innerHeight / 2)) + (window.innerHeight / 2);
    const el = document.createElement('div');
    el.className = 'dmg-float' + (dmg >= 300 ? ' crit' : (dmg >= 180 ? ' heavy' : ''));
    el.textContent = String(dmg);
    el.style.left = sx + 'px';
    el.style.top = sy + 'px';
    layer.appendChild(el);
    setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 980);
  },

  async spawnDummy(heroId, x, z, opts = {}) {
    try {
      const h = rosterMeta.find(r => r.id === heroId) || rosterMeta[0];
      const mesh = await loadCharacter3DModel(h.id);
      const ringGeo = new THREE.RingGeometry(1.45, 1.85, 32);
      const ringMesh = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0xef4444, side: THREE.DoubleSide }));
      ringMesh.rotation.x = -Math.PI / 2;
      ringMesh.position.y = 0.08;
      mesh.add(ringMesh);
      const auraMesh = createHeroAwakeningAuraMesh(h.id, h.color || 0xff7b00);
      auraMesh.visible = false;
      mesh.add(auraMesh);
      mesh.position.set(x, 0, z);
      arenaGroup.add(mesh);
      const labelEl = document.createElement('div');
      labelEl.className = 'unit-label red';
      labelEl.innerHTML = `
        <span class="u-name">${opts.name || 'BONECO'} <small class="u-lvl">Nv.1</small></span>
        <div class="u-hp-bg"><div class="u-hp-fill" style="width:100%"></div></div>
        <div class="u-ck-bg"><div class="u-ck-fill" style="width:100%"></div></div>
      `;
      document.getElementById('world-labels').appendChild(labelEl);
      const hs = HERO_STATS[h.id] || HERO_STATS.__d;
      const hp = opts.hp || Math.round(hs.hp * HERO_HP_SCALE);
      const u = {
        id: 'trn_' + (opts.id || heroId) + '_' + Math.floor(Math.random() * 1e5),
        heroId: h.id, name: opts.name || h.name, portrait: h.portrait,
        team: 'red', isPlayer: false, isDummy: true, isKakashi: !!opts.isKakashi,
        mesh, auraMesh, labelEl, kit: HERO_KITS[h.id] || HERO_KITS['1nrt'],
        x, z, spawnX: x, spawnZ: z, rotY: Math.atan2(-x, -z),
        hp, maxHp: hp, chakra: 0, maxChakra: 100,
        level: 1, kills: 0, deaths: 0, assists: 0, killStreak: 0, lastKillAt: 0,
        speed: 0, state: 'idle', animTimer: 0, animDuration: 0,
        comboStep: 0, comboResetTimer: 0, awakenedTimer: 0, deadTimer: 0, hitstun: 0,
        spawnShield: 0,
        cds: { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 },
        aiTarget: null, aiStrafeDir: 1,
        recentAttackers: new Map()
      };
      units.push(u);
      return u;
    } catch (err) {
      console.warn('[TRN] falha ao spawnar boneco:', err && err.message);
      return null;
    }
  },

  async begin(CFG) {
    this.reset(false);
    this.bells = 0;
    this.bell.active = false;
    this.bell.dummy = null;
    this.dummies = [];
    // Player entra em campo PERTO dos troncos reais do Campo 3 (createTrainingPosts)
    const p = units.find(u => u.isPlayer);
    if (p) {
      p.x = -30; p.z = 2; p.spawnX = -30; p.spawnZ = 2;
      p.rotY = Math.atan2(-17.5 - p.x, 13 - p.z);
      if (p.mesh) p.mesh.position.set(p.x, 0, p.z);
    }
    // Bonecos EM FRENTE aos tres troncos de madeira do Kakashi
    const spots = [
      { x: -15, z: 9.2 },
      { x: -17.5, z: 10.8 },
      { x: -20, z: 9.4 }
    ];
    const names = ['樹 BONECO I', '樹 BONECO II', '樹 BONECO III'];
    const heroes = ['1skr', '1nej', '1hnt'];
    for (let i = 0; i < spots.length; i++) {
      const u = await this.spawnDummy(heroes[i], spots[i].x, spots[i].z, { name: names[i], hp: this.DUMMY_HP, id: 'p' + i });
      if (u) this.dummies.push(u);
    }
    this.updateHud();
  },

  toggleBell() { if (this.bell.active) this.endBell(false, true); else this.startBell(); },

  async startBell() {
    if (this.bell.active) return;
    if (this.bell.dummy) {
      const li = units.indexOf(this.bell.dummy);
      if (li >= 0) units.splice(li, 1);
      if (this.bell.dummy.labelEl) this.bell.dummy.labelEl.remove();
      if (this.bell.dummy.mesh) { try { arenaGroup.remove(this.bell.dummy.mesh); } catch (e) {} }
      this.bell.dummy = null;
    }
    const u = await this.spawnDummy('1kks', -17.5, 15.5, { name: '鈴 KAKASHI', hp: this.KAKASHI_HP, isKakashi: true, id: 'kks' }); // entre os troncos do Campo 3
    if (!u) { showBanner('TESTE DOS SINOS INDISPONÍVEL — TENTE NOVAMENTE', 1800); return; }
    this.bell.active = true;
    this.bell.time = this.bell.limit;
    this.bell.dummy = u;
    this.bell.startedAt = performance.now();
    this.bells = 0;
    AUTH_SFX.play('bell_jingle', { vol: 0.95, min: 1 });
    showBanner('鈴 TESTE DOS SINOS — DERRUBE O KAKASHI 2x ANTES DO MEIO-DIA!', 3200);
    this.hudDirty = true;
  },

  endBell(won, cancelled) {
    if (!this.bell.active) return;
    this.bell.active = false;
    if (won) {
      const secs = Math.round((performance.now() - this.bell.startedAt) / 1000);
      if (this.bell.bestSecs == null || secs < this.bell.bestSecs) this.bell.bestSecs = secs;
      AUTH_SFX.play('bell_jingle', { vol: 1, min: 1 });
      showBanner('鈴鈴 VOCÊ PASSOU NO TESTE DOS SINOS! 2 sinos em ' + secs + 's', 4200);
    } else if (!cancelled) {
      AUTH_SFX.play('time_up', { vol: 0.9 });
      showBanner('縛 MEIO-DIA! SEM OS DOIS SINOS — AMARRADO AO TRONCO ATÉ O ALMOÇO', 4200);
    } else {
      showBanner('TESTE DOS SINOS ENCERRADO', 1600);
    }
    this.hudDirty = true;
  },

  onDummyKO(target, attacker) {
    if (target.isKakashi && this.bell.active) {
      this.bells++;
      if (this.bells >= 2) {
        this.endBell(true);
      } else {
        AUTH_SFX.play('bell_jingle', { vol: 0.95, min: 1 });
        showBanner('鈴 SINO ' + this.bells + '/2! O KAKASHI ESCAPOU COM KAWARIMI E VOLTOU...', 3000);
      }
      this.hudDirty = true;
    }
  },

  tick(dt) {
    const p = units.find(u => u.isPlayer);
    if (p && p.deadTimer <= 0) p.chakra = Math.min(p.maxChakra, p.chakra + dt * 28);
    if (this.dummies) for (const d of this.dummies) if (d.deadTimer <= 0) d.chakra = 0; // W-TRN: boneco nao acumula chakra
    if (this.bell.dummy && this.bell.dummy.deadTimer <= 0) this.bell.dummy.chakra = 0; // W-TRN: idem Kakashi
    if (this.bell.active) {
      this.bell.time = Math.max(0, this.bell.time - dt);
      if (this.bell.time <= 0) this.endBell(false);
      else this.hudDirty = true;
    }
    if (this.firstHitAt) {
      const secs = Math.max(0.5, (performance.now() - this.firstHitAt) / 1000);
      this.dps = Math.round(this.total / secs);
      this.hudDirty = true;
    }
    this._hudT += dt;
    if (this.hudDirty && this._hudT >= 0.12) { this._hudT = 0; this.hudDirty = false; this.updateHud(); }
  },

  updateHud() {
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    set('trn-last', this.last);
    set('trn-combo', this.combo);
    set('trn-combo-dmg', this.comboDmg);
    set('trn-best-combo', this.bestCombo ? this.bestCombo + ' · ' + this.bestComboDmg : '0');
    set('trn-total', this.total);
    set('trn-dps', this.dps);
    set('trn-hits', this.hits);
    set('trn-bells', this.bells);
    const bt = document.getElementById('trn-bell-timer');
    if (bt) bt.textContent = this.bell.active ? Math.ceil(this.bell.time) + 's' : (this.bell.bestSecs != null ? 'rec ' + this.bell.bestSecs + 's' : '');
    const bb = document.getElementById('trn-bell-btn');
    if (bb) bb.textContent = this.bell.active ? 'ENCERRAR (B)' : 'TESTE DOS SINOS';
  }
};
// W-TRN: numero de dano flutuante — projeta world->tela a cada frame e desvanece
function TRN_FLOATT(target, dmg) {
  const layer = document.getElementById('dmg-float-layer');
  if (!layer || !window.__camera) return;
  const el = document.createElement('div');
  el.className = 'dmg-text' + (dmg >= 300 ? ' crit' : (dmg >= 180 ? ' high' : ''));
  el.textContent = String(dmg);
  el.style.left = '-100px';
  layer.appendChild(el);
  const t0 = performance.now();
  const life = 900;
  const step = () => {
    if (!el.isConnected) return;
    const t = (performance.now() - t0) / life;
    if (t >= 1) { el.remove(); return; }
    const v = new THREE.Vector3(target.x, 2.2, target.z);
    v.project(window.__camera);
    const w = layer.clientWidth, h = layer.clientHeight;
    el.style.left = ((v.x * 0.5 + 0.5) * w) + 'px';
    el.style.top = ((-v.y * 0.5 + 0.5) * h) + 'px';
    el.style.opacity = String(1 - t);
    el.style.transform = 'translate(-50%,-' + (50 + t * 90) + '%) scale(' + (1.15 - t * 0.25) + ')';
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
window.__TRN = TRN; // W-TRN: telemetria E2E
(function trnWireButtons() {
  const bb = document.getElementById('trn-bell-btn');
  if (bb) bb.addEventListener('click', () => { if (TRN.active) TRN.toggleBell(); });
  const rb = document.getElementById('trn-reset-btn');
  if (rb) rb.addEventListener('click', () => { if (TRN.active) TRN.reset(true); });
})();

let scoreBlue = 0;
let scoreRed = 0;
let matchTimeRemaining = 300; // 5:00
let matchOvertime = false; // T5: prorrogacao de 1 min no empate
let matchSuddenDeath = false; // T5: morte subita apos prorrogacao empatada
const HERO_HP_SCALE = 1.5; // T5: resistencia geral — HP x1.5 (demora mais a matar)
const HERO_DMG_SCALE = 0.9; // T5: dano global x0.9
let units = [];
let projectiles = [];
let vfxList = [];
let shrineOrb = null;
let shrineCooldown = 0;

const keys = {};

// ============================================================================
// P1 JUICE SYSTEM — Hitstop, Camera Shake, Kill Slow-Mo & FOV Punch
// Additive combat-feel layer (docs/UI_SKIN_CONTRACT.md §5 compliant): scales
// ONLY simulation cadence + camera offsets. Match clock, cooldowns, respawn
// timers and every DOM contract keep real dt (E2E suite safety).
// ============================================================================
const JUICE = {
  hitstop: 0,      // seconds of combat freeze remaining
  timeScale: 1,    // live sim timescale (0 during hitstop, <1 in slow-mo)
  slowTarget: 1,   // target timescale while the slow-mo window is active
  slowTimer: 0,    // seconds remaining of the slow-mo window
  trauma: 0,       // camera shake energy 0..1 (linear decay)
  fovPunch: 0,     // cinematic zoom-in punch (degrees, fast decay)
  t: 0,            // juice clock in real time (drives shake noise)
  enabled: true    // W1.2: master gate da página de Ajustes
};

function juiceHitstop(d) { if (JUICE.enabled === false) return; JUICE.hitstop = Math.max(JUICE.hitstop, d); }
function juiceShake(power) { if (JUICE.enabled === false) return; JUICE.trauma = Math.min(1, JUICE.trauma + power); }
function juiceFovPunch(deg) { if (JUICE.enabled === false) return; JUICE.fovPunch = Math.max(JUICE.fovPunch, deg); }
function juiceSlowmo(scale, dur) {
  if (JUICE.enabled === false) return; // W1.2
  if (scale < JUICE.slowTarget || JUICE.slowTimer <= 0) JUICE.slowTarget = scale;
  JUICE.slowTimer = Math.max(JUICE.slowTimer, dur);
}

// Procedural radial flash texture for impact pops (additive sprite VFX)
const flashTexture = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 2, 64, 64, 62);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.85)');
  g.addColorStop(0.75, 'rgba(255,255,255,0.25)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();

function updateJuice(dt) {
  JUICE.t += dt;
  if (JUICE.hitstop > 0) JUICE.hitstop = Math.max(0, JUICE.hitstop - dt);
  if (JUICE.slowTimer > 0) {
    JUICE.slowTimer = Math.max(0, JUICE.slowTimer - dt);
  } else {
    JUICE.slowTarget = 1;
  }
  const targetScale = JUICE.hitstop > 0 ? 0 : JUICE.slowTarget;
  // Snap hard INTO the freeze, breathe softly out of it
  const rate = targetScale < JUICE.timeScale ? 45 : 6.5;
  JUICE.timeScale += (targetScale - JUICE.timeScale) * Math.min(1, dt * rate);
  JUICE.trauma = Math.max(0, JUICE.trauma - dt * 1.35);
  JUICE.fovPunch = Math.max(0, JUICE.fovPunch - dt * 30);
  // Cinematic zoom punch (48 = native PerspectiveCamera fov); W-SKL+ CINE
  // cut de ult contribui até 6 graus (autorrestaura: blend -> 0 = base)
  const fov = 48 - JUICE.fovPunch - ultCineBlend() * 6;
  if (camera.fov !== fov) {
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }
}

// Additive trauma shake applied AFTER the camera solves its target position.
// Offsets are re-clamped so the stage safety contract (Y >= 2.2, [-lim, lim])
// holds even mid-shake.
function applyCameraShake() {
  if (JUICE.trauma <= 0.001) return;
  const t2 = JUICE.trauma * JUICE.trauma;
  const tt = JUICE.t * 37.7;
  const amp = 2.1 * t2;
  camera.position.x += Math.sin(tt * 1.13 + 3.1) * amp;
  camera.position.y += Math.sin(tt * 1.71 + 1.7) * amp * 0.72;
  camera.position.z += Math.sin(tt * 0.97 + 5.9) * amp;
  camera.position.x = clampCamera(camera.position.x);
  camera.position.z = clampCamera(camera.position.z);
  camera.position.y = Math.max(2.2, camera.position.y);
}
let mouseDown = false;

// ============================================================================
// LOAD TEXTURE & 3D MODEL WITH GPU SKELETAL SKINNING
// ============================================================================
// PV-B.2: WebP first, PNG fallback. O .webp e gerado por tools/convert_webp.py
// (escada adaptativa com QA de delta). Se o .webp nao existir/errar, o MESMO objeto
// Texture recebe a imagem do .png original — nenhum material fica com textura quebrada.
function loadTex(url) {
  if (!url) return null;
  if (textureCache.has(url)) return textureCache.get(url);
  const webp = url.replace(/\.png$/i, '.webp');
  const t = (webp !== url)
    ? texLoader.load(webp, undefined, undefined, () => {
        // PV2-E: placeholder 1x1 enquanto o .png carrega — evita upload de imagem invalida
        const _ph = document.createElement('canvas'); _ph.width = 1; _ph.height = 1;
        t.image = _ph; t.needsUpdate = true;
        texLoader.load(url, (img) => { t.image = img; t.needsUpdate = true; });
      })
    : texLoader.load(url);
  t.colorSpace = THREE.SRGBColorSpace;
  t.flipY = false; // NUCC NTP3 UV coordinates are top-left origin
  t.wrapS = THREE.RepeatWrapping;
  t.wrapT = THREE.RepeatWrapping;
  t.userData.__url = url; // PV-B.3: permite liberar a textura ao trocar de arena
  textureCache.set(url, t);
  return t;
}

const gradientMap = (() => {
  const data = new Uint8Array([105, 175, 240, 255]);
  const tex = new THREE.DataTexture(data, 4, 1, THREE.RedFormat);
  tex.minFilter = THREE.NearestFilter;
  tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
})();

async function loadCharacter3DModel(heroId) {
  if (modelCache.has(heroId)) {
    return cloneCharacterModel(modelCache.get(heroId), heroId);
  }
  const res = await fetch(`assets/models/${heroId}.json?v=9`);
  const data = await res.json();
  modelCache.set(heroId, data);
  return cloneCharacterModel(data, heroId);
}

/**
 * Builds a true GPU-skinned THREE.SkinnedMesh + 20-bone THREE.Skeleton
 * using official Naruto Databook proportional heights baked into public/assets/models/*.json
 * and native forward kinematics coordinate spaces for exact nuccChunkAnm quaternion playback!
 */
function cloneCharacterModel(data, heroId) {
  const root = new THREE.Group();
  const inner = new THREE.Group();
  root.add(inner);

  const rawBones = data.bones || [];
  const scaledBonePos = rawBones.map(b => [b.pos[0], b.pos[1], b.pos[2]]);

  const bones = [];
  for (let i = 0; i < rawBones.length; i++) {
    const b = new THREE.Bone();
    b.name = rawBones[i].name;
    bones.push(b);
  }
  for (let i = 0; i < rawBones.length; i++) {
    const def = rawBones[i];
    const b = bones[i];
    const curP = new THREE.Vector3(scaledBonePos[i][0], scaledBonePos[i][1], scaledBonePos[i][2]);
    if (def.parent >= 0 && bones[def.parent]) {
      bones[def.parent].add(b);
      root.updateMatrixWorld(true);
      b.position.copy(bones[def.parent].worldToLocal(curP));
    } else {
      b.position.copy(curP);
      inner.add(b);
    }
    root.updateMatrixWorld(true);
  }

  root.updateMatrixWorld(true);
  const skeleton = new THREE.Skeleton(bones);
  const materials = [];

  // Authentic Storm Inverted-Hull Anime Cel-Shaded Outline Material
  const outlineMat = new THREE.MeshBasicMaterial({
    color: 0x141014,
    side: THREE.BackSide,
    wireframe: isWireframe
  });
  outlineMat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      `
      #include <begin_vertex>
      transformed += normal * 0.015;
      `
    );
  };
  materials.push(outlineMat);

  for (const sm of data.meshes) {
    const texPath = sm.texture ? `assets/${sm.texture}` : null;
    const mapTex = loadTex(texPath);
    const mat = new THREE.MeshToonMaterial({
      map: mapTex,
      gradientMap,
      side: THREE.DoubleSide,
      wireframe: isWireframe,
      alphaTest: 0.08
    });
    materials.push(mat);

    const geom = new THREE.BufferGeometry();
    const vCount = (sm.positions.length / 3) | 0;
    const posArr = new Float32Array(sm.positions);

    geom.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
    geom.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(sm.normals), 3));
    geom.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(sm.uvs), 2));
    geom.setIndex(sm.indices);

    let skinIdxArr = sm.skinIndices;
    let skinWgtArr = sm.skinWeights;
    if (!skinIdxArr || skinIdxArr.length !== vCount * 4) {
      skinIdxArr = new Uint16Array(vCount * 4);
      skinWgtArr = new Float32Array(vCount * 4);
      for (let v = 0; v < vCount; v++) {
        skinIdxArr[v * 4] = 2;
        skinWgtArr[v * 4] = 1.0;
      }
    } else {
      skinIdxArr = new Uint16Array(skinIdxArr);
      skinWgtArr = new Float32Array(skinWgtArr);
    }

    geom.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(skinIdxArr, 4));
    geom.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWgtArr, 4));

    const mesh = new THREE.SkinnedMesh(geom, mat);
    mesh.frustumCulled = false;
    inner.add(mesh);
    mesh.updateMatrixWorld(true);
    mesh.bind(skeleton);

    // Authentic Storm Cel-Shaded Outline Mesh
    const outlineMesh = new THREE.SkinnedMesh(geom, outlineMat);
    outlineMesh.frustumCulled = false;
    inner.add(outlineMesh);
    outlineMesh.updateMatrixWorld(true);
    outlineMesh.bind(skeleton);
  }

  // Authentic soft circular contact shadow beneath feet (from Storm APK)
  const shadowTex = loadTex('assets/skills/1efc_shadow02.png');
  const shadowGeo = new THREE.PlaneGeometry(2.7, 2.7);
  const shadowMat = new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    opacity: 0.80,
    depthWrite: false
  });
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.rotation.x = -Math.PI / 2;
  shadowMesh.position.y = 0.038;
  root.add(shadowMesh);

  const basePelvisPos = bones[1] ? bones[1].position.clone() : new THREE.Vector3(0, 2.3, 0);
  root.userData = {
    heroId: heroId || data.id,
    inner,
    bones,
    skeleton,
    materials,
    shadowMesh,
    baseScale: 1.0,
    basePelvisPos
  };
  return root;
}

// ============================================================================
// SKELETAL ANIMATION ENGINE (Faithful FK Quaternion Keyframes from nuccChunkAnm)
// ============================================================================
const _q0 = new THREE.Quaternion();
const _q1 = new THREE.Quaternion();
const _qTarget = new THREE.Quaternion();
const _vTarget = new THREE.Vector3();

function sampleAnimationCurve(heroId, clipName, timeVal, fps = null) {
  const heroAnms = animationsData[heroId] || animationsData['1nrt'];
  if (!heroAnms) return null;
  const clip = heroAnms[clipName] ||
               (clipName === 'charge' ? (heroAnms['charge'] || heroAnms['idle']) :
               (clipName === 'jutsu2' ? (heroAnms['jutsu2'] || heroAnms['jutsu']) :
               heroAnms['idle']));
  if (!clip) return null;
  const nFrames = clip.numFrames || 1;
  const effectiveFps = (fps !== null && fps !== undefined) ? fps : (clip.fps || 24);

  const rawFrame = timeVal * effectiveFps;
  let f0, f1, alpha;
  if (clip.loop) {
    const wrapped = ((rawFrame % nFrames) + nFrames) % nFrames;
    f0 = Math.floor(wrapped);
    f1 = (f0 + 1) % nFrames;
    alpha = wrapped - f0;
  } else {
    f0 = Math.min(nFrames - 1, Math.max(0, Math.floor(rawFrame)));
    f1 = Math.min(nFrames - 1, f0 + 1);
    alpha = Math.min(1.0, Math.max(0.0, rawFrame - f0));
  }

  let pelvisPos = null;
  if (clip.pelvisPos && clip.pelvisPos.length > 0) {
    const p0 = clip.pelvisPos[f0] || clip.pelvisPos[0];
    const p1 = clip.pelvisPos[f1] || p0;
    pelvisPos = [
      p0[0] + (p1[0] - p0[0]) * alpha,
      p0[1] + (p1[1] - p0[1]) * alpha,
      p0[2] + (p1[2] - p0[2]) * alpha
    ];
  }

  return { clip, f0, f1, alpha, pelvisPos };
}

// W-SKL+ TRAIL: rastro de mão/lâmina durante o cast — fiel ao nuccChunkTrail
// do APK (referência ao bone animado; o ribbon é procedural no engine Storm).
// W-SKL+ CINE: cut cinematográfico do ult — só player com coreografia
// autêntica (clip fps=60). Camera chunk do APK é stub de referência; o
// movimento reproduz o sabor Storm (aproximação baixa atrás do caster).
let ultCine = { active: false, t: 0, dur: 0 };
function ultCineBlend() {
  if (!ultCine.active) return 0;
  const ph = ultCine.t / ultCine.dur;
  if (ph < 0.24) return THREE.MathUtils.smoothstep(ph, 0, 0.24);
  if (ph < 0.62) return 1.0;
  return 1.0 - THREE.MathUtils.smoothstep(ph, 0.62, 1.0);
}

window.__CINE = () => ({ active: ultCine.active, b: +ultCineBlend().toFixed(3), fov: +camera.fov.toFixed(2), camY: +camera.position.y.toFixed(2) }); // W-SKL+ debug hook

const skillTrails = [];
const SKILL_TRAIL_MAP = {
  // Naruto
  '1nrt:q': { bones: [13], color: 0x00d4ff, width: 0.38 },
  '1nrt:atk': { bones: [13], color: 0xffa500, width: 0.28 },
  // Sasuke
  '1ssk:q': { bones: [9], color: 0x60a5fa, width: 0.40 },
  '1ssk:atk': { bones: [13], color: 0x818cf8, width: 0.28 },
  // Sakura
  '1skr:q': { bones: [13], color: 0xff5c8a, width: 0.42 },
  '1skr:atk': { bones: [13], color: 0xf43f5e, width: 0.30 },
  // Kakashi
  '1kks:q': { bones: [13], color: 0x38bdf8, width: 0.40 },
  '1kks:atk': { bones: [13], color: 0x93c5fd, width: 0.28 },
  // Rock Lee
  '1roc:q': { bones: [5, 8], color: 0x22c55e, width: 0.40 },
  '1roc:w': { bones: [9, 13], color: 0x4ade80, width: 0.38 },
  '1roc:atk': { bones: [13, 5], color: 0x86efac, width: 0.30 },
  // Itachi
  '1itc:q': { bones: [13], color: 0x991b1b, width: 0.38 },
  '1itc:atk': { bones: [13], color: 0xef4444, width: 0.26 },
  // Gaara
  '1gar:q': { bones: [13], color: 0xd97706, width: 0.45 },
  '1gar:atk': { bones: [13], color: 0xf59e0b, width: 0.32 },
  // Hinata
  '1hnt:q': { bones: [13], color: 0x8b5cf6, width: 0.35 },
  '1hnt:w': { bones: [9, 13], color: 0xa855f7, width: 0.42 },
  '1hnt:atk': { bones: [9, 13], color: 0xc084fc, width: 0.28 },
  // Neji
  '1nej:q': { bones: [9, 13], color: 0x38bdf8, width: 0.44 },
  '1nej:atk': { bones: [13], color: 0x67e8f9, width: 0.28 },
  // Jiraiya
  '1jry:q': { bones: [13], color: 0xf97316, width: 0.45 },
  '1jry:atk': { bones: [13], color: 0xfb923c, width: 0.34 },
  // Tsunade
  '1tnd:q': { bones: [5], color: 0x22c55e, width: 0.45 },
  '1tnd:atk': { bones: [13], color: 0x4ade80, width: 0.34 },
  // Orochimaru
  '1orc:q': { bones: [13], color: 0xa3e635, width: 0.36 },
  '1orc:w': { bones: [13], color: 0xc7d2fe, width: 0.38 },
  '1orc:atk': { bones: [13], color: 0x84cc16, width: 0.28 },
};
function startSkillTrail(unit, slot) {
  const cfg = SKILL_TRAIL_MAP[unit.heroId + ':' + slot];
  if (!cfg || !unit.mesh || !unit.mesh.userData.bones) return;
  const trailTex = loadTex('assets/skills/1efc_trl01.png');
  cfg.bones.forEach(bi => {
    const pts = [];
    const nSeg = 14;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(nSeg * 6), 3));
    const uvs = new Float32Array(nSeg * 4);
    for (let i = 0; i < nSeg; i++) {
      const u = i / (nSeg - 1);
      uvs[i * 4] = u; uvs[i * 4 + 1] = 0;
      uvs[i * 4 + 2] = u; uvs[i * 4 + 3] = 1;
    }
    geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
    const idx = [];
    for (let i = 0; i < nSeg - 1; i++) {
      const a = i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
    geo.setIndex(idx);
    const mat = new THREE.MeshBasicMaterial({
      map: trailTex,
      color: cfg.color,
      transparent: true,
      opacity: 0.88,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    arenaGroup.add(mesh);
    skillTrails.push({ unit, boneIdx: bi, pts, mesh, age: 0, dur: (unit.animDuration || 0.42) + 0.30, max: nSeg, width: cfg.width });
  });
}
function updateSkillTrails(dt) {
  for (let i = skillTrails.length - 1; i >= 0; i--) {
    const t = skillTrails[i];
    t.age += dt;
    const alive = t.age < t.dur * 0.7 && t.unit && t.unit.hp > 0 && t.unit.mesh && t.unit.mesh.userData.bones;
    if (alive) {
      const bone = t.unit.mesh.userData.bones[String(t.boneIdx)];
      if (bone) {
        t.unit.mesh.updateMatrixWorld(true);
        const wp = new THREE.Vector3();
        bone.getWorldPosition(wp);
        t.pts.unshift(wp);
        if (t.pts.length > t.max) t.pts.pop();
      }
    }
    if (t.age >= t.dur) {
      if (t.mesh.parent) t.mesh.parent.remove(t.mesh);
      t.mesh.geometry.dispose();
      t.mesh.material.dispose();
      skillTrails.splice(i, 1);
      continue;
    }
    const lifeLeft = Math.max(0, 1 - t.age / t.dur);
    t.mesh.material.opacity = lifeLeft * 0.9;
    const pos = t.mesh.geometry.attributes.position.array;
    const camPos = camera.position;
    for (let seg = 0; seg < t.max; seg++) {
      const p0 = t.pts[Math.min(seg * 2, t.pts.length - 1)];
      const o = seg * 6;
      if (!p0) { for (let k = 0; k < 6; k++) pos[o + k] = 0; continue; }
      const p1 = t.pts[Math.min(seg * 2 + 2, t.pts.length - 1)] || p0;
      const dir = new THREE.Vector3().subVectors(p1, p0);
      const toCam = new THREE.Vector3().subVectors(camPos, p0);
      const side = new THREE.Vector3().crossVectors(dir, toCam);
      if (side.lengthSq() < 1e-6) side.set(0, 1, 0); else side.normalize();
      const w = t.width * (1 - seg / t.max);
      pos[o] = p0.x + side.x * w; pos[o + 1] = p0.y + side.y * w; pos[o + 2] = p0.z + side.z * w;
      pos[o + 3] = p0.x - side.x * w; pos[o + 4] = p0.y - side.y * w; pos[o + 5] = p0.z - side.z * w;
    }
    t.mesh.geometry.attributes.position.needsUpdate = true;
  }
}

function animateCharacterRig(rig, state, time, animTimer = 0, animDuration = 0.42) {
  if (!rig || !rig.userData.bones) return;
  const b = rig.userData.bones;
  const inner = rig.userData.inner;
  const heroId = rig.userData.heroId || '1nrt';
  const basePelvisPos = rig.userData.basePelvisPos;

  inner.rotation.set(0, 0, 0);

  let clipKey = state;
  let isSpin = false;
  if (state === 'spin') {
    clipKey = 'jutsu';
    isSpin = true;
  } else if (state === 'charge') {
    clipKey = 'charge';
  } else if (!['idle', 'run', 'dash', 'attack', 'attack2', 'attack3', 'jutsu', 'jutsu2', 'ult', 'down', 'charge'].includes(state)) {
    clipKey = 'idle';
  }

  let timeVal = time;
  const isAction = ['attack', 'attack2', 'attack3', 'jutsu', 'jutsu2', 'ult', 'down'].includes(clipKey) || (clipKey === 'dash' && animTimer > 0);
  if (isAction) {
    const duration = animDuration > 0 ? animDuration : (state === 'ult' ? 1.15 : (state === 'jutsu2' ? 0.75 : (state === 'jutsu' ? 0.75 : (state === 'down' ? 1.5 : (state === 'dash' ? 0.35 : 0.42)))));
    const progress = THREE.MathUtils.clamp(1.0 - (animTimer / duration), 0.0, 1.0);
    const heroAnms = animationsData[heroId] || animationsData['1nrt'];
    const clip = heroAnms ? heroAnms[clipKey] : null;
    const totalClipDuration = clip ? (clip.numFrames / (clip.fps || 24)) : duration;
    if (clipKey === 'down' && progress >= 1.0) {
      // Freeze at final frame lying flat on the ground
      timeVal = Math.max(0, totalClipDuration - 0.001);
    } else {
      timeVal = progress * totalClipDuration;
    }
  } else if (clipKey === 'run') {
    // Fast ground ninja run stride cadence matching movement speed
    timeVal = time * 1.35;
  } else if (clipKey === 'dash') {
    // High speed aerial chakra dash
    timeVal = time * 1.55;
  } else if (clipKey === 'charge') {
    // Authentic chakra charge crouch stance (spk0)
    timeVal = time * 0.95;
  } else if (clipKey === 'idle') {
    timeVal = time * 0.95;
  }

  // 0.08s slerp cross-fade state management
  if (!rig.userData.fadeState) {
    rig.userData.fadeState = {
      lastClipKey: clipKey,
      timer: 0,
      duration: 0.08,
      prevQuats: Array.from({ length: 20 }, () => new THREE.Quaternion(0, 0, 0, 1)),
      prevPelvis: basePelvisPos.clone()
    };
  }
  const fs = rig.userData.fadeState;
  const lastTime = rig.userData.lastAnimTime !== undefined ? rig.userData.lastAnimTime : time;
  const frameDt = Math.max(0.001, Math.min(0.05, time - lastTime));
  rig.userData.lastAnimTime = time;

  if (clipKey !== fs.lastClipKey) {
    fs.timer = fs.duration;
    fs.lastClipKey = clipKey;
    if (b[1]) fs.prevPelvis.copy(b[1].position);
    for (let cb = 1; cb <= 19; cb++) {
      if (b[cb]) fs.prevQuats[cb].copy(b[cb].quaternion);
    }
  }

  const fadeActive = fs.timer > 0;
  const fadeAlpha = fadeActive ? THREE.MathUtils.clamp(1.0 - (fs.timer / fs.duration), 0.0, 1.0) : 1.0;
  if (fadeActive) {
    fs.timer = Math.max(0, fs.timer - frameDt);
  }

  const sample = sampleAnimationCurve(heroId, clipKey, timeVal);
  if (sample && sample.clip) {
    const { clip, f0, f1, alpha, pelvisPos } = sample;

    // 1. Sample pelvisPos [dx, y, dz] and apply to bones[1].position with crossfade
    if (pelvisPos) {
      _vTarget.set(
        basePelvisPos.x + pelvisPos[0],
        pelvisPos[1],
        basePelvisPos.z + pelvisPos[2]
      );
    } else {
      _vTarget.copy(basePelvisPos);
    }
    if (clipKey === 'charge') {
      _vTarget.y = Math.max(0.2, _vTarget.y - 0.22);
      _vTarget.z += 0.12;
    }
    if (b[1]) {
      if (fadeActive) {
        b[1].position.lerpVectors(fs.prevPelvis, _vTarget, fadeAlpha);
      } else {
        b[1].position.copy(_vTarget);
      }
    }

    // 2. Each bone cb (1..19) quaternions [qx, qy, qz, qw] sampled and slerped with crossfade
    if (clip.bones) {
      for (let cb = 1; cb <= 19; cb++) {
        if (!b[cb]) continue;
        const bKey = String(cb);
        const arr = clip.bones[bKey];
        if (arr && arr.length > 0) {
          const q0 = arr[f0] || arr[0];
          const q1 = arr[f1] || q0;
          _q0.set(q0[0], q0[1], q0[2], q0[3]);
          _q1.set(q1[0], q1[1], q1[2], q1[3]);
          _qTarget.slerpQuaternions(_q0, _q1, alpha);
          if (fadeActive) {
            b[cb].quaternion.slerpQuaternions(fs.prevQuats[cb], _qTarget, fadeAlpha);
          } else {
            b[cb].quaternion.copy(_qTarget);
          }
        }
      }
    }
  } else {
    if (b[1]) b[1].position.copy(basePelvisPos);
    for (let i = 1; i < b.length; i++) {
      b[i].quaternion.set(0, 0, 0, 1);
    }
  }

  if (isSpin) {
    inner.rotation.y = time * 20;
  }
}

// ============================================================================
// LOBBY & 3D PEDESTAL SETUP
// ============================================================================
function buildLobbyPedestal() {
  lobbyPedestalGroup.clear();
  const baseGeo = new THREE.CylinderGeometry(2.6, 3.1, 0.45, 32);
  const baseMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    metalness: 0.5,
    roughness: 0.35
  });
  const baseMesh = new THREE.Mesh(baseGeo, baseMat);
  baseMesh.position.y = -0.22;
  lobbyPedestalGroup.add(baseMesh);

  const ringGeo = new THREE.RingGeometry(2.35, 2.58, 48);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0xff7b00, side: THREE.DoubleSide });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.rotation.x = -Math.PI / 2;
  ringMesh.position.y = 0.02;
  lobbyPedestalGroup.add(ringMesh);
}

async function selectLobbyHero(heroId) {
  selectedHeroId = heroId;
  const hero = rosterMeta.find(h => h.id === heroId) || rosterMeta[0];
  if (!hero) return;

  document.querySelectorAll('.roster-card, .hero-card').forEach(el => {
    const isSel = el.dataset.id === heroId;
    el.classList.toggle('selected', isSel);
    el.classList.toggle('active', isSel);
  });

  document.getElementById('detail-portrait').src = hero.portrait;
  document.getElementById('detail-role').textContent = hero.role || 'Lutador / Rajada';
  document.getElementById('detail-name').textContent = hero.name;
  document.getElementById('detail-title').textContent = hero.title || hero.name;
  const metaEl = document.getElementById('detail-meta');
  if (metaEl) metaEl.textContent = `${hero.heightCm || 150} cm (Databook) • Dificuldade: ${hero.dif || '—'}`;

  // Update Stat Meters (Ataque, Defesa, Velocidade, Chakra)
  const sAtk = hero.atk || 4.5, sDef = hero.def || 4.0, sSpd = hero.spd || 4.0, sCk = hero.ck || 5.0;
  const elAtk = document.getElementById('stat-bar-atk');
  const elDef = document.getElementById('stat-bar-def');
  const elSpd = document.getElementById('stat-bar-spd');
  const elCk = document.getElementById('stat-bar-ck');
  if (elAtk) elAtk.style.width = `${(sAtk / 5) * 100}%`;
  if (elDef) elDef.style.width = `${(sDef / 5) * 100}%`;
  if (elSpd) elSpd.style.width = `${(sSpd / 5) * 100}%`;
  if (elCk) elCk.style.width = `${(sCk / 5) * 100}%`;

  const vAtk = document.getElementById('stat-val-atk');
  const vDef = document.getElementById('stat-val-def');
  const vSpd = document.getElementById('stat-val-spd');
  const vCk = document.getElementById('stat-val-ck');
  if (vAtk) vAtk.textContent = `${sAtk} / 5`;
  if (vDef) vDef.textContent = `${sDef} / 5`;
  if (vSpd) vSpd.textContent = `${sSpd} / 5`;
  if (vCk) vCk.textContent = `${sCk} / 5`;

  const kit = HERO_KITS[heroId] || HERO_KITS['1nrt'];
  const skillsEl = document.getElementById('detail-skills');
  skillsEl.innerHTML = [
    ['CLIQUE', kit.atk],
    ['Q', kit.q],
    ['E', kit.w],
    ['ESPAÇO', kit.e],
    ['R', kit.r]
  ].map(([k, sk]) => `
    <div class="skill-card">
      <span class="skill-slot-badge ${k === 'R' ? 'ult' : ''}">${k}</span>
      <div class="skill-content">
        <div class="skill-title-row">
          <span class="skill-name-txt">${sk.name}</span>
          <span class="skill-cd-badge">${sk.cost ? sk.cost + ' CK' : (sk.cd ? sk.cd + 's CD' : 'Combo de 3 Golpes')}</span>
        </div>
        <p class="skill-desc-txt">${sk.desc}</p>
      </div>
    </div>
  `).join('');

  const fichaDesc = document.getElementById('detail-ficha-desc');
  if (fichaDesc) fichaDesc.textContent = hero.desc || '';
  const fichaTags = document.getElementById('detail-ficha-tags');
  if (fichaTags) {
    fichaTags.innerHTML = [
      hero.jp,
      hero.clan ? `Clã ${hero.clan}` : '',
      hero.role
    ].filter(Boolean).map(t => `<span class="anm-tag">${t}</span>`).join('');
  }

  updateLobbyTeamsPreview(heroId);

  // Load 3D character onto pedestal
  if (lobbyHeroMesh) {
    lobbyPedestalGroup.remove(lobbyHeroMesh);
  }
  const model = await loadCharacter3DModel(heroId);
  model.rotation.y = 0.25;
  lobbyHeroMesh = model;
  lobbyPedestalGroup.add(lobbyHeroMesh);
}

function updateLobbyTeamsPreview(playerHeroId) {
  if (!Array.isArray(rosterMeta) || !rosterMeta.length) return; // P1 hardening: cold-load
  const others = rosterMeta.filter(h => h.id !== playerHeroId);
  const blueHeroes = [rosterMeta.find(h => h.id === playerHeroId) || rosterMeta[0], ...others.slice(0, 4)];
  const redHeroes = others.slice(4, 9);

  const squadSlot = (h, idx, side) => {
    const role = (h.role || 'Lutador').split('/')[0].trim();
    const isYou = side === 'blue' && idx === 0;
    const state = isYou ? 'VOCÊ' : (side === 'blue' ? 'PRONTO' : 'BOT');
    return `
      <div class="squad-slot ${isYou ? 'is-you' : ''}" title="${isYou ? 'VOCÊ: ' : ''}${h.name}">
        <img class="team-slot-icon" src="${h.portrait}" alt="${h.name}" />
        <div class="squad-meta">
          <span class="squad-name">${h.name}</span>
          <span class="squad-role">${role}</span>
        </div>
        <span class="squad-state ${isYou ? 'you' : (side === 'red' ? 'bot' : 'ready')}">${state}</span>
      </div>`;
  };

  document.getElementById('lobby-blue-team').innerHTML =
    blueHeroes.map((h, idx) => squadSlot(h, idx, 'blue')).join('');
  document.getElementById('lobby-red-team').innerHTML =
    redHeroes.map((h, idx) => squadSlot(h, idx, 'red')).join('');
}

// ============================================================================
// BUILD THE 3D KONOHA STAGE (sd00a)
// ============================================================================
const riverMaterials = [];
let leafParticlesGroup = null;
const LEAF_COUNT = 90;
const leafPositions = [];
const leafVelocities = [];

function createTrainingPosts() {
  const grp = new THREE.Group();
  const woodMat = new THREE.MeshLambertMaterial({ color: 0x854d0e }); // rich cedar wood
  const ropeMat = new THREE.MeshLambertMaterial({ color: 0xd97706 }); // rope twine
  const postPositions = [
    { x: -16, z: 12, rotZ: 0.04, h: 4.8 },
    { x: -18.5, z: 13.5, rotZ: -0.06, h: 5.2 },
    { x: -21, z: 12.2, rotZ: 0.02, h: 4.6 }
  ];
  for (const p of postPositions) {
    const postGeo = new THREE.CylinderGeometry(0.55, 0.65, p.h, 12);
    const postMesh = new THREE.Mesh(postGeo, woodMat);
    postMesh.position.set(p.x, p.h / 2, p.z);
    postMesh.rotation.z = p.rotZ;
    grp.add(postMesh);

    // Rope rings tied around posts (as seen in Team 7 bell test)
    for (let rh = 1.2; rh < p.h - 0.8; rh += 1.4) {
      const ropeGeo = new THREE.TorusGeometry(0.62, 0.06, 6, 16);
      const ropeMesh = new THREE.Mesh(ropeGeo, ropeMat);
      ropeMesh.rotation.x = Math.PI / 2;
      ropeMesh.position.set(p.x, rh, p.z);
      grp.add(ropeMesh);
    }
  }
  return grp;
}

function createKonohaLeafParticles() {
  const grp = new THREE.Group();
  const leafGeo = new THREE.PlaneGeometry(0.45, 0.35);
  const leafMat = new THREE.MeshBasicMaterial({
    color: 0x22c55e,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.75
  });
  leafPositions.length = 0;
  leafVelocities.length = 0;

  for (let i = 0; i < LEAF_COUNT; i++) {
    const m = new THREE.Mesh(leafGeo, leafMat.clone());
    if (Math.random() < 0.3) m.material.color.setHex(0xf59e0b);
    else if (Math.random() < 0.2) m.material.color.setHex(0x16a34a);

    const x = (Math.random() - 0.5) * 160;
    const y = 1.5 + Math.random() * 12;
    const z = (Math.random() - 0.5) * 160;
    m.position.set(x, y, z);
    grp.add(m);

    leafPositions.push(m);
    leafVelocities.push({
      vx: 3.5 + Math.random() * 4.5,
      vy: -0.8 - Math.random() * 0.8,
      vz: (Math.random() - 0.5) * 3.5,
      rotSpeedX: 2.0 + Math.random() * 4.0,
      rotSpeedY: 1.5 + Math.random() * 3.0
    });
  }
  return grp;
}

function updateKonohaLeaves(dt) {
  if (!leafParticlesGroup) return;
  for (let i = 0; i < leafPositions.length; i++) {
    const m = leafPositions[i];
    const v = leafVelocities[i];
    m.position.x += v.vx * dt;
    m.position.y += v.vy * dt;
    m.position.z += v.vz * dt;
    m.rotation.x += v.rotSpeedX * dt;
    m.rotation.y += v.rotSpeedY * dt;

    if (m.position.y < 0.4 || m.position.x > 85) {
      m.position.x = -85;
      m.position.y = 8 + Math.random() * 8;
      m.position.z = (Math.random() - 0.5) * 160;
    }
  }
}

function buildExtractedStageGroup() {
  if (cachedStageGroup) return cachedStageGroup;
  if (!stage3DData || !stage3DData.meshes) return null;

  riverMaterials.length = 0;
  const stgGrp = new THREE.Group();
  // NUCC stage coordinates are centimetres; each arena ships its own scale
  // (0.022 for sd00a, which maps it cleanly onto the MOBA arena units).
  const STAGE_SCALE = stage3DData.scale || 0.022;
  stgGrp.scale.set(STAGE_SCALE, STAGE_SCALE, STAGE_SCALE);
  stgGrp.position.set(0, 0.02, 0);

  for (const sm of stage3DData.meshes) {
    if (!sm.positions || sm.positions.length < 9) continue;
    const numVerts = (sm.positions.length / 3) | 0;
    let indices = sm.indices || [];
    if (indices.length > 0) {
      let needsFilter = false;
      for (let i = 0; i < indices.length; i++) {
        if (indices[i] >= numVerts || indices[i] < 0) {
          needsFilter = true;
          break;
        }
      }
      if (needsFilter) {
        const valid = [];
        for (let i = 0; i < indices.length - 2; i += 3) {
          const i1 = indices[i], i2 = indices[i + 1], i3 = indices[i + 2];
          if (i1 >= 0 && i1 < numVerts && i2 >= 0 && i2 < numVerts && i3 >= 0 && i3 < numVerts) {
            valid.push(i1, i2, i3);
          }
        }
        indices = valid;
      }
    }
    if (indices.length < 3) continue;

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(sm.positions), 3));
    geom.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(sm.normals), 3));
    geom.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(sm.uvs), 2));
    geom.setIndex(indices);

    const texPath = sm.texture ? `assets/${sm.texture}` : null;
    const mapTex = loadTex(texPath);
    if (mapTex) {
      mapTex.wrapS = THREE.RepeatWrapping;
      mapTex.wrapT = THREE.RepeatWrapping;
    }
    const mName = (sm.name || '').toLowerCase();
    const texName = (sm.texture || '').toLowerCase();
    const isSkyOrBack = mName.includes('dome') || mName.includes('bac');
    const isRiver = mName.includes('river') || texName.includes('river') || mName.includes('water') || texName.includes('water');
    const isFoliage = mName.includes('ki0') || mName.includes('kusa') || mName.includes('hana')
      || mName.includes('eda') || mName.includes('grass') || mName.includes('ha0')
      || mName.includes('tree') || mName.includes('plant')
      || texName.includes('1and') || texName.includes('and0') || texName.includes('alfa');

    let mat;
    if (isSkyOrBack) {
      mat = new THREE.MeshBasicMaterial({
        map: mapTex,
        side: THREE.DoubleSide,
        alphaTest: 0.12,
        depthWrite: false
      });
    } else if (isRiver) {
      mat = new THREE.MeshBasicMaterial({
        map: mapTex,
        color: 0x38bdf8,
        transparent: false,
        side: THREE.DoubleSide,
        depthWrite: true
      });
      riverMaterials.push(mat);
    } else if (isFoliage) {
      mat = new THREE.MeshLambertMaterial({
        map: mapTex,
        side: THREE.DoubleSide,
        alphaTest: 0.28,
        transparent: false
      });
    } else {
      mat = new THREE.MeshLambertMaterial({
        map: mapTex,
        side: THREE.DoubleSide,
        alphaTest: 0.08
      });
    }

    const mesh = new THREE.Mesh(geom, mat);
    mesh.name = sm.name || '';
    mesh.userData = { name: sm.name, texture: sm.texture };
    mesh.frustumCulled = false;
    if (isSkyOrBack) mesh.renderOrder = -100;
    stgGrp.add(mesh);
  }

  cachedStageGroup = stgGrp;
  return cachedStageGroup;
}

// ============================================================================
// ARENA SELECTION
// Each arena ships its own mesh map (public/assets/stage/arena/<id>.json, built
// by tools/build_arena.py) plus a playable radius in arenas.json. Radius drives
// the unit / camera / spawn clamps, so switching arenas rescales the whole fight.
// ============================================================================
function disposeStageGroup(grp, keepTextureUrls) {
  const keep = keepTextureUrls || null;
  grp.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (!m) continue;
        // PV-B.3: libera a textura do palco (o cache nunca era purgado -> VRAM crescia
        // a cada troca de arena). Texturas ainda em uso pela arena nova sao preservadas.
        const url = m.map && m.map.userData ? m.map.userData.__url : null;
        if (url && (!keep || !keep.has(url))) {
          try { m.map.dispose(); } catch (e) {}
          textureCache.delete(url);
        }
        if (m.dispose) m.dispose();
      }
    }
  });
}

async function applyArena(arenaId, opts = {}) {
  const entry = arenasCatalog.find(a => a.id === arenaId);
  selectedArenaId = arenaId;

  if (!entry) {
    // Fall back to the legacy single-map stage and the tuned Konoha numbers.
    ARENA = Object.assign({}, ARENA_DEFAULTS, { id: ARENA_DEFAULTS.id });
    return ARENA;
  }

  const radius = entry.radius || ARENA_DEFAULTS.radius;
  ARENA = Object.assign({}, ARENA_DEFAULTS, {
    id: entry.id,
    label: entry.label || entry.id,
    radius,
    cameraLimit: entry.cameraLimit !== undefined ? entry.cameraLimit : Math.round(radius * 1.045),
    playerLimit: entry.playerLimit !== undefined ? entry.playerLimit : Math.round(radius * 1.057),
    pushLimit: entry.pushLimit !== undefined ? entry.pushLimit : Math.round(radius * 1.08),
    baseOffset: entry.baseOffset !== undefined ? entry.baseOffset : Math.round(radius * 0.84),
    shape: entry.shape || 'box',
    cameraMaxY: entry.cameraMaxY || null,
    sanctuaryBlue: entry.sanctuaryBlue || null,
    sanctuaryRed: entry.sanctuaryRed || null,
    bounds: entry.bounds || null,
    lighting: entry.lighting || null
  });

  // Dynamically adjust lighting (indoor vs outdoor)
  if (entry.lighting) {
    if (entry.lighting.ambient !== undefined) ambLight.color.set(Number(entry.lighting.ambient));
    if (entry.lighting.ambientIntensity !== undefined) ambLight.intensity = entry.lighting.ambientIntensity;
    if (entry.lighting.directional !== undefined) dirLight.color.set(Number(entry.lighting.directional));
    if (entry.lighting.dirIntensity !== undefined) dirLight.intensity = entry.lighting.dirIntensity;
    if (entry.lighting.hemiIntensity !== undefined) hemiLight.intensity = entry.lighting.hemiIntensity;
  } else {
    ambLight.color.set(0xffffff);
    ambLight.intensity = 0.35;
    dirLight.color.set(0xfff7ed);
    dirLight.intensity = 1.65;
    hemiLight.intensity = 1.35;
  }

  // Load the arena map (mobile carrega a variante otimizada do Blender)
  const mapAsset = (entry.mapMobile && window.__DEVICE && window.__DEVICE.isMobile) ? entry.mapMobile : entry.map;
  if (mapAsset) {
    try {
      const res = await fetch(`assets/${mapAsset}?v=11`).then(r => r.json());
      if (res && res.meshes) {
        // PV3.2: telemetria de qual variante entrou (full vs .mobile.json)
        window.__ARENA_LOADED = { asset: String(mapAsset), meshes: res.meshes.length,
          isMobile: !!(window.__DEVICE && window.__DEVICE.isMobile), at: performance.now() };
        // PV-B.3: texturas da arena nova sao preservadas ao descartar o palco antigo
        const keepUrls = new Set();
        for (const sm of res.meshes) if (sm.texture) keepUrls.add(`assets/${sm.texture}`);
        if (cachedStageGroup) disposeStageGroup(cachedStageGroup, keepUrls);
        cachedStageGroup = null;
        stage3DData = res;
      }
    } catch (e) {
      console.warn('falha ao carregar o mapa da arena; mantendo o palco anterior', entry.id, e);
      // PV-B.1: o palco legado (7,29 MB) NAO e mais baixado no boot — so em ultimo recurso
      if (!stage3DData) {
        try {
          const legacy = await fetch('assets/stage/stage_3d.json?v=8').then(r => r.json());
          if (legacy && legacy.meshes) stage3DData = legacy;
        } catch (err2) { console.warn('palco legado indisponivel; usando o ground plane de fallback', err2); }
      }
    }
  }

  if (!opts.silent) rebuildArenaVisuals();
  updateArenaLabels();
  return ARENA;
}

function rebuildArenaVisuals() {
  if (!arenaGroup.visible && !matchActive) return;
  const wasVisible = arenaGroup.visible;
  arenaGroup.visible = true;
  buildMOBA3DArena();
  arenaGroup.visible = wasVisible;
  if (matchActive) {
    const bpB = basePos('blue');
    const bpR = basePos('red');
    for (const u of units) {
      const bp = u.team === 'blue' ? bpB : bpR;
      const a = (units.indexOf(u) % 5) / 5 * Math.PI * 2;
      u.spawnX = bp.x + Math.cos(a) * 8;
      u.spawnZ = bp.z + Math.sin(a) * 8;
      if (ARENA.shape === 'circle') {
        const hyp = Math.hypot(u.spawnX, u.spawnZ);
        if (hyp > ARENA.radius && hyp > 0.001) {
          const factor = ARENA.radius / hyp;
          u.spawnX *= factor;
          u.spawnZ *= factor;
        }
        u.x = u.spawnX;
        u.z = u.spawnZ;
      } else if (ARENA.bounds) {
        u.x = THREE.MathUtils.clamp(u.spawnX, ARENA.bounds.minX, ARENA.bounds.maxX);
        u.z = THREE.MathUtils.clamp(u.spawnZ, ARENA.bounds.minZ, ARENA.bounds.maxZ);
      } else {
        u.x = clampArena(u.spawnX);
        u.z = clampArena(u.spawnZ);
      }
      if (u.mesh) u.mesh.position.set(u.x, 0, u.z);
    }
  }
  updateArenaLabels();
}

function updateArenaLabels() {
  const nameEl = document.getElementById('arena-name');
  if (nameEl) nameEl.textContent = ARENA.label;
  const mapEl = document.getElementById('minimap-arena-name');
  if (mapEl) mapEl.textContent = `ARENA ${(ARENA.label || ARENA.id).split('(')[0].trim()}`;
}

function renderArenaPicker() {
  const host = document.getElementById('arena-picker');
  if (!host) return;
  if (!arenasCatalog.length) { host.style.display = 'none'; return; }
  host.style.display = '';
  host.innerHTML = arenasCatalog.map(a => `
    <button class="arena-chip${a.id === selectedArenaId ? ' selected' : ''}"
            data-arena="${a.id}" type="button">
      <span class="arena-chip-name">${a.label || a.id}</span>
      <span class="arena-chip-meta">${a.shape === 'circle' ? 'Arena circular' : 'Arena aberta'} · 5v5</span>
    </button>
  `).join('');
  host.querySelectorAll('.arena-chip').forEach(btn => {
    btn.addEventListener('click', async () => {
      sfx.init();
      sfx.click(); // W5: sem fallback genérico
      AUTH_SFX.play('stage_change', { vol: 0.75 }); // W1.1
      await applyArena(btn.dataset.arena);
      renderArenaPicker();
      updateArenaLabels();
      renderArenaPage();
    });
  });
}

// ============================================================================
// CLIENT NAV PAGES: JOGAR / NINJAS / ARENAS / PERFIL
// ============================================================================
const PROFILE_KEY = 'nuba.profile.v1';
const LOBBY_PAGES = ['play', 'ninjas', 'arenas', 'perfil', 'ajustes'];
let lobbyPage = 'play';
let collectionFilter = 'ALL';
let matchRecorded = false;

function loadProfileData() {
  const fallback = { matches: 0, wins: 0, losses: 0, ties: 0, kills: 0, deaths: 0, assists: 0, history: [], arenas: [], sound: true, volume: 0.85, quality: 'high', juice: true, music: true, musicVol: 0.55, sfxVol: 0.85 };
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return { ...fallback, ...parsed, history: Array.isArray(parsed.history) ? parsed.history : [] };
  } catch (err) {
    return fallback;
  }
}

function saveProfileData(data) {
  try { localStorage.setItem(PROFILE_KEY, JSON.stringify(data)); } catch (err) { /* storage blocked */ }
}

// ==================== PROGRESSAO (W-PROG) ====================
// Camada real sobre o perfil local (nuba.profile.v1): XP/nivel, RYO, missoes
// diarias deterministicas por data, contador de ougi e ninja favorito.
const PROG_XP_MATCH = 100, PROG_XP_WIN = 60, PROG_XP_KILL = 15;
const PROG_COIN_MATCH = 25, PROG_COIN_WIN = 10, PROG_COIN_KILL = 2;
const PROG_MISSION_POOL = [
  { id: 'play3', metric: 'matches', goal: 3, label: 'JOGUE 3 PARTIDAS', kanji: '戦', xp: 120, coins: 40 },
  { id: 'win2', metric: 'wins', goal: 2, label: 'VENCA 2 PARTIDAS', kanji: '勝', xp: 180, coins: 60 },
  { id: 'kill6', metric: 'kills', goal: 6, label: 'CAUSE 6 ABATES', kanji: '討', xp: 150, coins: 50 },
  { id: 'ult3', metric: 'ults', goal: 3, label: 'USE 3 OUGI (R)', kanji: '奥', xp: 200, coins: 70 },
  { id: 'hero2', metric: 'hero', goal: 2, label: 'JOGUE 2 PARTIDAS COM SEU NINJA FAVORITO', kanji: '忍', xp: 140, coins: 45 }
];
function progXpNeeded(level) { return 800 + (level - 1) * 400; }
let progUltCount = 0;

function progTodayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function progLevelState(xp) {
  let lvl = 1, into = xp, need = progXpNeeded(1);
  while (into >= need) { into -= need; lvl += 1; need = progXpNeeded(lvl); }
  return { lvl, into, need };
}
function progSeedRand(seed) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) { h ^= seed.charCodeAt(i); h = Math.imul(h, 16777619); }
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= (h >>> 16)) >>> 0) / 4294967296;
  };
}
function progFavHeroId(data) {
  const counts = data.heroUse || {};
  return Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0] || null;
}
function progDailyRefresh(data) {
  const today = progTodayKey();
  if (data.daily && data.daily.date === today && Array.isArray(data.daily.missions) && data.daily.missions.length) return data;
  const rnd = progSeedRand(`nuba-daily-${today}`);
  const pool = PROG_MISSION_POOL.slice();
  const picks = [];
  while (picks.length < 3 && pool.length) picks.push(...pool.splice(Math.floor(rnd() * pool.length), 1));
  data.daily = {
    date: today,
    heroId: progFavHeroId(data),
    counters: { matches: 0, wins: 0, kills: 0, ults: 0 },
    missions: picks.map(m => ({ id: m.id, label: m.label, kanji: m.kanji, metric: m.metric, goal: m.goal, xp: m.xp, coins: m.coins, progress: 0, done: false }))
  };
  return data;
}
function progApplyMatch(data, winner, player) {
  progDailyRefresh(data);
  const d = data.daily;
  const win = winner === 'blue';
  const kills = player ? (player.kills || 0) : 0;
  const ults = progUltCount;
  progUltCount = 0;
  data.xp = (data.xp || 0) + PROG_XP_MATCH + (win ? PROG_XP_WIN : 0) + kills * PROG_XP_KILL;
  data.coins = (data.coins || 0) + PROG_COIN_MATCH + (win ? PROG_COIN_WIN : 0) + kills * PROG_COIN_KILL;
  data.heroUse = data.heroUse || {};
  data.heroUse[selectedHeroId] = (data.heroUse[selectedHeroId] || 0) + 1;
  d.counters.matches += 1;
  if (win) d.counters.wins += 1;
  d.counters.kills += kills;
  d.counters.ults += ults;
  if (!d.heroId) d.heroId = progFavHeroId(data);
  if (d.heroId && d.heroId === selectedHeroId) d.counters.hero = (d.counters.hero || 0) + 1;
  for (const m of d.missions) {
    if (m.done) continue;
    m.progress = Math.min(m.goal, (d.counters[m.metric] || 0));
    if (m.progress >= m.goal) {
      m.done = true;
      data.xp += m.xp;
      data.coins += m.coins;
    }
  }
  return data;
}
function renderProgressUI(data) {
  const d = data || loadProfileData();
  progDailyRefresh(d);
  const st = progLevelState(d.xp || 0);
  const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  setText('profile-level', st.lvl);
  setText('profile-xp-text', `${st.into.toLocaleString('pt-BR')} / ${st.need.toLocaleString('pt-BR')} XP`);
  const fill = document.getElementById('profile-xp-fill');
  if (fill) fill.style.width = `${Math.round((st.into / st.need) * 100)}%`;
  setText('lobby-ryo', (d.coins || 0).toLocaleString('pt-BR'));
  setText('profile-ryo', (d.coins || 0).toLocaleString('pt-BR'));
  const lvlChip = document.getElementById('lobby-level');
  if (lvlChip) lvlChip.textContent = `Nível ${st.lvl} • Konoha`;
  const chip = document.querySelector('.player-chip-meta span');
  if (chip && !document.getElementById('lobby-level')) chip.textContent = `Nível ${st.lvl} • Konoha`;
  const mh = document.getElementById('profile-missions');
  if (mh) {
    const done = d.daily.missions.filter(m => m.done).length;
    mh.innerHTML = d.daily.missions.map(m => `
      <li class="mission${m.done ? ' done' : ''}">
        <span class="mission-kanji">${m.kanji}</span>
        <div class="mission-body">
          <strong>${m.label}</strong>
          <div class="mission-track"><div style="width: ${Math.round((m.progress / m.goal) * 100)}%"></div></div>
          <span class="mission-meta">${m.progress} / ${m.goal} - ${m.xp} XP + ${m.coins} RYO${m.done ? ' CONCLUIDA' : ''}</span>
        </div>
      </li>`).join('');
    setText('profile-missions-count', `${done} / ${d.daily.missions.length}`);
  }
}
window.progApplyMatch = progApplyMatch; // EXPORT E2E
window.progDailyRefresh = () => progDailyRefresh(loadProfileData()); // EXPORT E2E
window.renderProgressUI = renderProgressUI; // EXPORT E2E
window.PROG_MISSION_POOL = PROG_MISSION_POOL; // EXPORT E2E

function recordMatchResult(winner) {
  if (matchRecorded) return;
  matchRecorded = true;
  const data = loadProfileData();
  const player = units.find(u => u.isPlayer);
  data.matches += 1;
  if (winner === 'blue') data.wins += 1;
  else if (winner === 'red') data.losses += 1;
  else data.ties += 1;
  data.kills += player ? (player.kills || 0) : 0;
  data.deaths += player ? (player.deaths || 0) : 0;
  data.assists += player ? (player.assists || 0) : 0;
  data.history.unshift({
    t: Date.now(),
    result: winner === 'blue' ? 'win' : (winner === 'red' ? 'loss' : 'tie'),
    blue: Math.max(0, scoreBlue),
    red: Math.max(0, scoreRed),
    hero: selectedHeroId
  });
  data.history = data.history.slice(0, 6);
  data.arenas = [...new Set([...(data.arenas || []), selectedArenaId])];
  progApplyMatch(data, winner, player);
  saveProfileData(data);
  renderProfilePage();
}

function setLobbyPage(page) {
  const target = LOBBY_PAGES.includes(page) ? page : 'play';
  lobbyPage = target;
  AUTH_SFX.play('page_slct', { vol: 0.7 }); // W1.1

  document.querySelectorAll('.lobby-nav .nav-tab').forEach(tab => {
    const on = tab.dataset.page === target;
    tab.classList.toggle('active', on);
    tab.setAttribute('aria-selected', on ? 'true' : 'false');
  });

  const playPage = document.getElementById('page-play');
  if (playPage) {
    playPage.classList.toggle('active', target === 'play');
    playPage.style.display = target === 'play' ? '' : 'none';
  }

  document.querySelectorAll('.lobby-page').forEach(sec => {
    const on = sec.dataset.page === target;
    sec.classList.toggle('active', on);
    sec.setAttribute('aria-hidden', on ? 'false' : 'true');
  });

  if (!matchActive) lobbyPedestalGroup.visible = target === 'play';

  if (target === 'ninjas') renderCollectionPage();
  else if (target === 'arenas') renderArenaPage();
  else if (target === 'perfil') renderProfilePage();
  else { renderArenaPicker(); updateArenaLabels(); }
  renderProgressUI();
}

function heroRoleKey(hero) {
  const primary = (hero.role || 'Lutador').split('/')[0].trim().toUpperCase();
  const groups = [
    { key: 'LUTADOR', match: ['LUTADOR', 'CORPO A CORPO', 'BRIGÃO', 'FIGHTER', 'MELEE', 'BRUISER'] },
    { key: 'ASSASSINO', match: ['ASSASSINO', 'ASSASSIN'] },
    { key: 'NINJUTSU', match: ['MAGO', 'MAGE'] },
    { key: 'TANQUE', match: ['TANQUE', 'TANK'] },
    { key: 'SUPORTE', match: ['SUPORTE', 'SUPPORT'] }
  ];
  const group = groups.find(g => g.match.some(m => primary.includes(m)));
  return group ? group.key : primary;
}

const ARENA_AREA_LABELS = {
  AREA_TRAINING: 'TREINO',
  AREA_COLOSSEUM: 'COLISEU',
  AREA_PLAIN: 'PLANÍCIE',
  AREA_TOWER: 'TORRE',
  AREA_DEATH: 'VALE DO FIM',
  AREA_FOREST: 'FLORESTA',
  AREA_WILD: 'ESTÁDIO',
  AREA_YAGURA: 'YAGURA'
};

function updateCollectionLabel() {
  const hero = rosterMeta.find(h => h.id === selectedHeroId) || rosterMeta[0];
  const label = document.getElementById('collection-selected-label');
  if (label) label.textContent = hero ? `Selecionado: ${hero.name}` : 'Selecione um ninja';
  const btn = document.getElementById('btn-collection-play');
  if (btn) btn.textContent = hero ? `JOGAR COM ${hero.name.split(' ')[0].toUpperCase()}` : 'JOGAR COM ESTE NINJA';
}

function renderCollectionPage() {
  const grid = document.getElementById('collection-grid');
  if (!grid) return;
  if (!rosterMeta.length) {
    grid.innerHTML = '<p class="collection-hint">Carregando databook...</p>';
    return;
  }

  const roles = ['ALL', ...new Set(rosterMeta.map(heroRoleKey))];
  const filters = document.getElementById('collection-filters');
  if (filters && filters.dataset.built !== roles.join('|')) {
    filters.dataset.built = roles.join('|');
    filters.innerHTML = roles.map(role =>
      `<button type="button" class="filter-chip${role === collectionFilter ? ' active' : ''}" data-role="${role}">${role === 'ALL' ? 'TODOS' : role}</button>`
    ).join('');
    filters.querySelectorAll('.filter-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        collectionFilter = btn.dataset.role || 'ALL';
        renderCollectionPage();
      });
    });
  } else if (filters) {
    filters.querySelectorAll('.filter-chip').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.role === collectionFilter);
    });
  }

  const list = rosterMeta.filter(h => collectionFilter === 'ALL' || heroRoleKey(h) === collectionFilter);
  grid.innerHTML = list.map(h => `
    <button type="button" class="collection-card${h.id === selectedHeroId ? ' selected' : ''}"
            data-id="${h.id}" title="${h.name}">
      <img src="${h.portrait}" alt="${h.name}" loading="lazy" />
      <span class="cc-info">
        <span class="cc-name">${h.name}</span>
        <span class="cc-role">${heroRoleKey(h)} · ${(h.role.split('/')[1] || 'GENERALISTA').trim().toUpperCase()}</span>
        <span class="cc-stats">${h.heightCm || 150} cm · ATQ ${h.atk ?? 4} · DEF ${h.def ?? 4} · VEL ${h.spd ?? 4}</span>
      </span>
    </button>
  `).join('');

  grid.querySelectorAll('.collection-card').forEach(card => {
    card.addEventListener('click', async () => {
      sfx.init();
      sfx.clink();
      await selectLobbyHero(card.dataset.id);
      renderCollectionPage();
      updateCollectionLabel();
    });
  });

  updateCollectionLabel();
}

function renderArenaPage() {
  const grid = document.getElementById('arena-page-grid');
  if (!grid) return;
  if (!arenasCatalog.length) {
    grid.innerHTML = '<p class="collection-hint">Carregando arenas...</p>';
    return;
  }

  grid.innerHTML = arenasCatalog.map(a => {
    const shape = a.shape === 'box' ? 'box' : (a.shape === 'circle' ? 'circle' : 'free');
    const area = ARENA_AREA_LABELS[a.area] || 'ARENA';
    const layout = a.shape === 'box' ? 'RETANGULAR' : (a.shape === 'circle' ? 'CIRCULAR' : 'ABERTA');
    return `
      <button type="button" class="arena-card${a.id === selectedArenaId ? ' selected' : ''}" data-arena="${a.id}">
        <span class="arena-blueprint"><span class="arena-shape ${shape}"></span></span>
        <span class="arena-card-meta">
          <span class="arena-card-name">${a.label || a.id}</span>
          <span class="arena-card-sub">${area} · ${layout} · raio ${a.radius || '—'} m</span>
          <span class="arena-card-chips">
            <span class="arena-chip-mini">${a.meshes || 0} meshes</span>
            <span class="arena-chip-mini">${Math.round((a.tris || 0) / 1000)}k tris</span>
          </span>
        </span>
      </button>
    `;
  }).join('');

  grid.querySelectorAll('.arena-card').forEach(card => {
    card.addEventListener('click', async () => {
      if (card.classList.contains('loading') || card.dataset.arena === selectedArenaId) return;
      card.classList.add('loading');
      sfx.init();
      sfx.clink();
      try {
        await applyArena(card.dataset.arena);
      } finally {
        card.classList.remove('loading');
      }
      renderArenaPicker();
      updateArenaLabels();
      renderArenaPage();
    });
  });

  const selected = arenasCatalog.find(a => a.id === selectedArenaId);
  const label = document.getElementById('arena-page-selected');
  if (label) label.textContent = `Arena selecionada: ${selected ? (selected.label || selected.short || selected.id) : '—'}`;
  const count = document.getElementById('arena-page-count');
  if (count) count.textContent = arenasCatalog.length;
}

function renderProfilePage() {
  const data = loadProfileData();
  progDailyRefresh(data); // W-PROG: virada de dia regenera missoes e persiste
  saveProfileData(data);
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  setText('profile-matches', data.matches);
  setText('profile-wins', data.wins);
  const winRate = data.matches ? Math.round((data.wins / data.matches) * 100) : null;
  setText('profile-winrate', winRate === null ? '—' : `${winRate}%`);
  setText('profile-kda', `${data.kills} / ${data.deaths} / ${data.assists}`);

  const _progSt = progLevelState(data.xp || 0);
  setText('profile-level', _progSt.lvl);
  setText('profile-xp-text', `${_progSt.into.toLocaleString('pt-BR')} / ${_progSt.need.toLocaleString('pt-BR')} XP`);
  const xpFill = document.getElementById('profile-xp-fill');
  if (xpFill) xpFill.style.width = `${Math.round((_progSt.into / _progSt.need) * 100)}%`;

  const hero = rosterMeta.find(h => h.id === selectedHeroId) || rosterMeta[0];
  const avatar = document.getElementById('profile-avatar');
  if (avatar && hero) {
    avatar.src = hero.portrait;
    avatar.alt = hero.name;
  }
  setText('profile-rank', hero ? `${heroRoleKey(hero)} • KONOHA` : 'SHINOBI • KONOHA');

  const history = document.getElementById('profile-history');
  if (history) {
    history.innerHTML = data.history.length
      ? data.history.map(m => {
          const heroName = (rosterMeta.find(h => h.id === m.hero) || {}).name || 'Ninja';
          const when = new Date(m.t).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
          const label = m.result === 'win' ? 'VITÓRIA' : (m.result === 'loss' ? 'DERROTA' : 'EMPATE');
          return `<li class="ph-row ${m.result}">
            <span class="ph-result">${label}</span>
            <span>${heroName}</span>
            <span class="ph-score">${m.blue} — ${m.red}</span>
            <span class="ph-time">${when}</span>
          </li>`;
        }).join('')
      : '<li class="ph-empty">Nenhuma partida completa ainda — entre na arena para registrar seu histórico.</li>';
  }

  const sound = document.getElementById('pref-sound');
  if (sound) sound.checked = data.sound !== false;
  sfx.enabled = data.sound !== false;
  const _pm = document.getElementById('pref-music'); // W6
  if (_pm) _pm.checked = data.music !== false;
  const _pmv = document.getElementById('pref-music-vol');
  if (_pmv) _pmv.value = Math.round((data.musicVol != null ? data.musicVol : 0.55) * 100);
  const _psv = document.getElementById('pref-sfx-vol');
  if (_psv) _psv.value = Math.round((data.sfxVol != null ? data.sfxVol : 0.85) * 100);
  AUTH_SFX.volume = data.sfxVol != null ? data.sfxVol : 0.85;
  MUSIC.applySettings();

  let streak = 0;
  for (const m of data.history) {
    if (m.result !== 'win') break;
    streak += 1;
  }
  setText('profile-streak', streak);
  const last = data.history[0];
  setText('profile-last', last ? (last.result === 'win' ? 'VITÓRIA' : last.result === 'loss' ? 'DERROTA' : 'EMPATE') : '—');

  const heroCounts = {};
  data.history.forEach(m => { if (m.hero) heroCounts[m.hero] = (heroCounts[m.hero] || 0) + 1; });
  const favId = Object.keys(heroCounts).sort((a, b) => heroCounts[b] - heroCounts[a])[0];
  const favHero = rosterMeta.find(h => h.id === favId);
  setText('profile-fav', favHero ? favHero.name.split(' ')[0] : '—');

  const achievements = [
    { label: 'PRIMEIRA VITÓRIA', desc: 'Vença uma partida', ok: data.wins >= 1 },
    { label: 'VETERANO', desc: 'Jogue 5 partidas', ok: data.matches >= 5 },
    { label: 'CAÇADOR', desc: 'Some 10 abates', ok: data.kills >= 10 },
    { label: 'INTOCÁVEL', desc: '3 partidas sem morrer', ok: data.matches >= 3 && data.deaths === 0 },
    { label: 'DOMINADOR', desc: '60% de aproveitamento', ok: data.matches >= 3 && (data.wins / data.matches) >= 0.6 },
    { label: 'VIAJANTE', desc: 'Lute em 4 arenas', ok: (data.arenas || []).length >= 4 }
  ];
  const achHost = document.getElementById('profile-achievements');
  if (achHost) {
    achHost.innerHTML = achievements.map(a => `
      <div class="achievement${a.ok ? ' unlocked' : ''}">
        <strong>${a.label}</strong>
        <span>${a.desc}</span>
      </div>
    `).join('');
  }
  setText('profile-ach-count', `${achievements.filter(a => a.ok).length} / ${achievements.length}`);
  renderProgressUI(data);
}

function initLobbyNav() {
  document.querySelectorAll('.lobby-nav .nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      if (tab.dataset.page === lobbyPage) return;
      sfx.init();
      sfx.click();
      setLobbyPage(tab.dataset.page);
    });
  });

  const btnCollectionPlay = document.getElementById('btn-collection-play');
  if (btnCollectionPlay) {
    btnCollectionPlay.addEventListener('click', () => {
      sfx.init();
      sfx.click();
      setLobbyPage('play');
    });
  }

  const btnArenaReturn = document.getElementById('btn-arena-return');
  if (btnArenaReturn) {
    btnArenaReturn.addEventListener('click', () => {
      sfx.init();
      sfx.click();
      setLobbyPage('play');
    });
  }

  const btnArenaPlay = document.getElementById('btn-arena-play');
  if (btnArenaPlay) {
    btnArenaPlay.addEventListener('click', () => {
      sfx.init();
      sfx.click();
      startMatch(selectedModeId);
    });
  }

  const prefSound = document.getElementById('pref-sound');
  if (prefSound) {
    prefSound.addEventListener('change', () => {
      const data = loadProfileData();
      data.sound = prefSound.checked;
      saveProfileData(data);
      sfx.enabled = prefSound.checked;
      if (prefSound.checked) { sfx.init(); sfx.clink(); }
    });
  }

  const prefMusic = document.getElementById('pref-music'); // W6: settings funcionais
  if (prefMusic) prefMusic.addEventListener('change', () => {
    const d = loadProfileData(); d.music = prefMusic.checked; saveProfileData(d);
    MUSIC.applySettings();
  });
  const prefMusicVol = document.getElementById('pref-music-vol');
  if (prefMusicVol) prefMusicVol.addEventListener('input', () => {
    const d = loadProfileData(); d.musicVol = prefMusicVol.value / 100; saveProfileData(d);
    MUSIC.applySettings();
  });
  const prefSfxVol = document.getElementById('pref-sfx-vol');
  if (prefSfxVol) prefSfxVol.addEventListener('input', () => {
    const d = loadProfileData(); d.sfxVol = prefSfxVol.value / 100; saveProfileData(d);
    AUTH_SFX.volume = d.sfxVol;
  });

  const btnReset = document.getElementById('btn-profile-reset');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      if (btnReset.dataset.confirm !== '1') {
        btnReset.dataset.confirm = '1';
        btnReset.textContent = 'CONFIRMAR?';
        if (btnReset._resetTimer) clearTimeout(btnReset._resetTimer);
        btnReset._resetTimer = setTimeout(() => {
          btnReset.dataset.confirm = '0';
          btnReset.textContent = 'RESETAR';
        }, 3000);
        return;
      }
      clearTimeout(btnReset._resetTimer);
      btnReset.dataset.confirm = '0';
      btnReset.textContent = 'RESETAR';
      try { localStorage.removeItem(PROFILE_KEY); } catch (err) { /* storage blocked */ }
      renderProfilePage();
    });
  }

  sfx.enabled = loadProfileData().sound !== false;
  initAjustes(); // W1.2: wire da página de Ajustes
}

// ==================== W1.2 AJUSTES (página de configurações) ====================
function initAjustes() {
  const ajSound = document.getElementById('aj-sound');
  const prefSound = document.getElementById('pref-sound');
  const ajVol = document.getElementById('aj-volume');
  const ajVolLabel = document.getElementById('aj-volume-label');
  const ajJuice = document.getElementById('aj-juice');
  const pills = { low: document.getElementById('aj-q-low'), med: document.getElementById('aj-q-med'), high: document.getElementById('aj-q-high') };
  if (!ajSound) return;
  const QUALITY_CAPS = { low: 0.75, med: 1.25, high: 1.75 };
  const persistPatch = (patch) => { const d = loadProfileData(); Object.assign(d, patch); saveProfileData(d); };
  const applyQuality = (q) => {
    // PV3.1: respeita o cap do governor (mobile nunca passa de 1.25)
    const _mob = !!(window.__DEVICE && window.__DEVICE.isMobile);
    const _cap = _mob ? Math.min(QUALITY_CAPS[q] || 1.25, 1.25) : (QUALITY_CAPS[q] || 1.75);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, _cap));
    if (window.__GOV) { window.__GOV.pref = q; window.__GOV.dprCap = _cap; window.__GOV.vfxCap = _mob ? 24 : Infinity; }
    for (const k of Object.keys(pills)) if (pills[k]) pills[k].classList.toggle('active', k === q);
  };
  const data = loadProfileData();
  ajSound.checked = data.sound !== false;
  const vol = typeof data.volume === 'number' ? Math.max(0, Math.min(1, data.volume)) : 0.85;
  if (typeof AUTH_SFX !== 'undefined') AUTH_SFX.volume = vol;
  if (ajVol) ajVol.value = Math.round(vol * 100);
  if (ajVolLabel) ajVolLabel.textContent = Math.round(vol * 100) + '%';
  applyQuality(QUALITY_CAPS[data.quality] ? data.quality : 'high');
  const juiceOn = data.juice !== false;
  JUICE.enabled = juiceOn;
  if (ajJuice) ajJuice.checked = juiceOn;
  ajSound.addEventListener('change', () => {
    sfx.enabled = ajSound.checked;
    if (prefSound) prefSound.checked = ajSound.checked;
    persistPatch({ sound: ajSound.checked });
    if (ajSound.checked) { sfx.init(); sfx.clink(); }
  });
  if (prefSound) prefSound.addEventListener('change', () => { ajSound.checked = prefSound.checked; });
  if (ajVol) {
    ajVol.addEventListener('input', () => {
      const v = Math.max(0, Math.min(1, Number(ajVol.value) / 100));
      if (typeof AUTH_SFX !== 'undefined') AUTH_SFX.volume = v;
      if (ajVolLabel) ajVolLabel.textContent = Math.round(v * 100) + '%';
    });
    ajVol.addEventListener('change', () => persistPatch({ volume: Math.max(0, Math.min(1, Number(ajVol.value) / 100)) }));
  }
  if (ajJuice) ajJuice.addEventListener('change', () => { JUICE.enabled = ajJuice.checked; persistPatch({ juice: ajJuice.checked }); });
  for (const k of Object.keys(pills)) if (pills[k]) pills[k].addEventListener('click', () => { applyQuality(k); persistPatch({ quality: k }); });
}

function buildMOBA3DArena() {
  arenaGroup.clear();

  // 1. Add the REAL extracted 3D stage for the selected arena
  const extractedStage = buildExtractedStageGroup();
  if (extractedStage) {
    arenaGroup.add(extractedStage);
  } else {
    // Fallback ground plane only if the arena map hasn't finished loading
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(ARENA.radius * 2.5, ARENA.radius * 2.5),
      new THREE.MeshLambertMaterial({ color: 0x3b5e34 })
    );
    ground.rotation.x = -Math.PI / 2;
    arenaGroup.add(ground);
  }

  // Add Kakashi's 3 wooden training posts only on the Konoha training field (sd00a)
  if (ARENA.id === 'sd00a') {
    arenaGroup.add(createTrainingPosts());
  }

  // Add swirling Konoha leaf particle vortex
  leafParticlesGroup = createKonohaLeafParticles();
  arenaGroup.add(leafParticlesGroup);

  // 2. Subtle MOBA Tactical Lane Overlay & Central Scroll Shrine Objective
  const shrineBase = new THREE.Mesh(
    new THREE.CylinderGeometry(5.0, 6.0, 0.5, 24),
    new THREE.MeshLambertMaterial({ color: 0x334155 })
  );
  shrineBase.position.set(0, 0.28, 0);
  arenaGroup.add(shrineBase);

  shrineOrb = new THREE.Mesh(
    new THREE.OctahedronGeometry(1.4, 1),
    new THREE.MeshBasicMaterial({ color: 0xfde047 })
  );
  shrineOrb.position.set(0, 2.8, 0);
  arenaGroup.add(shrineOrb);

  // 3. Blue & Red Base Sanctuaries, placed from the active arena config
  const createBaseSanctuary = (x, z, colorHex) => {
    const pad = new THREE.Mesh(
      new THREE.CylinderGeometry(13, 14, 0.35, 32),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.28 })
    );
    pad.position.set(x, 0.25, z);
    arenaGroup.add(pad);

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(12.5, 13.8, 40),
      new THREE.MeshBasicMaterial({ color: colorHex, side: THREE.DoubleSide })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(x, 0.48, z);
    arenaGroup.add(ring);
  };
  if (activeMatchCfg.mode !== 'br') { // PV2: BR nao tem bases — a vila e' o mapa
    createBaseSanctuary(basePos('blue').x, basePos('blue').z, 0x3b82f6);
    createBaseSanctuary(basePos('red').x, basePos('red').z, 0xef4444);
  }
  updateArenaLabels();
}

// ============================================================================
// SPAWN 10 NINJAS (5 BLUE vs 5 RED) WITH REAL 3D SKINNED MODELS
// ============================================================================
// ==================== DRAFT (W-MENU T3/T4 — pick -> lock -> reveal) ====================
// Fluxo mobile-MOBA: board de 12 cards (padrao DOTA2), preview no pedestal 3D do lobby,
// timer de 20s com lock explicito ("SELAR"), bots "pensam" (delays humanos), reveal dos
// rivais um a um, badge VS, blackout -> startMatch(configId, {blue, red}).
const DRAFT = {
  phase: 'idle',          // idle | pick | lock | reveal | done
  modeId: null,
  sel: null,              // heroId em preview
  teamSize: 3,
  timer: 20,
  remaining: 20,
  blue: [], red: [],      // heroIds (null = vazio)
  redReady: [], redRevealed: [],
  filter: 'TODOS',
  lastWholeTick: -1,
  timers: [],
  raf: null
};
window.DRAFT = DRAFT; // EXPORT E2E

const DRAFT_FILTERS = ['TODOS', 'LUTADOR', 'ASSASSINO', 'MAGO', 'TANQUE', 'SUPORTE'];
const draftHeroById = (id) => rosterMeta.find(h => h.id === id) || null;
const draftClassOf = (h) => (h.role || '').split('/')[0].split(' ')[0].toUpperCase();

function draftClearTimers() {
  for (const t of DRAFT.timers) clearTimeout(t);
  DRAFT.timers = [];
  if (DRAFT.raf) cancelAnimationFrame(DRAFT.raf);
  DRAFT.raf = null;
}

async function openDraft(modeId) {
  const CFG = MATCH_CONFIGS[modeId];
  // Treino e BR tem fluxo proprio (sem times) — vao direto pra partida
  if (!CFG || CFG.mode === 'training' || CFG.mode === 'br') { await startMatch(modeId); return; }

  draftClearTimers();
  DRAFT.modeId = modeId;
  DRAFT.teamSize = CFG.teamSize;
  DRAFT.phase = 'pick';
  DRAFT.timer = 20;
  DRAFT.remaining = 20;
  DRAFT.filter = 'TODOS';
  DRAFT.lastWholeTick = 99;
  DRAFT.blue = Array(CFG.teamSize).fill(null);
  DRAFT.red = Array(CFG.teamSize).fill(null);
  DRAFT.redReady = Array(CFG.teamSize).fill(false);
  DRAFT.redRevealed = Array(CFG.teamSize).fill(false);

  document.getElementById('title-screen').classList.remove('active');
  document.getElementById('lobby-screen').classList.remove('active');
  document.getElementById('draft-screen').classList.add('active');
  document.getElementById('draft-mode-name').textContent = CFG.label || modeId;
  document.getElementById('draft-vs').hidden = true;
  const bo = document.getElementById('draft-blackout');
  bo.hidden = true; bo.classList.remove('on');
  const lockBtn = document.getElementById('btn-draft-lock');
  lockBtn.disabled = false;
  document.getElementById('draft-phase').textContent = 'ESCOLHA SEU NINJA';

  lobbyPedestalGroup.visible = true;
  await selectLobbyHero(selectedHeroId || '1nrt');
  draftPick(selectedHeroId || '1nrt');
  draftRenderFilters();
  draftRenderBoard();
  draftRenderTeams();
  draftStartTimer();

  try { sfx.init(); AUTH_SFX.play('chakura_use', { vol: 0.5 }); } catch (e) {}
  window.__DRAFT_READY = performance.now();
}
window.openDraft = openDraft; // EXPORT E2E

function closeDraft() {
  draftClearTimers();
  DRAFT.phase = 'idle';
  document.getElementById('draft-screen').classList.remove('active');
  document.getElementById('lobby-screen').classList.add('active');
  setLobbyPage('play');
  window.__DRAFT_CLOSED = performance.now();
}
window.closeDraft = closeDraft; // EXPORT E2E

function draftHeroInfo(hero) {
  const name = document.getElementById('draft-hero-name');
  const role = document.getElementById('draft-hero-role');
  const kit = document.getElementById('draft-hero-kit');
  if (!hero) { name.textContent = '—'; role.textContent = ''; kit.textContent = ''; return; }
  name.textContent = hero.name;
  role.textContent = (hero.role || '').toUpperCase();
  kit.textContent = `${hero.clan || ''} · ${hero.heightCm || 150}cm · ATQ ${hero.atk || 4.5} / DEF ${hero.def || 4} / VEL ${hero.spd || 4}`;
}

function draftPick(heroId) {
  if (DRAFT.phase !== 'pick') return;
  const taken = [...DRAFT.blue, ...DRAFT.red].filter(Boolean);
  if (taken.includes(heroId)) return;
  DRAFT.sel = heroId;
  selectLobbyHero(heroId);
  draftHeroInfo(draftHeroById(heroId));
  draftRenderBoard();
  try { AUTH_SFX.play('menu_slct', { vol: 0.6 }); } catch (e) {}
}
window.draftPick = draftPick; // EXPORT E2E

function draftRenderFilters() {
  const el = document.getElementById('draft-filters');
  el.innerHTML = DRAFT_FILTERS.map(f =>
    `<button class="draft-chip ${DRAFT.filter === f ? 'on' : ''}" data-f="${f}" type="button">${f}</button>`
  ).join('');
  el.querySelectorAll('.draft-chip').forEach(ch => {
    ch.addEventListener('click', () => {
      DRAFT.filter = ch.dataset.f;
      draftRenderFilters();
      draftRenderBoard();
      try { sfx.click(); } catch (e) {}
    });
  });
}

function draftRenderBoard() {
  const el = document.getElementById('draft-board');
  const taken = [...DRAFT.blue, ...DRAFT.red].filter(Boolean);
  const heroes = rosterMeta.filter(h => DRAFT.filter === 'TODOS' || draftClassOf(h) === DRAFT.filter);
  el.innerHTML = heroes.map(h => {
    const cls = [
      DRAFT.sel === h.id ? 'sel' : '',
      taken.includes(h.id) ? 'taken' : '',
      DRAFT.blue.includes(h.id) ? 'ally' : '',
      DRAFT.redRevealed.includes(h.id) ? 'foe' : ''
    ].filter(Boolean).join(' ');
    return `<div class="draft-card ${cls}" data-id="${h.id}">
      <img src="${h.portrait}" alt="${h.name}" loading="lazy" />
      <span class="draft-card-name">${h.name}</span>
      <span class="draft-card-tag">${(h.role || '').toUpperCase()}</span>
    </div>`;
  }).join('');
  el.querySelectorAll('.draft-card').forEach(card => {
    card.addEventListener('click', () => draftPick(card.dataset.id));
  });
}

function draftSlotHtml(heroId, opts) {
  const h = heroId ? draftHeroById(heroId) : null;
  if (h) {
    return `<div class="draft-slot filled ${opts.player ? 'is-player' : ''}">
      <img src="${h.portrait}" alt="${h.name}" />
      <div class="draft-slot-meta">
        <span class="draft-slot-name">${h.name}</span>
        <span class="draft-slot-tag ${opts.player ? 'you' : ''}">${opts.player ? 'VOCÊ' : (opts.ally ? 'ALIADO' : 'RIVAL')}</span>
      </div>
    </div>`;
  }
  if (opts.thinking) {
    return `<div class="draft-slot thinking"><span class="draft-slot-tag">ESCOLHENDO…</span></div>`;
  }
  return `<div class="draft-slot unknown"><span class="draft-slot-q">${opts.q || '?'}</span></div>`;
}

function draftRenderTeams() {
  const blueEl = document.getElementById('draft-blue-slots');
  const redEl = document.getElementById('draft-red-slots');
  if (blueEl) blueEl.innerHTML = DRAFT.blue.map((id, i) =>
    draftSlotHtml(id, { player: i === 0, ally: true })).join('');
  if (redEl) redEl.innerHTML = DRAFT.red.map((id, i) =>
    DRAFT.redRevealed[i]
      ? draftSlotHtml(id, {})
      : (DRAFT.redReady[i]
        ? `<div class="draft-slot thinking"><span class="draft-slot-tag">PRONTO ✓</span></div>`
        : `<div class="draft-slot unknown"><span class="draft-slot-q">?</span></div>`)).join('');
  const hint = document.getElementById('draft-blue-hint');
  if (hint) hint.textContent = DRAFT.phase === 'pick' ? 'toque num card para inspecionar' : '';
}

function draftPaintTimer() {
  const el = document.getElementById('draft-timer');
  if (!el) return;
  const t = Math.max(0, DRAFT.remaining);
  el.textContent = `00:${String(Math.floor(t)).padStart(2, '0')}`;
  el.classList.toggle('urgent', t < 5.001 && DRAFT.phase === 'pick');
}

function draftStartTimer() {
  if (DRAFT.raf) cancelAnimationFrame(DRAFT.raf);
  let last = performance.now();
  const step = () => {
    if (DRAFT.phase !== 'pick') { DRAFT.raf = null; return; }
    const now = performance.now();
    const dt = (now - last) / 1000;
    last = now;
    DRAFT.remaining = Math.max(0, DRAFT.remaining - dt);
    const whole = Math.ceil(DRAFT.remaining);
    if (DRAFT.remaining < 5 && whole !== DRAFT.lastWholeTick && whole > 0) {
      DRAFT.lastWholeTick = whole;
      try { AUTH_SFX.play('kunai_swing', { vol: 0.5 }); } catch (e) {}
    }
    draftPaintTimer();
    if (DRAFT.remaining <= 0) { DRAFT.raf = null; draftLock(); return; }
    DRAFT.raf = requestAnimationFrame(step);
  };
  DRAFT.raf = requestAnimationFrame(step);
  draftPaintTimer();
}

function draftLock() {
  if (DRAFT.phase !== 'pick') return;
  if (!DRAFT.sel) draftPick(selectedHeroId || '1nrt');
  DRAFT.phase = 'lock';
  DRAFT.remaining = 0;
  draftPaintTimer();
  document.getElementById('btn-draft-lock').disabled = true;
  document.getElementById('draft-phase').textContent = 'SELEÇÃO SELADA';
  try { AUTH_SFX.play('menu_fix', { vol: 0.7 }); } catch (e) {}

  DRAFT.blue[0] = DRAFT.sel;
  draftRenderBoard();
  draftRenderTeams();

  // Pool sem o heroi do jogador — aliados e rivais consomem sem repetir (12 herois >= 2*teamSize)
  const pool = rosterMeta.filter(h => h.id !== DRAFT.sel).map(h => h.id);
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const [a, b] = [pool[i], pool[j]]; pool[i] = b; pool[j] = a;
  }
  const blueN = DRAFT.teamSize - 1;
  const delays = [];
  for (let i = 0; i < blueN; i++) {
    const id = pool[i];
    delays.push(400 + Math.random() * 900 + i * 260);
    DRAFT.timers.push(setTimeout(() => {
      DRAFT.blue[i + 1] = id;
      draftRenderBoard();
      draftRenderTeams();
      try { AUTH_SFX.play('sword_hit', { vol: 0.45 }); } catch (e) {}
    }, delays[i]));
  }
  for (let i = 0; i < DRAFT.teamSize; i++) {
    const id = pool[blueN + i];
    delays.push(650 + Math.random() * 1200 + i * 300);
    DRAFT.timers.push(setTimeout(() => {
      DRAFT.red[i] = id;
      DRAFT.redReady[i] = true;
      draftRenderBoard();
      draftRenderTeams();
    }, delays[blueN + i]));
  }
  DRAFT.timers.push(setTimeout(draftReveal, Math.max(...delays) + 520));
}
window.draftLock = draftLock; // EXPORT E2E

function draftReveal() {
  if (DRAFT.phase !== 'lock') return;
  DRAFT.phase = 'reveal';
  const phaseEl = document.getElementById('draft-phase');
  if (phaseEl) phaseEl.textContent = 'REVELAÇÃO DOS TIMES';
  const vs = document.getElementById('draft-vs');
  if (vs) vs.hidden = false;
  DRAFT.red.forEach((_, i) => {
    DRAFT.timers.push(setTimeout(() => {
      DRAFT.redRevealed[i] = true;
      draftRenderTeams();
      draftRenderBoard();
      try { AUTH_SFX.play('sword_hit', { vol: 0.6 }); } catch (e) {}
    }, 380 + i * 340));
  });
  const totalReveal = 380 + DRAFT.red.length * 340;
  DRAFT.timers.push(setTimeout(() => {
    try { AUTH_SFX.play('oogi', { vol: 0.8 }); } catch (e) {}
  }, totalReveal));
  DRAFT.timers.push(setTimeout(() => {
    const bo = document.getElementById('draft-blackout');
    bo.hidden = false;
    requestAnimationFrame(() => bo.classList.add('on'));
    DRAFT.timers.push(setTimeout(async () => {
      await startMatch(DRAFT.modeId, { blue: DRAFT.blue, red: DRAFT.red });
      DRAFT.phase = 'done';
      document.getElementById('draft-screen').classList.remove('active');
      bo.classList.remove('on');
      DRAFT.timers.push(setTimeout(() => { bo.hidden = true; }, 460));
    }, 420));
  }, totalReveal + 520));
}
window.draftReveal = draftReveal; // EXPORT E2E

(function initDraftUi() {
  const screen = document.getElementById('draft-screen');
  if (!screen || screen.dataset.wired) return;
  screen.dataset.wired = '1';
  document.getElementById('btn-draft-lock').addEventListener('click', () => draftLock());
  document.getElementById('btn-draft-cancel').addEventListener('click', () => closeDraft());
})();

async function startMatch(configId, draft = null) {
  const CFG = MATCH_CONFIGS[configId] || MATCH_CONFIGS.dm_legacy_5v5;
  activeMatchCfg = CFG;
  lastMatchConfigId = MATCH_CONFIGS[configId] ? configId : 'dm_legacy_5v5';
  if (window.__DEVICE.isTouch && cameraMode !== 'thirdperson') toggleCameraMode(); // PV1.5a: câmera mobile
  // BOOT-GUARD (cold-load race): window.start5v5Match e exposto antes do fetch do boot
  // popular rosterMeta — sem esperar: TypeError reading 'id' + spawn incompleto (flake P2)
  for (let _bg = 0; _bg < 100 && (!Array.isArray(rosterMeta) || rosterMeta.length === 0); _bg++) {
    await new Promise(r => setTimeout(r, 100));
  }
  if (!Array.isArray(rosterMeta) || rosterMeta.length === 0) {
    console.warn('[NUBA] roster nao carregou — start5v5Match abortado');
    return;
  }
  sfx.init();
  matchActive = true;
  matchEnding = false; // M5.2: nova partida libera a guarda do fim (fim natural nao pode matar partidas futuras)
  MUSIC.play('battle'); // W6: trilha leve de batalha (stage00)
  scoreBlue = 0;
  scoreRed = 0;
  matchRecorded = false;
  renderSkinDigits(document.getElementById('score-blue'), 0);
  renderSkinDigits(document.getElementById('score-red'), 0);
  matchTimeRemaining = CFG.time;
  matchOvertime = false; // T5
  matchSuddenDeath = false; // T5
  const _goalEl = document.querySelector('.match-goal-txt');
  if (_goalEl) _goalEl.textContent = CFG.mode === 'training' ? 'TREINO LIVRE · CAMPO 3' : (CFG.killTarget != null ? `META: ${CFG.killTarget} ABATES` : 'SOBREVIVA · ÚLTIMO DE PÉ'); // PV2: BR nao tem meta de abates // W-TRN
  const _mtReset = document.getElementById('match-timer');
  if (_mtReset) _mtReset.classList.remove('overtime', 'sudden');
  projectiles = [];
  vfxList = [];
  for (const c of shadowClones) { try { arenaGroup.remove(c.mesh); } catch (e) {} } // SPP
  AUTH_SFX.play('battle_start', { vol: 0.9 }); // W1.1
  shadowClones = [];
  // P1 JUICE: fresh match, fresh feel state
  JUICE.hitstop = 0;
  JUICE.slowTimer = 0;
  JUICE.slowTarget = 1;
  JUICE.timeScale = 1;
  JUICE.trauma = 0;
  JUICE.fovPunch = 0;

  document.getElementById('title-screen').classList.remove('active'); // W-MENU T1: E2E chama startMatch direto
  document.getElementById('lobby-screen').classList.remove('active');
  document.getElementById('hud-screen').classList.add('active');
  lobbyPedestalGroup.visible = false;
  arenaGroup.visible = true;
  buildMOBA3DArena();

  // Clear old units
  for (const u of units) {
    if (u.mesh) arenaGroup.remove(u.mesh);
    if (u.labelEl) u.labelEl.remove();
  }
  units.length = 0;
  document.getElementById('world-labels').innerHTML = '';

  const playerHero = rosterMeta.find(h => h.id === selectedHeroId) || rosterMeta[0];
  const others = rosterMeta.filter(h => h.id !== playerHero.id);
  // Shuffle others so all 12 heroes have equal chance to appear in matches (5v5 DM and BR)
  for (let i = others.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = others[i]; others[i] = others[j]; others[j] = tmp;
  }
  document.body.classList.toggle('br-mode', CFG.mode === 'br'); // PV2: gate CSS do HUD BR
  document.body.classList.toggle('training-mode', CFG.mode === 'training'); // W-TRN: gate CSS do HUD de treino
  if (CFG.mode === 'br') { if (CFG.arena) { await applyArena(CFG.arena); } await startBRMatch(CFG, playerHero, others); return; } // PV2: branch total — forca a arena do config e spawna solo na vila
  if (CFG.mode === 'training') { for (let _trnWait = 0; _trnWait < 150 && !window.__ARENA_BOOT_DONE; _trnWait++) { await new Promise(r => setTimeout(r, 100)); } await applyArena('sd00a'); TRN.active = true; } else { TRN.active = false; } // W-TRN: campo de treinamento forçado (os troncos) — boot-guard espera o applyArena do boot (race da L5737); outro modo encerra treino anterior
  cleanupBRVisuals(); // PV2: partida DM nova — remove zona/baús de um BR anterior
  let blueRoster, redRoster;
  if (draft && Array.isArray(draft.blue) && draft.blue.filter(Boolean).length === CFG.teamSize &&
      Array.isArray(draft.red) && draft.red.filter(Boolean).length === CFG.teamSize) {
    // W-MENU: draft explicito (pick/lock/reveal) — rosters vindos do DRAFT
    blueRoster = draft.blue.map(draftHeroById).filter(Boolean);
    blueRoster[0] = playerHero; // seguranca: o jogador SEMPRE no slot 0 (isPlayer)
    redRoster = draft.red.map(draftHeroById).filter(Boolean);
    if (blueRoster.length < CFG.teamSize || redRoster.length < CFG.teamSize) {
      // draft degenerado (herois duplicados?) — cai pro shuffle padrao
      for (let i = others.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); const tmp = others[i]; others[i] = others[j]; others[j] = tmp; }
      blueRoster = [playerHero, ...others.slice(0, CFG.teamSize - 1)];
      redRoster = others.slice(CFG.teamSize - 1, 2 * CFG.teamSize - 1);
    }
  } else {
    // Shuffle others so all 12 heroes have equal chance to appear in matches
    for (let i = others.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = others[i]; others[i] = others[j]; others[j] = tmp;
    }
    blueRoster = [playerHero, ...others.slice(0, CFG.teamSize - 1)];
    redRoster = CFG.mode === 'training' ? [] : others.slice(CFG.teamSize - 1, 2 * CFG.teamSize - 1); // W-TRN: treino nao tem time vermelho humano — so bonecos
  }

  const spawnTeam = async (teamRoster, teamName, baseX, baseZ) => {
    const meshes = await Promise.all(teamRoster.map(h => loadCharacter3DModel(h.id)));
    for (let i = 0; i < teamRoster.length; i++) {
      const h = teamRoster[i];
      const isPlayer = (teamName === 'blue' && i === 0);
      const mesh = meshes[i];

      // Team Foot Circle Indicator
      const ringGeo = new THREE.RingGeometry(1.45, 1.85, 32);
      const ringColor = isPlayer ? 0x22c55e : (teamName === 'blue' ? 0x3b82f6 : 0xef4444);
      const ringMesh = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: ringColor, side: THREE.DoubleSide }));
      ringMesh.rotation.x = -Math.PI / 2;
      ringMesh.position.y = 0.08;
      mesh.add(ringMesh);

      // Awakening Chakra Aura (uses the 3D Aura Mesh if available, or sphere)
      const auraMesh = createHeroAwakeningAuraMesh(h.id, h.color || 0xff7b00);
      auraMesh.visible = false;
      mesh.add(auraMesh);

      const offsetAngle = (i / teamRoster.length) * Math.PI * 2;
      const sx = baseX + Math.cos(offsetAngle) * 8;
      const sz = baseZ + Math.sin(offsetAngle) * 8;
      mesh.position.set(sx, 0, sz);
      arenaGroup.add(mesh);

      // Floating HTML World Label
      const labelEl = document.createElement('div');
      labelEl.className = `unit-label ${isPlayer ? 'player' : teamName}`;
      labelEl.innerHTML = `
        <span class="u-name">${isPlayer ? '★ ' + h.name : h.name.split(' ')[0]} <small class="u-lvl">Lv.1</small></span>
        <div class="u-hp-bg"><div class="u-hp-fill" style="width:100%"></div></div>
        <div class="u-ck-bg"><div class="u-ck-fill" style="width:100%"></div></div>
      `;
      document.getElementById('world-labels').appendChild(labelEl);

      const kit = HERO_KITS[h.id] || HERO_KITS['1nrt'];
      const hs = HERO_STATS[h.id] || HERO_STATS.__d; // P2: identidade de combate
      units.push({
        id: `${teamName}_${i}`,
        heroId: h.id,
        name: h.name,
        portrait: h.portrait,
        team: teamName,
        isPlayer,
        mesh,
        auraMesh,
        labelEl,
        kit,
        x: sx,
        z: sz,
        spawnX: sx,
        spawnZ: sz,
        rotY: teamName === 'blue' ? Math.PI / 4 : -3 * Math.PI / 4,
        hp: Math.round(hs.hp * HERO_HP_SCALE), // T5
        maxHp: Math.round(hs.hp * HERO_HP_SCALE), // T5
        chakra: 100,
        maxChakra: 100,
        level: 1,
        kills: 0,
        deaths: 0,
        assists: 0,
        killStreak: 0, // STREAK
        lastKillAt: 0,
        speed: (isPlayer ? 21.5 : 19.5) * hs.spd, // P2
        state: 'idle',
        animTimer: 0,
        animDuration: 0,
        comboStep: 0,
        comboResetTimer: 0,
        awakenedTimer: 0,
        deadTimer: 0,
        spawnShield: 4.0, // SPAWN GUARD: imortalidade curta perto da base
        cds: { atk: 0, q: 0, w: 0, e: 0, r: 0 },
        aiTarget: null,
        aiStrafeDir: Math.random() < 0.5 ? 1 : -1
      });
    }
  };

  const blueBase = basePos('blue');
  const redBase = basePos('red');
  try {
    await Promise.all([
      spawnTeam(blueRoster, 'blue', blueBase.x, blueBase.z),
      spawnTeam(redRoster, 'red', redBase.x, redBase.z)
    ]);
  } catch (err) {
    console.error('[NUBA] FALHA AO SPAWNAR HEROIS:', err); // P0: sem partida zumbi
    matchActive = false;
    showBanner('FALHA AO CARREGAR HEROIS — TENTE NOVAMENTE', 2600);
    return;
  }

  const player = units.find(u => u.isPlayer);
  if (player) {
    tpCamYaw = player.rotY;
    tpCamPitch = 0.32;
  }

  setupHUDPlayerInfo(playerHero);
  renderTopTeamPortraits();
  playMatchIntro(blueRoster, redRoster);
  if (CFG.mode === 'training') await TRN.begin(CFG); // W-TRN: spawna os bonecos apos o player entrar em campo
}

// ============================================================================
// MATCH INTRO: contagem 3-2-1 com retratos + streak banner helpers
// Motor: GSAP (vendor/gsap.min.js) com fallback CSS/timers se ausente
// ============================================================================
let introTimers = []; // TIMERS do intro — limpos em novo intro/endMatch/lobby
let introTl = null;   // timeline GSAP do intro

function cancelMatchIntro() {
  for (const t of introTimers) clearTimeout(t);
  introTimers = [];
  if (introTl) { introTl.kill(); introTl = null; }
  if (window.gsap) {
    window.gsap.killTweensOf('#match-intro, #match-intro *, #streak-banner, #streak-banner *');
    window.gsap.set('#match-intro, #streak-banner', { clearProps: 'transform,opacity' });
  }
  const introEl = document.getElementById('match-intro');
  if (introEl) { introEl.classList.remove('show'); introEl.classList.add('hidden'); }
  const streakEl = document.getElementById('streak-banner');
  if (streakEl) { streakEl.classList.remove('show'); streakEl.classList.add('hidden'); }
}

// FIRE-AND-FORGET: start5v5Match nao espera a sequência (E2E/spawn livres)
function playMatchIntro(blueRoster, redRoster) {
  cancelMatchIntro();
  const introEl = document.getElementById('match-intro');
  const blueSlots = document.getElementById('intro-blue-slots');
  const redSlots = document.getElementById('intro-red-slots');
  const countDigit = document.getElementById('intro-count-digit');
  const finishIntro = () => {
    if (introEl) { introEl.classList.remove('show'); introEl.classList.add('hidden'); }
    showBanner(activeMatchCfg.mode === 'br' ? 'REALEZA NA VILA INICIADO! SOBREVIVA — ÚLTIMO DE PÉ VENCE' : activeMatchCfg.mode === 'training' ? '訓練 CAMPO DE TREINAMENTO — MEÇA SEU DANO, TESTE COMBOS E ENFRENTE O TESTE DOS SINOS' : `${activeMatchCfg.label} EM ${ARENA.label.toUpperCase()} INICIADO! META: ${activeMatchCfg.killTarget} ABATES`);
  };
  if (!introEl || !blueSlots || !redSlots) {
    showBanner(activeMatchCfg.mode === 'br' ? 'REALEZA NA VILA INICIADO! SOBREVIVA — ÚLTIMO DE PÉ VENCE' : activeMatchCfg.mode === 'training' ? '訓練 CAMPO DE TREINAMENTO — MEÇA SEU DANO, TESTE COMBOS E ENFRENTE O TESTE DOS SINOS' : `${activeMatchCfg.label} EM ${ARENA.label.toUpperCase()} INICIADO! META: ${activeMatchCfg.killTarget} ABATES`);
    return;
  }
  const fillSlots = (container, roster) => {
    container.innerHTML = (roster || []).map(h =>
      `<img class="intro-slot" src="${h.portrait}" alt="${h.name}" />`
    ).join('');
  };
  fillSlots(blueSlots, blueRoster);
  fillSlots(redSlots, redRoster);
  if (countDigit) {
    renderSkinDigits(countDigit, '');
    countDigit.style.display = 'none';
  }

  const gsapLib = window.gsap;
  if (!gsapLib) {
    introEl.classList.remove('hidden');
    void introEl.offsetWidth;
    introEl.classList.add('show');
    introTimers.push(setTimeout(() => {
      if (!countDigit) return;
      countDigit.style.display = '';
      renderSkinDigits(countDigit, '3');
    }, 700));
    introTimers.push(setTimeout(() => {
      if (countDigit) renderSkinDigits(countDigit, '2');
    }, 1200));
    introTimers.push(setTimeout(() => {
      if (countDigit) renderSkinDigits(countDigit, '1');
    }, 1700));
    introTimers.push(setTimeout(finishIntro, 2200));
    return;
  }

  introEl.classList.add('gsap-anim');
  introEl.classList.remove('hidden');
  introEl.classList.add('show');
  const blue = introEl.querySelector('.intro-blue');
  const red = introEl.querySelector('.intro-red');
  const vs = introEl.querySelector('.intro-vs');
  const shine = introEl.querySelector('.intro-shine');
  const kanji = introEl.querySelector('.intro-kanji');
  const slots = introEl.querySelectorAll('.intro-slot');
  const tl = gsapLib.timeline({ onComplete: finishIntro });
  introTl = tl;
  tl.fromTo(blue, { x: -90, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: 'back.out(1.5)' }, 0);
  tl.fromTo(red, { x: 90, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: 'back.out(1.5)' }, 0);
  tl.fromTo(slots, { scale: 0.4, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.35, ease: 'back.out(2.4)', stagger: 0.07 }, 0.35);
  tl.fromTo(vs, { scale: 2.4, rotation: -7, opacity: 0 }, { scale: 1, rotation: 0, opacity: 1, duration: 0.45, ease: 'back.out(2.2)' }, 0.35);
  tl.fromTo(shine, { xPercent: -140, skewX: -16, opacity: 1 }, { xPercent: 460, duration: 0.7, ease: 'power2.out' }, 0.5);
  tl.fromTo(kanji, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out' }, 0.2);
  const countPop = (d, at) => {
    tl.add(() => {
      if (!countDigit) return;
      countDigit.style.display = '';
      renderSkinDigits(countDigit, d);
    }, at);
    if (countDigit) {
      tl.fromTo(countDigit,
        { scale: 2.2, opacity: 0, xPercent: -50, yPercent: -50 },
        { scale: 1, opacity: 1, xPercent: -50, yPercent: -50, duration: 0.35, ease: 'back.out(2.4)' },
        at);
    }
  };
  countPop('3', 0.75);
  countPop('2', 1.25);
  countPop('1', 1.75);
  tl.add(() => {
    if (!countDigit) return;
    renderSkinDigits(countDigit, '');
    countDigit.style.display = 'none';
  }, 2.25);
}

function showStreakBanner(unit) {
  const tier = unit ? (unit.killStreak || 0) : 0;
  if (tier < 2) return;
  const banner = document.getElementById('streak-banner');
  if (!banner) return;
  const label = tier === 2 ? 'SEQUÊNCIA' : tier === 3 ? 'FURIA' : tier === 4 ? 'MASACRE' : 'LENDÁRIO';
  const textEl = banner.querySelector('.streak-text');
  const countEl = banner.querySelector('.streak-count');
  if (textEl) textEl.textContent = label;
  if (countEl) countEl.textContent = `${tier}x`;
  pulseSkinHook('streak-banner', 1600);
  // W7: toast no canto — spring física (Motion) com fallback GSAP; flare desativado
  w7Spring(banner, { opacity: [0, 1], scale: [0.94, 1], y: [-10, 0] }, { stiffness: 380, damping: 26 });
}

const SKIN_URL = 'assets/ui/skin/';
let skinManifest = null;
let matchClockText = '05:00';
let lastRenderedClock = '';

function renderSkinDigits(el, text) {
  if (!el) return;
  const value = text === null || text === undefined ? '' : String(text);
  el.dataset.value = value;
  el.setAttribute('aria-label', value);
  const wantSkin = Boolean(skinManifest);
  if (el._skinValue === value && el._skinMode === wantSkin) return;
  el._skinValue = value;
  el._skinMode = wantSkin;
  if (!skinManifest) {
    el._skinShape = null;
    el.textContent = value;
    return;
  }
  const shape = [...value].map(ch => (ch >= '0' && ch <= '9') ? 'd' : (ch === ':' ? ':' : 't')).join('');
  if (el._skinShape === shape && el.children.length === value.length) {
    [...value].forEach((ch, i) => {
      const node = el.children[i];
      if (ch >= '0' && ch <= '9') {
        const src = `${SKIN_URL}digit_${ch}.png`;
        if (node.getAttribute('src') !== src) {
          node.src = src;
          node.dataset.digit = ch;
          node.alt = ch;
        }
      } else if (ch !== ':' && node.textContent !== ch) {
        node.textContent = ch;
      }
    });
    return;
  }
  el.textContent = '';
  el._skinShape = shape;
  for (const ch of value) {
    if (ch >= '0' && ch <= '9') {
      const digit = document.createElement('img');
      digit.className = 'skin-digit';
      digit.dataset.digit = ch;
      digit.alt = ch;
      digit.src = `${SKIN_URL}digit_${ch}.png`;
      el.appendChild(digit);
    } else if (ch === ':') {
      const sep = document.createElement('span');
      sep.className = 'skin-digit-sep';
      sep.textContent = ':';
      el.appendChild(sep);
    } else {
      el.appendChild(document.createTextNode(ch));
    }
  }
}

function pulseSkinHook(id, duration) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('hidden');
  void el.offsetWidth;
  el.classList.add('show');
  if (el._skinHideTimer) clearTimeout(el._skinHideTimer);
  el._skinHideTimer = setTimeout(() => {
    el.classList.remove('show');
    el.classList.add('hidden');
  }, duration);
}

function showOugiBanner() {
  pulseSkinHook('ougi-banner', 1400);
}

function flashKawarimi() {
  pulseSkinHook('kawarimi-flash', 320);
}

function loadSkinManifest() {
  return fetch(`${SKIN_URL}skin.json`)
    .then(res => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
    .then(data => {
      skinManifest = (data && typeof data === 'object') ? data : {};
      document.documentElement.style.setProperty('--skin-has-manifest', '1');
      console.info(`[skin] manifesto carregado: ${Object.keys(skinManifest).length} assets de skin`);
    })
    .catch(() => {
      skinManifest = null;
      console.warn('[skin] skin.json ausente — HUD mantem texto puro');
    });
}

function setupHUDPlayerInfo(hero) {
  document.getElementById('hud-player-portrait').src = hero.portrait;
  const kit = HERO_KITS[hero.id] || HERO_KITS['1nrt'];
  document.getElementById('sk-name-atk').textContent = kit.atk.name;
  document.getElementById('sk-name-q').textContent = kit.q.name;
  document.getElementById('sk-name-w').textContent = kit.w.name;
  document.getElementById('sk-name-e').textContent = kit.e.name;
  document.getElementById('sk-name-r').textContent = kit.r.name;
}

function renderTopTeamPortraits() {
  const blueEl = document.getElementById('hud-blue-icons');
  const redEl = document.getElementById('hud-red-icons');
  if (!blueEl || !redEl) return;
  blueEl.innerHTML = units.filter(u => u.team === 'blue').map(u => `
    <div class="mini-p ${u.deadTimer > 0 ? 'dead' : ''}" id="top-icon-${u.id}">
      <img src="${u.portrait}" alt="${u.name}" />
      <span class="alive-dot"></span>
      <span class="respawn-countdown" id="respawn-cd-${u.id}">${u.deadTimer > 0 ? Math.ceil(u.deadTimer) : ''}</span>
    </div>
  `).join('');
  redEl.innerHTML = units.filter(u => u.team === 'red').map(u => `
    <div class="mini-p ${u.deadTimer > 0 ? 'dead' : ''}" id="top-icon-${u.id}">
      <img src="${u.portrait}" alt="${u.name}" />
      <span class="alive-dot"></span>
      <span class="respawn-countdown" id="respawn-cd-${u.id}">${u.deadTimer > 0 ? Math.ceil(u.deadTimer) : ''}</span>
    </div>
  `).join('');

  for (const u of units) {
    if (u.deadTimer > 0) renderSkinDigits(document.getElementById(`respawn-cd-${u.id}`), Math.ceil(u.deadTimer));
  }
}

function showBanner(text, duration = 2100) {
  const el = document.getElementById('center-banner');
  el.textContent = text;
  el.classList.remove('hidden');
  w7Spring(el, { opacity: [0, 1], scale: [0.94, 1], x: ['-50%', '-50%'], y: ['-50%', '-50%'] },
    { stiffness: 520, damping: 34 }); // W7: pill com spring pop (Motion)
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), duration);
}

const KILL_FEED_JP = {
  // Q/W/R por heroi + atk basico (kanji autenticos Storm)
  'Rasengan!': '螺旋丸', 'Kage Bunshin no Jutsu': '影分身', 'Kawarimi (Substituição)': '替わり', 'Oodama Rasengan + Kyuubi': '大玉螺旋丸',
  'Chidori (Mil Pássaros)': '千鳥', 'Katon: Gokakyu no Jutsu': '火遁・豪火球', 'Sharingan Kawarimi': '写輪眼', 'Kirin + Marca da Maldição': '麒麟',
  'Oukahou (Impacto da Flor)': '桜花衝', 'Ninjutsu Médico (Cura em Área)': '掌仙術', 'Kawarimi no Jutsu': '替わり', 'Força de Uma Centena (Byakugou)': '百豪',
  'Raikiri (Corte Relâmpago)': '雷切', 'Suiton: Suiryudan no Jutsu': '水遁・水龍弾', 'Raiton Kage Bunshin': '雷遁影分身', 'Kamui (Mangekyo Sharingan)': '神威',
  'Konoha Senpuu (Furacão da Folha)': '木ノ葉旋風', 'Omote Renge (Lótus Primária)': '表蓮華', 'Retirada Pesos de Treino': '瞬身', 'Ura Renge (Oito Portões Internos)': '裏蓮華',
  'Amaterasu (Chamas Negras)': '天照', 'Katon: Gokakyu + Clone Explosivo': '火遁・爆分身', 'Genjutsu de Corvos': '幻術・烏', 'Tsukuyomi + Susanoo': '月読',
  'Sabaku Kyuu (Caixão de Areia)': '砂縛柩', 'Suna no Tate (Escudo Absoluto)': '砂の盾', 'Substituição de Areia': '砂替わり', 'Sabaku Taisou + Shukaku': '砂漠大葬',
  'Shugohakke Rokujuyonsho': '守護八卦六十四掌', 'Punho dos Leões Gêmeos': '双獅拳', 'Byakugan Kawarimi': '白眼', 'Oito Trigramas: Leões Gêmeos Supremos': '双獅拳・極',
  'Hakkeshō Kaiten (Rotação)': '回天', 'Hakke Kuusho (Palma de Ar)': '八卦空掌', 'Byakugan Evasão': '白眼', 'Oito Trigramas: 64 Golpes': '八卦六十四掌',
  'Katon: Gamayu Endan': '蛤蟆油弾', 'Hari Jizo (Escudo de Espinhos)': '針地蔵', 'Kawarimi do Sapo': '蛤蟇替わり', 'Chou Oodama Rasengan + Modo Sennin': '仙法・大玉螺旋丸',
  'Combo Uzumaki + Kunai': '打撃', 'Uchiha Taijutsu + Shuriken': '手裏剣', 'Punho de Chakra Concentrado': '拳', 'Kunai Relâmpago + Taijutsu': '雷遁',
  'Punho Forte Acelerado': '木ノ葉拳', 'Shuriken Uchiha + Corvos': '烏', 'Rajada de Areia': '砂', 'Punho Gentil (Juken)': '柔拳',
  'Juken: Golpe de Tenketsu': '柔拳', 'Taijutsu Eremita dos Sapos': '仙法'
}; // M4.2 HUD PASS: kanji do kill-feed

function addKillFeed(killer, victim, skillName) {
  const feed = document.getElementById('kill-feed');
  if (!feed) return;
  const item = document.createElement('div');
  item.className = 'kill-toast';
  const kColor = killer.team === 'blue' ? '#60a5fa' : '#f87171';
  const vColor = victim.team === 'blue' ? '#60a5fa' : '#f87171';
  const kName = killer.name.split(' ')[0];
  const vName = victim.name.split(' ')[0];
  const baseSkill = String(skillName || '').replace(/\s*\[.*\]\s*$/, ''); // M4.2 HUD PASS
  const jpHtml = KILL_FEED_JP[baseSkill] ? ` <span class="feed-jp">${KILL_FEED_JP[baseSkill]}</span>` : '';
  const streakHtml = (killer.killStreak || 0) >= 2 ? `<span class="feed-streak">x${killer.killStreak}</span>` : ''; // STREAK
  item.innerHTML = `
    <img class="feed-portrait" src="${killer.portrait}" alt="${kName}" />
    <span class="feed-name" style="color:${kColor}">${kName}</span>
    <span class="feed-ability-tag">[${skillName}]</span>${jpHtml}
    <span class="feed-arrow">➔</span>
    <img class="feed-portrait" src="${victim.portrait}" alt="${vName}" />
    <span class="feed-name" style="color:${vColor}">${vName}</span>${streakHtml}
  `;
  feed.prepend(item);
  while (feed.children.length > 5) feed.lastChild.remove();

  setTimeout(() => {
    item.classList.add('fade-out');
  }, 4200);

  setTimeout(() => {
    if (item.parentNode) item.remove();
  }, 4700);
}

// ============================================================================
// 3D SKILL VFX & COMBAT JUTSU ENGINE
// ============================================================================
function buildExtractedVfxMeshGroup(heroId, colorHex, targetScale = 0.08, modelName = null) {
  const vfxDef = skillVfxData[heroId] || skillVfxData['common'] || skillVfxData['1ssk'] || skillVfxData['1gar'];
  if (!vfxDef) return null;

  let meshesToUse = null;
  if (modelName && vfxDef.models && vfxDef.models[modelName]) {
    meshesToUse = vfxDef.models[modelName];
  } else if (modelName && skillVfxData['common'] && skillVfxData['common'].models && skillVfxData['common'].models[modelName]) {
    meshesToUse = skillVfxData['common'].models[modelName];
  } else if (vfxDef.meshes && vfxDef.meshes.length > 0) {
    meshesToUse = vfxDef.meshes.slice(0, 3);
  } else if (skillVfxData['common'] && skillVfxData['common'].models) {
    meshesToUse = skillVfxData['common'].models['1efc_chakra00'] || null;
  }
  if (!meshesToUse || meshesToUse.length === 0) return null;

  const grp = new THREE.Group();
  grp.scale.setScalar(targetScale);
  let _bx0 = 1e9, _bx1 = -1e9, _by0 = 1e9, _by1 = -1e9, _bz0 = 1e9, _bz1 = -1e9; // W-VIS-ALL bbox

  for (const sm of meshesToUse) {
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(sm.positions), 3));
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
    }
    if (sm.uvs && sm.uvs.length > 0) {
      geom.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(sm.uvs), 2));
    }
    if (sm.indices && sm.indices.length > 0) {
      geom.setIndex(sm.indices);
    }

    const texPath = sm.texture ? `assets/${sm.texture}` : 'assets/skills/1efc_chakra00.png';
    const mapTex = loadTex(texPath);
    const mat = new THREE.MeshBasicMaterial({
      map: mapTex,
      color: colorHex || 0xffffff,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide
    });
    const m = new THREE.Mesh(geom, mat);
    grp.add(m);
    const _pos = geom.getAttribute('position');
    for (let _i = 0; _i < _pos.count; _i++) {
      const _vx = _pos.getX(_i), _vy = _pos.getY(_i), _vz = _pos.getZ(_i);
      if (_vx < _bx0) _bx0 = _vx; if (_vx > _bx1) _bx1 = _vx;
      if (_vy < _by0) _by0 = _vy; if (_vy > _by1) _by1 = _vy;
      if (_vz < _bz0) _bz0 = _vz; if (_vz > _bz1) _bz1 = _vz;
    }
  }
  // W-VIS-ALL: bbox raw dos modelos extraidos varia de ~17u a ~472u — escala
  // fixa deixava rasengan gigante e caco micro. Normaliza: extent final do
  // grupo ~ targetScale * 250u (chakra medio), proporcional em TODAS as skills.
  const _ext = Math.max(_bx1 - _bx0, _by1 - _by0, _bz1 - _bz0);
  if (_ext > 1) grp.scale.setScalar(targetScale * (250 / _ext));
  return grp;
}

function createHeroAwakeningAuraMesh(heroId, colorHex) {
  const grp = new THREE.Group();
  const aura = buildExtractedVfxMeshGroup(heroId, colorHex, 0.065) ||
               buildExtractedVfxMeshGroup('common', colorHex, 0.065, '1efc_chakra05');
  if (aura) {
    aura.position.y = 2.2;
    aura.userData.rotSpeed = new THREE.Vector3(0, 6, 0);
    grp.add(aura);
  }
  const ring = buildExtractedVfxMeshGroup('common', colorHex, 0.010, '1efc_ring01');
  if (ring) {
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.12;
    ring.userData.rotSpeed = new THREE.Vector3(0, 0, 10);
    grp.add(ring);
  }
  return grp;
}

// ==================== SPP: CLONES DAS SOMBRAS 3D (Kage Bunshin) ====================
function spawnShadowClones(caster, count, contactDmg) {
  for (let i = 0; i < count; i++) {
    let mesh = null;
    try { mesh = cloneCharacterModel(modelCache.get(caster.heroId), caster.heroId); } catch (e) { window.__sppCloneErr = String(e && e.message ? e.message : e); mesh = null; }
    if (!mesh) break;
    const ang = caster.rotY + (i === 0 ? 0 : (i % 2 ? 0.7 : -0.7) * Math.ceil(i / 2));
    const cx = caster.x + Math.sin(ang) * 2.2;
    const cz = caster.z + Math.cos(ang) * 2.2;
    mesh.position.set(cx, 0, cz);
    mesh.rotation.y = ang;
    mesh.traverse(cn => { if (cn.material) { cn.material = cn.material.clone(); cn.material.transparent = true; cn.material.opacity = 0.85; } });
    arenaGroup.add(mesh);
    spawnVFX(cx, 1.4, cz, 0xd9d9e3, 2.6, 0.35, 'sphere', caster.heroId); // poof de invocacao
    shadowClones.push({ mesh, x: cx, z: cz, rotY: ang, team: caster.team, heroId: caster.heroId, owner: caster, dmg: contactDmg, ttl: 4.5 });
  }
}
function updateShadowClones(dt) {
  for (let i = shadowClones.length - 1; i >= 0; i--) {
    const c = shadowClones[i];
    c.ttl -= dt;
    let target = null, bd = 999; // SPP: clones perseguem atraves da arena (licao M6.2)
    for (const e of units) { if (e.team !== c.team && e.deadTimer <= 0) { const d = Math.hypot(e.x - c.x, e.z - c.z); if (d < bd) { bd = d; target = e; } } }
    if (target) {
      const dx = target.x - c.x, dz = target.z - c.z, L = Math.hypot(dx, dz) || 1;
      c.rotY = Math.atan2(dx, dz);
      const spd = 14 * dt;
      c.x += (dx / L) * spd; c.z += (dz / L) * spd;
      if (L < 2.4) {
        dealDamage(c.owner, target, c.dmg, 'Kage Bunshin no Jutsu');
        spawnVFX(c.x, 1.6, c.z, 0xff9900, 2.2, 0.3, 'sphere', c.heroId);
        c.ttl = -1;
      }
    }
    if (c.ttl <= 0) {
      spawnVFX(c.x, 1.4, c.z, 0xd9d9e3, 2.6, 0.35, 'sphere', c.heroId); // poof final
      arenaGroup.remove(c.mesh);
      shadowClones.splice(i, 1);
      continue;
    }
    c.mesh.position.set(c.x, 0, c.z);
    c.mesh.rotation.y = c.rotY;
    animateCharacterRig(c.mesh, 'run', performance.now() / 1000, 0, 0.42); // SPP: corrida real
  }
}

function findNearestEnemy(unit, maxDist = 45) {
  let best = null;
  let bestD = maxDist;
  for (const other of units) {
    if (other.team === unit.team || other.deadTimer > 0) continue;
    const d = Math.hypot(other.x - unit.x, other.z - unit.z);
    if (d < bestD) {
      bestD = d;
      best = other;
    }
  }
  return best;
}

function spawnVFX(x, y, z, color, radius = 3.5, duration = 0.45, style = 'sphere', heroId = null) {
  // Spawn 3D VFX mesh alongside procedural shockwave
  if (heroId && (style === 'sphere' || style === 'pillar' || style === 'ring')) {
    const extGrp = buildExtractedVfxMeshGroup(heroId, color, radius * 0.006, activeSkillVfxModel); // M7 // W-VIS-ALL: extent ~ radius*1.5u
    if (extGrp) {
      extGrp.position.set(x, y, z);
      arenaGroup.add(extGrp);
      if (activeSkillVfxFaceY !== null) extGrp.rotation.y = activeSkillVfxFaceY; // SPP: direcao do cast
      vfxList.push({ mesh: extGrp, age: 0, duration: duration * 1.7, style: 'extracted', anim: activeSkillVfxAnim, faceDir: activeSkillVfxFaceY !== null ? { x: Math.sin(activeSkillVfxFaceY), z: Math.cos(activeSkillVfxFaceY) } : null }); // SPP
    }
  }

  let geo;
  let op = 0.40;
  if (style === 'ring') {
    geo = new THREE.TorusGeometry(radius * 0.5, 0.08, 6, 24);
    op = 0.45;
  } else if (style === 'pillar') {
    geo = new THREE.CylinderGeometry(radius * 0.12, radius * 0.18, radius * 1.6, 12);
    op = 0.35;
  } else {
    geo = new THREE.IcosahedronGeometry(radius * 0.32, 1);
    op = 0.35;
  }
  const mat = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: op,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    wireframe: false
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(x, y, z);
  if (style === 'ring') mesh.rotation.x = Math.PI / 2;
  arenaGroup.add(mesh);
  vfxList.push({ mesh, age: 0, duration, style });
}

// ============================================================================
// 3D NINJA WEAPONS (SHURIKEN & KUNAI) & CUSTOM JUTSU VFX GENERATORS
// ============================================================================
function createShurikenMesh() {
  const shape = new THREE.Shape();
  const numPoints = 4;
  const rOuter = 0.82;
  const rInner = 0.24;
  for (let i = 0; i < numPoints * 2; i++) {
    const angle = (i * Math.PI) / numPoints;
    const r = (i % 2 === 0) ? rOuter : rInner;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r;
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();

  const holePath = new THREE.Path();
  holePath.absarc(0, 0, 0.11, 0, Math.PI * 2, true);
  shape.holes.push(holePath);

  const extrudeSettings = {
    depth: 0.05,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 1,
    bevelSize: 0.03,
    bevelThickness: 0.03
  };
  const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
  geo.center();
  const mat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    metalness: 0.92,
    roughness: 0.22,
    side: THREE.DoubleSide
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.rotation.x = Math.PI / 2;
  return mesh;
}

function createKunaiMesh() {
  const grp = new THREE.Group();
  const bladeShape = new THREE.Shape();
  bladeShape.moveTo(0, 1.35);
  bladeShape.lineTo(0.24, 0.45);
  bladeShape.lineTo(0.10, 0.0);
  bladeShape.lineTo(-0.10, 0.0);
  bladeShape.lineTo(-0.24, 0.45);
  bladeShape.closePath();

  const bladeGeo = new THREE.ExtrudeGeometry(bladeShape, {
    depth: 0.05,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 1,
    bevelSize: 0.03,
    bevelThickness: 0.03
  });
  bladeGeo.center();
  const steelMat = new THREE.MeshStandardMaterial({
    color: 0x334155,
    metalness: 0.88,
    roughness: 0.24
  });
  const bladeMesh = new THREE.Mesh(bladeGeo, steelMat);
  bladeMesh.position.y = 0.68;
  grp.add(bladeMesh);

  const collarGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.08, 12);
  const collarMesh = new THREE.Mesh(collarGeo, steelMat);
  collarMesh.position.y = 0.0;
  grp.add(collarMesh);

  const handleGeo = new THREE.CylinderGeometry(0.065, 0.065, 0.75, 10);
  const handleMat = new THREE.MeshStandardMaterial({
    color: 0xf8fafc,
    roughness: 0.85,
    metalness: 0.05
  });
  const handleMesh = new THREE.Mesh(handleGeo, handleMat);
  handleMesh.position.y = -0.42;
  grp.add(handleMesh);

  const ringGeo = new THREE.TorusGeometry(0.13, 0.035, 8, 16);
  const ringMesh = new THREE.Mesh(ringGeo, steelMat);
  ringMesh.position.y = -0.88;
  grp.add(ringMesh);

  grp.scale.setScalar(1.25);
  return grp;
}

function createProceduralLightningArcs(radius = 1.35, count = 10, color = 0x93c5fd) {
  const segmentsPerArc = 5;
  const totalPoints = count * segmentsPerArc * 2;
  const positions = new Float32Array(totalPoints * 3);
  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  function randomizeArcs() {
    let pIdx = 0;
    for (let a = 0; a < count; a++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const sinPhi = Math.sin(phi);
      const startR = radius * (0.35 + Math.random() * 0.25);
      const endR = radius * (1.15 + Math.random() * 0.55);

      const sX = startR * sinPhi * Math.cos(theta);
      const sY = startR * sinPhi * Math.sin(theta);
      const sZ = startR * Math.cos(phi);

      const thetaE = theta + (Math.random() - 0.5) * 1.2;
      const phiE = phi + (Math.random() - 0.5) * 1.2;
      const eX = endR * Math.sin(phiE) * Math.cos(thetaE);
      const eY = endR * Math.sin(phiE) * Math.sin(thetaE);
      const eZ = endR * Math.cos(phiE);

      let prevX = sX, prevY = sY, prevZ = sZ;
      for (let s = 1; s <= segmentsPerArc; s++) {
        const frac = s / segmentsPerArc;
        let curX = sX + (eX - sX) * frac;
        let curY = sY + (eY - sY) * frac;
        let curZ = sZ + (eZ - sZ) * frac;
        if (s < segmentsPerArc) {
          const jitter = radius * 0.32;
          curX += (Math.random() - 0.5) * jitter;
          curY += (Math.random() - 0.5) * jitter;
          curZ += (Math.random() - 0.5) * jitter;
        }
        positions[pIdx++] = prevX;
        positions[pIdx++] = prevY;
        positions[pIdx++] = prevZ;
        positions[pIdx++] = curX;
        positions[pIdx++] = curY;
        positions[pIdx++] = curZ;
        prevX = curX;
        prevY = curY;
        prevZ = curZ;
      }
    }
    geom.attributes.position.needsUpdate = true;
  }

  randomizeArcs();
  const mat = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.95,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
  const lines = new THREE.LineSegments(geom, mat);
  let arcTimer = 0;
  lines.userData = {
    updateArcs: function(dt) {
      arcTimer += dt;
      if (arcTimer > 0.04) {
        arcTimer = 0;
        randomizeArcs();
      }
    }
  };
  return lines;
}

function createRasenganMesh(radius = 1.0, color = 0x00d4ff) {
  const grp = new THREE.Group();
  const core = buildExtractedVfxMeshGroup('1nrt', color, radius * 0.011, '1nrveff1_chakra01') ||
               buildExtractedVfxMeshGroup('1nrt', color, radius * 0.011, 'rasengan') ||
               buildExtractedVfxMeshGroup('common', color, radius * 0.011, '1efc_chakra00');
  if (core) {
    core.userData.rotSpeed = new THREE.Vector3(0, 15, 0);
    core.userData.uvScroll = { x: 0.5, y: 1.1 };
    grp.add(core);
  }
  const outer = buildExtractedVfxMeshGroup('1nrt', color, radius * 0.013, 'spl_rasengan');
  if (outer) {
    outer.userData.rotSpeed = new THREE.Vector3(0, -9, 0);
    outer.userData.uvScroll = { x: -0.3, y: 0.8 };
    grp.add(outer);
  }
  return grp;
}

function createChidoriMesh(radius = 0.95, color = 0x60a5fa) {
  const grp = new THREE.Group();
  const body = buildExtractedVfxMeshGroup('1ssk', color, radius * 0.012, '1szneff_chak01') ||
               buildExtractedVfxMeshGroup('1ssk', color, radius * 0.012, 'chidori_spark') ||
               buildExtractedVfxMeshGroup('common', color, radius * 0.012, '1efc_spk01');
  if (body) {
    body.userData.rotSpeed = new THREE.Vector3(4, 10, 3);
    body.userData.jitter = 0.30;
    body.userData.uvScroll = { x: 0.2, y: 1.6 };
    grp.add(body);
  }
  const sparks = buildExtractedVfxMeshGroup('common', color, radius * 0.009, '1efc_spk01');
  if (sparks) {
    sparks.userData.rotSpeed = new THREE.Vector3(0, 22, 0);
    sparks.userData.jitter = 0.5;
    grp.add(sparks);
  }
  return grp;
}

function createKaitenMesh(radius = 3.2) {
  const grp = new THREE.Group();
  const dome = buildExtractedVfxMeshGroup('1nej', 0x60a5fa, radius * 0.026, 'kaiten_dome') ||
               buildExtractedVfxMeshGroup('common', 0x60a5fa, radius * 0.026, '1efc_wind01');
  if (dome) {
    dome.userData.rotSpeed = new THREE.Vector3(0, 24, 0);
    dome.userData.uvScroll = { x: 2.5, y: 1.0 };
    grp.add(dome);
  }
  const dust = buildExtractedVfxMeshGroup('common', 0xbae6fd, radius * 0.022, '1efc_shock01');
  if (dust) {
    dust.rotation.x = -Math.PI / 2;
    dust.position.y = 0.12;
    dust.userData.rotSpeed = new THREE.Vector3(0, 0, 12);
    grp.add(dust);
  }
  return grp;
}

function createSandShieldMesh(radius = 3.0) {
  const grp = new THREE.Group();
  const base = buildExtractedVfxMeshGroup('1gar', 0xd97706, radius * 0.018, '1gareff1_bd_snd02') ||
               buildExtractedVfxMeshGroup('1gar', 0xd97706, radius * 0.018, 'sand_dust');
  if (base) { base.rotation.x = -Math.PI / 2; grp.add(base); }
  for (let i = 0; i < 3; i++) {
    const wall = buildExtractedVfxMeshGroup('1gar', 0xd97706, radius * 0.022, '1gareff1_snd14') ||
                 buildExtractedVfxMeshGroup('1gar', 0xd97706, radius * 0.022, '1gareff1_snd13');
    if (!wall) break;
    wall.rotation.y = (i * Math.PI * 2) / 3;
    wall.userData.rotSpeed = new THREE.Vector3(0, -5, 2);
    wall.userData.uvScroll = { x: 0.4, y: 0.2 };
    grp.add(wall);
  }
  return grp;
}

function createSandHandMesh(scale = 0.12) {
  const grp = new THREE.Group();
  const hand = buildExtractedVfxMeshGroup('1gar', 0xd97706, scale, '1gareff1_hnd01_body');
  if (hand) {
    hand.rotation.x = -Math.PI / 2;
    grp.add(hand);
  }
  const geyser = buildExtractedVfxMeshGroup('1gar', 0xd97706, scale * 1.1, '1gareff1_snd07') ||
                 buildExtractedVfxMeshGroup('1gar', 0xd97706, scale * 1.1, '1gareff1_snd02');
  if (geyser) {
    geyser.rotation.x = -Math.PI / 2;
    geyser.userData.rotSpeed = new THREE.Vector3(0, 0, 9);
    grp.add(geyser);
  }
  return grp;
}

function createAmaterasuMesh(radius = 4.2) {
  const grp = new THREE.Group();
  const flameA = buildExtractedVfxMeshGroup('1ssk', 0x7f1d1d, radius * 0.020, '1ssveff1_fire06');
  if (flameA) {
    flameA.position.y = radius * 1.3;
    flameA.userData.rotSpeed = new THREE.Vector3(0, 5, 0);
    flameA.userData.uvScroll = { x: 0, y: 3.4 };
    grp.add(flameA);
  }
  const flameB = buildExtractedVfxMeshGroup('1ssk', 0x991b1b, radius * 0.023, '1ssveff1_fire01');
  if (flameB) {
    flameB.position.y = radius * 0.7;
    flameB.userData.rotSpeed = new THREE.Vector3(0, -4, 0);
    flameB.userData.uvScroll = { x: 0.1, y: 2.6 };
    grp.add(flameB);
  }
  const core = buildExtractedVfxMeshGroup('1itc', 0x450a0a, radius * 0.016, 'amaterasu_flame') ||
               buildExtractedVfxMeshGroup('common', 0x450a0a, radius * 0.016, '1efc_fire03');
  if (core) {
    core.position.y = radius * 0.5;
    core.userData.uvScroll = { x: 0, y: 2.2 };
    grp.add(core);
  }
  return grp;
}

function createLionFistMesh(radius = 1.35) {
  const grp = new THREE.Group();
  const lion = buildExtractedVfxMeshGroup('1hnt', 0x8b5cf6, radius * 0.013, 'lion_chakra') ||
               buildExtractedVfxMeshGroup('common', 0x8b5cf6, radius * 0.013, '1efc_chakra04');
  if (lion) {
    lion.userData.rotSpeed = new THREE.Vector3(0, 10, 0);
    lion.userData.jitter = 0.12;
    lion.userData.uvScroll = { x: 0.1, y: 1.8 };
    grp.add(lion);
  }
  return grp;
}

function createTornadoMesh(radius = 4.2) {
  const grp = new THREE.Group();
  const funnel = buildExtractedVfxMeshGroup('1roc', 0x22c55e, radius * 0.022, 'air_tornado') ||
                 buildExtractedVfxMeshGroup('common', 0x4ade80, radius * 0.022, '1efc_wind02');
  if (funnel) {
    funnel.position.y = radius * 1.1;
    funnel.userData.rotSpeed = new THREE.Vector3(0, 20, 0);
    funnel.userData.uvScroll = { x: 1.6, y: 2.0 };
    grp.add(funnel);
  }
  const gust = buildExtractedVfxMeshGroup('1roc', 0x86efac, radius * 0.024, 'whirlwind') ||
               buildExtractedVfxMeshGroup('common', 0x86efac, radius * 0.024, '1efc_wind01');
  if (gust) {
    gust.position.y = radius * 0.5;
    gust.userData.rotSpeed = new THREE.Vector3(0, -14, 0);
    grp.add(gust);
  }
  return grp;
}

function createFireballMesh(radius = 2.4, color = 0xff5500) {
  const grp = new THREE.Group();
  const body = buildExtractedVfxMeshGroup('1ssk', color, radius * 0.021, '1ssveff1_fire03') ||
               buildExtractedVfxMeshGroup('1ssk', color, radius * 0.021, 'fireball') ||
               buildExtractedVfxMeshGroup('common', color, radius * 0.021, '1efc_fire03');
  if (body) {
    body.userData.rotSpeed = new THREE.Vector3(3, 9, 2);
    body.userData.uvScroll = { x: 0.2, y: 2.6 };
    grp.add(body);
  }
  const tail = buildExtractedVfxMeshGroup('1ssk', color, radius * 0.017, '1ssveff1_fire05') ||
               buildExtractedVfxMeshGroup('common', color, radius * 0.017, '1efc_fire03');
  if (tail) {
    tail.position.z = -radius * 0.8;
    tail.userData.rotSpeed = new THREE.Vector3(0, -7, 0);
    tail.userData.uvScroll = { x: 0, y: 1.6 };
    grp.add(tail);
  }
  return grp;
}

function createWaterDragonMesh(radius = 2.8) {
  const grp = new THREE.Group();
  const dragon = buildExtractedVfxMeshGroup('1kks', 0x0ea5e9, radius * 0.024, 'water_dragon') ||
                 buildExtractedVfxMeshGroup('common', 0x0ea5e9, radius * 0.024, '1efc_wtr02');
  if (dragon) {
    dragon.userData.rotSpeed = new THREE.Vector3(0, 0, 14);
    dragon.userData.uvScroll = { x: 0, y: 3.2 };
    grp.add(dragon);
  }
  const foam = buildExtractedVfxMeshGroup('common', 0xbae6fd, radius * 0.016, '1efc_wav01');
  if (foam) {
    foam.position.z = -radius * 1.2;
    foam.rotation.x = -Math.PI / 2;
    grp.add(foam);
  }
  return grp;
}

function createGroundShatterMesh(radius = 5.5) {
  const grp = new THREE.Group();
  const fist = buildExtractedVfxMeshGroup('1skr', 0xf43f5e, radius * 0.028, '1skneff_fist01');
  if (fist) {
    fist.position.y = radius * 0.75;
    fist.userData.rotSpeed = new THREE.Vector3(0, 8, 0);
    fist.userData.jitter = 0.10;
    grp.add(fist);
  }
  const shock = buildExtractedVfxMeshGroup('1skr', 0xff5c8a, radius * 0.018, 'shatter') ||
                buildExtractedVfxMeshGroup('common', 0xff5c8a, radius * 0.018, '1efc_brk01_02');
  if (shock) {
    shock.rotation.x = -Math.PI / 2;
    shock.position.y = 0.15;
    grp.add(shock);
  }
  return grp;
}

function createToadOilFlameMesh(radius = 3.2) {
  const grp = new THREE.Group();
  const flame = buildExtractedVfxMeshGroup('1jry', 0xf97316, radius * 0.024, '1jryeff01') ||
               buildExtractedVfxMeshGroup('common', 0xf97316, radius * 0.024, '1efc_fire03');
  if (flame) {
    flame.position.z = radius * 1.2;
    flame.userData.rotSpeed = new THREE.Vector3(0, 0, 7);
    flame.userData.uvScroll = { x: 0, y: 3.4 };
    grp.add(flame);
  }
  const smoke = buildExtractedVfxMeshGroup('1jry', 0x94a3b8, radius * 0.016, '1jryeff02');
  if (smoke) {
    smoke.position.z = radius * 2.2;
    smoke.position.y = radius * 0.6;
    smoke.userData.rotSpeed = new THREE.Vector3(0, 4, 0);
    grp.add(smoke);
  }
  return grp;
}

function createKirinMesh(x, z) {
  const grp = new THREE.Group();
  grp.position.set(x, 0, z);
  const bolt = buildExtractedVfxMeshGroup('1kks', 0x93c5fd, 0.28, '1kmmeff1_blt01') ||
               buildExtractedVfxMeshGroup('common', 0x93c5fd, 0.28, '1efc_spk03');
  if (bolt) {
    bolt.position.y = 26;
    bolt.userData.rotSpeed = new THREE.Vector3(0, 26, 0);
    bolt.userData.uvScroll = { x: 0, y: 6.5 };
    grp.add(bolt);
  }
  const shock = buildExtractedVfxMeshGroup('common', 0x60a5fa, 0.030, '1efc_shock01');
  if (shock) {
    shock.rotation.x = -Math.PI / 2;
    shock.position.y = 0.2;
    shock.userData.rotSpeed = new THREE.Vector3(0, 0, 16);
    grp.add(shock);
  }
  return grp;
}

function createTsunadeUltRuptureMesh(radius = 5.5) {
  const grp = new THREE.Group();
  // Ground rupture fracture mesh (1efc_grd01 / 1efc_brk01)
  const rupture = buildExtractedVfxMeshGroup('common', 0x10b981, radius * 0.022, '1efc_grd01') ||
                  buildExtractedVfxMeshGroup('common', 0x10b981, radius * 0.022, '1efc_brk01_01');
  if (rupture) {
    rupture.position.y = 0.05;
    grp.add(rupture);
  }

  // Emerald & gold celestial healing & shockwave disc burst
  const shockTex = loadTex('assets/skills/1efc_shock02.png');
  const shockRing = new THREE.Mesh(
    new THREE.RingGeometry(1.0, radius * 1.15, 32),
    new THREE.MeshBasicMaterial({
      color: 0x10b981,
      map: shockTex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.78,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  );
  shockRing.rotation.x = -Math.PI / 2;
  shockRing.position.y = 0.08;
  shockRing.userData = { rotSpeed: new THREE.Vector3(0, 0, 12) };
  grp.add(shockRing);

  const goldRing = new THREE.Mesh(
    new THREE.RingGeometry(0.5, radius * 0.75, 32),
    new THREE.MeshBasicMaterial({
      color: 0xfbbf24,
      map: shockTex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  );
  goldRing.rotation.x = -Math.PI / 2;
  goldRing.position.y = 0.12;
  goldRing.userData = { rotSpeed: new THREE.Vector3(0, 0, -16) };
  grp.add(goldRing);

  // Celestial healing chakra pillar burst (1efc_chakra10a / 1efc_chakra02)
  const pillar = buildExtractedVfxMeshGroup('common', 0x34d399, radius * 0.025, '1efc_chakra10a') ||
                 buildExtractedVfxMeshGroup('common', 0xfbbf24, radius * 0.025, '1efc_chakra02');
  if (pillar) {
    pillar.position.y = radius * 0.6;
    pillar.userData = { rotSpeed: new THREE.Vector3(0, 10, 0), uvScroll: { x: 0, y: 3.2 } };
    grp.add(pillar);
  }

  // Tsutenkyaku ground break stone shards
  const brkMesh = buildExtractedVfxMeshGroup('common', 0xd97706, radius * 0.018, '1efc_brk01_02');
  if (brkMesh) {
    brkMesh.rotation.x = -Math.PI / 2;
    brkMesh.position.y = 0.15;
    grp.add(brkMesh);
  }
  return grp;
}

function createOrochimaruDemonicBarrierMesh(radius = 5.5) {
  const grp = new THREE.Group();
  // Authentic Storm 1 extracted ground serpents (Sen'nejashu surge - 1orceff1_01)
  const serpents = buildExtractedVfxMeshGroup('1orc', 0x84cc16, radius * 0.024, '1orceff1_01');
  if (serpents) {
    serpents.position.set(0, 0.08, 0);
    grp.add(serpents);
  }
  const serpents2 = buildExtractedVfxMeshGroup('1orc', 0xa855f7, radius * 0.020, '1orceff1_02') ||
                    buildExtractedVfxMeshGroup('1orc', 0x65a30d, radius * 0.020, '1orceff1_03');
  if (serpents2) {
    serpents2.position.set(0, 0.15, radius * 0.2);
    grp.add(serpents2);
  }

  // Dark purple demonic barrier (Rashomon Gate / Edo Tensei)
  const gateMat = new THREE.MeshBasicMaterial({
    color: 0x3b0764,
    transparent: true,
    opacity: 0.88,
    side: THREE.DoubleSide
  });

  const pillarGeo = new THREE.CylinderGeometry(0.55, 0.75, 7.0, 12);
  const leftPillar = new THREE.Mesh(pillarGeo, gateMat);
  leftPillar.position.set(-radius * 0.65, 3.5, 0);
  grp.add(leftPillar);

  const rightPillar = new THREE.Mesh(pillarGeo, gateMat);
  rightPillar.position.set(radius * 0.65, 3.5, 0);
  grp.add(rightPillar);

  const lintelGeo = new THREE.BoxGeometry(radius * 1.55, 0.85, 0.95);
  const lintel = new THREE.Mesh(lintelGeo, gateMat);
  lintel.position.set(0, 6.8, 0);
  grp.add(lintel);

  // Demonic barrier face / barrier wall
  const wall = buildExtractedVfxMeshGroup('common', 0x581c87, radius * 0.028, '1efc_wall01');
  if (wall) {
    wall.position.set(0, 3.2, 0);
    grp.add(wall);
  } else {
    const barrierPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(radius * 1.3, 6.0),
      new THREE.MeshBasicMaterial({
        color: 0x7e22ce,
        transparent: true,
        opacity: 0.75,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    barrierPlane.position.set(0, 3.2, 0);
    grp.add(barrierPlane);
  }

  // Dark purple demonic shockwave ring
  const darkShockTex = loadTex('assets/skills/1efc_shock02.png');
  const darkDisc = new THREE.Mesh(
    new THREE.RingGeometry(0.8, radius * 1.2, 32),
    new THREE.MeshBasicMaterial({
      color: 0x6b21a8,
      map: darkShockTex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.80,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  );
  darkDisc.rotation.x = -Math.PI / 2;
  darkDisc.position.y = 0.06;
  darkDisc.userData = { rotSpeed: new THREE.Vector3(0, 0, 7) };
  grp.add(darkDisc);

  // Purple demonic aura flame (1efc_chakra04)
  const demonAura = buildExtractedVfxMeshGroup('common', 0x9333ea, radius * 0.022, '1efc_chakra04');
  if (demonAura) {
    demonAura.position.set(0, 2.5, 0);
    demonAura.userData = { rotSpeed: new THREE.Vector3(0, 10, 0), uvScroll: { x: 0, y: 2.8 } };
    grp.add(demonAura);
  }
  return grp;
}

function spawnSmokePuff(x, y, z, radius = 3.5) {
  for (let i = 0; i < 6; i++) {
    const smoke = new THREE.Mesh(
      new THREE.DodecahedronGeometry(radius * (0.35 + Math.random() * 0.35)),
      new THREE.MeshLambertMaterial({ color: 0xe2e8f0, transparent: true, opacity: 0.75 })
    );
    smoke.position.set(
      x + (Math.random() - 0.5) * 2.5,
      y + (Math.random() - 0.5) * 1.8,
      z + (Math.random() - 0.5) * 2.5
    );
    arenaGroup.add(smoke);
    vfxList.push({ mesh: smoke, age: 0, duration: 0.55 + Math.random() * 0.25, style: 'smoke' });
  }
}

function spawnGroundCrackDecal(x, z, radius = 2.8) {
  const crackTex = loadTex('assets/skills/1efc_brk01.png');
  const crackGeo = new THREE.PlaneGeometry(radius, radius);
  const crackMat = new THREE.MeshBasicMaterial({
    map: crackTex,
    transparent: true,
    opacity: 0.88,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1
  });
  const crackMesh = new THREE.Mesh(crackGeo, crackMat);
  crackMesh.rotation.x = -Math.PI / 2;
  crackMesh.rotation.z = Math.random() * Math.PI * 2;
  crackMesh.position.set(x, 0.045, z);
  arenaGroup.add(crackMesh);
  vfxList.push({
    mesh: crackMesh,
    age: 0,
    duration: 3.5,
    style: 'decal'
  });
}

function spawnHitSparks(x, y, z, colorHex = 0xfde047, intensity = 1) {
  // P1 JUICE: intensity 0.75 light hit / 1.0 skill / 1.7 KO & ult impact
  // 0. White radial impact flash (procedural additive sprite)
  const flashMat = new THREE.SpriteMaterial({
    map: flashTexture,
    color: 0xffffff,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
  const flashMesh = new THREE.Sprite(flashMat);
  flashMesh.position.set(x, y, z);
  const juiceFs = 3.2 * intensity;
  flashMesh.scale.set(juiceFs, juiceFs, 1);
  arenaGroup.add(flashMesh);
  vfxList.push({ mesh: flashMesh, age: 0, duration: 0.12, style: 'flash' });

  // 1. Central bright starburst flash
  const starGeo = new THREE.OctahedronGeometry(1.2, 0);
  const starMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.95,
    wireframe: false,
    blending: THREE.AdditiveBlending
  });
  const starMesh = new THREE.Mesh(starGeo, starMat);
  starMesh.position.set(x, y, z);
  starMesh.scale.set(1.4 * intensity, 1.4 * intensity, 1.4 * intensity);
  arenaGroup.add(starMesh);
  vfxList.push({ mesh: starMesh, age: 0, duration: 0.18, style: 'hit_star' });

  // 2. Cel-shaded impact ring
  spawnVFX(x, y, z, colorHex, 2.2 * intensity, 0.22, 'ring');

  // 3. Directional spark shards flying outward
  const shardCount = 6 + Math.round(4 * Math.min(1.7, intensity));
  for (let i = 0; i < shardCount; i++) {
    const angle = (i / shardCount) * Math.PI * 2 + (Math.random() - 0.5) * 0.4;
    const speed = (7.0 + Math.random() * 6.0) * (0.8 + 0.35 * intensity);
    const shardGeo = new THREE.ConeGeometry(0.12, 0.55, 4);
    const shardMat = new THREE.MeshBasicMaterial({
      color: (i % 2 === 0) ? colorHex : 0xffffff,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending
    });
    const shardMesh = new THREE.Mesh(shardGeo, shardMat);
    shardMesh.position.set(x, y, z);
    shardMesh.rotation.set(Math.random() * Math.PI, angle, Math.random() * Math.PI);
    arenaGroup.add(shardMesh);
    vfxList.push({
      mesh: shardMesh,
      age: 0,
      duration: 0.24 + Math.random() * 0.1,
      style: 'spark',
      vel: {
        x: Math.cos(angle) * speed,
        y: (Math.random() - 0.2) * 4.5,
        z: Math.sin(angle) * speed
      }
    });
  }
}

function spawnSoulChakraBurst(x, y, z, colorHex = 0x38bdf8) {
  // Rising soul chakra motes with heavenly drift
  const count = 12;
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 + (Math.random() - 0.5) * 0.5;
    const horizSpeed = 0.8 + Math.random() * 1.5;
    const orbGeo = new THREE.SphereGeometry(0.35 + Math.random() * 0.25, 8, 8);
    const orbMat = new THREE.MeshBasicMaterial({
      color: colorHex,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending
    });
    const orb = new THREE.Mesh(orbGeo, orbMat);
    orb.position.set(x + (Math.random() - 0.5) * 1.2, y + Math.random() * 0.8, z + (Math.random() - 0.5) * 1.2);
    arenaGroup.add(orb);
    vfxList.push({
      mesh: orb,
      age: 0,
      duration: 1.35 + Math.random() * 0.45,
      style: 'soul',
      vel: {
        x: Math.cos(angle) * horizSpeed,
        y: 3.2 + Math.random() * 2.8,
        z: Math.sin(angle) * horizSpeed
      }
    });
  }
}

// PV3.3: haptics com throttle + gate de perfil (data.haptics === false desliga).
// Throttle 60ms evita buzz continuo em atk rapido / dano por tick de zona.
let _lastHaptic = 0;
function haptic(pattern) {
  if (!navigator.vibrate) return;
  const now = performance.now();
  if (now - _lastHaptic < 60) return;
  _lastHaptic = now;
  try {
    const d = loadProfileData();
    if (d && d.haptics === false) return;
  } catch (e) {}
  try { navigator.vibrate(pattern); } catch (err) {}
}

function dealDamage(attacker, target, amount, skillName) {
  if (!target || !attacker || !Number.isFinite(amount)) return; // P2 hardening: robustez de API
  if (target.deadTimer > 0) return;
  if (target.spawnShield > 0) { // SPAWN GUARD: imortal perto da propria base
    const _sgp = basePos(target.team);
    if (Math.hypot(target.x - _sgp.x, target.z - _sgp.z) < 16) return;
  }
  attacker.spawnShield = 0; // atacar quebra a propria protecao
  const mult = attacker.awakenedTimer > 0 ? 1.35 : 1.0;
  const dmgRaw = Math.round(amount * mult * (1 + (attacker.level - 1) * 0.08));
  const dmg = Math.max(1, Math.round(dmgRaw * HERO_DMG_SCALE * ((HERO_STATS[target.heroId] || HERO_STATS.__d).dr))); // T5 escala global + P2 dano por heroi
  if (TRN.active && attacker.isPlayer && target !== attacker) TRN.recordHit(attacker, target, dmg, skillName); // W-TRN: medição de dano do treino
  if (TRN.active && attacker.isPlayer && target !== attacker) TRN_FLOATT(target, dmg); // W-TRN: numero de dano flutuante
  target.hp = Math.max(0, target.hp - dmg);

  // PV3.3: haptics — levou dano (18ms) > acertou (12ms)
  if (window.__GOV && window.__GOV.mobile) {
    if (target.isPlayer) haptic(18); else if (attacker.isPlayer) haptic(12);
  }

  // Assists tracking
  if (!target.recentAttackers) target.recentAttackers = new Map();
  target.recentAttackers.set(attacker, performance.now());

  // Synchronized SFX on damage impact
  AUTH_SFX.playAt('hit_s', target.x, target.z, { vol: 0.55 }); // W5: impacto posicionado
  if (dmg >= 180) AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), target.x, target.z, { vol: 0.85, min: 260 }); // W5: tombo pesado autêntico
  window.unitVoice(target, dmg >= 180 ? 'dmg_m' : 'dmg_s'); // W5-F2: voz do herói ao levar dano

  // Cel-shaded impact hit spark burst on damage impact
  // P1 JUICE: hitstop + shake + zoom scaled by damage weight, player
  // involvement and distance (no shake fatigue from distant bot fights)
  const juiceW = dmg >= 300 ? 3 : (dmg >= 180 ? 2 : (dmg >= 60 ? 1 : 0));
  const juicePl = units.find(x => x.isPlayer);
  const juiceDist = juicePl ? Math.hypot(target.x - juicePl.x, target.z - juicePl.z) : 999;
  const juiceNear = THREE.MathUtils.clamp(1 - (juiceDist - 14) / 34, 0, 1);
  const juiceScale = (attacker.isPlayer || target.isPlayer) ? 1 : juiceNear * 0.7;
  spawnHitSparks(target.x, 2.2, target.z, attacker.awakenedTimer > 0 ? 0xf97316 : 0xfde047, 0.7 + 0.25 * juiceW);
  if (juiceScale > 0.05) {
    const juiceHs = [0.018, 0.03, 0.052, 0.082][juiceW] * juiceScale;
    if (juiceHs >= 0.012) juiceHitstop(juiceHs);
    juiceShake((0.05 + juiceW * 0.115) * juiceScale);
    if (juiceW >= 3) juiceFovPunch(3.0 * juiceScale);
  }

  // Knockback impulse away from attacker
  const dx = target.x - attacker.x;
  const dz = target.z - attacker.z;
  const len = Math.hypot(dx, dz) || 1;
  if (!target.isDummy) { // W-TRN: boneco de treino fica cravado no chao, como os troncos
    target.x = clampPush(target.x + (dx / len) * 1.4);
    target.z = clampPush(target.z + (dz / len) * 1.4);
    // Authentic Storm Airborne Launch Parabola on heavy/finisher hits
    const isHeavy = dmg >= 170 || (skillName && (skillName.includes('Rasengan') || skillName.includes('Chidori') || skillName.includes('Kaiten') || skillName.includes('Oukahou') || skillName.includes('Finalizador')));
    if (isHeavy) {
      target.vy = 7.5;
      target.vx = (dx / len) * 8.0;
      target.vz = (dz / len) * 8.0;
      target.isAirborne = true;
    }
  }

  // APK HITSTUN (engine de dano do Storm, medido do APK: dmg0f FACE_DAMAGE_NORMAL
  // 21f = 0.35s hit normal / hsta0 hit-stagger 36f = 0.60s hit pesado): alvo VIVO
  // fica preso na reacao — hit novo reinicia (juggle de combo); kawarimi escapa.
  if (target.hp > 0) {
    target.hitstun = dmg >= 180 ? 0.60 : 0.35;
  }

  if (target.hp <= 0) {
    if (window.__GOV && window.__GOV.mobile && target.isPlayer) haptic([40, 60, 40]); // PV3.3: morri
    target.deadTimer = activeMatchCfg.respawn != null ? activeMatchCfg.respawn : 6.0; // respawn por modo (legacy 6s, 3v3 5s; PV2: BR = anim down normal, rebirth gate torna permanente)
    AUTH_SFX.playAt('down', target.x, target.z, { vol: 0.8 }); AUTH_SFX.playAt('ko', target.x, target.z, { vol: 0.9 }); // W5: KO posicionado
    window.unitVoice(target, 'dmg_l', { min: 0 }); // W5-F2: gemido de queda do herói
    target.state = 'down'; // Authentic knockdown fall animation
    target.animDuration = 2.0; // Lie on ground for 2.0s before vanishing
    target.animTimer = 2.0;
    target.deaths++;
    target.mesh.visible = true; // MUST remain visible lying on ground!
    target.poofed = false;
    if (target.labelEl) {
      target.labelEl.style.display = 'flex';
      target.labelEl.classList.add('dead');
      target.labelEl.innerHTML = `
        ${activeMatchCfg.respawn == null ? '<div class="ko-label-world">☠️ ELIMINADO</div>' : `<div class="ko-label-world">☠️ K.O.</div><div class="respawn-timer-world">蘇生 ${Math.ceil(target.deadTimer)}s</div>`}
      `;
    }

    // W5: genérico removido — 'down'+'ko' autênticos tocam posicionados acima

    // P1 JUICE: kill drama — deep slow-mo + hitstop + heavy shake.
    // Full drama when the player is involved; distant bot kills stay subtle.
    const ultKill = juiceW === 3;
    if (attacker.isPlayer || target.isPlayer) {
      juiceHitstop(ultKill ? 0.13 : 0.08);
      juiceSlowmo(ultKill ? 0.22 : 0.34, ultKill ? 0.75 : 0.45);
      juiceShake(ultKill ? 0.55 : 0.35);
      juiceFovPunch(ultKill ? 5.5 : 3.2);
    } else if (juiceNear > 0.3) {
      juiceHitstop(0.05);
      juiceShake(0.18 * juiceNear);
    }

    // VFX: KO shockwave ring + hit sparks + soul chakra particle burst
    spawnVFX(target.x, 0.4, target.z, 0xef4444, 8.5, 0.65, 'ring');
    spawnHitSparks(target.x, 2.0, target.z, 0xff2222, 1.7);
    spawnSoulChakraBurst(target.x, 1.8, target.z, target.team === 'blue' ? 0x38bdf8 : 0xf87171);

    // Attacker progression rewards
    attacker.kills++;
    attacker.level = Math.min(10, attacker.level + 1);
    AUTH_SFX.playAt('level_up', attacker.x, attacker.z, { vol: 0.75 }); // W5: level up posicionado
    attacker.maxHp += 80;
    attacker.hp = Math.min(attacker.maxHp, attacker.hp + 250);

    // STREAK: janela de 15s reinicia antes do incremento; vítima zera a dela
    const killNow = performance.now();
    attacker.killStreak = (killNow - (attacker.lastKillAt || 0) > 15000) ? 1 : (attacker.killStreak || 0) + 1;
    attacker.lastKillAt = killNow;
    target.killStreak = 0;
    if (TRN.active && target.isDummy) TRN.onDummyKO(target, attacker); // W-TRN: sino quando o Kakashi cai

    // Assist attribution: all teammates who damaged target in last 10s
    const now = performance.now();
    for (const [recentAttacker, time] of target.recentAttackers.entries()) {
      if (recentAttacker !== attacker && recentAttacker.team === attacker.team && (now - time) <= 10000) {
        recentAttacker.assists = (recentAttacker.assists || 0) + 1;
      }
    }
    target.recentAttackers.clear();

    if (attacker.team === 'blue') scoreBlue++;
    else scoreRed++;

    const scoreBlueEl = document.getElementById('score-blue');
    if (scoreBlueEl) renderSkinDigits(scoreBlueEl, scoreBlue);
    const scoreRedEl = document.getElementById('score-red');
    if (scoreRedEl) renderSkinDigits(scoreRedEl, scoreRed);

    renderTopTeamPortraits();
    addKillFeed(attacker, target, skillName);
    updateScoreboardTables();
    showStreakBanner(attacker); // STREAK (>=2)

    if (attacker.isPlayer) {
      showBanner(`VOCÊ ELIMINOU ${target.name.toUpperCase()}!`, 1800);
    } else if (target.isPlayer) {
      const deathOverlay = document.getElementById('player-death-overlay');
      if (deathOverlay) {
        deathOverlay.classList.remove('hidden');
        const timerNum = document.getElementById('death-timer-num');
        if (timerNum) renderSkinDigits(timerNum, '6');
        const progressFill = document.getElementById('death-progress-fill');
        if (progressFill) progressFill.style.width = '0%';
      }
      showBanner(`VOCÊ FOI DERROTADO POR ${attacker.name.toUpperCase()}!`, 2200);
    }

    if (matchSuddenDeath) {
      endMatch(scoreBlue > scoreRed ? 'MORTE SÚBITA — VITÓRIA TIME AZUL!' : 'MORTE SÚBITA — VITÓRIA TIME VERMELHO!'); // T5
    } else if (activeMatchCfg.killTarget != null && (scoreBlue >= activeMatchCfg.killTarget || scoreRed >= activeMatchCfg.killTarget)) { // PV2: blindagem vs null (BR decide por last-standing)
      endMatch(scoreBlue >= activeMatchCfg.killTarget ? 'VITÓRIA DO TIME KONOHA AZUL!' : 'VITÓRIA DO TIME RIVAL VERMELHO!');
    }
  }
}

// ==================== M7: IDENTIDADE VISUAL DE CADA SKILL ====================
// Modelo extracted autentico por heroi x slot (fallback: pipeline comum atual).
// Fonte: assets/skills/skill_vfx.json (meshes 3D das skills).
const SKILL_VFX_MAP = {
  '1nrt': { q: 'rasengan',            w: 'smoke',             e: '1efc_log01',          r: 'giant_rasengan' },
  '1ssk': { q: 'chidori_spark',       w: 'fireball',          e: '1sskeff1_sharin01',   r: '1sskeff1_aura01' },
  '1skr': { q: 'shatter',             w: 'heal_chakra',       e: '1efc_log01',          r: 'shatter' },
  '1kks': { q: 'raikiri_spark',       w: 'water_dragon',      e: 'raikiri_spark',       r: '1kkseff1_sharin01' },
  '1roc': { q: 'whirlwind',           w: 'air_tornado',       e: 'leaf_flurry',         r: 'air_tornado' },
  '1itc': { q: 'amaterasu_flame',     w: 'crow_smoke',        e: 'crow_smoke',          r: 'amaterasu_flame' },
  '1gar': { q: '1gareff1_bd_snd02',   w: '1gareff1_hnd01_body', e: 'sand_dust',          r: '1gareff1_snd15' },
  '1hnt': { q: 'palms_rotation',      w: 'lion_chakra',       e: 'palms_rotation',       r: 'lion_chakra' },
  '1nej': { q: 'kaiten_dome',         w: 'air_palm',          e: 'kaiten_dome',         r: 'kaiten_dome' },
  '1jry': { q: 'toad_fire',           w: '1jryeff01',         e: '1efc_log01',          r: 'chou_rasengan' },
  '1tnd': { q: '1efc_chakra04', w: '1efc_chakra00', e: '1efc_log01', r: '1efc_nor_dst01' },
  '1orc': { q: '1orceff1_01', w: '1efc_strk01', e: '1efc_log01', r: '1efc_nor_rpl02' }
};
let activeSkillVfxModel = null; // M7: modelo extraido do cast atual (spawnVFX le daqui)
let activeSkillVfxAnim = null; // SPP: anim procedural do cast atual
let activeSkillVfxFaceY = null; // SPP: rotY do caster no cast (facing do VFX)
let shadowClones = []; // SPP: clones 3D vivos
// SPP: anim do VFX extraido por skill — spin=gira (rasengan/chidori/kaiten),
// thrust=avanca (projeteis), pulse=pulsa (selos/areia), rise=sobe (fumacas)
const SKILL_VFX_ANIM = {
  '1nrt': { q: 'spin',  w: 'rise',   e: 'rise',   r: 'spin' },
  '1ssk': { q: 'spin',  w: 'thrust', e: 'pulse', r: 'pulse' },
  '1skr': { q: 'pulse', w: 'pulse',  e: 'rise',  r: 'pulse' },
  '1kks': { q: 'spin',  w: 'thrust', e: 'spin',  r: 'pulse' },
  '1roc': { q: 'spin',  w: 'rise',   e: 'thrust', r: 'rise' },
  '1itc': { q: 'pulse', w: 'rise',   e: 'rise',  r: 'pulse' },
  '1gar': { q: 'pulse', w: 'pulse',  e: 'pulse', r: 'pulse' },
  '1hnt': { q: 'spin',  w: 'spin',   e: 'spin',  r: 'spin' },
  '1nej': { q: 'spin',  w: 'thrust', e: 'spin',  r: 'spin' },
  '1jry': { q: 'thrust', w: 'pulse', e: 'rise',  r: 'spin' },
  '1tnd': { q: 'thrust', w: 'pulse', e: 'rise',  r: 'spin' },
  '1orc': { q: 'rise',   w: 'thrust', e: 'rise', r: 'pulse' }
};

// W-VFX-SEQ: emissores REAIS por fase do cast (at = fracao da duracao; o relogio e
// o animTimer, que PAUSA no hitstop como no Storm). s = extent alvo em unidades de mundo;
// fd = offset a frente do caster; dx = offset lateral; y = altura; c = tinta; g = grupo do modelo.
const SKILL_VFX_PHASES = {
  '1nrt': {
    q: [{ m: '1nrveff1_sonic01_air02', at: 0.55, s: 4.5, y: 1.4, fd: 2.6, c: 0x00d4ff }],
    w: [{ m: '1nrveff1_ptc01', at: 0.10, s: 2.6, y: 1.6, c: 0xffffff },
        { m: '1nrveff1_smk01', at: 0.30, s: 3.2, y: 1.2, dx: 1.7, c: 0xe2e8f0 },
        { m: '1nrveff1_smk01', at: 0.30, s: 3.2, y: 1.2, dx: -1.7, c: 0xe2e8f0 }],
    e: [{ m: '1nrveff1_smk02', at: 0.05, s: 3.0, y: 1.2, c: 0xe2e8f0 }],
    r: [{ m: '1nrveff1_chakra03', at: 0.15, s: 5.5, y: 2.2, c: 0xff3b00 },
        { m: '1nrveff1_ring01', at: 0.80, s: 6.0, y: 0.6, c: 0xffedd5 }]
  },
  '1ssk': {
    q: [{ m: '1ssveff1_shock01', at: 0.45, s: 3.2, y: 1.8, fd: 1.6, c: 0x60a5fa }],
    w: [{ m: '1ssveff1_smk01', at: 0.35, s: 2.8, y: 1.6, fd: -1.6, c: 0x94a3b8 }],
    e: [{ m: '1ssveff1_smk02', at: 0.05, s: 3.0, y: 1.2, c: 0xe2e8f0 }],
    r: [{ m: '1ssveff1_smk02', at: 0.55, s: 4.5, y: 1.0, c: 0x93c5fd }]
  },
  '1skr': {
    q: [{ m: '1skneff_leg01', at: 0.40, s: 5.0, y: 1.6, fd: 1.8, c: 0xf43f5e }],
    e: [{ m: 'shatter', at: 0.05, s: 2.6, y: 1.0, c: 0xe2e8f0 }],
    r: [{ g: 'common', m: '1efc_brk01_02', at: 0.60, s: 8.0, y: 0.4, c: 0xff5c8a }]
  },
  '1kks': {
    q: [{ m: 'raikiri_spark', at: 0.50, s: 2.8, y: 1.8, fd: 1.4, c: 0x38bdf8 }],
    w: [{ g: 'common', m: '1efc_wtr03', at: 0.35, s: 3.5, y: 1.2, fd: 3.0, c: 0x0ea5e9 }]
  },
  '1roc': {
    q: [{ m: 'leaf_flurry', at: 0.35, s: 3.5, y: 1.4, c: 0x4ade80 }],
    w: [{ m: 'leaf_flurry', at: 0.50, s: 4.2, y: 1.6, c: 0x4ade80 }]
  },
  '1itc': {
    q: [{ m: 'amaterasu_flame', at: 0.50, s: 3.2, y: 1.4, fd: 2.0, c: 0x450a0a }]
  },
  '1gar': {
    q: [{ m: '1gareff1_snd15', at: 0.40, s: 5.0, y: 1.2, c: 0xd97706 }],
    w: [{ m: '1gareff1_snd03', at: 0.50, s: 4.0, y: 1.0, fd: 2.2, c: 0xd97706 }]
  },
  '1nej': {
    q: [{ m: 'air_palm', at: 0.35, s: 3.0, y: 1.4, fd: 2.0, c: 0x60a5fa }]
  },
  '1jry': {
    q: [{ m: '1jryeff03', at: 0.50, s: 3.2, y: 1.8, fd: 2.4, c: 0x94a3b8 }]
  },
  '1tnd': {
    r: [{ g: 'common', m: '1efc_brk01_02', at: 0.50, s: 7.0, y: 0.4, c: 0xfbbf24 }]
  },
  '1orc': {
    q: [{ m: '1orceff1_02', at: 0.40, s: 3.6, y: 1.4, fd: 2.4, c: 0xa3e635 }],
    w: [{ g: 'common', m: '1efc_slash01', at: 0.50, s: 3.5, y: 1.6, fd: 2.0, c: 0xc7d2fe }]
  }
};

// ==================== P2: STATS POR HEROI (identidade de combate) ====================
// hp = vida base; spd = multiplicador de velocidade; dr = dano RECEBIDO (tank < 1 < frágil);
// reg = multiplicador do regen no santuário. Derivado dos papéis do roster (Fighter/Burst,
// Tank/Control, Speed, Support...). Suite E2E usa asserts relativos — seguro.
const HERO_STATS = {
  '1nrt': { hp: 1050, spd: 1.06, dr: 1.00, reg: 1.15 }, // Jinchuriki: vigor
  '1ssk': { hp: 920,  spd: 1.10, dr: 1.05, reg: 1.00 }, // Assassino veloz
  '1skr': { hp: 1000, spd: 1.00, dr: 0.95, reg: 1.30 }, // Ninja médica: sustain
  '1kks': { hp: 950,  spd: 1.08, dr: 1.05, reg: 1.00 }, // Assassino preciso
  '1roc': { hp: 900,  spd: 1.18, dr: 1.10, reg: 1.00 }, // Speed: o mais rápido
  '1itc': { hp: 850,  spd: 1.02, dr: 1.18, reg: 0.95 }, // Burst nuker frágil
  '1gar': { hp: 1250, spd: 0.90, dr: 0.82, reg: 1.00 }, // Tanque absoluto
  '1hnt': { hp: 920,  spd: 1.06, dr: 1.05, reg: 1.05 }, // DPS sustentado
  '1nej': { hp: 940,  spd: 1.05, dr: 1.02, reg: 1.05 }, // DPS controle
  '1jry': { hp: 1150, spd: 0.94, dr: 0.90, reg: 1.10 }, // Bruiser pesado,
  '1tnd': { hp: 1150, spd: 0.98, dr: 1.05, reg: 1.45 }, // Hokage medica: sustain maximo
  '1orc': { hp: 1000, spd: 1.02, dr: 1.00, reg: 1.10 }, // Sannin versatil
  __d:    { hp: 1000, spd: 1.00, dr: 1.00, reg: 1.00 }  // fallback
};

function executeSkill(unit, slot) {
  if (!unit || !unit.kit || !unit.heroId) return; // P2 hardening: robustez de API
  activeSkillVfxModel = ((SKILL_VFX_MAP[unit.heroId] || {})[slot]) || null; // M7: identidade por skill
  activeSkillVfxAnim = ((SKILL_VFX_ANIM[unit.heroId] || {})[slot]) || null; // SPP: anim por skill
  const _authSfx = ((SKILL_SFX_MAP[unit.heroId] || {})[slot]) || null; // W1.1
  window.unitVoice(unit, slot === 'atk' ? 'atk_s' : (slot === 'r' ? 'atk_l' : 'atk_m'), { min: 4200 }); // W5-F2: voz de ataque do herói
  if (_authSfx) AUTH_SFX.playAt(_authSfx, unit.x, unit.z, { vol: 0.8 }); // W5: voz do herói posicionada
  else if (slot === 'atk') AUTH_SFX.playAt(AUTH_SFX.pick('punch_swing', 'kick_swing'), unit.x, unit.z, { vol: 0.5 }); // W5: swing alternado
  activeSkillVfxFaceY = unit.rotY; // SPP: VFX encara a direcao do caster

  if (unit.deadTimer > 0) return;
  const sk = unit.kit[slot];
  if (!sk || unit.cds[slot] > 0) return;
  if (unit.chakra < sk.cost) return;
  if (unit.hitstun > 0 && sk.type !== 'kawarimi') return; // APK: preso na reacao de dano; kawarimi = escape autentico

  unit.chakra -= sk.cost;
  unit.cds[slot] = sk.cd;
  if (slot === 'r' && unit.isPlayer) progUltCount += 1; // W-PROG: missoes diarias contam ougi
  const _ph = (SKILL_VFX_PHASES[unit.heroId] || {})[slot];
  if (_ph && _ph.length) unit.pendingVfxPhases = _ph.map(p => Object.assign({}, p, { done: false }));
  else unit.pendingVfxPhases = null;

  // Auto-face nearest enemy
  const nearest = findNearestEnemy(unit, 32);
  if (nearest) {
    unit.rotY = Math.atan2(nearest.x - unit.x, nearest.z - unit.z);
  }
  const dirX = Math.sin(unit.rotY);
  const dirZ = Math.cos(unit.rotY);

  if (slot === 'atk') {
    if (unit.comboResetTimer <= 0) {
      unit.comboStep = 0;
    }
    const comboStates = ['attack', 'attack2', 'attack3'];
    const currentComboState = comboStates[unit.comboStep % 3];
    unit.state = currentComboState;
    unit.comboStep = (unit.comboStep + 1) % 3;
    unit.comboResetTimer = 1.1; // Window to chain next hit of 3-hit combo

    const hitIdx = (unit.comboStep === 0) ? 3 : unit.comboStep; // 1, 2, or 3
    unit.animDuration = hitIdx === 1 ? 0.38 : (hitIdx === 2 ? 0.42 : 0.52);
    unit.animTimer = unit.animDuration;
    startSkillTrail(unit, 'atk'); // Authentic Taijutsu slash ribbon trail

    // Check if enemy is in close melee range (<= 7.5 units)
    const meleeTarget = findNearestEnemy(unit, 7.5);

    if (meleeTarget) {
      // MELEE TAIJUTSU: Authentic Punches and Kicks!
      if (unit.isPlayer) {
        AUTH_SFX.playAt(hitIdx === 2 ? AUTH_SFX.pick('kick_hit', 'kick_hit2') : AUTH_SFX.pick('punch_hit', 'punch_hit2'), meleeTarget.x, meleeTarget.z, { vol: 0.62 }); // W5: soco/chute autêntico com variação
      }

      const baseComboDmg = hitIdx === 1 ? 82 : (hitIdx === 2 ? 105 : 150);
      dealDamage(unit, meleeTarget, baseComboDmg, `${sk.name} [${hitIdx === 1 ? 'Soco Jab' : (hitIdx === 2 ? 'Chute Giratório' : 'Golpe Finalizador')}]`);

      // Cel-shaded hit sparks on melee combo hit
      spawnHitSparks(meleeTarget.x, 2.2, meleeTarget.z, hitIdx === 3 ? 0xef4444 : (hitIdx === 2 ? 0xf97316 : 0xfde047));

      if (hitIdx === 1) {
        // Punch spark flash
        spawnVFX(meleeTarget.x, 2.5, meleeTarget.z, 0xfde047, 2.4, 0.22, 'ring', unit.heroId);
      } else if (hitIdx === 2) {
        // Kick sweeping arc
        spawnVFX(meleeTarget.x, 2.3, meleeTarget.z, 0xf97316, 3.2, 0.28, 'ring', unit.heroId);
      } else {
        // Heavy finisher slam + ground shockwave + heavy knockback
        spawnVFX(meleeTarget.x, 1.8, meleeTarget.z, 0xef4444, 5.2, 0.38, 'ring', unit.heroId);
        spawnVFX(meleeTarget.x, 2.8, meleeTarget.z, 0xf97316, 4.2, 0.32, 'sphere', unit.heroId);
        const kx = meleeTarget.x - unit.x;
        const kz = meleeTarget.z - unit.z;
        const klen = Math.hypot(kx, kz) || 1;
        meleeTarget.x = clampArena(meleeTarget.x + (kx / klen) * 3.2);
        meleeTarget.z = clampArena(meleeTarget.z + (kz / klen) * 3.2);
      }
    } else {
      // RANGED NINJA TOOLS: 3D Steel Kunais & Spinning Shurikens!
      AUTH_SFX.playAt(hitIdx === 1 ? 'kunai_swing' : 'shuriken', unit.x, unit.z, { vol: hitIdx === 1 ? 0.7 : 0.75 }); // W5: arremesso autêntico por golpe

      if (hitIdx === 1) {
        // Hit 1: 1 High-velocity steel Kunai point-first!
        const kunai = createKunaiMesh();
        kunai.position.set(unit.x + dirX * 1.8, 2.6, unit.z + dirZ * 1.8);
        kunai.rotation.x = Math.PI / 2;
        kunai.rotation.z = -unit.rotY;
        arenaGroup.add(kunai);
        projectiles.push({
          owner: unit,
          mesh: kunai,
          type: 'kunai',
          x: kunai.position.x,
          z: kunai.position.z,
          vx: dirX * 54,
          vz: dirZ * 54,
          radius: 2.0,
          dmg: 72,
          skillName: `${sk.name} [Kunai de Aço]`,
          color: 0x94a3b8,
          life: 0.85
        });
      } else if (hitIdx === 2) {
        // Hit 2: 2 Spinning 4-pointed Shurikens offset slightly!
        for (const offset of [-0.65, 0.65]) {
          const perpX = -dirZ * offset;
          const perpZ = dirX * offset;
          const shuriken = createShurikenMesh();
          shuriken.position.set(unit.x + dirX * 1.8 + perpX, 2.6, unit.z + dirZ * 1.8 + perpZ);
          arenaGroup.add(shuriken);
          projectiles.push({
            owner: unit,
            mesh: shuriken,
            type: 'shuriken',
            x: shuriken.position.x,
            z: shuriken.position.z,
            vx: dirX * 50,
            vz: dirZ * 50,
            radius: 1.8,
            dmg: 56,
            skillName: `${sk.name} [Shuriken Dupla]`,
            color: 0x64748b,
            life: 0.85
          });
        }
      } else {
        // Hit 3: 3 Spinning Shurikens in a wide fan spread (-14 deg, 0 deg, +14 deg)!
        const angles = [-0.24, 0.0, 0.24];
        for (const ang of angles) {
          const cosA = Math.cos(ang);
          const sinA = Math.sin(ang);
          const sDirX = dirX * cosA - dirZ * sinA;
          const sDirZ = dirX * sinA + dirZ * cosA;
          const shuriken = createShurikenMesh();
          shuriken.position.set(unit.x + sDirX * 1.8, 2.6, unit.z + sDirZ * 1.8);
          arenaGroup.add(shuriken);
          projectiles.push({
            owner: unit,
            mesh: shuriken,
            type: 'shuriken',
            x: shuriken.position.x,
            z: shuriken.position.z,
            vx: sDirX * 52,
            vz: sDirZ * 52,
            radius: 2.0,
            dmg: 65,
            skillName: `${sk.name} [Leque Triplo de Shuriken]`,
            color: 0xf59e0b,
            life: 0.90
          });
        }
      }
    }
    return;
  }

  // W5: genéricos de cast removidos — vozes autênticas do herói tocam via SKILL_SFX_MAP

  // Skin HUD hooks (Ougi ultimate / Kawarimi substitution)
  if (unit.isPlayer) {
    if (slot === 'r') {
      showOugiBanner();
      // P1 JUICE: ultimate cast drama — wind-up freeze + rising cinematic zoom
      juiceHitstop(0.09);
      juiceSlowmo(0.55, 0.35);
      juiceShake(0.30);
      juiceFovPunch(4.0);
    } else if (slot === 'e') {
      flashKawarimi();
    }
  }

  // W-SKL+ TRAIL: rastro autêntico de mão/lâmina (Hinata W, Orochimaru W)
  startSkillTrail(unit, slot);

  // HERO-SPECIFIC SKILL LOGIC & 3D VISUAL EFFECTS (AUTHENTIC STORM 1)
  if (unit.heroId === '1nrt') {
    if (slot === 'q') {
      // Primary: Rasengan Dash (attached to right hand bone 13)
      unit.state = 'jutsu';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const rasMesh = createRasenganMesh(1.0, 0x00d4ff);
      rasMesh.position.set(unit.x + dirX * 2.2, 2.5, unit.z + dirZ * 2.2);
      arenaGroup.add(rasMesh);
      vfxList.push({ mesh: rasMesh, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });

      // W-VIS: modelo EXTRAIDO do APK ('rasengan', eff1) bound a mao direita
      // durante TODO o cast (~2.65u, proporcao Storm) — o visual autentico
      // junto ao casting; procedural vira o core glow interno
      const rasGrp = buildExtractedVfxMeshGroup(unit.heroId, 0x00d4ff, 0.0105, activeSkillVfxModel || 'rasengan');
      if (rasGrp) {
        rasGrp.position.set(unit.x, 2.5, unit.z);
        arenaGroup.add(rasGrp);
        vfxList.push({ mesh: rasGrp, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });
      }

      unit.x = clampArena(unit.x + dirX * 11.5);
      unit.z = clampArena(unit.z + dirZ * 11.5);
      spawnVFX(unit.x, 1.8, unit.z, 0x00d4ff, 3.2, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Kage Bunshin no Jutsu (Shadow Clones)
      unit.state = 'jutsu2';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      spawnSmokePuff(unit.x - dirZ * 2.5, 2.2, unit.z + dirX * 2.5, 3.5);
      spawnSmokePuff(unit.x + dirZ * 2.5, 2.2, unit.z - dirX * 2.5, 3.5);
      spawnVFX(unit.x, 1.8, unit.z, 0xff9900, 3.5, 0.45, 'ring', unit.heroId);
      const tx = nearest ? nearest.x : unit.x + dirX * 8;
      const tz = nearest ? nearest.z : unit.z + dirZ * 8;
      spawnSmokePuff(tx, 2.2, tz, 4.2);
      spawnShadowClones(unit, 3, Math.round(sk.dmg * 0.6)); // SPP: clones 3D reais (Kage Bunshin)
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - tx, enemy.z - tz) <= 9.2) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    }
  } else if (unit.heroId === '1ssk') {
    if (slot === 'q') {
      // Primary: Chidori (attached to left hand bone 9)
      unit.state = 'jutsu';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const chiMesh = createChidoriMesh(0.95);
      chiMesh.position.set(unit.x + dirX * 2.0, 2.5, unit.z + dirZ * 2.0);
      arenaGroup.add(chiMesh);
      vfxList.push({ mesh: chiMesh, age: 0, duration: 0.7, style: 'compound', bindUnit: unit, bindBoneIdx: 9 });

      // W-VIS-ALL: chidori_spark EXTRAIDO do APK bound na mao esquerda (bone 9)
      // durante todo o cast (~2.6u) — autentico junto ao procedural core
      const chiGrp = buildExtractedVfxMeshGroup(unit.heroId, 0x60a5fa, 0.0105, 'chidori_spark');
      if (chiGrp) {
        chiGrp.position.set(unit.x + dirX * 2.0, 2.5, unit.z + dirZ * 2.0);
        arenaGroup.add(chiGrp);
        vfxList.push({ mesh: chiGrp, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 9 });
      }

      unit.x = clampArena(unit.x + dirX * 12.5);
      unit.z = clampArena(unit.z + dirZ * 12.5);
      spawnVFX(unit.x, 1.8, unit.z, 0x60a5fa, 3.2, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Katon: Goukakyuu no Jutsu (Fireball)
      unit.state = 'jutsu2';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const fMesh = createFireballMesh(1.8, 0xff5500);
      fMesh.position.set(unit.x + dirX * 2.2, 2.6, unit.z + dirZ * 2.2);
      arenaGroup.add(fMesh);
      projectiles.push({
        owner: unit,
        mesh: fMesh,
        type: 'fireball',
        x: fMesh.position.x,
        z: fMesh.position.z,
        vx: dirX * 42,
        vz: dirZ * 42,
        radius: 3.2,
        dmg: sk.dmg,
        skillName: sk.name,
        color: 0xff5500,
        life: 1.25
      });
      spawnVFX(unit.x + dirX * 1.5, 2.0, unit.z + dirZ * 1.5, 0xff5500, 3.0, 0.40, 'ring', unit.heroId);
      return;
    }
  } else if (unit.heroId === '1skr') {
    if (slot === 'q') {
      // Primary: Oukashou Ground Shatter
      unit.state = 'jutsu';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const tx = nearest ? nearest.x : unit.x + dirX * 6;
      const tz = nearest ? nearest.z : unit.z + dirZ * 6;
      const shatter = createGroundShatterMesh(4.5);
      shatter.position.set(tx, 0.1, tz);
      arenaGroup.add(shatter);
      vfxList.push({ mesh: shatter, age: 0, duration: 1.15, style: 'compound' });
      spawnVFX(tx, 1.2, tz, 0xff5c8a, 4.0, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - tx, enemy.z - tz) <= 9.0) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Ninjutsu Medico (Cura Area)
      unit.state = 'jutsu2';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      spawnVFX(unit.x, 1.5, unit.z, 0x4ade80, 5.0, 0.65, 'ring', unit.heroId);
      for (const ally of units) {
        if (ally.team === unit.team && ally.deadTimer <= 0) {
          if (Math.hypot(ally.x - unit.x, ally.z - unit.z) <= 12.0) {
            ally.hp = Math.min(ally.maxHp, ally.hp + sk.dmg);
          }
        }
      }
      return;
    }
  } else if (unit.heroId === '1kks') {
    if (slot === 'q') {
      // Primary: Raikiri Lightning Blade (attached to right hand bone 13)
      unit.state = 'jutsu';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const rkMesh = createChidoriMesh(0.95, 0x38bdf8);
      rkMesh.position.set(unit.x + dirX * 2.0, 2.5, unit.z + dirZ * 2.0);
      arenaGroup.add(rkMesh);
      vfxList.push({ mesh: rkMesh, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });

      // W-VIS-ALL: raikiri_spark EXTRAIDO do APK bound na mao direita (bone 13)
      const rkGrp = buildExtractedVfxMeshGroup(unit.heroId, 0x38bdf8, 0.0105, 'raikiri_spark');
      if (rkGrp) {
        rkGrp.position.set(unit.x + dirX * 2.0, 2.5, unit.z + dirZ * 2.0);
        arenaGroup.add(rkGrp);
        vfxList.push({ mesh: rkGrp, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });
      }

      unit.x = clampArena(unit.x + dirX * 12.0);
      unit.z = clampArena(unit.z + dirZ * 12.0);
      spawnVFX(unit.x, 1.8, unit.z, 0x38bdf8, 3.2, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Suiton: Suiryuudan no Jutsu (Water Dragon)
      unit.state = 'jutsu2';
      unit.animDuration = 0.8;
      unit.animTimer = unit.animDuration;
      const wdMesh = createWaterDragonMesh(2.2);
      wdMesh.position.set(unit.x + dirX * 2.4, 2.6, unit.z + dirZ * 2.4);
      wdMesh.rotation.y = unit.rotY;
      arenaGroup.add(wdMesh);
      projectiles.push({
        owner: unit,
        mesh: wdMesh,
        type: 'fireball',
        x: wdMesh.position.x,
        z: wdMesh.position.z,
        vx: dirX * 38,
        vz: dirZ * 38,
        radius: 3.5,
        dmg: sk.dmg,
        skillName: sk.name,
        color: 0x0ea5e9,
        directional: true,
        life: 1.3
      });
      spawnVFX(unit.x + dirX * 1.5, 2.0, unit.z + dirZ * 1.5, 0x0ea5e9, 3.2, 0.45, 'ring', unit.heroId);
      return;
    }
  } else if (unit.heroId === '1roc') {
    if (slot === 'q') {
      // Primary: Konoha Senpuu (Emerald Cyclone with Leaf Flurry)
      unit.state = 'jutsu';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const tMesh = createTornadoMesh(3.2);
      tMesh.position.set(unit.x, 0.1, unit.z);
      arenaGroup.add(tMesh);
      vfxList.push({ mesh: tMesh, age: 0, duration: 0.75, style: 'compound' });
      spawnVFX(unit.x, 1.5, unit.z, 0x22c55e, 3.5, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Omote Renge (Primary Lotus Air Tornado)
      unit.state = 'jutsu2';
      unit.animDuration = 0.8;
      unit.animTimer = unit.animDuration;
      const tMesh = createTornadoMesh(3.8);
      tMesh.position.set(unit.x + dirX * 2.2, 0.1, unit.z + dirZ * 2.2);
      arenaGroup.add(tMesh);
      vfxList.push({ mesh: tMesh, age: 0, duration: 1.1, style: 'compound' });

      unit.x = clampArena(unit.x + dirX * 11.0);
      unit.z = clampArena(unit.z + dirZ * 11.0);
      spawnVFX(unit.x, 1.8, unit.z, 0x86efac, 3.8, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 9.0) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    }
  } else if (unit.heroId === '1itc') {
    if (slot === 'q') {
      // Primary: Amaterasu (Inextinguishable Black Flame Pillar)
      unit.state = 'jutsu';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const tx = nearest ? nearest.x : unit.x + dirX * 8;
      const tz = nearest ? nearest.z : unit.z + dirZ * 8;
      const amat = createAmaterasuMesh(3.2);
      amat.position.set(tx, 0.1, tz);
      arenaGroup.add(amat);
      vfxList.push({ mesh: amat, age: 0, duration: 1.35, style: 'compound' });
      spawnVFX(tx, 1.2, tz, 0xdc2626, 3.5, 0.50, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - tx, enemy.z - tz) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Katon Goukakyuu + Crow Clone
      unit.state = 'jutsu2';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const fMesh = createFireballMesh(1.8, 0xef4444);
      fMesh.position.set(unit.x + dirX * 2.2, 2.6, unit.z + dirZ * 2.2);
      arenaGroup.add(fMesh);
      projectiles.push({
        owner: unit,
        mesh: fMesh,
        type: 'fireball',
        x: fMesh.position.x,
        z: fMesh.position.z,
        vx: dirX * 40,
        vz: dirZ * 40,
        radius: 3.2,
        dmg: sk.dmg,
        skillName: sk.name,
        color: 0xef4444,
        life: 1.25
      });
      spawnSmokePuff(unit.x, 2.2, unit.z, 3.5);
      return;
    }
  } else if (unit.heroId === '1gar') {
    if (slot === 'q') {
      // Primary: Sabaku Kyuu (Giant Sand Hand Crush)
      unit.state = 'jutsu';
      unit.animDuration = 0.8;
      unit.animTimer = unit.animDuration;
      const tx = nearest ? nearest.x : unit.x + dirX * 7;
      const tz = nearest ? nearest.z : unit.z + dirZ * 7;
      const sHand = createSandHandMesh(0.08);
      sHand.position.set(tx, 0.1, tz);
      sHand.rotation.y = unit.rotY;
      arenaGroup.add(sHand);
      vfxList.push({ mesh: sHand, age: 0, duration: 1.15, style: 'compound', directional: true });
      spawnVFX(tx, 1.2, tz, 0xf59e0b, 3.8, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - tx, enemy.z - tz) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Suna no Tate (Absolute Sand Shield Cocoon)
      unit.state = 'jutsu2';
      unit.animDuration = 0.85;
      unit.animTimer = unit.animDuration;
      const shield = createSandShieldMesh(3.0);
      shield.position.set(unit.x, 0.2, unit.z);
      arenaGroup.add(shield);
      vfxList.push({ mesh: shield, age: 0, duration: 1.0, style: 'compound' });
      spawnVFX(unit.x, 1.5, unit.z, 0xf59e0b, 3.5, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.5) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    }
  } else if (unit.heroId === '1hnt') {
    if (slot === 'q') {
      // Primary: Shugohakke Rokujuyonsho
      unit.state = 'jutsu';
      unit.animDuration = 0.8;
      unit.animTimer = unit.animDuration;
      spawnVFX(unit.x, 1.5, unit.z, 0xa78bfa, 4.0, 0.50, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 9.0) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Twin Lion Fists (Juho Soshiken bound to dual hands 9 and 13)
      unit.state = 'jutsu2';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const lf1 = createLionFistMesh(0.95);
      const lf2 = createLionFistMesh(0.95);
      lf1.position.set(unit.x - dirZ * 1.4, 2.5, unit.z + dirX * 1.4);
      lf2.position.set(unit.x + dirZ * 1.4, 2.5, unit.z - dirX * 1.4);
      arenaGroup.add(lf1);
      arenaGroup.add(lf2);
      vfxList.push({ mesh: lf1, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 9, directional: true });
      vfxList.push({ mesh: lf2, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13, directional: true });

      // W-VIS-ALL: lion_chakra EXTRAIDO do APK nos dois punhos (bones 9 e 13)
      const lfGrp1 = buildExtractedVfxMeshGroup(unit.heroId, 0x8b5cf6, 0.008, 'lion_chakra');
      const lfGrp2 = buildExtractedVfxMeshGroup(unit.heroId, 0x8b5cf6, 0.008, 'lion_chakra');
      if (lfGrp1) {
        lfGrp1.position.set(unit.x - dirZ * 1.4, 2.5, unit.z + dirX * 1.4);
        arenaGroup.add(lfGrp1);
        vfxList.push({ mesh: lfGrp1, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 9 });
      }
      if (lfGrp2) {
        lfGrp2.position.set(unit.x + dirZ * 1.4, 2.5, unit.z - dirX * 1.4);
        arenaGroup.add(lfGrp2);
        vfxList.push({ mesh: lfGrp2, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });
      }

      unit.x = clampArena(unit.x + dirX * 10.5);
      unit.z = clampArena(unit.z + dirZ * 10.5);
      spawnVFX(unit.x, 1.8, unit.z, 0x8b5cf6, 3.5, 0.45, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.5) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    }
  } else if (unit.heroId === '1nej') {
    if (slot === 'q') {
      // Primary: Hakkeshou Kaiten (360 Dome)
      unit.state = 'jutsu';
      unit.animDuration = 0.85;
      unit.animTimer = unit.animDuration;
      const kaiten = createKaitenMesh(3.2);
      kaiten.position.set(unit.x, 2.2, unit.z);
      arenaGroup.add(kaiten);
      vfxList.push({ mesh: kaiten, age: 0, duration: 0.85, style: 'compound' });
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 9.2) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    } else if (slot === 'w') {
      // Secondary: Hakke Kuusho (Air Palm)
      unit.state = 'jutsu2';
      unit.animDuration = 0.75;
      unit.animTimer = unit.animDuration;
      const apMesh = buildExtractedVfxMeshGroup('1nej', 0x38bdf8, 0.08, 'air_palm') ||
                     new THREE.Mesh(new THREE.RingGeometry(1.2, 2.8, 16), new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide, transparent: true, opacity: 0.85 }));
      apMesh.position.set(unit.x + dirX * 2.2, 2.6, unit.z + dirZ * 2.2);
      apMesh.rotation.y = unit.rotY;
      arenaGroup.add(apMesh);
      projectiles.push({
        owner: unit,
        mesh: apMesh,
        type: 'fireball',
        x: apMesh.position.x,
        z: apMesh.position.z,
        vx: dirX * 45,
        vz: dirZ * 45,
        radius: 3.5,
        dmg: sk.dmg,
        skillName: sk.name,
        color: 0x38bdf8,
        directional: true,
        life: 1.2
      });
      spawnVFX(unit.x + dirX * 1.5, 2.0, unit.z + dirZ * 1.5, 0x38bdf8, 3.2, 0.40, 'ring', unit.heroId);
      return;
    }
  } else if (unit.heroId === '1jry') {
    if (slot === 'q') {
      // Primary: Katon: Gamayu Endan (Flaming Toad Oil Cone Spray)
      unit.state = 'jutsu';
      unit.animDuration = 0.8;
      unit.animTimer = unit.animDuration;
      const toadFlame = createToadOilFlameMesh(2.2);
      toadFlame.position.set(unit.x + dirX * 2.2, 2.6, unit.z + dirZ * 2.2);
      toadFlame.rotation.y = unit.rotY;
      arenaGroup.add(toadFlame);
      projectiles.push({
        owner: unit,
        mesh: toadFlame,
        type: 'fireball',
        x: toadFlame.position.x,
        z: toadFlame.position.z,
        vx: dirX * 38,
        vz: dirZ * 38,
        radius: 4.8,
        dmg: sk.dmg,
        skillName: sk.name,
        color: 0xf97316,
        directional: true,
        life: 1.3
      });
      spawnVFX(unit.x + dirX * 2, 2.5, unit.z + dirZ * 2, 0xf97316, 7.5, 0.55, 'ring', unit.heroId);
      return;
    } else if (slot === 'w') {
      // Secondary: Hari Jizo (Spiky Needle Hair Shield)
      unit.state = 'jutsu2';
      unit.animDuration = 0.85;
      unit.animTimer = unit.animDuration;
      const shield = createSandShieldMesh(5.0);
      shield.position.set(unit.x, 0.2, unit.z);
      arenaGroup.add(shield);
      vfxList.push({ mesh: shield, age: 0, duration: 1.0, style: 'compound' });
      spawnVFX(unit.x, 2.2, unit.z, 0xf43f5e, 8.5, 0.65, 'ring', unit.heroId);
      for (const enemy of units) {
        if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
          if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.8) {
            dealDamage(unit, enemy, sk.dmg, sk.name);
          }
        }
      }
      return;
    }
  }

  // STANDARD / FALLBACK SKILL TYPES
  if (sk.type === 'dash_aoe') {
    unit.state = (slot === 'w') ? 'jutsu2' : 'jutsu';
    unit.animDuration = 0.7;
    unit.animTimer = unit.animDuration;
    for (let step = 1; step <= 4; step++) {
      spawnVFX(unit.x + dirX * step * 2.8, 2.6, unit.z + dirZ * step * 2.8, sk.color, 3.4, 0.42, 'sphere', unit.heroId);
    }
    unit.x = clampArena(unit.x + dirX * 11.5);
    unit.z = clampArena(unit.z + dirZ * 11.5);
    spawnVFX(unit.x + dirX * 2, 2.6, unit.z + dirZ * 2, sk.color, 6.8, 0.55, 'sphere', unit.heroId);
    for (const enemy of units) {
      if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
        if (Math.hypot(enemy.x - unit.x, enemy.z - unit.z) <= 8.2) {
          dealDamage(unit, enemy, sk.dmg, sk.name);
        }
      }
    }
  } else if (sk.type === 'fireball') {
    unit.state = (slot === 'w') ? 'jutsu2' : 'jutsu';
    unit.animDuration = 0.65;
    unit.animTimer = unit.animDuration;
    let pMesh = buildExtractedVfxMeshGroup(unit.heroId, sk.color, 0.085);
    if (!pMesh) {
      pMesh = new THREE.Mesh(
        new THREE.IcosahedronGeometry(1.8, 1),
        new THREE.MeshBasicMaterial({ color: sk.color })
      );
    }
    pMesh.position.set(unit.x + dirX * 2.4, 2.8, unit.z + dirZ * 2.4);
    arenaGroup.add(pMesh);
    projectiles.push({
      owner: unit,
      mesh: pMesh,
      type: 'fireball',
      x: pMesh.position.x,
      z: pMesh.position.z,
      vx: dirX * 38,
      vz: dirZ * 38,
      radius: 4.2,
      dmg: sk.dmg,
      skillName: sk.name,
      color: sk.color,
      life: 1.35
    });
  } else if (sk.type === 'spin_aoe' || sk.type === 'slam_aoe' || sk.type === 'clone_burst') {
    unit.state = (slot === 'w') ? 'jutsu2' : 'jutsu';
    unit.animDuration = 0.7;
    unit.animTimer = unit.animDuration;
    const tx = nearest && sk.type === 'slam_aoe' ? nearest.x : unit.x;
    const tz = nearest && sk.type === 'slam_aoe' ? nearest.z : unit.z;
    spawnVFX(tx, 2.2, tz, sk.color, 9.0, 0.55, 'ring', unit.heroId);
    if (sk.type === 'clone_burst') spawnShadowClones(unit, 3, Math.round(sk.dmg * 0.6)); // SPP: clones 3D de verdade
    spawnVFX(tx, 2.8, tz, sk.color, 7.5, 0.5, 'sphere', unit.heroId);
    for (const enemy of units) {
      if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
        if (Math.hypot(enemy.x - tx, enemy.z - tz) <= 9.5) {
          dealDamage(unit, enemy, sk.dmg, sk.name);
        }
      }
    }
  } else if (sk.type === 'heal_aoe') {
    unit.state = (slot === 'w') ? 'jutsu2' : 'jutsu';
    unit.animDuration = 0.65;
    unit.animTimer = unit.animDuration;
    spawnVFX(unit.x, 1.5, unit.z, 0x4ade80, 10.5, 0.65, 'ring', unit.heroId);
    for (const ally of units) {
      if (ally.team === unit.team && ally.deadTimer <= 0) {
        if (Math.hypot(ally.x - unit.x, ally.z - unit.z) <= 12.0) {
          ally.hp = Math.min(ally.maxHp, ally.hp + sk.dmg);
        }
      }
    }
  } else if (sk.type === 'kawarimi') {
    unit.state = 'dash';
    AUTH_SFX.playAt('dash', unit.x, unit.z, { vol: 0.5 }); // W5: dash posicionado
    unit.animDuration = 0.35;
    unit.animTimer = unit.animDuration;
    const extLog = buildExtractedVfxMeshGroup('common', 0x78350f, 0.055, '1efc_log01');
    const logMesh = extLog || new THREE.Mesh(
      new THREE.CylinderGeometry(0.65, 0.65, 3.2, 10),
      new THREE.MeshLambertMaterial({ color: 0x78350f })
    );
    logMesh.rotation.z = 0.4;
    logMesh.position.set(unit.x, 1.8, unit.z);
    arenaGroup.add(logMesh);
    vfxList.push({ mesh: logMesh, age: 0, duration: 1.2, style: 'log' });
    spawnSmokePuff(unit.x, 2.2, unit.z, 4.0);

    if (nearest) {
      const behindX = nearest.x + Math.sin(nearest.rotY + Math.PI) * 4.5;
      const behindZ = nearest.z + Math.cos(nearest.rotY + Math.PI) * 4.5;
      unit.x = clampArena(behindX);
      unit.z = clampArena(behindZ);
      unit.rotY = Math.atan2(nearest.x - unit.x, nearest.z - unit.z);
      if (sk.dmg > 0) dealDamage(unit, nearest, sk.dmg, sk.name);
    } else {
      unit.x = clampArena(unit.x - dirX * 10);
      unit.z = clampArena(unit.z - dirZ * 10);
    }
    unit.hp = Math.min(unit.maxHp, unit.hp + 90);
  } else if (sk.type === 'ultimate') {
    unit.state = 'ult';
    // W-SKL+: janela do ult casada à coreografia real do APK (clamp 1.15-1.8s;
    // ults curtos mantêm 1.15, longos (2.4-2.8s) tocam quase em velocidade real)
    const _ultClip = (animationsData[unit.heroId] || animationsData['1nrt'] || {}).ult;
    unit.animDuration = (_ultClip && _ultClip.fps) ? Math.min(1.8, Math.max(1.15, _ultClip.numFrames / _ultClip.fps)) : 1.15;
    unit.animTimer = unit.animDuration;
    if (unit.isPlayer && _ultClip && _ultClip.fps) { ultCine.active = true; ultCine.t = 0; ultCine.dur = unit.animDuration; }
    unit.awakenedTimer = 14.0; // 14 seconds of Awakening Mode!
    AUTH_SFX.playAt('awake_open', unit.x, unit.z, { vol: 0.9 }); AUTH_SFX.playAt('awake_flash', unit.x, unit.z, { vol: 0.8 }); // W5: awakening posicionado
    window.unitVoice(unit, 'awake', { min: 0 }); // W5-F2: grito de despertar do herói
    unit.auraMesh.visible = true;

    const maxReach = 9.5;
    const dist = nearest ? Math.min(Math.hypot(nearest.x - unit.x, nearest.z - unit.z), maxReach) : 7.0;
    const ux = unit.x + dirX * dist;
    const uz = unit.z + dirZ * dist;
    spawnVFX(ux, 1.2, uz, sk.color, 6.0, 0.65, 'ring', unit.heroId);

    if (unit.heroId === '1nrt') {
      // W-VIS: giant_rasengan EXTRAIDO do APK bound a mao (forma na mao e explode,
      // ~5.5u) — fallback procedural plantado se o extraido nao existir
      const giantGrp = buildExtractedVfxMeshGroup(unit.heroId, 0xff3b00, 0.019, activeSkillVfxModel || 'giant_rasengan');
      if (giantGrp) {
        giantGrp.position.set(ux, 2.8, uz);
        arenaGroup.add(giantGrp);
        vfxList.push({ mesh: giantGrp, age: 0, duration: 1.25, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });
      } else {
        const giantRas = createRasenganMesh(2.2, 0xff3b00);
        giantRas.position.set(ux, 2.8, uz);
        arenaGroup.add(giantRas);
        vfxList.push({ mesh: giantRas, age: 0, duration: 1.25, style: 'compound' });
      }

      // Authentic Kyuubi awakening explosion ground shockwave disc with 1efc_shock02.png
      const shockTex = loadTex('assets/skills/1efc_shock02.png');
      const shockRing = new THREE.Mesh(
        new THREE.RingGeometry(1.0, 6.5, 32),
        new THREE.MeshBasicMaterial({
          color: 0xff3b00,
          map: shockTex,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.60,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          wireframe: false
        })
      );
      shockRing.rotation.x = -Math.PI / 2;
      shockRing.position.set(ux, 0.15, uz);
      shockRing.userData = { rotSpeed: new THREE.Vector3(0, 0, 14) };
      arenaGroup.add(shockRing);
      vfxList.push({ mesh: shockRing, age: 0, duration: 1.25, style: 'compound' });
    } else if (unit.heroId === '1ssk') {
      const kirin = createKirinMesh(ux, uz);
      kirin.rotation.y = unit.rotY;
      arenaGroup.add(kirin);
      vfxList.push({ mesh: kirin, age: 0, duration: 1.35, style: 'compound' });
      spawnVFX(ux, 1.5, uz, 0x60a5fa, 6.0, 0.70, 'ring', unit.heroId);
    } else if (unit.heroId === '1skr') {
      const shatter = createGroundShatterMesh(5.5);
      shatter.position.set(ux, 0.1, uz);
      shatter.rotation.y = unit.rotY;
      arenaGroup.add(shatter);
      vfxList.push({ mesh: shatter, age: 0, duration: 1.4, style: 'compound' });
    } else if (unit.heroId === '1kks') {
      const rkMesh = createChidoriMesh(1.8, 0x38bdf8);
      rkMesh.position.set(unit.x + dirX * 1.5, 2.5, unit.z + dirZ * 1.5);
      arenaGroup.add(rkMesh);
      vfxList.push({ mesh: rkMesh, age: 0, duration: 1.25, style: 'compound' });
      const wdMesh = createWaterDragonMesh(2.5);
      wdMesh.position.set(ux, 1.0, uz);
      wdMesh.rotation.y = unit.rotY;
      arenaGroup.add(wdMesh);
      vfxList.push({ mesh: wdMesh, age: 0, duration: 1.25, style: 'compound', directional: true });
      spawnVFX(ux, 2.0, uz, 0x38bdf8, 6.0, 0.70, 'ring', unit.heroId);
    } else if (unit.heroId === '1roc') {
      const tMesh = createTornadoMesh(4.2);
      tMesh.position.set(ux, 0.1, uz);
      tMesh.rotation.y = unit.rotY;
      arenaGroup.add(tMesh);
      vfxList.push({ mesh: tMesh, age: 0, duration: 1.35, style: 'compound' });
      spawnVFX(ux, 1.5, uz, 0xef4444, 5.5, 0.65, 'ring', unit.heroId);
    } else if (unit.heroId === '1itc') {
      const amat = createAmaterasuMesh(3.8);
      amat.position.set(ux, 0.1, uz);
      amat.rotation.y = unit.rotY;
      arenaGroup.add(amat);
      vfxList.push({ mesh: amat, age: 0, duration: 1.45, style: 'compound' });
      spawnSmokePuff(ux, 2.2, uz, 3.8);
    } else if (unit.heroId === '1gar') {
      const shield = createSandShieldMesh(4.2);
      shield.position.set(unit.x, 0.2, unit.z);
      arenaGroup.add(shield);
      vfxList.push({ mesh: shield, age: 0, duration: 1.4, style: 'compound' });
      const colossalHand = createSandHandMesh(0.10);
      colossalHand.position.set(ux, 0.1, uz);
      colossalHand.rotation.y = unit.rotY;
      arenaGroup.add(colossalHand);
      vfxList.push({ mesh: colossalHand, age: 0, duration: 1.4, style: 'compound', directional: true });
      spawnVFX(ux, 1.8, uz, 0xb45309, 5.5, 0.65, 'ring', unit.heroId);
    } else if (unit.heroId === '1hnt') {
      const perpX = -dirZ * 1.8;
      const perpZ = dirX * 1.8;
      const lf1 = createLionFistMesh(1.6);
      lf1.position.set(ux + perpX, 2.8, uz + perpZ);
      lf1.rotation.y = unit.rotY;
      const lf2 = createLionFistMesh(1.6);
      lf2.position.set(ux - perpX, 2.8, uz - perpZ);
      lf2.rotation.y = unit.rotY;
      arenaGroup.add(lf1);
      arenaGroup.add(lf2);
      vfxList.push({ mesh: lf1, age: 0, duration: 1.25, style: 'compound', directional: true });
      vfxList.push({ mesh: lf2, age: 0, duration: 1.25, style: 'compound', directional: true });
    } else if (unit.heroId === '1nej') {
      const kaiten = createKaitenMesh(4.5);
      kaiten.position.set(unit.x, 2.2, unit.z);
      arenaGroup.add(kaiten);
      vfxList.push({ mesh: kaiten, age: 0, duration: 1.35, style: 'compound' });
    } else if (unit.heroId === '1jry') {
      const giantRas = createRasenganMesh(2.4, 0xef4444);
      // W-VIS-ALL: chou_rasengan EXTRAIDO do APK bound a mao direita (~4.75u)
      const chouGrp = buildExtractedVfxMeshGroup(unit.heroId, 0xf43f5e, 0.019, 'chou_rasengan');
      if (chouGrp) {
        chouGrp.position.set(unit.x + dirX * 2.0, 2.8, unit.z + dirZ * 2.0);
        arenaGroup.add(chouGrp);
        vfxList.push({ mesh: chouGrp, age: 0, duration: 1.25, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });
      }
      giantRas.position.set(ux, 3.0, uz);
      arenaGroup.add(giantRas);
      vfxList.push({ mesh: giantRas, age: 0, duration: 1.35, style: 'compound' });
    } else if (unit.heroId === '1tnd') {
      const ruptureMesh = createTsunadeUltRuptureMesh(5.5);
      ruptureMesh.position.set(ux, 0.1, uz);
      ruptureMesh.rotation.y = unit.rotY;
      arenaGroup.add(ruptureMesh);
      vfxList.push({ mesh: ruptureMesh, age: 0, duration: 1.45, style: 'compound', directional: true });
      spawnVFX(ux, 1.5, uz, 0x10b981, 6.5, 0.70, 'ring', unit.heroId);
      spawnVFX(ux, 2.0, uz, 0xfbbf24, 5.5, 0.65, 'sphere', unit.heroId);

      // heal_chakra burst centered on Tsunade (Souzou Saisei)
      const healChakraGrp = new THREE.Group();
      healChakraGrp.position.set(unit.x, 0.1, unit.z);
      const healPillar = buildExtractedVfxMeshGroup('common', 0x10b981, 0.065, '1efc_chakra05') ||
                         buildExtractedVfxMeshGroup('common', 0x34d399, 0.065, '1efc_chakra00');
      if (healPillar) {
        healPillar.position.y = 2.0;
        healPillar.userData = { rotSpeed: new THREE.Vector3(0, 8, 0) };
        healChakraGrp.add(healPillar);
      }
      arenaGroup.add(healChakraGrp);
      vfxList.push({ mesh: healChakraGrp, age: 0, duration: 1.35, style: 'compound' });
      spawnVFX(unit.x, 1.5, unit.z, 0x10b981, 5.5, 0.70, 'ring', unit.heroId);
      spawnVFX(unit.x, 2.2, unit.z, 0x34d399, 4.0, 0.60, 'sphere', unit.heroId);
      unit.hp = Math.min(unit.maxHp, unit.hp + 380);
    } else if (unit.heroId === '1orc') {
      const gateMesh = createOrochimaruDemonicBarrierMesh(5.5);
      gateMesh.position.set(ux, 0.1, uz);
      gateMesh.rotation.y = unit.rotY;
      arenaGroup.add(gateMesh);
      vfxList.push({ mesh: gateMesh, age: 0, duration: 1.45, style: 'compound', directional: true });
      spawnVFX(ux, 1.8, uz, 0x84cc16, 6.0, 0.70, 'ring', unit.heroId);
      spawnVFX(ux, 2.4, uz, 0x7e22ce, 5.0, 0.65, 'sphere', unit.heroId);
      spawnSmokePuff(ux, 2.0, uz, 4.2);
    }

    if (unit.isPlayer) {
      showBanner(`${unit.name.toUpperCase()}: ${sk.name.toUpperCase()}!`, 2200);
    }

    const hitCenterX = unit.heroId === '1nej' ? unit.x : ux;
    const hitCenterZ = unit.heroId === '1nej' ? unit.z : uz;
    for (const enemy of units) {
      if (enemy.team !== unit.team && enemy.deadTimer <= 0) {
        if (Math.hypot(enemy.x - hitCenterX, enemy.z - hitCenterZ) <= 14.0) {
          dealDamage(unit, enemy, sk.dmg, sk.name);
        }
      }
    }
  }
}

function endMatch(bannerText) {
  if (matchEnding) return; // M5: abate final + fim do tempo nao disparam duas vezes
  matchEnding = true;
  cancelMatchIntro(); // INTRO/STREAK: sem overlay fantasma sobre o slow-mo/placar
  if (bannerText) showBanner(bannerText, 2200);
  const b = Math.max(0, scoreBlue), r = Math.max(0, scoreRed);
  const winner = b === r ? 'tie' : (b > r ? 'blue' : 'red'); // M5.1: decidido NO trigger — bots nao viram o placar durante o drama
  setTimeout(() => {
    showMatchResults(winner);
  }, 1500); // M5: deixa o slow-mo do abate final (P1 juice) respirar antes da tela de vitoria
}

// ==================== M5 MATCH RESULTS: VITORIA + QUADRO FINAL + MVP ====================
function computeMVP(prefTeam) {
  let pool = units.filter(u => (prefTeam ? u.team === prefTeam : true) && ((u.kills || 0) + (u.assists || 0)) > 0);
  if (!pool.length) pool = units.filter(u => (prefTeam ? u.team === prefTeam : true));
  if (!pool.length) pool = units.slice();
  let best = pool[0], bestScore = -Infinity;
  for (const u of pool) {
    const s = (u.kills || 0) * 100 + (u.assists || 0) * 50 + (u.level || 1) * 20 - (u.deaths || 0) * 15;
    if (s > bestScore) { bestScore = s; best = u; }
  }
  return best;
}

function hideMatchResults() {
  const ov = document.getElementById('match-results-overlay');
  if (ov) ov.className = 'match-results-overlay hidden';
}

function showMatchResults(winner, bannerTextFallback) {
  const ov = document.getElementById('match-results-overlay');
  if (!ov) { returnToLobby(); return; }
  const b = Math.max(0, scoreBlue), r = Math.max(0, scoreRed);
  const win = (winner === 'blue' || (!winner && b > r)) ? 'blue'
             : (winner === 'red' || (!winner && r > b)) ? 'red' : 'tie';
  if (matchActive) recordMatchResult(win);
  AUTH_SFX.play('result', { vol: 0.9 }); // W1.1
  const CONF = {
    blue: { img: 'banner_win.png',  kanji: '勝利',      text: 'VITÓRIA DO TIME KONOHA',    cls: 'win'  },
    red:  { img: 'banner_lose.png', kanji: '敗北',      text: 'DERROTA — TIME RIVAL VENCEU', cls: 'lose' },
    tie:  { img: 'banner_tie.png',  kanji: '引き分け',  text: 'EMPATE',                   cls: 'tie'  }
  }[win];
  const bannerImg = document.getElementById('mr-banner-img');
  if (bannerImg) bannerImg.src = `${SKIN_URL}${CONF.img}`;
  const kanjiEl = document.getElementById('mr-banner-kanji');
  if (kanjiEl) kanjiEl.textContent = CONF.kanji;
  const textEl = document.getElementById('mr-banner-text');
  if (textEl) textEl.textContent = bannerTextFallback || CONF.text;

  renderSkinDigits(document.getElementById('mr-score-blue'), b);
  renderSkinDigits(document.getElementById('mr-score-red'), r);

  const mvp = computeMVP(win === 'tie' ? null : win);
  window.MVP_RESULT = mvp ? { name: mvp.name, heroId: mvp.heroId, k: mvp.kills || 0, d: mvp.deaths || 0, a: mvp.assists || 0 } : null;
  const mvpPort = document.getElementById('mr-mvp-portrait');
  if (mvpPort && mvp) mvpPort.src = mvp.portrait || (`assets/portraits/${mvp.heroId}.png`);
  const mvpName = document.getElementById('mr-mvp-name');
  if (mvpName && mvp) mvpName.textContent = mvp.name;
  const mvpKda = document.getElementById('mr-mvp-kda');
  if (mvpKda && mvp) mvpKda.textContent = `AB ${mvp.kills || 0} · MT ${mvp.deaths || 0} · AS ${mvp.assists || 0} · Nv.${mvp.level || 1}`;
  const mvpTeam = document.getElementById('mr-mvp-team');
  if (mvpTeam && mvp) mvpTeam.textContent = `MVP · ${mvp.team === 'blue' ? 'KONOHA 木ノ葉' : 'RIVAIS 敵'}`;

  const buildFinalRow = (u) => {
    const k = u.kills || 0, d = u.deaths || 0, a = u.assists || 0;
    const kdaRatio = ((k + a) / Math.max(1, d)).toFixed(1);
    const isMvp = mvp && u.id === mvp.id;
    const tag = isMvp ? '<span class="mr-mvp-tag">最優秀</span>'
             : (u.isPlayer ? '<span class="sb-status-alive">VOCÊ</span>' : '—');
    return `
      <tr class="${u.isPlayer ? 'is-player-row' : ''}">
        <td><div class="sb-ninja-cell"><img class="sb-avatar" src="${u.portrait || ('assets/portraits/' + u.heroId + '.png')}" alt="${u.name}" /><span class="sb-ninja-name">${u.name}</span></div></td>
        <td><span class="sb-lvl-badge">Nv.${u.level || 1}</span></td>
        <td><strong style="color:#8fd96a">${k}</strong></td>
        <td><strong style="color:#e09a9a">${d}</strong></td>
        <td><strong style="color:#cfc7b4">${a}</strong></td>
        <td><span class="sb-kda-stat">${kdaRatio}</span></td>
        <td>${tag}</td>
      </tr>`;
  };
  const blues = units.filter(u => u.team === 'blue');
  const reds = units.filter(u => u.team === 'red');
  const tbodyBlue = document.getElementById('mr-tbody-blue');
  const tbodyRed = document.getElementById('mr-tbody-red');
  if (tbodyBlue) tbodyBlue.innerHTML = blues.map(buildFinalRow).join('');
  if (tbodyRed) tbodyRed.innerHTML = reds.map(buildFinalRow).join('');
  const sum = (arr, f) => arr.reduce((s, u) => s + (f(u) || 0), 0);
  const subB = document.getElementById('mr-sub-blue');
  if (subB) subB.textContent = `KDA: ${sum(blues, u => u.kills)} / ${sum(blues, u => u.deaths)} / ${sum(blues, u => u.assists)}`;
  const subR = document.getElementById('mr-sub-red');
  if (subR) subR.textContent = `KDA: ${sum(reds, u => u.kills)} / ${sum(reds, u => u.deaths)} / ${sum(reds, u => u.assists)}`;

  matchActive = false; // congela o mundo 3D atras do overlay
  document.getElementById('player-death-overlay')?.classList.add('hidden');
  document.getElementById('scoreboard-tab-overlay')?.classList.add('hidden');
  ov.className = `match-results-overlay show ${CONF.cls}`;
  ov.setAttribute('aria-hidden', 'false');

  const btnRematch = document.getElementById('btn-rematch');
  if (btnRematch) btnRematch.onclick = () => { hideMatchResults(); matchEnding = false; startMatch(lastMatchConfigId); };
  const btnLobby = document.getElementById('btn-results-lobby');
  if (btnLobby) btnLobby.onclick = () => { hideMatchResults(); matchEnding = false; returnToLobby(); };
}

function returnToLobby() {
  matchActive = false;
  if (TRN.active) { TRN.active = false; TRN.bell.active = false; document.body.classList.remove('training-mode'); } // W-TRN
  hideMatchResults();
  cancelMatchIntro(); // INTRO/STREAK: limpa timers e esconde overlays ao voltar
  document.getElementById('hud-screen').classList.remove('active');
  document.getElementById('title-screen').classList.remove('active'); // W-MENU T1: nunca volta direto pro titulo
  document.getElementById('lobby-screen').classList.add('active');
  arenaGroup.visible = false;
  lobbyPedestalGroup.visible = true;
  setLobbyPage('play');
  MUSIC.play('menu'); // W6: volta a trilha do lobby
}

function toggleCameraMode() {
  cameraMode = cameraMode === 'moba' ? 'thirdperson' : 'moba';
  const player = units.find(u => u.isPlayer);
  if (cameraMode === 'thirdperson' && player) {
    tpCamYaw = player.rotY;
    tpCamPitch = 0.32;
    const camHorizDist = Math.cos(tpCamPitch) * 13.5;
    const snapX = clampCamera(player.x - Math.sin(tpCamYaw) * camHorizDist);
    const snapZ = clampCamera(player.z - Math.cos(tpCamYaw) * camHorizDist);
    const snapY = Math.max(2.2, 3.2 + Math.sin(tpCamPitch) * 13.5);
    camera.position.set(snapX, snapY, snapZ);
    camera.lookAt(player.x + Math.sin(tpCamYaw) * 6, 2.8, player.z + Math.cos(tpCamYaw) * 6);
  }
  const btn = document.getElementById('btn-cam-mode');
  if (btn) {
    btn.textContent = cameraMode === 'moba' ? '🎥 Câmera (C)' : '🎥 3ª Pessoa (C)';
  }
}

function toggleControlsDrawer() {
  const drawer = document.getElementById('controls-drawer');
  if (drawer) {
    drawer.classList.toggle('hidden');
  }
}

let scoreboardVisible = false;

function toggleScoreboard(forceState) {
  const overlay = document.getElementById('scoreboard-tab-overlay');
  if (!overlay) return;
  if (typeof forceState === 'boolean') {
    scoreboardVisible = forceState;
  } else {
    scoreboardVisible = !scoreboardVisible;
  }
  if (scoreboardVisible) {
    updateScoreboardTables();
    overlay.classList.remove('hidden');
  } else {
    overlay.classList.add('hidden');
  }
}

function updateScoreboardTables() {
  const tbodyBlue = document.getElementById('sb-tbody-blue');
  const tbodyRed = document.getElementById('sb-tbody-red');
  if (!tbodyBlue || !tbodyRed) return;

  const blueUnits = units.filter(u => u.team === 'blue');
  const redUnits = units.filter(u => u.team === 'red');

  let blueK = 0, blueD = 0, blueA = 0;
  let redK = 0, redD = 0, redA = 0;

  const renderRow = (u) => {
    const k = u.kills || 0;
    const d = u.deaths || 0;
    const a = u.assists || 0;
    if (u.team === 'blue') {
      blueK += k; blueD += d; blueA += a;
    } else {
      redK += k; redD += d; redA += a;
    }
    const kdaRatio = ((k + a) / Math.max(1, d)).toFixed(1);
    const isDead = u.deadTimer > 0;
    const statusHtml = isDead
      ? `<span class="sb-status-dead">${Math.ceil(u.deadTimer)}s</span>`
      : `<span class="sb-status-alive">Vivo</span>`;

    return `
      <tr class="${u.isPlayer ? 'is-player-row' : ''} ${isDead ? 'is-dead-row' : ''}">
        <td>
          <div class="sb-ninja-cell">
            <img class="sb-avatar" src="${u.portrait || ('assets/portraits/' + u.heroId + '.png')}" alt="${u.name}" />
            <span class="sb-ninja-name">${u.name}</span>
          </div>
        </td>
        <td><span class="sb-lvl-badge">Nv.${u.level || 1}</span></td>
        <td><strong style="color:#4ade80">${k}</strong></td>
        <td><strong style="color:#f87171">${d}</strong></td>
        <td><strong style="color:#94a3b8">${a}</strong></td>
        <td><span class="sb-kda-stat">${kdaRatio}</span></td>
        <td>${statusHtml}</td>
      </tr>
    `;
  };

  tbodyBlue.innerHTML = blueUnits.map(renderRow).join('');
  tbodyRed.innerHTML = redUnits.map(renderRow).join('');

  const subBlue = document.getElementById('blue-subtotal-kda');
  if (subBlue) subBlue.textContent = `KDA: ${blueK} / ${blueD} / ${blueA}`;
  const subRed = document.getElementById('red-subtotal-kda');
  if (subRed) subRed.textContent = `KDA: ${redK} / ${redD} / ${redA}`;

  const sbBlue = document.getElementById('sb-score-blue');
  if (sbBlue) renderSkinDigits(sbBlue, scoreBlue);
  const sbRed = document.getElementById('sb-score-red');
  if (sbRed) renderSkinDigits(sbRed, scoreRed);

  const sbClock = document.getElementById('sb-clock');
  const timer = document.getElementById('match-timer');
  if (sbClock && timer) renderSkinDigits(sbClock, matchClockText);
}

// ============================================================================
// MAIN GAME LOOP (60 FPS)
// ============================================================================
let lastTime = performance.now();

function updateMatch(dt, elapsed) {
  updateJuice(dt);
  // P1 JUICE: simDt drives combat cadence (units/AI/projectiles/VFX).
  // Clock, cooldowns, respawn and regen keep real dt (E2E contracts safe).
  const simDt = dt * JUICE.timeScale;
  if (activeMatchCfg.time != null) matchTimeRemaining = Math.max(0, matchTimeRemaining - dt); else matchTimeRemaining = 9999; // W-TRN: time null = treino sem relogio (nunca expira)
  const mins = String(Math.floor(matchTimeRemaining / 60)).padStart(2, '0');
  const secs = String(Math.floor(matchTimeRemaining % 60)).padStart(2, '0');
  matchClockText = `${mins}:${secs}`;
  if (matchClockText !== lastRenderedClock) {
    lastRenderedClock = matchClockText;
    renderSkinDigits(document.getElementById('match-timer'), matchClockText);
  }
  if (matchSuddenDeath) {
    // T5 MORTE SUBITA: timer congelado — o proximo abate decide
  } else if (matchTimeRemaining <= 0) {
    if (activeMatchCfg.mode === 'br') { // PV2: BR nao tem prorrogacao — decide por vivos/HP
      const _alive = units.filter(u => u.deadTimer <= 0);
      if (_alive.length === 1) brEndMatch(_alive[0].isPlayer, 'ÚLTIMO DE PÉ');
      else {
        const _best = _alive.slice().sort((a, b) => (b.hp / b.maxHp) - (a.hp / a.maxHp))[0];
        brEndMatch(!!(_best && _best.isPlayer), 'TEMPO ESGOTADO');
      }
      return;
    }
    if (scoreBlue === scoreRed && !matchOvertime) {
      matchOvertime = true;
      matchTimeRemaining = activeMatchCfg.overtime; // T5: prorrogacao por modo (legacy 60s, 3v3 30s)
      AUTH_SFX.play('time_up', { vol: 0.9 }); // W1.1
      showBanner('PRORROGAÇÃO! 1 MINUTO PARA DESEMPATAR', 2400);
      const _mt = document.getElementById('match-timer');
      if (_mt) _mt.classList.add('overtime');
      return;
    }
    if (scoreBlue === scoreRed) {
      matchSuddenDeath = true; // T5: empatou a prorrogacao — morte subita
      showBanner('MORTE SÚBITA! O PRÓXIMO ABATE VENCE', 2400);
      const _mt2 = document.getElementById('match-timer');
      if (_mt2) _mt2.classList.add('sudden');
      return;
    }
    endMatch(scoreBlue > scoreRed ? 'FIM DE TEMPO — VITÓRIA TIME AZUL!' : 'FIM DE TEMPO — VITÓRIA TIME VERMELHO!');
    return;
  }

  // PV2: tick do modo Realeza na Vila (zona/baús/last-standing)
  if (activeMatchCfg && activeMatchCfg.mode === 'br' && brState && matchActive && !matchEnding) updateBR(dt);
  if (TRN.active && matchActive && !matchEnding) TRN.tick(dt); // W-TRN: sinos, DPS, chakra de treino e HUD

  // Central Scroll Shrine Buff Orb
  if (shrineOrb) {
    if (shrineCooldown > 0) {
      shrineCooldown -= dt;
      shrineOrb.visible = false;
    } else {
      shrineOrb.visible = true;
      shrineOrb.rotation.y += dt * 2.5;
      shrineOrb.position.y = 2.6 + Math.sin(elapsed * 4) * 0.4;
      for (const u of units) {
        if (u.deadTimer <= 0 && Math.hypot(u.x, u.z) < 4.5) {
          u.hp = Math.min(u.maxHp, u.hp + 350);
          u.chakra = u.maxChakra;
          u.awakenedTimer = Math.max(u.awakenedTimer, 8.0);
          u.auraMesh.visible = true;
          shrineCooldown = 20.0;
          spawnVFX(0, 2.5, 0, 0xfde047, 8.0, 0.6, 'ring', u.heroId);
          if (u.isPlayer) {
            showBanner('PERGAMINHO DO CENTRO CAPTURADO! (+HP / +CHAKRA / DESPERTAR)', 2000);
            showOugiBanner();
          }
          break;
        }
      }
    }
  }

  // Update all 10 Ninjas
  for (const u of units) {
    for (const k of Object.keys(u.cds)) {
      if (u.cds[k] > 0) u.cds[k] = Math.max(0, u.cds[k] - dt);
    }
    u.chakra = Math.min(u.maxChakra, u.chakra + dt * 5.5);
    const _ultReady = u.isPlayer && u.chakra >= u.maxChakra && u.cds.r <= 0; // W5: ult pronto (anuncia 1x)
    if (_ultReady && !u._ultReadyAnnounced) AUTH_SFX.playAt('max_gauge', u.x, u.z, { vol: 0.85, min: 2500 });
    u._ultReadyAnnounced = _ultReady;

    // Base Sanctuary Healing (-74,-74 for Blue, +74,+74 for Red)
    const _bp = basePos(u.team);
    const bx = _bp.x;
    const bz = _bp.z;
    if (u.spawnShield > 0) u.spawnShield = Math.max(0, u.spawnShield - dt); // SPAWN GUARD
    if (u.hitstun > 0) u.hitstun = Math.max(0, u.hitstun - dt); // APK HITSTUN (dt real — tempo de parede)
    if (u.deadTimer <= 0 && Math.hypot(u.x - bx, u.z - bz) < 14.5) {
      u.hp = Math.min(u.maxHp, u.hp + dt * 95 * ((HERO_STATS[u.heroId] || HERO_STATS.__d).reg)); // P2
      u.chakra = Math.min(u.maxChakra, u.chakra + dt * 25);
    }

    // Respawn Timer & Fallen Ninja Logic
    if (u.deadTimer > 0) {
      u.deadTimer -= dt;

      // 1. Fallen Ninja: For the first 2.0s (deadTimer: 6.0 -> 4.0), ninja plays authentic 'down' fall and lies on ground
      if (u.deadTimer > 4.0) {
        u.mesh.visible = true;
        u.mesh.position.set(u.x, 0, u.z);
        u.mesh.rotation.y = u.rotY;
        animateCharacterRig(u.mesh, 'down', elapsed, u.deadTimer - 4.0, 2.0);
      } else if (!u.poofed) {
        // At 4.0s mark: Ninja poofs away in substitution smoke
        u.poofed = true;
        spawnSmokePuff(u.x, 1.2, u.z, 3.5);
        u.mesh.visible = false;
      }

      // Update 3D Floating World Label for dead unit
      if (u.labelEl) {
        u.labelEl.style.display = 'flex';
        u.labelEl.classList.add('dead');
        u.labelEl.innerHTML = `
          ${activeMatchCfg.respawn == null ? '<div class="ko-label-world">☠️ ELIMINADO</div>' : `<div class="ko-label-world">☠️ K.O.</div><div class="respawn-timer-world">蘇生 ${Math.ceil(u.deadTimer)}s</div>`}
        `;
      }

      // If player is dead: update death overlay countdown & progress bar
      if (u.isPlayer) {
        const deathOverlay = document.getElementById('player-death-overlay');
        if (deathOverlay) {
          deathOverlay.classList.remove('hidden');
          const timerNum = document.getElementById('death-timer-num');
          if (timerNum) renderSkinDigits(timerNum, Math.ceil(u.deadTimer));
          const progressFill = document.getElementById('death-progress-fill');
          if (progressFill) {
            const pct = Math.max(0, Math.min(100, ((6.0 - u.deadTimer) / 6.0) * 100));
            progressFill.style.width = `${pct}%`;
          }
        }
      }

      // Rebirth at Sanctuary when deadTimer reaches 0
      if (u.deadTimer <= 0) {
        if (activeMatchCfg.respawn == null) { // PV2: BR — morte permanente (nao renasce)
          u.deadTimer = 999;
          u.mesh.visible = false;
          if (u.labelEl) { u.labelEl.style.display = 'flex'; u.labelEl.classList.add('dead'); u.labelEl.innerHTML = '<div class="ko-label-world">☠️ ELIMINADO</div>'; }
        } else {
        u.spawnShield = 4.0; // SPAWN GUARD
        spawnVFX(u.x, 1.0, u.z, 0xfbbf24, 3.4, 0.55, 'ring', u.heroId);
        u.hp = u.maxHp;
        u.chakra = u.maxChakra;
        u.x = u.spawnX;
        u.z = u.spawnZ;
        u.state = 'idle';
        u.animTimer = 0;
        u.mesh.visible = true;
        u.poofed = false;
        if (u.labelEl) {
          u.labelEl.classList.remove('dead');
          u.labelEl.innerHTML = `
            <span class="u-name">${u.isPlayer ? '★ ' + u.name : u.name.split(' ')[0]} <small class="u-lvl">Nv.${u.level}</small></span>
            <div class="u-hp-bg"><div class="u-hp-fill" style="width:100%"></div></div>
            <div class="u-ck-bg"><div class="u-ck-fill" style="width:100%"></div></div>
          `;
        }

        // Divine radiant chakra light pillar & ring on resurrection
        spawnVFX(u.x, 7.0, u.z, u.team === 'blue' ? 0x38bdf8 : 0xf87171, 12.0, 1.2, 'pillar');
        spawnVFX(u.x, 1.2, u.z, 0xfde047, 10.0, 0.8, 'ring');

        // W5: ressurreição autêntica posicionada
        AUTH_SFX.playAt(AUTH_SFX.pick('stand_up1', 'stand_up2'), u.x, u.z, { vol: 0.85, min: 900 });

        // Hide player death overlay
        if (u.isPlayer) {
          const deathOverlay = document.getElementById('player-death-overlay');
          if (deathOverlay) deathOverlay.classList.add('hidden');
          showBanner('RENASCIDO NO SANTUÁRIO COM CHAKRA COMPLETO!', 2000);
        }

        renderTopTeamPortraits();
        updateScoreboardTables();
        } // PV2: fim do else (respawn normal)
      }
      continue;
    }

    // Awakening Timer & Ground Aura Rings Animation
    if (u.awakenedTimer > 0) {
      u.awakenedTimer -= dt;
      u.auraMesh.rotation.y += dt * 4;
      const r1 = u.auraMesh.getObjectByName('groundRing1');
      const r2 = u.auraMesh.getObjectByName('groundRing2');
      if (r1) {
        const s1 = 1 + (Math.sin(elapsed * 7) * 0.25 + 0.25);
        r1.scale.set(s1, s1, s1);
        if (r1.material) r1.material.opacity = 0.4 + 0.4 * Math.sin(elapsed * 7);
      }
      if (r2) {
        const s2 = 1 + (Math.cos(elapsed * 6) * 0.3 + 0.3);
        r2.scale.set(s2, s2, s2);
        if (r2.material) r2.material.opacity = 0.3 + 0.35 * Math.cos(elapsed * 6);
      }
      if (u.awakenedTimer <= 0) { u.auraMesh.visible = false; AUTH_SFX.playAt('awake_off', u.x, u.z, { vol: 0.7, min: 1500 }); } // W5: fim do awakening
    }

    if (u.comboResetTimer > 0) {
      u.comboResetTimer -= simDt; // P1 JUICE: combo window freezes in hitstop
      if (u.comboResetTimer <= 0) u.comboStep = 0;
    }

    if (u.animTimer > 0) {
      u.animTimer -= simDt; // P1 JUICE: THE hitstop — action animations freeze
    }

    if (u.pendingVfxPhases && u.pendingVfxPhases.length) {
      if (u.animDuration > 0 && u.animTimer > 0) {
        const frac = 1 - (u.animTimer / u.animDuration);
        for (const p of u.pendingVfxPhases) {
          if (!p.done && frac >= p.at) {
            p.done = true;
            const grp = buildExtractedVfxMeshGroup(p.g || u.heroId, p.c || 0xffffff, (p.s || 3) * 0.004, p.m);
            if (grp) {
              const fx = Math.sin(u.rotY), fz = Math.cos(u.rotY);
              const fd = p.fd || 0, dx = p.dx || 0;
              grp.position.set(u.x + fx * fd + fz * dx, p.y || 1.2, u.z + fz * fd - fx * dx);
              grp.rotation.y = u.rotY;
              grp.userData.rotSpeed = new THREE.Vector3(0, 4, 0);
              arenaGroup.add(grp);
              vfxList.push({ mesh: grp, age: 0, duration: p.dur || 0.7, style: 'compound', directional: true, bindUnit: u });
            }
          }
        }
        if (u.pendingVfxPhases.every(q => q.done)) u.pendingVfxPhases = null;
      } else if (u.animTimer <= 0) {
        u.pendingVfxPhases = null;
      }
    }

    if (u.isPlayer) {
      updatePlayerUnit(u, simDt); // P1 JUICE: movement/AI scale with hitstop & slow-mo
    } else {
      updateAIBotUnit(u, simDt);
    }

    // Authentic Airborne Knockback Parabola Physics
    if (u.isAirborne) {
      u.y = (u.y || 0) + (u.vy || 0) * simDt;
      u.vy = (u.vy || 0) - 26.0 * simDt;
      u.x = clampPush(u.x + (u.vx || 0) * simDt);
      u.z = clampPush(u.z + (u.vz || 0) * simDt);
      if (u.y <= 0) {
        u.y = 0;
        u.vy = 0;
        u.vx = 0;
        u.vz = 0;
        u.isAirborne = false;
        spawnGroundCrackDecal(u.x, u.z, 2.8);
        spawnSmokePuff(u.x, 0.4, u.z, 3.0);
        AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), u.x, u.z, { vol: 0.85 });
      }
    }

    // Apply position & rotation to 3D SkinnedMesh Rig
    u.mesh.position.set(u.x, u.y || 0, u.z);
    u.mesh.rotation.y = u.rotY;

    // Contact drop shadow tracking (stays on ground plane)
    if (u.mesh.userData && u.mesh.userData.shadowMesh) {
      const sm = u.mesh.userData.shadowMesh;
      sm.position.y = 0.038 - (u.y || 0);
      const airScale = Math.max(0.35, 1.0 - (u.y || 0) * 0.12);
      sm.scale.set(airScale, airScale, airScale);
      if (sm.material) sm.material.opacity = Math.max(0.18, 0.80 - (u.y || 0) * 0.1);
    }

    // M6.1: RUN autentico quando ha deslocamento real no frame
    // (nao sobrescreve attack/jutsu/ult/down — so promove idle<->run)
    const _mvd = (u.deadTimer <= 0) &&
      ((Math.abs(u.x - (u._lastX ?? u.x)) + Math.abs(u.z - (u._lastZ ?? u.z))) > 0.004);
    if (_mvd) { if (u.state === 'idle') u.state = 'run'; }
    else if (u.state === 'run') u.state = 'idle';
    u._lastX = u.x; u._lastZ = u.z;
    animateCharacterRig(u.mesh, u.state, elapsed, u.animTimer, u.animDuration);
  }

  // Animate Konoha Stage River Water flow
  for (const rMat of riverMaterials) {
    if (rMat.map) {
      rMat.map.offset.x = (elapsed * 0.08) % 1.0;
      rMat.map.offset.y = (elapsed * 0.04) % 1.0;
    }
  }

  // Animate drifting Konoha leaves
  updateKonohaLeaves(dt);

  // Update Projectiles
  for (let i = projectiles.length - 1; i >= 0; i--) {
    const p = projectiles[i];
    const dt = simDt; // P1 JUICE: kunai freeze mid-air in hitstop, drift in slow-mo
    p.life -= dt;
    p.x += p.vx * dt;
    p.z += p.vz * dt;
    p.mesh.position.set(p.x, 2.6, p.z);
    if (p.type === 'shuriken') {
      p.mesh.rotation.z += dt * 42; // Fast 3D ninja star spin!
    } else if (p.type === 'kunai' || p.directional) {
      // Stays oriented with sharp tip forward / flight direction
    } else {
      p.mesh.rotation.y += dt * 12;
    }

    let hit = false;
    for (const target of units) {
      if (target.team !== p.owner.team && target.deadTimer <= 0) {
        if (Math.hypot(target.x - p.x, target.z - p.z) <= p.radius) {
          dealDamage(p.owner, target, p.dmg, p.skillName);
          if (p.type === 'shuriken' || p.type === 'kunai') {
            AUTH_SFX.playAt(AUTH_SFX.pick('kunai_hit', 'kunai_hit2'), target.x, target.z, { vol: 0.7, min: 60 }); // W5: impacto metálico autêntico
          }
          spawnVFX(p.x, 2.6, p.z, p.color, p.radius * 1.4, 0.35, 'sphere', p.owner.heroId);
          hit = true;
          break;
        }
      }
    }
    if (hit || p.life <= 0) {
      if (!hit && (p.type === 'kunai' || p.type === 'shuriken')) AUTH_SFX.playAt('kunai_hit_wall', p.x, p.z, { vol: 0.4, min: 400 }); // W5: crava no chão
      arenaGroup.remove(p.mesh);
      projectiles.splice(i, 1);
    }
  }

  updateSkillTrails(simDt); // W-SKL+ TRAIL: rastros de mão/lâmina (congelam com o mundo no juice)
  if (ultCine.active) { // W-SKL+ CINE: cut de ult avança com o mundo (congela no hitstop)
    ultCine.t += simDt;
    const _pc = units.find(u => u.isPlayer);
    if (ultCine.t >= ultCine.dur || !_pc || _pc.state !== 'ult') ultCine.active = false;
  }
  updateShadowClones(simDt); // SPP: clones 3D (congelam com o mundo no juice)
  // PV3.1: VFX cap — acima do teto descarta o mais ANTIGO (o frescor do impacto
  // importa; efeito velho ja entregou o feedback). So roda no mobile (cap 24).
  if (window.__GOV && vfxList.length > window.__GOV.vfxCap) {
    let _wi = 0;
    for (let _k = 1; _k < vfxList.length; _k++) if (vfxList[_k].age > vfxList[_wi].age) _wi = _k;
    const _w = vfxList[_wi];
    if (_w && _w.mesh && _w.mesh.parent) _w.mesh.parent.remove(_w.mesh);
    vfxList.splice(_wi, 1);
  }
  // Update VFX
  for (let i = vfxList.length - 1; i >= 0; i--) {
    const v = vfxList[i];
    const dt = simDt; // P1 JUICE: VFX freeze with the world, play slow on kills
    v.age += dt;
    const t = v.age / v.duration;
    // Dynamic hand bone tracking if bound
    if (v.bindUnit && v.bindBoneIdx !== undefined) {
      const uMesh = v.bindUnit.mesh;
      const bones = uMesh && uMesh.userData ? uMesh.userData.bones : null;
      if (bones && bones[v.bindBoneIdx]) {
        const bone = bones[v.bindBoneIdx];
        uMesh.updateMatrixWorld(true);
        const wp = new THREE.Vector3();
        bone.getWorldPosition(wp);
        v.mesh.position.copy(wp);
        if (v.bindOffset) v.mesh.position.add(v.bindOffset);
      }
    }
    // SPP: anim procedural por skill (spin/pulse/thrust/rise)
    if (v.anim && v.mesh) {
      if (!v.mesh.userData.baseScale) v.mesh.userData.baseScale = v.mesh.scale.x || 1;
      const bs = v.mesh.userData.baseScale;
      if (v.anim === 'spin') { v.mesh.rotation.y += dt * 9.0; }
      else if (v.anim === 'pulse') { const p = 1.0 + 0.18 * Math.sin(v.age * 14.0); v.mesh.scale.set(bs * p, bs * p, bs * p); }
      else if (v.anim === 'thrust' && v.faceDir) { const mv = 14.0 * Math.max(0, 1.0 - t); v.mesh.position.x += v.faceDir.x * mv * dt; v.mesh.position.z += v.faceDir.z * mv * dt; }
      else if (v.anim === 'rise') { v.mesh.position.y += dt * 2.2; }
    }

    // Multi-axis gyroscopic rotation, stochastic jitter, procedural arcs & animated UV scrolling
    if (v.mesh) {
      v.mesh.traverse(child => {
        if (child.userData) {
          if (child.userData.rotSpeed) {
            child.rotation.x += child.userData.rotSpeed.x * dt;
            child.rotation.y += child.userData.rotSpeed.y * dt;
            child.rotation.z += child.userData.rotSpeed.z * dt;
          }
          if (child.userData.jitter) {
            const j = child.userData.jitter;
            const baseS = child.userData.baseScale || 1.0;
            const s = baseS * (1.0 + (Math.random() - 0.5) * j);
            child.scale.set(s, s, s);
          }
          if (child.userData.updateArcs) {
            child.userData.updateArcs(dt);
          }
        }
        if (child.material && child.material.map && child.userData && child.userData.uvScroll) {
          child.material.map.offset.x += child.userData.uvScroll.x * dt;
          child.material.map.offset.y += child.userData.uvScroll.y * dt;
        }
      });
    }

    if (v.style === 'extracted') {
      v.mesh.rotation.y += dt * 8;
      v.mesh.scale.multiplyScalar(1 + dt * 1.4);
    } else if (v.style === 'compound') {
      // Directional jutsu (dragons, hands, fists, cones) keep the caster's facing;
      // only radially symmetric effects get the global yaw spin.
      if (v.directional) {
        if (v.bindUnit) v.mesh.rotation.y = v.bindUnit.rotY;
      } else {
        v.mesh.rotation.y += dt * 4;
      }
      if (v.mesh.scale) v.mesh.scale.multiplyScalar(1 + dt * 0.35);
    } else if (v.style === 'smoke') {
      v.mesh.position.y += dt * 2.2;
      v.mesh.scale.multiplyScalar(1 + dt * 1.8);
      if (v.mesh.material) v.mesh.material.opacity = Math.max(0, (1 - t) * 0.75);
    } else if (v.style === 'hit_star') {
      v.mesh.rotation.x += dt * 12;
      v.mesh.rotation.y += dt * 16;
      v.mesh.scale.multiplyScalar(Math.max(0.01, 1 - dt * 4.0));
      if (v.mesh.material) v.mesh.material.opacity = Math.max(0, 1 - t);
    } else if (v.style === 'flash') {
      // P1 JUICE: white radial impact flash — explosive pop, instant fade
      const pop = 1 + t * 9;
      v.mesh.scale.set(pop, pop, 1);
      if (v.mesh.material) v.mesh.material.opacity = Math.max(0, 0.9 * (1 - t * 3.2));
    } else if (v.style === 'spark') {
      if (v.vel) {
        v.mesh.position.x += v.vel.x * dt;
        v.mesh.position.y += v.vel.y * dt;
        v.mesh.position.z += v.vel.z * dt;
      }
      v.mesh.scale.multiplyScalar(Math.max(0.01, 1 - dt * 2.5));
      if (v.mesh.material && v.mesh.material.opacity !== undefined) {
        v.mesh.material.opacity = Math.max(0, 1 - t);
      }
    } else if (v.style === 'soul') {
      if (v.vel) {
        v.mesh.position.x += v.vel.x * dt;
        v.mesh.position.y += v.vel.y * dt;
        v.mesh.position.z += v.vel.z * dt;
      }
      v.mesh.scale.multiplyScalar(Math.max(0.01, 1 - dt * 0.45));
      if (v.mesh.material && v.mesh.material.opacity !== undefined) {
        v.mesh.material.opacity = Math.max(0, (1 - t) * 0.95);
      }
    } else if (v.style === 'decal') {
      if (v.mesh.material) {
        const fade = v.age > 2.0 ? Math.max(0, 1.0 - (v.age - 2.0) / 1.5) : 1.0;
        v.mesh.material.opacity = fade * 0.88;
      }
    } else if (v.style !== 'log') {
      v.mesh.scale.setScalar(1 + t * 0.85);
      if (v.mesh.material && v.mesh.material.opacity !== undefined) {
        v.mesh.material.opacity = Math.max(0, (1 - t) * 0.85);
      }
    }
    if (v.age >= v.duration) {
      arenaGroup.remove(v.mesh);
      vfxList.splice(i, 1);
    }
  }

  if (scoreboardVisible) {
    updateScoreboardTables();
  }

  updateCameraAndHUD();
  drawMinimap();
}

function updatePlayerUnit(u, dt) {
  if (u.animTimer > 0) return;

  const charging = keys['ShiftLeft'] || keys['ShiftRight'] || keys['KeyF'] || (window.INPUT && window.INPUT.chakra);
  if (charging && u.animTimer <= 0) {
    u.state = 'charge';
    u.chakra = Math.min(u.maxChakra, u.chakra + dt * 32);
    u.auraMesh.visible = true;
    u.auraMesh.rotation.y += dt * 6;
    const r1 = u.auraMesh.getObjectByName('groundRing1');
    const r2 = u.auraMesh.getObjectByName('groundRing2');
    if (r1) r1.scale.setScalar(1 + (Math.sin(performance.now() * 0.01) * 0.25 + 0.25));
    if (r2) r2.scale.setScalar(1 + (Math.cos(performance.now() * 0.009) * 0.3 + 0.3));
    return;
  } else if (u.awakenedTimer <= 0) {
    u.auraMesh.visible = false;
  }

  let inputForward = 0;
  let inputRight = 0;
  if (keys['KeyW'] || keys['ArrowUp']) inputForward += 1;
  if (keys['KeyS'] || keys['ArrowDown']) inputForward -= 1;
  if (keys['KeyD'] || keys['ArrowRight']) inputRight += 1;
  if (keys['KeyA'] || keys['ArrowLeft']) inputRight -= 1;
  // PV0.3: joystick analogico soma com as teclas digitais e clampa em [-1, 1]
  inputForward = Math.max(-1, Math.min(1, inputForward + (window.INPUT ? window.INPUT.moveZ : 0)));
  inputRight = Math.max(-1, Math.min(1, inputRight + (window.INPUT ? window.INPUT.moveX : 0)));

  let mx = 0, mz = 0;

  if (inputForward !== 0 || inputRight !== 0) {
    if (cameraMode === 'thirdperson') {
      // 3rd-person movement relative to horizontal camera view vector
      const camFwd = camera.getWorldDirection(new THREE.Vector3());
      const fLen = Math.hypot(camFwd.x, camFwd.z);
      const fwdX = fLen > 0.001 ? camFwd.x / fLen : Math.sin(tpCamYaw);
      const fwdZ = fLen > 0.001 ? camFwd.z / fLen : Math.cos(tpCamYaw);
      const rightX = -fwdZ;
      const rightZ = fwdX;

      // Forward (W) moves in camera forward direction, S moves opposite,
      // D moves right perpendicular to camera, A moves left
      mx = fwdX * inputForward + rightX * inputRight;
      mz = fwdZ * inputForward + rightZ * inputRight;
    } else {
      // Fixed world axes for MOBA Top-Down mode
      mx = inputRight;
      mz = -inputForward; // W moves North (-Z), S moves South (+Z)
    }

    const len = Math.hypot(mx, mz);
    if (len > 0.0001) {
      mx /= len;
      mz /= len;
    }

    const spd = u.speed * (u.awakenedTimer > 0 ? 1.25 : 1.0);
    let nextX = u.x + mx * spd * dt;
    let nextZ = u.z + mz * spd * dt;
    if (ARENA.shape === 'circle') {
      const hyp = Math.hypot(nextX, nextZ);
      if (hyp > ARENA.radius && hyp > 0.001) {
        const factor = ARENA.radius / hyp;
        nextX *= factor;
        nextZ *= factor;
      }
      u.x = nextX;
      u.z = nextZ;
    } else if (ARENA.bounds) {
      u.x = THREE.MathUtils.clamp(nextX, ARENA.bounds.minX, ARENA.bounds.maxX);
      u.z = THREE.MathUtils.clamp(nextZ, ARENA.bounds.minZ, ARENA.bounds.maxZ);
    } else {
      u.x = clampArena(nextX);
      u.z = clampArena(nextZ);
    }

    // Smooth rotation towards movement direction
    const targetRot = Math.atan2(mx, mz);
    let rotDiff = targetRot - u.rotY;
    rotDiff = Math.atan2(Math.sin(rotDiff), Math.cos(rotDiff));
    const rotSpeed = 14; // smooth angular speed (rad/s)
    u.rotY += Math.sign(rotDiff) * Math.min(Math.abs(rotDiff), rotSpeed * dt);

    // In 3rd-person mode, when running forward, gently align camera yaw to follow behind
    if (cameraMode === 'thirdperson' && inputForward > 0) {
      let camYawDiff = u.rotY - tpCamYaw;
      camYawDiff = Math.atan2(Math.sin(camYawDiff), Math.cos(camYawDiff));
      tpCamYaw += camYawDiff * 0.035;
    }

    if (u.animTimer <= 0) {
      u.state = u.awakenedTimer > 0 ? 'dash' : 'run';
    }
  } else if (u.animTimer <= 0) {
    u.state = 'idle';
  }

  // Left mouse click for basic combo attack (Space is reserved for Kawarimi)
  if (mouseDown || (window.INPUT && window.INPUT.fire)) executeSkill(u, 'atk');
}

function updateAIBotUnit(u, dt) {
  if (u.isDummy) { u.state = 'idle'; return; } // W-TRN: boneco de treino nao pensa — e um tronco
  if (u.animTimer > 0) return;

  // Low HP retreat to base fountain
  if (u.hp < u.maxHp * 0.24) {
    if (u.cds.e <= 0 && u.chakra >= u.kit.e.cost) {
      executeSkill(u, 'e');
      return;
    }
    const _bp = basePos(u.team);
    const bx = _bp.x;
    const bz = _bp.z;
    const dx = bx - u.x, dz = bz - u.z;
    const dist = Math.hypot(dx, dz) || 1;
    u.x += (dx / dist) * u.speed * dt;
    u.z += (dz / dist) * u.speed * dt;
    u.rotY = Math.atan2(dx, dz);
    u.state = 'run';
    return;
  }

  const enemy = findNearestEnemy(u, 999); // M6.2: arena viva — bases ficam a ~209u; busca de 90 deixava a arena cidade-fantasma
  if (!enemy) {
    u.state = 'idle';
    return;
  }

  const dx = enemy.x - u.x;
  const dz = enemy.z - u.z;
  const dist = Math.hypot(dx, dz) || 1;
  u.rotY = Math.atan2(dx, dz);

  // Use Ultimate, Q, W or Basic Attack when in range
  if (dist < 12 && u.cds.r <= 0 && u.chakra >= u.kit.r.cost && Math.random() < 0.08) {
    executeSkill(u, 'r');
    return;
  }
  if (dist < 11 && u.cds.q <= 0 && u.chakra >= u.kit.q.cost && Math.random() < 0.12) {
    executeSkill(u, 'q');
    return;
  }
  if (dist < 16 && u.cds.w <= 0 && u.chakra >= u.kit.w.cost && Math.random() < 0.1) {
    executeSkill(u, 'w');
    return;
  }
  if (dist <= 6.2) {
    if (u.cds.atk <= 0) executeSkill(u, 'atk');
    const sx = -dz / dist * u.aiStrafeDir;
    const sz = dx / dist * u.aiStrafeDir;
    let nextX = u.x + sx * u.speed * 0.55 * dt;
    let nextZ = u.z + sz * u.speed * 0.55 * dt;
    if (ARENA.shape === 'circle') {
      const hyp = Math.hypot(nextX, nextZ);
      if (hyp > ARENA.playerLimit && hyp > 0.001) {
        const factor = ARENA.playerLimit / hyp;
        nextX *= factor;
        nextZ *= factor;
      }
      u.x = nextX;
      u.z = nextZ;
    } else if (ARENA.bounds) {
      u.x = THREE.MathUtils.clamp(nextX, ARENA.bounds.minX, ARENA.bounds.maxX);
      u.z = THREE.MathUtils.clamp(nextZ, ARENA.bounds.minZ, ARENA.bounds.maxZ);
    } else {
      u.x = clampPlayer(nextX);
      u.z = clampPlayer(nextZ);
    }
    u.state = u.awakenedTimer > 0 ? 'dash' : 'run';
  } else {
    let nextX = u.x + (dx / dist) * u.speed * dt;
    let nextZ = u.z + (dz / dist) * u.speed * dt;
    if (ARENA.shape === 'circle') {
      const hyp = Math.hypot(nextX, nextZ);
      if (hyp > ARENA.playerLimit && hyp > 0.001) {
        const factor = ARENA.playerLimit / hyp;
        nextX *= factor;
        nextZ *= factor;
      }
      u.x = nextX;
      u.z = nextZ;
    } else if (ARENA.bounds) {
      u.x = THREE.MathUtils.clamp(nextX, ARENA.bounds.minX, ARENA.bounds.maxX);
      u.z = THREE.MathUtils.clamp(nextZ, ARENA.bounds.minZ, ARENA.bounds.maxZ);
    } else {
      u.x = clampPlayer(nextX);
      u.z = clampPlayer(nextZ);
    }
    u.state = u.awakenedTimer > 0 ? 'dash' : 'run';
  }
}

function updateCameraAndHUD() {
  if (cameraMode === 'cinematic' || cameraMode === 'free') return;
  const player = units.find(u => u.isPlayer);
  if (!player) return;

  if (cameraMode === 'moba') {
    const targetCamPos = new THREE.Vector3(player.x, 38, player.z + 32);
    camera.position.lerp(targetCamPos, 0.12);
    camera.lookAt(player.x, 1.5, player.z - 2);
  } else {
    // 3rd-Person Action Camera with stage clipping & glitch prevention
    const camDist = 16; // PV4.2: zoom afastado a pedido (era 13.5)
    const camPitchOffset = Math.sin(tpCamPitch) * camDist;
    const camHorizDist = Math.cos(tpCamPitch) * camDist;

    let targetX = player.x - Math.sin(tpCamYaw) * camHorizDist;
    let targetZ = player.z - Math.cos(tpCamYaw) * camHorizDist;
    let targetY = 3.2 + camPitchOffset;

    // Prevent stage / scenario clipping or glitching:
    // 1. Clamp Y so it never dips below ground/river level (Math.max(2.2, ...)) and respect ceiling clamp (cameraMaxY)
    targetY = Math.min(ARENA.cameraMaxY || 100, Math.max(2.2, targetY));

    // 2. Clamp X and Z within arena boundary: circular clamp for circular arenas, bounds/box for others
    if (ARENA.shape === 'circle') {
      const hyp = Math.hypot(targetX, targetZ);
      const limit = ARENA.cameraLimit || ARENA.radius;
      if (hyp > limit && hyp > 0.001) {
        const factor = limit / hyp;
        targetX *= factor;
        targetZ *= factor;
      }
    } else if (ARENA.bounds) {
      targetX = THREE.MathUtils.clamp(targetX, ARENA.bounds.minX, ARENA.bounds.maxX);
      targetZ = THREE.MathUtils.clamp(targetZ, ARENA.bounds.minZ, ARENA.bounds.maxZ);
    } else {
      targetX = clampCamera(targetX);
      targetZ = clampCamera(targetZ);
    }

    // 3. Prevent camera from clipping inside player model if compressed by wall clamping
    const distToPlayer = Math.hypot(targetX - player.x, targetZ - player.z);
    if (distToPlayer < 3.0 && distToPlayer > 0.001) {
      const pushFactor = 3.0 / distToPlayer;
      targetX = player.x + (targetX - player.x) * pushFactor;
      targetZ = player.z + (targetZ - player.z) * pushFactor;
    }

    // 4. Smooth camera follow with damping/lerp so fast turning does not cause visual glitches or inverted normals
    camera.position.lerp(new THREE.Vector3(targetX, targetY, targetZ), 0.12);

    // Enforce safety clamping on actual position
    if (ARENA.shape === 'circle') {
      const hyp = Math.hypot(camera.position.x, camera.position.z);
      const limit = ARENA.cameraLimit || ARENA.radius;
      if (hyp > limit && hyp > 0.001) {
        const factor = limit / hyp;
        camera.position.x *= factor;
        camera.position.z *= factor;
      }
    } else if (ARENA.bounds) {
      camera.position.x = THREE.MathUtils.clamp(camera.position.x, ARENA.bounds.minX, ARENA.bounds.maxX);
      camera.position.z = THREE.MathUtils.clamp(camera.position.z, ARENA.bounds.minZ, ARENA.bounds.maxZ);
    } else {
      camera.position.x = clampCamera(camera.position.x);
      camera.position.z = clampCamera(camera.position.z);
    }
    camera.position.y = Math.min(ARENA.cameraMaxY || 100, Math.max(2.2, camera.position.y));

    const lookTarget = new THREE.Vector3(
      player.x + Math.sin(tpCamYaw) * 6,
      2.8,
      player.z + Math.cos(tpCamYaw) * 6
    );
    if (camera.position.distanceToSquared(lookTarget) > 0.01) {
      camera.lookAt(lookTarget);
    }
  }

  // P1 JUICE: additive impact shake on top of the solved camera position
  applyCameraShake();

  // W-SKL+ CINE: blend do cut de ult por cima da posição resolvida
  const _ucb = ultCineBlend();
  if (_ucb > 0.01) {
    const fx = Math.sin(player.rotY), fz = Math.cos(player.rotY);
    const cinePos = new THREE.Vector3(player.x - fx * 7.2, 2.7, player.z - fz * 7.2);
    camera.position.lerpVectors(camera.position, cinePos, Math.min(1, _ucb * 0.92));
    camera.lookAt(player.x + fx * 2.0, 1.75, player.z + fz * 2.0);
  }

  // Update Player HUD Bars
  const hpPct = Math.round((player.hp / player.maxHp) * 100);
  const ckPct = Math.round((player.chakra / player.maxChakra) * 100);
  document.getElementById('hud-hp-fill').style.width = `${hpPct}%`;
  document.getElementById('hud-hp-text').textContent = `VIDA ${Math.ceil(player.hp)} / ${player.maxHp}`;
  document.getElementById('hud-ck-fill').style.width = `${ckPct}%`;
  document.getElementById('hud-ck-text').textContent = `CHAKRA ${Math.floor(player.chakra)} / ${player.maxChakra}`;
  document.getElementById('hud-player-lvl').textContent = `Nv.${player.level}`;
  document.getElementById('hud-kda').textContent = `ABATES: ${player.kills}  |  MORTES: ${player.deaths}`;
  document.getElementById('hud-awakening-state').classList.toggle('hidden', player.awakenedTimer <= 0);

  for (const slot of ['atk', 'q', 'w', 'e', 'r']) {
    const cdEl = document.getElementById(`cd-${slot}`);
    if (!cdEl) continue;
    const rem = player.cds[slot];
    const maxCd = (player.kit && player.kit[slot] && player.kit[slot].cd) ? player.kit[slot].cd : 1;
    if (rem > 0.05) {
      const pct = Math.min(100, Math.max(0, (rem / maxCd) * 100));
      cdEl.style.display = 'flex';
      cdEl.style.background = `conic-gradient(rgba(0,0,0,0.78) ${pct.toFixed(1)}%, transparent 0%)`;
      cdEl.textContent = rem.toFixed(1) + 's';
    } else {
      cdEl.style.display = 'none';
      cdEl.style.background = 'none';
      cdEl.textContent = '';
    }
  }

  // PV4: espelha o CD dos slots nos botoes touch (mesma fonte de verdade #cd-*)
  for (const _s of ['atk', 'q', 'w', 'e', 'r']) {
    const _src = document.getElementById(`cd-${_s}`);
    const _dst = document.getElementById(`cdt-${_s}`);
    if (_src && _dst) {
      _dst.style.display = _src.style.display;
      _dst.style.background = _src.style.background;
      _dst.textContent = _src.textContent;
    }
  }

  // Synchronize 5v5 Top Team Mini-Portraits (Alive dot & Respawn Countdown)
  for (const u of units) {
    const topIcon = document.getElementById(`top-icon-${u.id}`);
    if (!topIcon) continue;
    const cdEl = document.getElementById(`respawn-cd-${u.id}`);
    const aliveDot = topIcon.querySelector('.alive-dot');
    if (u.deadTimer > 0) {
      if (!topIcon.classList.contains('dead')) topIcon.classList.add('dead');
      if (aliveDot) aliveDot.style.display = 'none';
      if (cdEl) {
        cdEl.style.display = 'flex';
        renderSkinDigits(cdEl, Math.ceil(u.deadTimer));
      }
    } else {
      if (topIcon.classList.contains('dead')) topIcon.classList.remove('dead');
      if (aliveDot) aliveDot.style.display = 'block';
      if (cdEl) {
        cdEl.textContent = '';
        cdEl.style.display = 'none';
      }
    }
  }

  // Project 3D coordinates of all 10 ninjas to 2D screen labels
  const halfW = window.innerWidth / 2;
  const halfH = window.innerHeight / 2;
  const projVec = new THREE.Vector3();

  for (const u of units) {
    const py = u.deadTimer > 0 ? 3.2 : 6.2;
    projVec.set(u.x, py, u.z).project(camera);
    if (projVec.z > 1) {
      u.labelEl.style.display = 'none';
      continue;
    }
    const sx = (projVec.x * halfW) + halfW;
    const sy = -(projVec.y * halfH) + halfH;
    u.labelEl.style.display = 'flex';
    u.labelEl.style.left = `${sx}px`;
    u.labelEl.style.top = `${sy}px`;
    if (u.deadTimer <= 0) {
      u.labelEl.classList.toggle('shielded', u.spawnShield > 0); // SPAWN GUARD
      const hpFill = u.labelEl.querySelector('.u-hp-fill');
      if (hpFill) hpFill.style.width = `${(u.hp / u.maxHp) * 100}%`;
      const ckFill = u.labelEl.querySelector('.u-ck-fill');
      if (ckFill) ckFill.style.width = `${(u.chakra / u.maxChakra) * 100}%`;
      const lvl = u.labelEl.querySelector('.u-lvl');
      if (lvl) lvl.textContent = `Nv.${u.level}`;
    }
  }
}

function drawMinimap() {
  const mCanvas = document.getElementById('minimap-canvas');
  if (!mCanvas) return;
  const ctx = mCanvas.getContext('2d');
  const w = mCanvas.width, h = mCanvas.height;
  ctx.fillStyle = '#14261c';
  ctx.fillRect(0, 0, w, h);

  const rad = ARENA.radius || 88;
  const toMapX = (val) => THREE.MathUtils.clamp(((val + rad) / (rad * 2)) * w, 4, w - 4);
  const toMapZ = (val) => THREE.MathUtils.clamp(((val + rad) / (rad * 2)) * h, 4, h - 4);

  // River diagonal (sd00a and sd04a have river; sd01b and sd03b do not)
  if (ARENA.id === 'sd00a' || ARENA.id === 'sd04a') {
    ctx.strokeStyle = '#0284c7';
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(w, 0);
    ctx.stroke();
  }

  const bpB = basePos('blue');
  const bpR = basePos('red');

  // Main Lane connecting bases
  ctx.strokeStyle = '#785a3c';
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.moveTo(toMapX(bpB.x), toMapZ(bpB.z));
  ctx.lineTo(toMapX(bpR.x), toMapZ(bpR.z));
  ctx.stroke();

  // Base Sanctuaries
  ctx.fillStyle = '#3b82f6';
  ctx.beginPath();
  ctx.arc(toMapX(bpB.x), toMapZ(bpB.z), 5.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#ef4444';
  ctx.beginPath();
  ctx.arc(toMapX(bpR.x), toMapZ(bpR.z), 5.5, 0, Math.PI * 2);
  ctx.fill();

  // Central Shrine
  if (shrineOrb && shrineOrb.visible) {
    ctx.fillStyle = '#fde047';
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 4.5, 0, Math.PI * 2);
    ctx.fill();
  }

  // Units
  for (const u of units) {
    if (u.deadTimer > 0) continue;
    const mx = toMapX(u.x);
    const mz = toMapZ(u.z);
    ctx.fillStyle = u.isPlayer ? '#22c55e' : (u.team === 'blue' ? '#3b82f6' : '#ef4444');
    ctx.beginPath();
    ctx.arc(mx, mz, u.isPlayer ? 5 : 3.8, 0, Math.PI * 2);
    ctx.fill();
    if (u.isPlayer) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
}

function animate(now) {
  requestAnimationFrame(animate);
  const dt = Math.min(0.05, (now - lastTime) / 1000);
  const frameMs = now - lastTime;
  lastTime = now;
  const elapsed = now / 1000;

  // PV-A: amostragem de perf (barata: 1 subtracao + 1 comparacao por frame)
  if (window.__PERF && window.__PERF.enabled) {
    PERF.frames++;
    PERF.lastFrameMs = frameMs;
    if (frameMs > PERF.worstFrameMs) PERF.worstFrameMs = frameMs;
    PERF.frameRing.push(frameMs);
    if (PERF.frameRing.length > 1200) PERF.frameRing.shift();
    if (now - PERF.lastSample >= 500 && PERF.frames > 0) {
      PERF.fpsWindow.push(+(1000 / Math.max(1, (now - PERF.lastSample) / PERF.frames)).toFixed(1));
      if (PERF.fpsWindow.length > 600) PERF.fpsWindow.shift();
      PERF.frames = 0;
      PERF.lastSample = now;
    }
  }

  if (!matchActive) {
    // Lobby 3D Character Pedestal Camera
    camera.position.set(0, 3.35, 11.6);
    camera.lookAt(0, 2.28, 0);
    if (camera.fov !== 48) { // P1 JUICE: restore native fov after match drama
      camera.fov = 48;
      camera.updateProjectionMatrix();
    }
    if (lobbyHeroMesh) {
      if (!mouseDown) lobbyHeroMesh.rotation.y += dt * 0.55;
      const isActionPose = (lobbyPreviewPose === 'attack' || lobbyPreviewPose === 'attack2' || lobbyPreviewPose === 'attack3' || lobbyPreviewPose === 'jutsu' || lobbyPreviewPose === 'ult');
      const previewTimer = isActionPose
        ? 0.85 - (elapsed % 0.85)
        : elapsed;
      animateCharacterRig(lobbyHeroMesh, lobbyPreviewPose, elapsed, previewTimer, 0.85);
    }
  } else {
    updateMatch(dt, elapsed);
  }

  renderer.render(scene, camera);
}

// ============================================================================
// INITIALIZE UI & LOAD GAME ASSETS
// ============================================================================
async function init() {
  loadSkinManifest();
  buildLobbyPedestal();

  const [metaRes, anmRes, vfxRes, arenasRes] = await Promise.all([
    fetch('assets/data/roster_meta.json?v=9').then(r => r.json()).catch(() => ({})), // P0 hardening
    fetch('assets/data/animations.json?v=10').then(r => r.json()).catch(() => ({})),
    fetch('assets/skills/skill_vfx.json?v=10').then(r => r.json()).catch(() => ({})),
    // PV-B.1: stage_3d.json (7,29 MB) saiu do boot — o mapa da arena e a fonte da verdade
    fetch('assets/data/arenas.json?v=9').then(r => r.json()).catch(() => null)
  ]);

  rosterMeta = (metaRes && metaRes.roster) || []; // P0: boot nunca morre por roster falho
  animationsData = anmRes || {};
  skillVfxData = vfxRes || {};
  stage3DData = null; // preenchido por applyArena() (ou fallback legado em caso de falha)
  arenasCatalog = (arenasRes && arenasRes.arenas) || [];

  if (arenasRes && arenasRes.default) selectedArenaId = arenasRes.default;
  await applyArena(selectedArenaId, { silent: true });
  window.__ARENA_BOOT_DONE = performance.now(); // W-TRN: readiness — applyArena silencioso do boot concluido
  renderArenaPicker();

  const gridEl = document.getElementById('roster-grid');
  gridEl.innerHTML = rosterMeta.map(h => `
    <div class="hero-card roster-card" data-id="${h.id}">
      <img class="card-avatar" src="${h.portrait}" alt="${h.name}" />
      <div class="card-info">
        <span class="card-name">${h.name}</span>
        <span class="card-meta">${h.clan || (h.title ? h.title.split('•')[0].trim() : '')}</span>
        <span class="card-height">${h.heightCm || 150} cm (Databook)</span>
      </div>
    </div>
  `).join('');

  gridEl.querySelectorAll('.roster-card').forEach(card => {
    card.addEventListener('click', () => {
      sfx.init();
      AUTH_SFX.play('menu_slct', { vol: 0.6 }); // W5: UI autêntica
      selectLobbyHero(card.dataset.id);
    });
  });

  await selectLobbyHero('1nrt');

  initLobbyNav();
  window.__ajustesReady = true; // W1.2.3: TODOS os listeners do lobby attached — sinal E2E determinístico
  renderCollectionPage();
  renderArenaPage();
  renderProfilePage();
  setLobbyPage('play');

  // Pointer events for lobby rotation and 3rd-person camera rotation
  let rightMouseDown = false;
  window.addEventListener('contextmenu', (e) => {
    if (matchActive) e.preventDefault();
  });

  window.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'touch') return; // PV1.4c: touch tem controles proprios (joystick/cluster)
    if (e.button === 2) {
      rightMouseDown = true;
    } else if (e.button === 0) {
      // Filter out clicks on UI buttons/drawer/cards
      if (e.target && e.target.closest && e.target.closest('button, #controls-drawer, .controls-cheat-sheet, .hud-top-bar, .moba-ability-btn, .skill-slot, .roster-card, .btn')) {
        return;
      }
      mouseDown = true;
    }
  });

  window.addEventListener('pointerup', (e) => {
    if (e.button === 2) rightMouseDown = false;
    else if (e.button === 0) mouseDown = false;
  });

  window.addEventListener('pointermove', (e) => {
    if (!matchActive && mouseDown && lobbyHeroMesh) {
      lobbyHeroMesh.rotation.y += e.movementX * 0.012;
    } else if (matchActive && cameraMode === 'thirdperson' && !window.__DEVICE.isTouch && (rightMouseDown || mouseDown)) {
      tpCamYaw -= e.movementX * 0.005;
      tpCamPitch = THREE.MathUtils.clamp(tpCamPitch + e.movementY * 0.003, 0.05, 0.75);
    }
  });

  document.getElementById('btn-toggle-wireframe').addEventListener('click', (e) => {
    isWireframe = !isWireframe;
    e.target.textContent = `MALHA 3D: ${isWireframe ? 'LIGADA' : 'DESLIGADA'}`;
    if (lobbyHeroMesh) {
      lobbyHeroMesh.userData.materials.forEach(m => { m.wireframe = isWireframe; });
    }
  });

  const poses = [
    { key: 'idle', label: 'PARADO (POSTURA)' },
    { key: 'run', label: 'CORRIDA NINJA (RUN0)' },
    { key: 'dash', label: 'INVESTIDA RÁPIDA (DSH0L)' },
    { key: 'attack', label: 'COMBO GOLPE 1' },
    { key: 'attack2', label: 'COMBO GOLPE 2' },
    { key: 'attack3', label: 'COMBO FINALIZADOR' },
    { key: 'jutsu', label: 'NINJUTSU (SKL1)' },
    { key: 'ult', label: 'DESPERTAR / OUGI (SKL2)' }
  ];
  let poseIdx = 0;
  document.getElementById('btn-toggle-pose').addEventListener('click', (e) => {
    poseIdx = (poseIdx + 1) % poses.length;
    lobbyPreviewPose = poses[poseIdx].key;
    e.target.textContent = `Animar: ${poses[poseIdx].label}`;
    sfx.init();
    AUTH_SFX.play('menu_fix', { vol: 0.7 }); // W5: UI autêntica
  });

  document.getElementById('btn-start-match').addEventListener('click', () => {
    startMatch(selectedModeId);
  });

  // PV1.1: seletor de modo (#mode-picker) — decisao #1: 3v3 default
  document.querySelectorAll('#mode-picker .mode-chip').forEach(ch => {
    ch.addEventListener('click', () => {
      if (ch.disabled) return;
      selectedModeId = ch.dataset.mode;
      document.querySelectorAll('#mode-picker .mode-chip').forEach(c => c.classList.toggle('selected', c === ch));
      sfx.click();
    });
  });

  document.getElementById('btn-back-lobby').addEventListener('click', () => {
    returnToLobby();
  });

  const btnCam = document.getElementById('btn-cam-mode');
  if (btnCam) {
    btnCam.addEventListener('click', toggleCameraMode);
  }

  const btnHelp = document.getElementById('btn-help-controls');
  const btnCloseHelp = document.getElementById('btn-close-controls');
  if (btnHelp) {
    btnHelp.addEventListener('click', () => {
      toggleControlsDrawer();
    });
  }
  if (btnCloseHelp) {
    btnCloseHelp.addEventListener('click', () => {
      const drawer = document.getElementById('controls-drawer');
      if (drawer) drawer.classList.add('hidden');
    });
  }

  const btnScoreboard = document.getElementById('btn-toggle-scoreboard');
  const btnCloseScoreboard = document.getElementById('btn-close-scoreboard');
  if (btnScoreboard) {
    btnScoreboard.addEventListener('click', () => {
      toggleScoreboard();
    });
  }
  if (btnCloseScoreboard) {
    btnCloseScoreboard.addEventListener('click', () => {
      toggleScoreboard(false);
    });
  }

  // Skill Bar Clicks (both .moba-ability-btn and .skill-slot)
  document.querySelectorAll('.moba-ability-btn, .skill-slot').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const player = units.find(u => u.isPlayer);
      if (!player) return;
      const slot = btn.dataset.slot;
      if (slot === 'c') {
        player.chakra = Math.min(player.maxChakra, player.chakra + 25);
        AUTH_SFX.play('chakura_use', { vol: 0.7 }); // W5: chakra autêntico
      } else {
        executeSkill(player, slot);
      }
    });
  });

  // Keyboard Listeners (Tab -> Scoreboard, W -> Move, E -> Skill 2, Space -> Kawarimi, R -> Ult)
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Tab') {
      e.preventDefault();
      toggleScoreboard(true);
      return;
    }
    if (e.code === 'Escape') {
      toggleScoreboard(false);
      const drawer = document.getElementById('controls-drawer');
      if (drawer) drawer.classList.add('hidden');
    }

    keys[e.code] = true;
    if (!matchActive) return;
    const player = units.find(u => u.isPlayer);
    if (!player) return;

    if (e.code === 'KeyQ' || e.code === 'Digit1') {
      executeSkill(player, 'q');
    } else if (e.code === 'KeyE' || e.code === 'Digit2') {
      executeSkill(player, 'w'); // Skill 2 is kit slot 'w'
    } else if (e.code === 'Space' || e.code === 'Digit3') {
      executeSkill(player, 'e'); // Kawarimi is kit slot 'e'
    } else if (e.code === 'KeyR' || e.code === 'Digit4') {
      executeSkill(player, 'r'); // Ultimate is kit slot 'r'
    } else if (e.code === 'KeyC') {
      toggleCameraMode();
    } else if (e.code === 'KeyH') {
      toggleControlsDrawer();
    } else if (e.code === 'KeyT') {
      if (TRN.active) TRN.reset(true); // W-TRN: resetar stats/chakra/recargas
    } else if (e.code === 'KeyB') {
      if (TRN.active) TRN.toggleBell(); // W-TRN: Teste dos Sinos
    }
  });

  window.addEventListener('keyup', (e) => {
    keys[e.code] = false;
    if (e.code === 'Tab') {
      e.preventDefault();
      toggleScoreboard(false);
    }
  });

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  requestAnimationFrame(animate);
}

// Expose runtime hooks for inspection & testing
window.startMatch = startMatch;                           // PV1.1: API por modo
window.MATCH_CONFIGS = MATCH_CONFIGS;                     // PV-A: leitura por tool/E2E
window.__activeMatchCfg = () => activeMatchCfg;           // PV-A: config da partida em curso
window.start5v5Match = () => startMatch('dm_legacy_5v5'); // alias legacy — contrato E2E (F02/F04)
window.setLobbyPage = setLobbyPage;
window.__lobbyPage = () => lobbyPage;
window.__pedestalVisible = () => lobbyPedestalGroup.visible;
window.__profileData = loadProfileData;
window.showMatchResults = showMatchResults; // M5
window.computeMVP = computeMVP; // M5
window.hideMatchResults = hideMatchResults; // M5
window.returnToLobby = returnToLobby; // M5
window.endMatch = endMatch; // M5 (teste/captura)
window.__isMatchEnding = () => matchEnding; // M5.2 (debug/teste)
window.__activeVfxModel = () => activeSkillVfxModel; // M7 (validacao E2E)
window.SKILL_VFX_MAP = SKILL_VFX_MAP; // M7 (inspecao)
window.SKILL_VFX_ANIM = SKILL_VFX_ANIM; // SPP (inspecao)
window.__shadowClones = () => shadowClones; // SPP (validacao E2E)
window.HERO_STATS = HERO_STATS; // P2 (validacao)
window.HERO_KITS = HERO_KITS;
window.loadCharacter3DModel = loadCharacter3DModel;
window.__matchState = {
  get time() { return matchTimeRemaining; },
  get br() { return brState; }, // PV2: estado BR p/ E2E
  set time(v) { matchTimeRemaining = Math.max(0, v); },
  get overtime() { return matchOvertime; },
  get suddenDeath() { return matchSuddenDeath; },
  get blue() { return scoreBlue; },
  get red() { return scoreRed; }
}; // T5 (debug/teste)
window.executeSkill = executeSkill;
window.dealDamage = dealDamage;
window.JUICE = JUICE; // P1 JUICE: exposed for E2E/inspection
window.selectLobbyHero = selectLobbyHero;
window.toggleCameraMode = toggleCameraMode;
window.toggleControlsDrawer = toggleControlsDrawer;
window.toggleScoreboard = toggleScoreboard;
window.updateScoreboardTables = updateScoreboardTables;
window.renderSkinDigits = renderSkinDigits;
window.showOugiBanner = showOugiBanner;
window.flashKawarimi = flashKawarimi;
Object.defineProperty(window, 'scoreboardVisible', {
  get: () => scoreboardVisible,
  set: (v) => { toggleScoreboard(v); }
});
Object.defineProperty(window, 'cameraMode', {
  get: () => cameraMode,
  set: (v) => {
    cameraMode = v;
    const p = units.find(u => u.isPlayer);
    if (v === 'thirdperson' && p) {
      tpCamYaw = p.rotY;
      tpCamPitch = 0.32;
      const camHorizDist = Math.cos(tpCamPitch) * 13.5;
      const snapX = clampCamera(p.x - Math.sin(tpCamYaw) * camHorizDist);
      const snapZ = clampCamera(p.z - Math.cos(tpCamYaw) * camHorizDist);
      const snapY = Math.max(2.2, 3.2 + Math.sin(tpCamPitch) * 13.5);
      camera.position.set(snapX, snapY, snapZ);
      camera.lookAt(p.x + Math.sin(tpCamYaw) * 6, 2.8, p.z + Math.cos(tpCamYaw) * 6);
    }
  }
});
Object.defineProperty(window, 'keys', { get: () => keys });
Object.defineProperty(window, 'tpCamYaw', {
  get: () => tpCamYaw,
  set: (v) => {
    tpCamYaw = v;
    if (cameraMode === 'thirdperson') {
      const p = units.find(u => u.isPlayer);
      if (p) {
        const camHorizDist = Math.cos(tpCamPitch) * 13.5;
        const snapX = clampCamera(p.x - Math.sin(tpCamYaw) * camHorizDist);
        const snapZ = clampCamera(p.z - Math.cos(tpCamYaw) * camHorizDist);
        const snapY = Math.max(2.2, 3.2 + Math.sin(tpCamPitch) * 13.5);
        camera.position.set(snapX, snapY, snapZ);
        let lookX = clampCamera(p.x + Math.sin(tpCamYaw) * 6);
        let lookY = Math.max(2.2, 3.0);
        let lookZ = clampCamera(p.z + Math.cos(tpCamYaw) * 6);
        camera.lookAt(lookX, lookY, lookZ);
      }
    }
  }
});
Object.defineProperty(window, 'tpCamPitch', { get: () => tpCamPitch, set: (v) => { tpCamPitch = v; } });
Object.defineProperty(window, 'camera', { get: () => camera });
Object.defineProperty(window, 'units', { get: () => units });
Object.defineProperty(window, 'matchActive', { get: () => matchActive });
Object.defineProperty(window, 'selectedHeroId', { get: () => selectedHeroId });
Object.defineProperty(window, 'lobbyHeroMesh', { get: () => lobbyHeroMesh });
window.__HITSTUN = { normal: 0.35, heavy: 0.60, source: 'APK storm: dmg0f media 21f, hsta0 36f' }; // telemetria E2E (W-HS)
window.__HAND_VFX = () => vfxList.filter(v => v.style === 'compound' && v.bindUnit).length; // telemetria E2E (W-VIS)
Object.defineProperty(window, 'rosterMeta', { get: () => rosterMeta });
Object.defineProperty(window, 'animationsData', { get: () => animationsData });
Object.defineProperty(window, 'skillVfxData', { get: () => skillVfxData });
Object.defineProperty(window, 'stage3DData', { get: () => stage3DData });
Object.defineProperty(window, 'ARENA', { get: () => ARENA });
Object.defineProperty(window, 'arenasCatalog', { get: () => arenasCatalog });
Object.defineProperty(window, 'selectedArenaId', { get: () => selectedArenaId });
Object.defineProperty(window, 'basePos', { value: basePos });
Object.defineProperty(window, 'applyArena', { value: applyArena });
Object.defineProperty(window, 'rebuildArenaVisuals', { value: rebuildArenaVisuals });
Object.defineProperty(window, 'projectiles', { get: () => projectiles });
Object.defineProperty(window, 'vfxList', { get: () => vfxList });
Object.defineProperty(window, 'scene', { get: () => scene });
Object.defineProperty(window, 'arenaGroup', { get: () => arenaGroup });

init().catch(err => { console.error('[NUBA] BOOT FALHOU:', err); }); // P0 hardening


// ============================================================================
// PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) — escreve em window.INPUT
// ============================================================================
(function initTouchControls() {
  const clamp1 = (v) => Math.max(-1, Math.min(1, v));
  const joy = document.getElementById('touch-joystick');
  const base = document.getElementById('joystick-base');
  const knob = document.getElementById('joystick-knob');

  if (joy && base && knob) {
    let joyId = null, cx = 0, cy = 0;
    const R = 56, DEAD = 0.18;
    const place = (x, y) => {
      base.style.left = (x - 60) + 'px'; base.style.top = (y - 60) + 'px';
      knob.style.left = (x - 30) + 'px'; knob.style.top = (y - 30) + 'px';
    };
    joy.addEventListener('pointerdown', (e) => {
      if (joyId !== null) return;
      joyId = e.pointerId;
      try { joy.setPointerCapture(joyId); } catch (err) {}
      cx = e.clientX; cy = e.clientY;
      place(cx, cy);
      joy.classList.add('active');
      e.preventDefault();
    });
    joy.addEventListener('pointermove', (e) => {
      if (e.pointerId !== joyId) return;
      const dx = e.clientX - cx, dy = e.clientY - cy;
      const len = Math.hypot(dx, dy) || 1;
      const cl = Math.min(len, R);
      const nx = dx / len, ny = dy / len;
      knob.style.transform = 'translate(' + (nx * cl).toFixed(1) + 'px,' + (ny * cl).toFixed(1) + 'px)';
      const mag = cl / R;
      if (mag < DEAD) { window.INPUT.moveX = 0; window.INPUT.moveZ = 0; }
      else { window.INPUT.moveX = clamp1(nx * mag); window.INPUT.moveZ = clamp1(-ny * mag); }
      e.preventDefault();
    });
    const joyEnd = (e) => {
      if (e.pointerId !== joyId) return;
      joyId = null;
      window.INPUT.moveX = 0; window.INPUT.moveZ = 0;
      knob.style.transform = 'translate(0,0)';
      joy.classList.remove('active');
    };
    joy.addEventListener('pointerup', joyEnd);
    joy.addEventListener('pointercancel', joyEnd);
  }

  // PV1.4: auto-aim — alvo inimigo mais próximo em alcance (teste/inspeção: window.findAimTarget)
  function findAimTarget(unit, range) {
    let best = null, bestD = Infinity;
    for (const t of units) {
      if (t === unit || t.team === unit.team || t.deadTimer > 0) continue;
      const d = Math.hypot(t.x - unit.x, t.z - unit.z);
      if (d <= range && d < bestD) { best = t; bestD = d; }
    }
    return best;
  }
  window.findAimTarget = findAimTarget;

  const SLOT_BTNS = [['tbtn-atk', 'atk'], ['tbtn-q', 'q'], ['tbtn-w', 'w'], ['tbtn-e', 'e'], ['tbtn-r', 'r']];
  for (const [id, slot] of SLOT_BTNS) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      if (!matchActive) return;
      const player = units.find(u => u.isPlayer);
      if (!player) return;
      if (slot === 'atk') {
        window.INPUT.fire = true;
      } else {
        const tgt = findAimTarget(player, 46);
        if (tgt) {
          player.rotY = Math.atan2(tgt.x - player.x, tgt.z - player.z);
          player.mesh.rotation.y = player.rotY;
        }
        executeSkill(player, slot);
      }
      if (navigator.vibrate) { try { navigator.vibrate(12); } catch (err) {} }
      btn.classList.add('pressed');
    });
    const up = () => {
      if (slot === 'atk') window.INPUT.fire = false;
      btn.classList.remove('pressed');
    };
    btn.addEventListener('pointerup', up);
    btn.addEventListener('pointercancel', up);
    btn.addEventListener('pointerleave', up);
  }

  const btnC = document.getElementById('tbtn-c');
  if (btnC) {
    btnC.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      window.INPUT.chakra = true;
      btnC.classList.add('pressed');
    });
    const upc = () => { window.INPUT.chakra = false; btnC.classList.remove('pressed'); };
    btnC.addEventListener('pointerup', upc);
    btnC.addEventListener('pointercancel', upc);
    btnC.addEventListener('pointerleave', upc);
  }
})();


// ============================================================================
// PV2: REALEZA NA VILA — modo battle royale solo na Vila Konoha (sa00z)
// Layout real de spawns/baús/zona via assets/data/br_vila_layout.json (raycast)
// ============================================================================

function cleanupBRVisuals() {
  if (brState) {
    if (brState.zoneMesh) { try { arenaGroup.remove(brState.zoneMesh); } catch (e) {} }
    for (const ch of (brState.chests || [])) { try { arenaGroup.remove(ch.mesh); } catch (e) {} }
  }
  brState = null;
}

async function startBRMatch(CFG, playerHero, others) {
  let layout = null;
  try {
    layout = await fetch('assets/data/br_vila_layout.json?v=9').then(r => r.json());
  } catch (e) { console.warn('[PV2] layout BR indisponivel — usando anel geometrico', e); }
  const ring = (layout && Array.isArray(layout.spawnRing) && layout.spawnRing.length >= CFG.players)
    ? layout.spawnRing : null;
  const roster = [playerHero, ...others.slice(0, CFG.players - 1)];
  const meshes = await Promise.all(roster.map(h2 => loadCharacter3DModel(h2.id)));
  const zoneStart = (layout && layout.zoneRadiusStart) || CFG.zoneStart || 65;
  brState = {
    phase: 0,
    zoneTimer: CFG.phaseTime || 25,
    zoneR: zoneStart,
    zoneTargetR: zoneStart,
    zoneStart,
    zoneMin: (layout && layout.zoneRadiusMin) || CFG.zoneMin || 6,
    zonePhases: CFG.zonePhases || 6,
    center: (layout && layout.zoneCenter) || { x: 0, z: 0 },
    damageTick: 1.0,
    chests: [],
    zoneMesh: null,
    alive: roster.length
  };
  for (let i = 0; i < roster.length; i++) {
    const h2 = roster[i];
    const isPlayer = i === 0;
    const mesh = meshes[i];
    const ringGeo = new THREE.RingGeometry(1.45, 1.85, 32);
    const ringColor = isPlayer ? 0x22c55e : 0xa855f7;
    const ringMesh = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: ringColor, side: THREE.DoubleSide }));
    ringMesh.rotation.x = -Math.PI / 2;
    ringMesh.position.y = 0.08;
    mesh.add(ringMesh);
    const auraMesh = createHeroAwakeningAuraMesh(h2.id, h2.color || 0xff7b00);
    auraMesh.visible = false;
    mesh.add(auraMesh);
    const sp = ring ? ring[i] : { x: Math.cos(i / roster.length * Math.PI * 2) * (zoneStart * 0.8), z: Math.sin(i / roster.length * Math.PI * 2) * (zoneStart * 0.8) };
    mesh.position.set(sp.x, 0, sp.z);
    arenaGroup.add(mesh);
    const labelEl = document.createElement('div');
    labelEl.className = `unit-label ${isPlayer ? 'player' : 'red'}`;
    labelEl.innerHTML = `
      <span class="u-name">${isPlayer ? '★ ' + h2.name : h2.name.split(' ')[0]} <small class="u-lvl">Lv.1</small></span>
      <div class="u-hp-bg"><div class="u-hp-fill" style="width:100%"></div></div>
      <div class="u-ck-bg"><div class="u-ck-fill" style="width:100%"></div></div>
    `;
    document.getElementById('world-labels').appendChild(labelEl);
    const kit = HERO_KITS[h2.id] || HERO_KITS['1nrt'];
    const hs = HERO_STATS[h2.id] || HERO_STATS.__d;
    units.push({
      id: `solo_${i}`,
      heroId: h2.id,
      name: h2.name,
      portrait: h2.portrait,
      team: `solo_${i}`,
      isPlayer,
      mesh, auraMesh, labelEl, kit,
      x: sp.x, z: sp.z, spawnX: sp.x, spawnZ: sp.z,
      rotY: Math.atan2(brState.center.z - sp.z, brState.center.x - sp.x),
      hp: Math.round(hs.hp * HERO_HP_SCALE),
      maxHp: Math.round(hs.hp * HERO_HP_SCALE),
      chakra: 100, maxChakra: 100,
      level: 1, kills: 0, deaths: 0, assists: 0, killStreak: 0, lastKillAt: 0,
      speed: (isPlayer ? 21.5 : 19.5) * hs.spd,
      state: 'idle', animTimer: 0, animDuration: 0,
      comboStep: 0, comboResetTimer: 0, awakenedTimer: 0, deadTimer: 0, spawnShield: 3.0, hitstun: 0,
      cds: { atk: 0, q: 0, w: 0, e: 0, r: 0 },
      aiTarget: null, aiStrafeDir: Math.random() < 0.5 ? 1 : -1
    });
  }
  const player = units.find(u => u.isPlayer);
  if (player) { tpCamYaw = player.rotY; tpCamPitch = 0.32; }
  setupHUDPlayerInfo(playerHero);
  renderTopTeamPortraits();
  // Zona 結界 — cilindro translúcido (roxo chakra), escala = raio atual
  const zoneGeo = new THREE.CylinderGeometry(1, 1, 40, 64, 1, true);
  const zoneMat = new THREE.MeshBasicMaterial({ color: 0xa855f7, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false });
  brState.zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
  brState.zoneMesh.scale.set(brState.zoneR, 1, brState.zoneR);
  brState.zoneMesh.position.set(brState.center.x, 18, brState.center.z);
  arenaGroup.add(brState.zoneMesh);
  // Baús de chakra nas posições reais do layout
  const chestGeo = new THREE.BoxGeometry(1.6, 1.2, 1.2);
  const chestMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
  const chestPos = (layout && Array.isArray(layout.chests)) ? layout.chests : [];
  for (const cp of chestPos) {
    const cm = new THREE.Mesh(chestGeo, chestMat);
    cm.position.set(cp.x, 0.9, cp.z);
    arenaGroup.add(cm);
    brState.chests.push({ x: cp.x, z: cp.z, mesh: cm, taken: false, bob: Math.random() * Math.PI * 2 });
  }
  const _goalEl = document.querySelector('.match-goal-txt');
  if (_goalEl) _goalEl.textContent = 'SOBREVIVA · ÚLTIMO DE PÉ';
  updateBRHUD();
  playMatchIntro([playerHero], roster.slice(1)); // PV2: intro 1 vs todos (arrays planos de heroes)
}

function updateBRHUD() {
  const el = document.getElementById('br-alive');
  const ph = document.getElementById('br-phase');
  if (el) renderSkinDigits(el, String(brState ? brState.alive : 0));
  if (ph) ph.textContent = brState ? `FASE ${Math.min(brState.phase, brState.zonePhases)}/${brState.zonePhases}` : '';
}

function brEndMatch(playerWon, reason) {
  if (matchEnding) return;
  scoreBlue = playerWon ? 1 : 0;
  scoreRed = playerWon ? 0 : 1;
  endMatch(playerWon ? `REALEZA NA VILA — ${reason}! VITÓRIA!` : `REALEZA NA VILA — ${reason}... DERROTA`);
}

function updateBR(dt) {
  const alive = units.filter(u => u.deadTimer <= 0);
  brState.alive = alive.length;
  updateBRHUD();
  // ---- Zona 結界: fases + encolhimento contínuo ----
  if (brState.phase < brState.zonePhases) {
    brState.zoneTimer -= dt;
    if (brState.zoneTimer <= 0) {
      brState.phase++;
      brState.zoneTimer = 25;
      const span = brState.zoneStart - brState.zoneMin;
      brState.zoneTargetR = Math.max(brState.zoneMin, brState.zoneStart - brState.phase * span / brState.zonePhases);
      showBanner(brState.phase >= brState.zonePhases
        ? '結界 FINAL! NENHUM ESCONDERIJO!'
        : `結界 ESTÁ ENCOLHENDO — FASE ${brState.phase}/${brState.zonePhases}`, 2000);
    }
    const shrinkSpeed = (brState.zoneStart - brState.zoneMin) / (25 * brState.zonePhases);
    brState.zoneR = Math.max(brState.zoneTargetR, brState.zoneR - dt * shrinkSpeed);
    if (brState.zoneMesh) brState.zoneMesh.scale.set(brState.zoneR, 1, brState.zoneR);
  }
  // ---- Dano fora da zona (chakra drain 結界) ----
  brState.damageTick -= dt;
  if (brState.damageTick <= 0) {
    brState.damageTick = 1.0;
    for (const u of alive) {
      const d = Math.hypot(u.x - brState.center.x, u.z - brState.center.z);
      if (d > brState.zoneR + 1.5) dealDamage(u, u, 2 + brState.phase, '結界');
    }
  }
  // ---- Baús: bob visual + coleta por proximidade ----
  for (const ch of brState.chests) {
    if (ch.taken) continue;
    ch.bob += dt * 2.4;
    ch.mesh.position.y = 0.9 + Math.sin(ch.bob) * 0.18;
    ch.mesh.rotation.y += dt * 1.2;
    for (const u of alive) {
      if (Math.hypot(u.x - ch.x, u.z - ch.z) < 2.6) {
        ch.taken = true;
        ch.mesh.visible = false;
        AUTH_SFX.playAt('box_open', ch.x, ch.z, { vol: 0.9, min: 1200 }); AUTH_SFX.playAt('chakura_get', ch.x, ch.z, { vol: 0.8, min: 1200 }); // W5: baú BR autêntico
        spawnSmokePuff(ch.x, 1.2, ch.z, 2.5);
        u.hp = Math.min(u.maxHp, u.hp + 35);
        u.chakra = Math.min(u.maxChakra, u.chakra + 50);
        if (u.isPlayer) showBanner('BAÚ DE CHAKRA! +35 HP · +50 CHAKRA', 1400);
        break;
      }
    }
  }
  // ---- Last standing ----
  if (alive.length <= 1 && !matchEnding) {
    const winner = alive[0];
    if (winner && winner.isPlayer) brEndMatch(true, 'ÚLTIMO DE PÉ');
    else brEndMatch(false, winner ? `${winner.name} VENCEU` : 'TODOS CAÍRAM');
  }
}
