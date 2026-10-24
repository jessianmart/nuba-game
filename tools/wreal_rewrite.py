# -*- coding: utf-8 -*-
"""W-REAL F4: rewrite cirurgico dos 14 create*Mesh procedurais -> 100% corpos
reais do APK (billboards extraidos + corpos NDP3 calibrados). Zero geometria
inventada (sem SphereGeometry/TorusGeometry/ConeGeometry/CylinderGeometry/
RingGeometry/DodecahedronGeometry nos efeitos de skill)."""
import io, re, sys

GAME = r'public/game.js'

BLOCS = {}

BLOCS['createRasenganMesh'] = """function createRasenganMesh(radius = 1.0, color = 0x00d4ff) {
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
"""

BLOCS['createChidoriMesh'] = """function createChidoriMesh(radius = 0.95, color = 0x60a5fa) {
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
"""

BLOCS['createKaitenMesh'] = """function createKaitenMesh(radius = 3.2) {
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
"""

BLOCS['createSandShieldMesh'] = """function createSandShieldMesh(radius = 3.0) {
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
"""

BLOCS['createSandHandMesh'] = """function createSandHandMesh(scale = 0.12) {
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
"""

BLOCS['createAmaterasuMesh'] = """function createAmaterasuMesh(radius = 4.2) {
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
"""

BLOCS['createLionFistMesh'] = """function createLionFistMesh(radius = 1.35) {
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
"""

BLOCS['createTornadoMesh'] = """function createTornadoMesh(radius = 4.2) {
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
"""

BLOCS['createFireballMesh'] = """function createFireballMesh(radius = 2.4, color = 0xff5500) {
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
"""

BLOCS['createWaterDragonMesh'] = """function createWaterDragonMesh(radius = 2.8) {
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
"""

BLOCS['createGroundShatterMesh'] = """function createGroundShatterMesh(radius = 5.5) {
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
"""

BLOCS['createToadOilFlameMesh'] = """function createToadOilFlameMesh(radius = 3.2) {
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
"""

BLOCS['createKirinMesh'] = """function createKirinMesh(x, z) {
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
"""

BLOCS['createHeroAwakeningAuraMesh'] = """function createHeroAwakeningAuraMesh(heroId, colorHex) {
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
"""


def main():
    s = io.open(GAME, encoding='utf-8').read()
    for name, new in BLOCS.items():
        marker = f'function {name}('
        start = s.index(marker)
        end = s.index('\n}\n', start) + 3
        old_len = end - start
        s = s[:start] + new + s[end:]
        print(f'  {name}: {old_len} -> {len(new)} chars')
    io.open(GAME, 'w', encoding='utf-8', newline='\n').write(s)
    print('rewrite OK')


if __name__ == '__main__':
    main()
