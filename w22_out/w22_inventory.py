
"""W2.2 step 1: inventory data.awb TOC coverage for candidate hero #12."""
import sys, os, zipfile, json
REPO = r"C:\Users\jessi\Documents\antigravity\goofy-mendeleev"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime"))
from tools.apk_inspect import APK_PATH, parse_utf

CANDS = ["1sik","1tnd","1knk","1tyo","1kib","1sin","1hkg","1ino","1ten","1szn",
         "1guy","1orc","1dea","1kmm","1ank","1kdm","1jrb","1krs","1krn","1kmv"]
NEED = ["bod1","prm","skl1","skl2","eff1"]

with zipfile.ZipFile(APK_PATH) as z:
    with z.open("assets/data/sim/data.awb") as f:
        cpk = parse_utf(f.read(65536), 16)[0]
        f.seek(cpk["TocOffset"])
        toc = parse_utf(f.read(cpk["TocSize"]), 16)
names = sorted(r["FileName"].lower() for r in toc)
print("data.awb entries:", len(names))

out = {}
for cid in CANDS:
    files = [n for n in names if n.startswith(cid + "")]
    # exact prefix match on hero id (e.g. 1sik...), avoid matching 1sikxx vs other
    files = [n for n in files if n[len(cid):len(cid)+1].isalpha() or n[len(cid):len(cid)+1] in "._-"]
    cov = {suf: [n for n in files if suf in n and n.endswith(".xfbin")] for suf in NEED}
    rec = {suf: len(v) for suf, v in cov.items()}
    rec["files"] = sorted(files)
    rec["complete"] = all(rec[s] > 0 for s in NEED)
    out[cid] = rec
    print(f"{cid}: bod1={rec['bod1']} prm={rec['prm']} skl1={rec['skl1']} skl2={rec['skl2']} eff1={rec['eff1']} complete={rec['complete']} nfiles={len(files)}")

with open(__file__.replace("w22_inventory.py", "inventory_data_awb.json"), "w") as f:
    json.dump(out, f, indent=1)
print("saved inventory_data_awb.json")
