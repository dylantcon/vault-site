#!/usr/bin/env python3
# Make every content dir a clickable Hugo section (needs _index.md). Handle collisions:
#  - drop junk 'index.html.md' notes (they collide with the section's index.html URL)
#  - a real 'index.md' note becomes the section's _index.md (its landing page)
import os, sys
root = sys.argv[1]; created = renamed = removed = 0
for dp, dirs, files in os.walk(root):
    if dp == root: continue
    for junk in ("index.html.md", "index.htm.md"):
        jp = os.path.join(dp, junk)
        if os.path.exists(jp):
            os.remove(jp); removed += 1
            if junk in files: files.remove(junk)
    if "_index.md" in files: continue
    sec = os.path.join(dp, "_index.md"); idx = os.path.join(dp, "index.md")
    if os.path.exists(idx):
        os.rename(idx, sec); renamed += 1
    else:
        with open(sec, "w", encoding="utf-8") as fh:
            fh.write(f'---\ntitle: "{os.path.basename(dp)}"\n---\n')
        created += 1
print(f"sections: {created} created, {renamed} renamed, {removed} junk removed")
