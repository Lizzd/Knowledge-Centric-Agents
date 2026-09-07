# Project page — Knowledge-Centric Agents for Workflow Generation in ComfyUI (ECCV 2026)

Static site, no build step needed to deploy.

## Deploy on GitHub Pages
1. Create a repository (for example `knowledge-centric-agents`) and copy the contents of this folder to its root
   (or into `docs/`).
2. Repository → Settings → Pages → *Deploy from a branch* → `main`, folder `/ (root)` (or `/docs`).
3. The page is then served at `https://<user>.github.io/<repo>/`.

## Three things to fill in (search for them in `index.html`)
- `CODE_URL` — the code repository. Also remove `class="soon"`, `aria-disabled` and the `onclick` on that button.
- `YOUTUBE_URL` — set the constant at the top of the script; the hero's "5-minute talk" button then appears and links there.
- `SITE_URL` — the absolute URL of the deployed page, used for the Open Graph preview image (`assets/og.jpg`).

## Contents
- `index.html` — the page (single file, inline CSS/JS, Google Fonts as the only external dependency).
- `assets/` — images, the 39 s demo video (`demo.mp4`), social card (`og.jpg`).
- `tools/` — `build_page.py` + `page_template.html` regenerate `index.html` and `assets/` from the paper's source data; not needed for deployment.
