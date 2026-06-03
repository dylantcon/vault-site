#!/usr/bin/env python3
"""Normalize notes for obsidian-export's strict parser. STAGING copy only; atomic writes.
Excalidraw: standalone *.excalidraw.md -> a page embedding its .svg (dropped if no .svg);
embedded ![[X.excalidraw]] -> ![[X.svg]]. Body '---' horizontal rules become '***' ONLY
outside code fences (so Mermaid/code blocks that use '---' are preserved)."""
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
def hr_outside_fences(body):
    """'---' on its own line -> '***', but NEVER inside a ```/~~~ code fence (preserves Mermaid)."""
    out = []; fence = None
    for ln in body.split('\n'):
        if fence is None:
            m = re.match(r'^\s*(`{3,}|~{3,})', ln)
            if m: fence = m.group(1); out.append(ln); continue
            out.append('***' if re.match(r'^---[ \t]*$', ln) else ln)
        else:
            c = re.match(r'^\s*(`{3,}|~{3,})\s*$', ln)
            if c and c.group(1)[0] == fence[0] and len(c.group(1)) >= len(fence): fence = None
            out.append(ln)
    return '\n'.join(out)
EXCAL = re.compile(r'(!\[\[[^\]\n|]*?)\.excalidraw(?:\.md)?(\s*[|\]])')

# Markdown-style note embeds: ![alt](target) where target is another NOTE (not an image/URL).
# obsidian-export renders these as <img> (broken). We rewrite the target to the note's
# absolute logical path so the Hugo render-image hook can transclude its rendered content
# (this is the only way to nest e.g. a table inside a table cell — valid HTML, not markdown).
MEDIA_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.avif',
             '.pdf', '.mp4', '.webm', '.ogg', '.mov', '.mp3', '.wav', '.ico')
MD_EMBED = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')

def build_md_index(rt):
    idx = {}
    for d, _, fs in os.walk(rt):
        for f in fs:
            if f.endswith(".md"):
                idx.setdefault(f[:-3].lower(), []).append(os.path.relpath(os.path.join(d, f), rt))
    return idx

def resolve_note_embed(target, cur_dir, idx):
    t = target.strip()
    low = t.lower()
    if low.startswith(("http://", "https://", "data:", "mailto:", "#", "/")) or "://" in low:
        return None
    stem = t.split("#", 1)[0].split("|", 1)[0].rstrip("/")
    if stem.lower().endswith(MEDIA_EXT) or not stem:
        return None
    base = stem.split("/")[-1]
    if base.lower().endswith(".md"): base = base[:-3]
    cands = idx.get(base.lower())
    if not cands: return None
    top = cur_dir.split(os.sep, 1)[0] if cur_dir not in (".", "") else ""
    pick = next((c for c in cands if c.split(os.sep, 1)[0] == top), cands[0])
    return "/" + pick[:-3].replace(os.sep, "/")

MD_INDEX = build_md_index(root)
norm = excl = draw = dropped = 0
for dp, _, files in os.walk(root):
    for f in files:
        if not f.endswith(".md"): continue
        p = os.path.join(dp, f)
        if f.endswith(".excalidraw.md"):
            base = f[:-len(".excalidraw.md")]
            if os.path.exists(os.path.join(dp, base + ".svg")):
                t = clean_title(base).replace('\\', '\\\\').replace('"', '\\"')
                outp = os.path.join(dp, base + ".md")
                if os.path.exists(outp): outp = p
                write(outp, dp, f'---\ntitle: "{t}"\n---\n\n![[{base}.svg]]\n')
                if outp != p: os.remove(p)
                draw += 1
            else:
                os.remove(p); dropped += 1
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        fm, body = strip_fm(text)
        # compat-mode Excalidraw: plain *.md carrying excalidraw-plugin frontmatter / '# Excalidraw Data'
        # body (the raw compressed-json drawing). Same treatment as *.excalidraw.md: embed sibling .svg or drop.
        if 'excalidraw-plugin:' in fm or re.search(r'(?m)^#\s+Excalidraw Data\s*$', body):
            base = f[:-len(".md")]
            if os.path.exists(os.path.join(dp, base + ".svg")):
                t = (clean_title(base.replace("-", " ").replace("_", " ")) or "Untitled")
                t = t.replace('\\', '\\\\').replace('"', '\\"')
                write(p, dp, f'---\ntitle: "{t}"\n---\n\n![[{base}.svg]]\n'); draw += 1
            else:
                os.remove(p); dropped += 1
            continue
        if is_private(fm, body): os.remove(p); excl += 1; continue
        body = body.lstrip("\n")
        m = re.search(r'^title:\s*(.+?)\s*$', fm, re.M)
        fm_title = clean_title(m.group(1)) if m else ""
        h1 = re.match(r'#\s+(.+?)\s*\n', body)
        if h1: title = fm_title or clean_title(h1.group(1)); body = body[h1.end():].lstrip("\n")
        else: title = fm_title or clean_title(f.rsplit(".", 1)[0].replace("-", " ").replace("_", " "))
        body = hr_outside_fences(body)
        body = EXCAL.sub(r'\1.svg\2', body)
        cur_dir = os.path.relpath(dp, root)
        body = MD_EMBED.sub(lambda m: f'{m.group(1)}{resolve_note_embed(m.group(2), cur_dir, MD_INDEX) or m.group(2)}{m.group(3)}', body)
        title = (title or "Untitled").replace('\\', '\\\\').replace('"', '\\"')
        write(p, dp, f'---\ntitle: "{title}"\n---\n\n' + body); norm += 1
print(f"normalized: {norm} notes, {excl} private, {draw} drawings, {dropped} drawings-without-svg dropped")
