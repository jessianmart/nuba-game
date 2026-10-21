"""Restore the clamp expressions lost by the bad regex migration.

Each line was `clampHelper(\x01);` and is rewritten with the original argument,
recovered from surrounding context plus the pre-migration inventory.
"""

import io

REPAIRS = {
    # knockback away from attacker
    1632: "  target.x = clampPush(target.x + (dx / len) * 1.4);",
    1633: "  target.z = clampPush(target.z + (dz / len) * 1.4);",
    # melee follow-up
    1759: "        meleeTarget.x = clampArena(meleeTarget.x + (kx / klen) * 3.2);",
    1760: "        meleeTarget.z = clampArena(meleeTarget.z + (kz / klen) * 3.2);",
    # Rasengan / Chidori / Rasen-Kyusen / Tornado / lightning field dashes
    1860: "      unit.x = clampArena(unit.x + dirX * 11.5);",
    1861: "      unit.z = clampArena(unit.z + dirZ * 11.5);",
    1903: "      unit.x = clampArena(unit.x + dirX * 12.5);",
    1904: "      unit.z = clampArena(unit.z + dirZ * 12.5);",
    1988: "      unit.x = clampArena(unit.x + dirX * 12.0);",
    1989: "      unit.z = clampArena(unit.z + dirZ * 12.0);",
    2051: "      unit.x = clampArena(unit.x + dirX * 11.0);",
    2052: "      unit.z = clampArena(unit.z + dirZ * 11.0);",
    2176: "      unit.x = clampArena(unit.x + dirX * 10.5);",
    2177: "      unit.z = clampArena(unit.z + dirZ * 10.5);",
    # dash_aoe
    2286: "    unit.x = clampArena(unit.x + dirX * 11.5);",
    2287: "    unit.z = clampArena(unit.z + dirZ * 11.5);",
    # substitution: land behind the target
    2368: "      unit.x = clampArena(behindX);",
    2369: "      unit.z = clampArena(behindZ);",
    2373: "      unit.x = clampArena(unit.x - dirX * 10);",
    2374: "      unit.z = clampArena(unit.z - dirZ * 10);",
    # toggleCameraMode snap
    2447: "    const snapX = clampCamera(player.x - Math.sin(tpCamYaw) * camHorizDist);",
    2448: "    const snapZ = clampCamera(player.z - Math.cos(tpCamYaw) * camHorizDist);",
    # AI movement
    2880: "    u.x = clampArena(u.x + mx * spd * dt);",
    2881: "    u.z = clampArena(u.z + mz * spd * dt);",
    2957: "    u.x = clampPlayer(u.x + sx * u.speed * 0.55 * dt);",
    2958: "    u.z = clampPlayer(u.z + sz * u.speed * 0.55 * dt);",
    2961: "    u.x = clampPlayer(u.x + (dx / dist) * u.speed * dt);",
    2962: "    u.z = clampPlayer(u.z + (dz / dist) * u.speed * dt);",
    # third-person follow camera
    2990: "    targetX = clampCamera(targetX);",
    2991: "    targetZ = clampCamera(targetZ);",
    3005: "    camera.position.x = clampCamera(camera.position.x);",
    3006: "    camera.position.z = clampCamera(camera.position.z);",
    # window.cameraMode setter
    3430: "      const snapX = clampCamera(p.x - Math.sin(tpCamYaw) * camHorizDist);",
    3431: "      const snapZ = clampCamera(p.z - Math.cos(tpCamYaw) * camHorizDist);",
    # window.tpCamYaw setter
    3447: "        const snapX = clampCamera(p.x - Math.sin(tpCamYaw) * camHorizDist);",
    3448: "        const snapZ = clampCamera(p.z - Math.cos(tpCamYaw) * camHorizDist);",
    3451: "        let lookX = clampCamera(p.x + Math.sin(tpCamYaw) * 6);",
    3453: "        let lookZ = clampCamera(p.z + Math.cos(tpCamYaw) * 6);",
}


def main():
    path = "public/game.js"
    lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
    fixed = 0
    for lineno, repl in REPAIRS.items():
        idx = lineno - 1
        if idx >= len(lines):
            raise SystemExit(f"line {lineno} out of range")
        if "\x01" not in lines[idx]:
            raise SystemExit(f"line {lineno} is not corrupt: {lines[idx]!r}")
        lines[idx] = repl
        fixed += 1
    text = "\n".join(lines)
    leftover = text.count("\x01")
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    print(f"repaired {fixed} lines, control chars left: {leftover}")


if __name__ == "__main__":
    main()