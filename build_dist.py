#!/usr/bin/env python3
"""Build the final asset distribution (dist/) from the working pipeline data.

NPCs (dat-sourced): out/scan sprites + out/validation.json (user-validated set),
posed sprites preferred when rendered; names from known_names/item_names CSVs.

This repo handles NPCs only — items are wiki-sourced and live with the site
(wiki icons are same-resolution originals, no game extraction needed).

Outputs:
  dist/npc.jsonl, dist/npc/<model>.png (+ <model>_idle.png opt-in variants)

UUIDs are deterministic (uuid5) so regeneration never changes ids.
"""
import csv
import json
import os
import re
import shutil
import uuid

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
SCAN = os.path.join(OUT, "scan")
HIRES = os.path.join(OUT, "hires")  # 512px final renders, preferred when present
WIKI_ICONS = os.path.join(ROOT, "wiki-icons")
DIST = os.path.join(ROOT, "dist")
NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://cedricdessalles.dev/gw1-assets")

CATEGORY_MAP = [
    ("armor icons", "armor"),
    ("miniature", "miniature"),
    ("trophy", "trophy"),
    ("quest item", "quest"),
    ("weapon icons", "weapon"),
]
WEAPON_TYPES = ("sword", "axe", "hammer", "bow", "staff", "wand", "shield",
                "focus", "dagger", "scythe", "spear")


def safe_name(n):
    # mirrors fetch_wiki_icons.py sanitization
    return re.sub(r"[^A-Za-z0-9._'() %!+,-]", "_", n)


def main():
    # ---------------- NPCs (dat-sourced) ----------------
    meta = {}
    with open(os.path.join(OUT, "classifications.csv")) as f:
        for r in csv.DictReader(f):
            meta[r["hash"].upper()] = r

    names = {}
    for src in ("item_names.csv", "known_names.csv"):
        try:
            with open(os.path.join(OUT, src)) as f:
                for r in csv.DictReader(f):
                    names[r["hash"].upper()] = (r["name"], r.get("wiki", ""))
        except FileNotFoundError:
            pass

    with open(os.path.join(OUT, "validation.json")) as f:
        validation = json.load(f)
    npc_ok = {h.upper() for h in validation.get("npcOk", {})}

    sprites, posed = {}, {}
    for f in os.listdir(SCAN):
        if not f.endswith(".png"):
            continue
        h = f.replace("model_", "").replace("_gwmb.png", "")
        if h.endswith("_posed"):
            posed[h[:-6].upper()] = f
        else:
            sprites[h.upper()] = f

    os.makedirs(os.path.join(DIST, "npc"), exist_ok=True)

    npcs = []
    for h in sorted(npc_ok):
        if h not in sprites:
            continue
        m = meta.get(h, {})
        name, wiki = names.get(h, ("", ""))
        model = "0x" + h.replace("0X", "")
        stats = {k: int(m[k]) for k in ("verts", "parts", "ntex")
                 if m.get(k, "").isdigit()}
        # Bind pose only — idle captures can freeze a bad animation frame.
        e = {
            "id": str(uuid.uuid5(NS, h)),
            "model": model,
            "title": name or f"NPC {model}",
            "name": name or None,
            "wiki": wiki or None,
            "sprite": f"npc/{model}.png",
            "tags": ["validated"],
            "categories": [],
            "stats": stats,
        }
        hires = os.path.join(HIRES, sprites[h])
        src = hires if os.path.exists(hires) else os.path.join(SCAN, sprites[h])
        shutil.copyfile(src, os.path.join(DIST, "npc", f"{model}.png"))
        npcs.append(e)

    npcs.sort(key=lambda e: e["model"])
    # JSONL: one NPC per line — streamable, line-diffable, editable per record.
    with open(os.path.join(DIST, "npc.jsonl"), "w") as f:
        for e in npcs:
            f.write(json.dumps(e) + "\n")
    print(f"dist built: {len(npcs)} npcs ({sum(1 for e in npcs if e['name'])} named)")


if __name__ == "__main__":
    main()
