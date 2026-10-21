import json
import os

MODELS_DIR = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\models"
ROSTER_META_PATH = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\data\roster_meta.json"

# Official Naruto Classic (Part 1) Databook ("To no Sho") Heights in cm
DATABOOK_HEIGHTS_CM = {
    "1nrt": 147.5,  # Naruto Uzumaki (147.5 cm)
    "1gar": 148.1,  # Gaara (148.1 cm)
    "1hnt": 148.3,  # Hinata Hyuga (148.3 cm)
    "1skr": 150.1,  # Sakura Haruno (150.1 cm)
    "1ssk": 153.2,  # Sasuke Uchiha (153.2 cm)
    "1nej": 160.1,  # Neji Hyuga (160.1 cm)
    "1roc": 162.1,  # Rock Lee (162.1 cm)
    "1itc": 175.2,  # Itachi Uchiha (175.2 cm)
    "1kks": 181.0,  # Kakashi Hatake (181.0 cm)
    "1jry": 191.2,  # Jiraiya (191.2 cm)
}

# 150 cm = 5.00 MOBA world units (1 cm = 1/30 world unit)
CM_TO_WORLD = 5.0 / 150.0


def apply_heights():
    for cid, cm in DATABOOK_HEIGHTS_CM.items():
        path = os.path.join(MODELS_DIR, f"{cid}.json")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Measure current model height (min_y to max_y across all submeshes)
        min_y = 999999.0
        max_y = -999999.0
        for sm in data["meshes"]:
            ys = sm["positions"][1::3]
            if ys:
                min_y = min(min_y, min(ys))
                max_y = max(max_y, max(ys))

        cur_h = max(0.01, max_y - min_y)
        target_h = round(cm * CM_TO_WORLD, 3)
        ratio = target_h / cur_h

        for sm in data["meshes"]:
            pos = sm["positions"]
            for i in range(0, len(pos), 3):
                pos[i] = round(pos[i] * ratio, 4)
                pos[i + 1] = round((pos[i + 1] - min_y) * ratio, 4)
                pos[i + 2] = round(pos[i + 2] * ratio, 4)

        for b in data["bones"]:
            bp = b["pos"]
            b["pos"] = [
                round(bp[0] * ratio, 4),
                round((bp[1] - min_y) * ratio, 4),
                round(bp[2] * ratio, 4),
            ]

        data["databookHeightCm"] = cm
        data["worldHeight"] = target_h

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        print(f"[{cid}] Databook={cm:5.1f}cm -> WorldHeight={target_h:.2f}m (scaled by {ratio:.4f}x)")

    if os.path.exists(ROSTER_META_PATH):
        with open(ROSTER_META_PATH, "r", encoding="utf-8") as f:
            rmeta = json.load(f)
        for hero in rmeta.get("roster", []):
            cid = hero["id"]
            if cid in DATABOOK_HEIGHTS_CM:
                hero["heightCm"] = DATABOOK_HEIGHTS_CM[cid]
                hero["worldHeight"] = round(DATABOOK_HEIGHTS_CM[cid] * CM_TO_WORLD, 3)
        with open(ROSTER_META_PATH, "w", encoding="utf-8") as f:
            json.dump(rmeta, f, indent=2)


if __name__ == "__main__":
    apply_heights()
