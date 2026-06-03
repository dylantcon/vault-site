# vault-site

Hugo pipeline that publishes a curated subset of my Obsidian vault to
**[vault.dconn.dev](https://vault.dconn.dev)**.

`publish.sh` mirrors the vault → normalizes frontmatter for `obsidian-export`
→ exports → builds with Hugo (custom `vault` theme) → deploys to nginx.
Supports MathJax, Mermaid, Obsidian callouts, and Excalidraw SVGs.

The vault content itself is **not** in this repo — generated dirs
(`content/`, `static/`, `public/`, `staging/`, `export/`) are gitignored.
