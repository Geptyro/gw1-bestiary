#!/usr/bin/env python3
"""Match extracted dat inventory icons against downloaded wiki icons by pixels.

Phase 2 of icon->name matching (run with Blender's python for PIL):
  match_icons.py <dat-icons-dir> <wiki-icons-dir> <classifications.csv> <out.csv>

Method: 64-bit dHash shortlist (Hamming <= MAX_D), then 16x16 RGB mean-abs-diff
verification on gray-composited images. Names derive from wiki filenames; wiki
page links are verified in batches via the MediaWiki API (existing pages only).
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

MAX_D = 8         # dHash Hamming shortlist threshold
MAX_DIFF = 18.0   # mean abs channel diff (0-255) acceptance for verification
API = "https://wiki.guildwars.com/api.php"
UA = "gw1-fan-asset-tools/1.0 (personal fan project; contact: dessallescedric@gmail.com)"


def load_gray_composite(path, size):
    im = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
    bg = Image.new("RGBA", size, (128, 128, 128, 255))
    bg.paste(im, (0, 0), im)
    return bg.convert("RGB")


def dhash(path):
    im = load_gray_composite(path, (9, 8)).convert("L")
    px = list(im.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[row * 9 + col] > px[row * 9 + col + 1])
    return bits


def pixsig(path):
    return list(load_gray_composite(path, (16, 16)).getdata())


def meandiff(a, b):
    return sum(abs(x[0] - y[0]) + abs(x[1] - y[1]) + abs(x[2] - y[2])
               for x, y in zip(a, b)) / (len(a) * 3)


def main():
    dat_dir, wiki_dir, cls_csv, out_csv = sys.argv[1:5]

    icon_to_model = {}
    for r in csv.DictReader(open(cls_csv)):
        if r.get("icon"):
            icon_to_model.setdefault(r["icon"], r["hash"])

    wiki = []
    for f in sorted(os.listdir(wiki_dir)):
        if not f.lower().endswith(".png"):
            continue
        p = os.path.join(wiki_dir, f)
        try:
            wiki.append((f, dhash(p), p))
        except Exception:
            pass
    print(f"{len(wiki)} wiki icons hashed", flush=True)

    results = []
    todo = sorted(icon_to_model.items())
    for n, (icon_file, model) in enumerate(todo, 1):
        p = os.path.join(dat_dir, icon_file)
        if not os.path.exists(p):
            continue
        try:
            h = dhash(p)
        except Exception:
            continue
        cands = [(bin(h ^ wh).count("1"), wf, wp) for wf, wh, wp in wiki]
        cands = sorted(c for c in cands if c[0] <= MAX_D)[:8]
        if not cands:
            continue
        sig = pixsig(p)
        best = None
        for d, wf, wp in cands:
            diff = meandiff(sig, pixsig(wp))
            if diff <= MAX_DIFF and (best is None or diff < best[0]):
                best = (diff, wf)
        if best:
            name = os.path.splitext(best[1])[0].replace("_", " ").strip()
            results.append({"hash": model, "name": name, "diff": round(best[0], 1),
                            "wikifile": best[1]})
        if n % 500 == 0:
            print(f"{n}/{len(todo)} matched so far: {len(results)}", flush=True)

    print(f"matched {len(results)} of {len(todo)} dat icons", flush=True)

    # verify wiki pages exist for the derived names (batched)
    names = sorted({r["name"] for r in results})
    exists = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        qs = urllib.parse.urlencode({"action": "query", "titles": "|".join(batch),
                                     "format": "json"})
        req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            norm = {}
            for nz in data.get("query", {}).get("normalized", []):
                norm[nz["from"]] = nz["to"]
            pages = data.get("query", {}).get("pages", {})
            titles_ok = {p["title"] for pid, p in pages.items() if int(pid) > 0}
            for nm in batch:
                exists[nm] = norm.get(nm, nm) in titles_ok
        except Exception as e:
            print(f"verify batch failed: {e}", flush=True)
        time.sleep(0.3)

    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hash", "name", "wiki", "diff", "wikifile"])
        for r in results:
            url = ""
            if exists.get(r["name"]):
                url = "https://wiki.guildwars.com/wiki/" + urllib.parse.quote(
                    r["name"].replace(" ", "_"))
            w.writerow([r["hash"], r["name"], url, r["diff"], r["wikifile"]])
    linked = sum(1 for r in results if exists.get(r["name"]))
    print(f"wrote {len(results)} names ({linked} with verified wiki pages) -> {out_csv}",
          flush=True)


if __name__ == "__main__":
    main()
