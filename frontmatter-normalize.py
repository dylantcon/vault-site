#!/usr/bin/env python3
"""Normalize notes for obsidian-export's strict parser. STAGING copy only; atomic writes.
Also handles Excalidraw: standalone *.excalidraw.md -> a page embedding its exported .svg
(dropped if no .svg yet); embedded ![[X.excalidraw]] -> ![[X.svg]]."""
import os, sys, re, tempfile
root = os.path.abspath(sys.argv[1])
assert "staging" in root, f"refusing to run outside a staging dir: {root}"

def is_private(fm, body):
    if re.search(r'(^|\s)#private\b', body): return True
    if re.search(r'tags:.*\bprivate\b', fm, re.I): return True
    if re.search(r'^\s*-\s*private\s*$', fm, re.I | re.M): return True
    if re.search(r'^\s*publish:\s*false\b', fm, re.I | re.M): return True
    if re.search(r'^\s*private:\s*true\b', fm, re.I | re.M): return True
    return False
def strip_fm(t):
    if not t.startswith("---\n"): return "", t
    e = t.find("\n---", 4); return ("", t) if e == -1 else (t[4:e], t[e+4:])
def clean_title(s):
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', s.strip().strip('"').strip("'"))
    s = re.sub(r'[*_`#]', '', s); s = re.sub(r'[\x00-\x1f]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()
def write(p, dp, new):
    fd, tmp = tempfile.mkstemp(dir=dp, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh: fh.write(new)
    os.replace(tmp, p)
EXCAL = re.compile(r'(!\[\[[^\]\n|]*?)\.excalidraw(?:\.md)?(\s*[|\]])')  # embedded drawing -> .svg

norm = excl = draw = dropped = 0
for dp, _, files in os.walk(root):
    for f in files:
        if not f.endswith(".md"): continue
        p = os.path.join(dp, f)
        # ---- standalone Excalidraw drawing files ----
        if f.endswith(".excalidraw.md"):
            base = f[:-len(".excalidraw.md")]
            if os.path.exists(os.path.join(dp, base + ".svg")):
                t = clean_title(base).replace('\\', '\\\\').replace('"', '\\"')
                outp = os.path.join(dp, base + ".md")
                if os.path.exists(outp): outp = p          # avoid clobbering a real note
                write(outp, dp, f'---\ntitle: "{t}"\n---\n\n![[{base}.svg]]\n')
                if outp != p: os.remove(p)
                draw += 1
            else:
                os.remove(p); dropped += 1                  # not exported yet -> don't publish raw blob
            continue
        # ---- normal notes ----
        text = open(p, encoding="utf-8", errors="replace").read()
        fm, body = strip_fm(text)
        if is_private(fm, body): os.remove(p); excl += 1; continue
        body = body.lstrip("\n")
        m = re.search(r'^title:\s*(.+?)\s*$', fm, re.M)
        fm_title = clean_title(m.group(1)) if m else ""
        h1 = re.match(r'#\s+(.+?)\s*\n', body)
        if h1: title = fm_title or clean_title(h1.group(1)); body = body[h1.end():].lstrip("\n")
        else: title = fm_title or clean_title(f.rsplit(".", 1)[0].replace("-", " ").replace("_", " "))
        body = re.sub(r'(?m)^---[ \t]*$', '***', body)
        body = EXCAL.sub(r'\1.svg\2', body)
        title = (title or "Untitled").replace('\\', '\\\\').replace('"', '\\"')
        write(p, dp, f'---\ntitle: "{title}"\n---\n\n' + body); norm += 1
print(f"normalized: {norm} notes, {excl} private, {draw} drawings, {dropped} drawings-without-svg dropped")
