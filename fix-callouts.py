#!/usr/bin/env python3
import os, re, sys
root = sys.argv[1]; n = 0
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith('.md'): continue
        p = os.path.join(dp, f)
        s = open(p, encoding='utf-8', errors='replace').read(); o = s
        s = re.sub(r'(?m)^ (>)', r'\1', s)                       # de-indent (export adds 1 space)
        s = re.sub(r'\\(\[!\w+)\\(\])', r'\1\2', s)              # \[!todo\] -> [!todo]
        s = re.sub(r'(?m)^>[ \t]*\n(?=>[ \t]*\[!\w)', '', s)     # drop blank '>' before a callout
        if s != o: open(p, 'w').write(s); n += 1
print(f"callouts fixed in {n} files")
