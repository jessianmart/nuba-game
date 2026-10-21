import re

with open('public/game.js', 'r', encoding='utf-8') as f:
    text = f.read()

ids = set()
for line in text.splitlines():
    m = re.search(r"getElementById\(['\"]([^'\"]+)['\"]\)", line)
    if m:
        ids.add(m.group(1))

print("DOM IDs used in game.js:")
for i in sorted(ids):
    print(" -", i)
