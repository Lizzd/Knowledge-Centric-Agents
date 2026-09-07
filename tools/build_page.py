"""Build the GitHub-Pages-ready project page into <project>/project_page/.

Reads the paper's source data (strategy records, executed workflow JSONs, output images,
poster, talk video) and writes index.html + assets/. Re-run after editing page_template.html.
"""
import base64, json, os, re, shutil, textwrap
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SW = os.path.dirname(HERE)                      # session scratchpad (has assets/, paperfigs/, video_720.mp4)
PROJ = r"C:\Users\krist\Desktop\Knowledge-Centric Agents"
OUT = os.path.join(PROJ, "project_page")
A = os.path.join(OUT, "assets")
os.makedirs(A, exist_ok=True)
FONTS = r"C:\Windows\Fonts"

def save_jpg(im, name, w=None, q=84):
    im = im.convert("RGB")
    if w and im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(A, name), "JPEG", quality=q, optimize=True, progressive=True)
def save_png(im, name, w=None):
    if w and im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(A, name), "PNG", optimize=True)
def sq(im, size):
    im = im.convert("RGB"); w, h = im.size; m = min(w, h)
    return im.crop(((w - m) // 2, (h - m) // 2, (w - m) // 2 + m, (h - m) // 2 + m)).resize((size, size), Image.LANCZOS)

# ------------------------------------------------------------------ static assets
for fn in ("logo_insait.png", "logo_adobe.png", "logo_eccv.png", "qr_arxiv.png", "poster_1280.jpg", "poster_2560.jpg",
           "qual_portrait.jpg", "qual_airship.jpg", "qual_outpaint.jpg"):
    shutil.copy(os.path.join(SW, "assets", fn), os.path.join(A, fn))
shutil.copy(os.path.join(PROJ, "ECCV2026_poster_Knowledge-Centric-Agents.pdf"), os.path.join(A, "poster.pdf"))
shutil.copy(os.path.join(PROJ, "ECCV2026_demo_Knowledge-Centric-Agents_captioned.mp4"), os.path.join(A, "demo.mp4"))
shutil.copy(os.path.join(SW, "video_720.mp4"), os.path.join(A, "talk_720p.mp4"))
shutil.copy(os.path.join(SW, "video_poster.jpg"), os.path.join(A, "talk_poster.jpg"))
save_png(Image.open(os.path.join(SW, "paperfigs", "method.png")).convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=256), "method.png", 1800)

# demo poster frame: pull a frame from the demo video with ffmpeg
FF = r"C:\Users\krist\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
import subprocess
subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", "9.5", "-i", os.path.join(A, "demo.mp4"), "-frames:v", "1", "-q:v", "4", os.path.join(A, "demo_poster.jpg")], check=True)

# favicon
open(os.path.join(A, "favicon.svg"), "w", encoding="utf-8").write(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#8B1A58"/>'
    '<circle cx="9" cy="11" r="3" fill="#FFD500"/><circle cx="23" cy="16" r="3" fill="#64B5F6"/><circle cx="11" cy="23" r="3" fill="#FF9CF9"/>'
    '<path d="M12 11 C17 11 18 16 20 16 M14 23 C17 23 18 16 20 16" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/></svg>')

# ------------------------------------------------------------------ examples (real agent outputs)
def clean(s): return " ".join(str(s).replace("它", " it").replace("‑", "-").replace("‐", "-").split())
def excerpt(s, maxlen=520):
    s = clean(s)
    if len(s) <= maxlen: return s
    cut = s[:maxlen]; k = max(cut.rfind(". "), cut.rfind(", "))
    return (cut[:k + 1] if k > 200 else cut.rstrip()) + " …"

REC = {}
for fn in ("similarity_dataset_top25_complete_validated.json", "random_test_15_complete_validated.json", "lowest_similarity_15_complete_validated.json"):
    dd = json.load(open(os.path.join(PROJ, "strategy", fn), encoding="utf-8"))
    for p in dd.get("similarity_pairs", []): REC.setdefault(p["test_sample"]["idx"], p["test_sample"])
    for r in dd.get("results", []): REC.setdefault(r["idx"], r)

def meta_for(n, hide_prompt=False):
    t, w = n["type"], n.get("widgets_values") or []
    try:
        if t in ("CheckpointLoaderSimple", "VAELoader", "UpscaleModelLoader", "ControlNetLoader", "LoadImage"): return [w[0]]
        if t == "LoraLoader": return [w[0], f"strength model {w[1]} · clip {w[2]}"]
        if t in ("CLIPTextEncode", "Text"):
            if hide_prompt or not w or not str(w[0]).strip(): return []
            parts = textwrap.wrap(" ".join(str(w[0]).split()), 30)
            return parts[:2] if len(parts) <= 2 else [parts[0], parts[1][:29] + "…"]
        if t == "KSampler": return [f"{w[2]} steps · cfg {w[3]} · denoise {w[6]}", f"{w[4]} · {w[5]}"]
        if t == "KSamplerAdvanced": return [f"{w[3]} steps · cfg {w[4]}", f"{w[5]} · {w[6]}"]
        if t == "EmptyLatentImage": return [f"{w[0]} × {w[1]} · batch {w[2]}"]
        if t == "UltimateSDUpscale": return [f"upscale ×{w[0]} · denoise {w[7]}", f"tile {w[9]} × {w[10]}"]
        if t == "ImagePadForOutpaint": return [f"pad {w[0]} / {w[1]} / {w[2]} / {w[3]} · feather {w[4]}"]
        if t == "ImageScale": return [f"{w[0]}"]
        if t in ("SaveImage", "easy imageSave"): return [f"filename prefix: {w[0]}"]
    except Exception:
        pass
    return []

def graph_from_json(path, hide_prompt=False):
    w = json.load(open(path, encoding="utf-8"))
    nodes = []
    for n in w["nodes"]:
        outs = [[o.get("name") or "", o.get("type") or ""] for o in n.get("outputs", [])]
        while outs and not outs[-1][0]: outs.pop()
        nodes.append({"id": n["id"], "type": n["type"], "order": n.get("order", 0),
                      "inputs": [[i.get("name") or "", i.get("type") or ""] for i in n.get("inputs", [])],
                      "outputs": outs, "meta": meta_for(n, hide_prompt)})
    links = [[l[1], l[2], l[3], l[4], l[5]] for l in w["links"]]
    return {"nodes": nodes, "links": links}

def var_type(name):
    base = re.sub(r"_\d+$", "", name); up = base.upper(); low = base.lower()
    if up in ("MODEL", "CLIP", "VAE", "CONDITIONING", "LATENT", "IMAGE", "CONTROL_NET", "MASK", "UPSCALE_MODEL", "STRING", "INT", "BBOX_DETECTOR", "SEGM_DETECTOR", "SAM_MODEL"): return up
    if low in ("positive", "negative", "conditioning"): return "CONDITIONING"
    if low in ("image", "images", "cropped_refined", "cropped_enhanced_alpha", "cnet_images", "pixels"): return "IMAGE"
    if low == "mask": return "MASK"
    if low in ("latent", "latents", "samples"): return "LATENT"
    if low.startswith("image_gen"): return "INT"
    if low == "detailer_pipe": return "DETAILER_PIPE"
    return up

def graph_from_pseudocode(text):
    """The agent's skeleton pseudo-code parsed into nodes + links (what rule-based reconstruction starts from)."""
    nodes, links, producer, code = [], [], {}, []
    for i, line in enumerate(text.strip().splitlines(), 1):
        m = re.match(r"\s*(.*?)\s*=\s*([^()]+?)\((.*)\)\s*$", line)
        if not m: code.append([line, None]); continue
        lhs, callee, args = m.group(1), m.group(2).strip(), m.group(3)
        outs = [v.strip() for v in lhs.split(",") if v.strip() and v.strip() != "_"]
        node = {"id": i, "type": callee, "order": i, "inputs": [], "outputs": [[re.sub(r"_\d+$", "", v), var_type(v)] for v in outs], "meta": []}
        for k, v in enumerate(outs): producer[v] = (i, k, var_type(v))
        for name, val in re.findall(r"(\w+)\s*=\s*([^,()]+)", args):
            val = val.strip().strip('"')
            if val in producer:
                pid, slot, ty = producer[val]
                node["inputs"].append([name, ty]); links.append([pid, slot, i, len(node["inputs"]) - 1, ty])
        nodes.append(node); code.append([line, i])
    return {"nodes": nodes, "links": links}, code

def skeleton_from_json(g):
    """Rule-based inversion: the executed JSON graph written back as skeleton pseudo-code, one line per node."""
    byid = {n["id"]: n for n in g["nodes"]}
    preds = {n["id"]: set() for n in g["nodes"]}
    for f, fs, t, ts, ty in g["links"]: preds[t].add(f)
    done, order = set(), []
    while len(order) < len(g["nodes"]):
        ready = sorted([i for i in byid if i not in done and preds[i] <= done], key=lambda i: (byid[i]["order"], i))
        for i in ready: done.add(i); order.append(i)
    var, code = {}, []
    for i in order:
        n = byid[i]; outs = []
        for k, (name, ty) in enumerate(n["outputs"]):
            v = f"{(ty or name).upper().replace(' ', '_')}_{i}"; var[(i, k)] = v; outs.append(v)
        args = [f"{n['inputs'][ts][0]}={var.get((f, fs), '?')}" for f, fs, t, ts, ty in g["links"] if t == i]
        code.append([f"{', '.join(outs) if outs else '_'} = {n['type']}({', '.join(args)})", i])
    return code

def mark_sink(g, image_path):
    succ = {n["id"]: 0 for n in g["nodes"]}
    for f, fs, t, ts, ty in g["links"]: succ[f] += 1
    # sink with the longest path from sources = last stage
    preds = {n["id"]: [] for n in g["nodes"]}
    for f, fs, t, ts, ty in g["links"]: preds[t].append(f)
    depth = {}
    def d(i):
        if i in depth: return depth[i]
        depth[i] = max((d(p) for p in preds[i]), default=-1) + 1; return depth[i]
    sinks = [n["id"] for n in g["nodes"] if succ[n["id"]] == 0]
    best = max(sinks, key=d)
    for n in g["nodes"]:
        if n["id"] == best: n["image"] = image_path

EX = [
    dict(idx=90, short="Text-to-image + 2× upscale", json="Figures/workflow_compare/pair_4/ours_90_workflow.json", out="Figures/example/our_benchmark/workflow_90_our.png",
         outLabel="output · 1024 × 1024", inp=None, hide=False, frame=None,
         note="Text-to-image with a prompt-guided two-stage upscale: a 512 × 512 latent is sampled, decoded, then enlarged 2× by UltimateSDUpscale with the same model and prompts. Graph and parameters are read from the workflow JSON the agent produced; the skeleton pseudo-code is that JSON written back in the paper's notation."),
    dict(idx=448, short="LoRA style preset + upscale", json="Figures/workflow_compare/pair_3/ours_448_workflow.json", out="Figures/example/our_benchmark/workflow_448_our.png",
         outLabel="output · 1024 × 1024", inp=None, hide=True, frame=None,
         note="A style preset is applied as a LoRA on both the UNet and CLIP before sampling, then the decoded image is upscaled 2× with tile-aware diffusion. Prompt widgets are hidden here; everything else is the agent's JSON."),
    dict(idx=300, short="Outpainting", json="Figures/workflow_compare/pair_2/ours_300_workflow.json", out="Figures/example/our_benchmark/workflow_300_our.png",
         outLabel="output · 1536 × 1536 · dashed = original canvas", inp=None, hide=False, frame=128 / 1536,
         note="The canvas is padded by 128 px on every side, the padded image is VAE-encoded, the pad becomes a latent noise mask, and only the border is resynthesised under the text conditioning. The dashed frame marks the original 1280 × 1280 canvas."),
    dict(idx=85, short="Restore + stylise a blurry photo", json=None, out="Figures/example/our_benchmark/workflow_85_our.png",
         outLabel="output · restored, face-detailed, colour-matched", inp="Figures/example/our_benchmark/模糊_2.jpg", hide=False, frame=None,
         note="The richest of the four: an automatic tagger writes the prompt, a Canny edge map anchors the layout through ControlNet, a face detailer segments and refines the face, and the colours are matched back to the source. No executed JSON was kept for this task, so the graph is parsed directly from the agent's skeleton pseudo-code; parameters are therefore not shown."),
]
examples = []
for e in EX:
    rec = REC[e["idx"]]
    if e["json"]:
        g = graph_from_json(os.path.join(PROJ, e["json"]), e["hide"]); code = skeleton_from_json(g)
    else:
        g, code = graph_from_pseudocode(rec["final_refined_pseudocode_from_refined_model_strategy"])
    out_name = f"ex_{e['idx']}.jpg"; save_jpg(sq(Image.open(os.path.join(PROJ, e["out"])), 900), out_name, q=86)
    mark_sink(g, "assets/" + out_name)
    inp_name = None
    if e["inp"]:
        inp_name = f"ex_{e['idx']}_input.jpg"; save_jpg(sq(Image.open(os.path.join(PROJ, e["inp"])), 400), inp_name, q=84)
    examples.append(dict(idx=e["idx"], short=e["short"], question=clean(rec["question"]), strategy=excerpt(rec["refined_model_strategy"]), code=code, graph=g,
                         out="assets/" + out_name, inp=("assets/" + inp_name) if inp_name else None, outLabel=e["outLabel"], frame=e["frame"], note=e["note"]))
    print(f"task {e['idx']}: {len(g['nodes'])} nodes, {len(g['links'])} links, {len(code)} code lines")

# ------------------------------------------------------------------ subtitles / transcript
srt = open(os.path.join(PROJ, "ECCV2026_video_Knowledge-Centric-Agents.srt"), encoding="utf-8").read().strip()
cues = []
for b in re.split(r"\n\s*\n", srt):
    lines = b.strip().splitlines()
    if len(lines) < 3: continue
    m = re.match(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> ", lines[1])
    start = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
    cues.append((start, lines[1].replace(",", "."), " ".join(lines[2:])))
open(os.path.join(A, "talk.vtt"), "w", encoding="utf-8").write("WEBVTT\n\n" + "\n\n".join(f"{i+1}\n{t}\n{txt}" for i, (_, t, txt) in enumerate(cues)) + "\n")
chapters = [(0, "Introduction"), (18, "The task"), (51, "Why direct text-to-JSON fails"), (86, "Our idea"), (110, "Knowledge inversion"), (145, "Knowledge injection"),
            (172, "Knowledge inference"), (198, "Results"), (227, "Generalisation and ablation"), (249, "Qualitative comparison"), (275, "Conclusion")]
transcript = []
for i, (s, title) in enumerate(chapters):
    e = chapters[i + 1][0] if i + 1 < len(chapters) else 1e9
    transcript.append([title, " ".join(c[2] for c in cues if s - 0.5 <= c[0] < e - 0.5)])

# ------------------------------------------------------------------ social card (1200 x 630)
def F(name, size): return ImageFont.truetype(os.path.join(FONTS, name), size)
og = Image.new("RGB", (1200, 630), (248, 246, 247)); d = ImageDraw.Draw(og)
d.rounded_rectangle((40, 150, 1160, 430), 18, fill=(139, 26, 88))
d.text((600, 230), "Knowledge-Centric Agents for", font=F("arialbd.ttf", 54), fill="white", anchor="mm")
d.text((600, 300), "Workflow Generation in ComfyUI", font=F("arialbd.ttf", 54), fill="white", anchor="mm")
d.text((600, 380), "From a plain task description to an executable ComfyUI workflow", font=F("arial.ttf", 26), fill=(245, 225, 236), anchor="mm")
d.text((600, 490), "Zhendong Li · Lei Sun · Ruibo Ming · He Zhang · Danda Pani Paudel · Luc Van Gool · Jinjin Gu", font=F("arial.ttf", 22), fill=(78, 67, 75), anchor="mm")
d.text((600, 530), "INSAIT, Sofia University  ·  Adobe Research  ·  ECCV 2026, Malmö", font=F("arial.ttf", 22), fill=(126, 114, 122), anchor="mm")
li = Image.open(os.path.join(A, "logo_insait.png")).convert("RGBA"); li = li.resize((round(li.width * 46 / li.height), 46), Image.LANCZOS); og.paste(li, (60, 52), li)
la = Image.open(os.path.join(A, "logo_adobe.png")).convert("RGBA"); la = la.resize((36, 36), Image.LANCZOS); og.paste(la, (300, 57), la)
d.text((346, 75), "Adobe Research", font=F("arialbd.ttf", 24), fill=(29, 21, 32), anchor="lm")
le = Image.open(os.path.join(A, "logo_eccv.png")).convert("RGBA"); le = le.resize((round(le.width * 70 / le.height), 70), Image.LANCZOS); og.paste(le, (1160 - le.width, 40), le)
og.save(os.path.join(A, "og.jpg"), "JPEG", quality=88)

# ------------------------------------------------------------------ assemble
tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
html = tpl.replace("__DATA_examples__", json.dumps(examples, ensure_ascii=False)).replace("__DATA_cues__", json.dumps(transcript, ensure_ascii=False))
assert "__DATA_" not in html
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
open(os.path.join(OUT, ".nojekyll"), "w").write("")
os.makedirs(os.path.join(OUT, "tools"), exist_ok=True)
shutil.copy(__file__, os.path.join(OUT, "tools", "build_page.py"))
shutil.copy(os.path.join(HERE, "page_template.html"), os.path.join(OUT, "tools", "page_template.html"))
open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write("""# Project page — Knowledge-Centric Agents for Workflow Generation in ComfyUI (ECCV 2026)

Static site, no build step needed to deploy.

## Deploy on GitHub Pages
1. Create a repository (for example `knowledge-centric-agents`) and copy the contents of this folder to its root
   (or into `docs/`).
2. Repository → Settings → Pages → *Deploy from a branch* → `main`, folder `/ (root)` (or `/docs`).
3. The page is then served at `https://<user>.github.io/<repo>/`.

## Three things to fill in (search for them in `index.html`)
- `CODE_URL` — the code repository. Also remove `class="soon"`, `aria-disabled` and the `onclick` on that button.
- `YOUTUBE_URL` — set the constant at the top of the script to show a YouTube link under the talk video.
- `SITE_URL` — the absolute URL of the deployed page, used for the Open Graph preview image (`assets/og.jpg`).

## Contents
- `index.html` — the page (single file, inline CSS/JS, Google Fonts as the only external dependency).
- `assets/` — images, the 39 s demo video (`demo.mp4`), the 5-minute talk (`talk_720p.mp4` + `talk.vtt`), poster (`poster.pdf`, JPEGs), social card (`og.jpg`).
- `tools/` — `build_page.py` + `page_template.html` regenerate `index.html` and `assets/` from the paper's source data; not needed for deployment.
""")
total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
print("written:", OUT, f"{total/1e6:.1f} MB total")
for f in sorted(os.listdir(A)): print(f"  assets/{f:<22} {os.path.getsize(os.path.join(A, f))/1e3:8.0f} KB")
