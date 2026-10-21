"""W2.2 step 4: validate w22_out artifacts against the production formats (1nrt.json etc.)."""
import json
import os
import sys

REPO = r"C:\Users\jessi\Documents\antigravity\goofy-mendeleev"
W22 = os.path.dirname(os.path.abspath(__file__))
W21 = W22  # keep var names
PROD = os.path.join(REPO, "public", "assets")
MINE = os.path.join(W21, "assets")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def keycmp(a, b):
    return set(a.keys()) == set(b.keys())


def list_keycmp(a, b, path, problems, name="entry"):
    for i, x in enumerate(a[:1]):
        if isinstance(x, dict):
            if not keycmp(x, b):
                problems.append(f"{path}: {name} keys differ: mine={list(x.keys())} prod={list(b.keys())}")


def main():
    problems = []
    results = {}

    # ---------- MODEL ----------
    prod_m = load(os.path.join(PROD, "models", "1nrt.json"))
    my_m = load(os.path.join(MINE, "models", "1orc.json"))
    if not keycmp(prod_m, my_m):
        problems.append(f"model top keys differ: mine={list(my_m.keys())} prod={list(prod_m.keys())}")
    # bones
    pb = prod_m["bones"]
    mb = my_m["bones"]
    if len(mb) != 20:
        problems.append(f"model bones: {len(mb)} != 20")
    for i, bb in enumerate(mb):
        if set(bb.keys()) != {"name", "parent", "pos"}:
            problems.append(f"model bone {i} keys: {list(bb.keys())}")
            break
    if [b["name"] for b in mb] != [b["name"] for b in pb]:
        problems.append("model bone names differ")
    if [b["parent"] for b in mb] != [b["parent"] for b in pb]:
        problems.append("model bone parents differ")
    if len(bb["pos"]) != 3 or not all(isinstance(v, (int, float)) for v in bb["pos"]):
        problems.append("model bone pos shape")
    for k in ("normalizedHeight", "armBindZ", "databookHeightCm", "worldHeight"):
        if k not in my_m:
            problems.append(f"model missing {k}")
    if my_m.get("normalizedHeight") != prod_m["normalizedHeight"]:
        problems.append(f"normalizedHeight mismatch: {my_m.get('normalizedHeight')}")
    # meshes
    mine_keys = set()
    for sm in my_m["meshes"]:
        mine_keys.update(sm.keys())
    if mine_keys != set(pb := [k for sm in prod_m["meshes"] for k in sm.keys()]):
        problems.append(f"mesh keys differ: mine={sorted(mine_keys)} prod={sorted(pb)}")
    # numeric sanity
    n_v = sum(len(sm["positions"]) // 3 for sm in my_m["meshes"])
    n_t = sum(len(sm["indices"]) // 3 for sm in my_m["meshes"])
    for sm in my_m["meshes"]:
        nv = len(sm["positions"]) // 3
        if len(sm["normals"]) // 3 != nv or len(sm["uvs"]) // 2 != nv:
            problems.append(f"mesh {sm['name']}: normals/uvs len mismatch")
        if len(sm["skinIndices"]) != nv * 4 or len(sm["skinWeights"]) != nv * 4:
            problems.append(f"mesh {sm['name']}: skin arrays length mismatch")
    results["model"] = {
        "keysOk": keycmp(prod_m, my_m) and not any("model" in p for p in problems),
        "holes": sorted(set(keycmp(prod_m, my_m) and [] or [p for p in problems if "model" in p])),
        "meshes": len(my_m["meshes"]), "verts": n_v, "tris": n_t,
        "bones": len(my_m["bones"]),
        "databookHeightCm": my_m["databookHeightCm"], "normalizedHeight": my_m["normalizedHeight"],
        "worldHeight": my_m["worldHeight"], "id": my_m["id"], "name": my_m["name"],
    }
    if any("model" in p for p in problems):
        results["model"]["keysOk"] = False

    # ---------- ANIMATIONS ----------
    prod_a = load(os.path.join(PROD, "data", "animations.json"))
    my_a = load(os.path.join(MINE, "data", "animations.json"))
    my_clips = my_a.get("1orc", {})
    prod_clips = prod_a.get("1nrt", {})
    results["animations"] = {"clips": list(my_clips.keys()), "prod_clips": list(prod_clips.keys())}
    if not keycmp(prod_clips, my_clips):
        problems.append(f"animation clip set differs: mine={list(my_clips.keys())} prod={list(prod_clips.keys())}")
    for ck, cv in my_clips.items():
        pv = prod_clips.get(ck)
        if not pv:
            continue
        if not keycmp(pv, cv):
            problems.append(f"anim clip {ck} keys differ: mine={list(cv.keys())} prod={list(pv.keys())}")
            continue
        if len(cv["pelvisPos"]) != cv["numFrames"]:
            problems.append(f"anim clip {ck}: pelvisPos frames {len(cv['pelvisPos'])} != numFrames {cv['numFrames']}")
        bones = cv["bones"]
        if len(bones) != 19 or set(bones.keys()) != set(pv["bones"].keys()):
            problems.append(f"anim clip {ck}: bone channels {len(bones)} != prod {len(pv['bones'])}")
        for bk, frames in bones.items():
            if len(frames) != cv["numFrames"]:
                problems.append(f"anim clip {ck} bone {bk}: {len(frames)} frames != numFrames")
                break
            if len(frames[0]) != 4:
                problems.append(f"anim clip {ck} bone {bk}: quat len {len(frames[0])}")
    results["animations"]["problem"] = [p for p in problems if "anim" in p]
    results["animations"]["keysOk"] = not results["animations"]["problem"]

    # ---------- SKILL VFX ----------
    prod_v = load(os.path.join(PROD, "skills", "skill_vfx.json"))
    my_v = load(os.path.join(MINE, "skills", "skill_vfx.json"))
    results["skill_vfx"] = {"keys": list(my_v.keys())}
    if "1orc" not in my_v:
        problems.append("skill_vfx missing 1orc")
    else:
        hv = my_v["1orc"]
        phv = prod_v["1nrt"]
        if not keycmp(phv, hv):
            problems.append(f"vfx hero keys differ: mine={list(hv.keys())} prod={list(phv.keys())}")
        mek = set()
        for lst in hv["models"].values():
            for sm in lst:
                mek.update(sm.keys())
        pek = set()
        for lst in phv["models"].values():
            for sm in lst:
                pek.update(sm.keys())
        if mek != pek:
            problems.append(f"vfx mesh keys differ: mine={sorted(mek)} prod={sorted(pek)}")
        n_mesh = sum(len(lst) for lst in hv["models"].values())
        results["skill_vfx"].update({
            "heroKeysOk": keycmp(phv, hv) and not any("vfx" in p for p in problems),
            "source": hv["source"], "n_models": len(hv["models"]),
            "n_meshes_total": n_mesh, "model_names": list(hv["models"].keys()),
            "problem": [p for p in problems if "vfx" in p],
        })
    results["skill_vfx"]["keysOk"] = not results["skill_vfx"].get("problem")

    # textures exist?
    for rel in my_m["textures"] if isinstance(my_m.get("textures"), list) else []:
        pass
    tex_problems = []
    for sm in my_m["meshes"]:
        t = sm.get("texture")
        if t and not os.path.exists(os.path.join(MINE, t.replace("textures/", "textures/"))):
            tex_problems.append(t)
    problems.extend(tex_problems)
    results["textures_ok"] = not tex_problems

    results["problems"] = problems
    print(json.dumps(results, indent=1, ensure_ascii=False))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
