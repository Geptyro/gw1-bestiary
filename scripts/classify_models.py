#!/usr/bin/env python3
"""Deterministic auto-classification of exported GW1 models.

Sources, in priority order:
  1. inventory icon exists for the hash  -> item (authoritative)
  2. known_names.csv                     -> keeps class but adds name
  3. geometry heuristics from the scan CSV (bbox, verts, textures)

Output: classifications.csv (hash, cls, source, name, icon)
Usage: classify_models.py <scores.csv> <icons-dir> <names.csv> <out.csv>
"""
import csv
import os
import sys


def main():
    scores_csv, icons_dir, names_csv, out_csv = sys.argv[1:5]

    icons = {}
    for f in os.listdir(icons_dir):
        if f.startswith("itemIcon_") and f.endswith(".png"):
            num = f.replace("itemIcon_", "").replace(".png", "").split("_")[0]
            try:
                icons.setdefault(int(num), f)
            except ValueError:
                pass

    names = {}
    try:
        for r in csv.DictReader(open(names_csv)):
            names[r["hash"].upper()] = r["name"]
    except FileNotFoundError:
        pass

    rows_out = []
    for r in csv.DictReader(open(scores_csv)):
        h = r["hash"]
        hnum = int(h, 16)
        height, dx, dz = float(r["height"]), float(r["dx"]), float(r["dz"])
        verts, ntex = int(r["verts"]), int(r["textures"])
        w = max(dx, dz)
        tall = height / max(w, 1e-6)

        if hnum in icons:
            cls, source = "item", "icon"
        elif ntex == 0:
            cls, source = "part", "geometry"  # untextured body/armor part
        elif 1.2 <= tall <= 6 and 500 <= verts <= 20000 and height > 20:
            cls, source = "npc", "geometry"
        elif height < 25 and w < 25:
            cls, source = "small", "geometry"  # small object/prop/item-like
        elif height > 200 or w > 300:
            cls, source = "building", "geometry"  # large structure/terrain piece
        elif tall < 0.15:
            cls, source = "terrain", "geometry"
        else:
            cls, source = "unclear", "geometry"

        rows_out.append({
            "hash": h,
            "cls": cls,
            "source": source,
            "name": names.get(h.upper(), ""),
            "icon": icons.get(hnum, ""),
            "score": r.get("score", ""),
        })

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["hash", "cls", "source", "name", "icon", "score"])
        w.writeheader()
        w.writerows(rows_out)

    counts = {}
    for r in rows_out:
        counts[r["cls"]] = counts.get(r["cls"], 0) + 1
    print(f"{len(rows_out)} classified -> {out_csv}")
    print(dict(sorted(counts.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
