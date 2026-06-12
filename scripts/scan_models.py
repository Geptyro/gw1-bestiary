#!/usr/bin/env python3
"""Scan GWMB model JSONs and rank them by NPC/creature-likeness.

Outputs a CSV (hash, score, height, width, depth, verts, submodels, textures)
sorted so tall, organic-vertex-count models come first. GWMB JSON is
left-handed Y-up, so height = Y extent.

Usage: python3 scan_models.py <export-dir> <out-csv> [workers]
Incremental: hashes already present in out-csv are skipped.
"""
import csv
import json
import os
import sys
from multiprocessing import Pool


def scan_one(path):
    try:
        size = os.path.getsize(path)
        if size < 200:
            return None  # empty model (no geometry)
        with open(path) as f:
            data = json.load(f)
        subs = data.get("submodels", [])
        if not subs:
            return None
        mins = [float("inf")] * 3
        maxs = [float("-inf")] * 3
        verts = 0
        for sm in subs:
            for v in sm.get("vertices", []):
                p = v["pos"]
                verts += 1
                for k, axis in enumerate(("x", "y", "z")):
                    val = p[axis]
                    if val < mins[k]:
                        mins[k] = val
                    if val > maxs[k]:
                        maxs[k] = val
        if not verts:
            return None
        dx, dy, dz = (maxs[k] - mins[k] for k in range(3))
        width = max(dx, dz, 1e-6)
        # NPC heuristic: clearly taller than wide, human-ish poly budget,
        # multiple submodels (body parts), at least one texture.
        tall = dy / width
        score = 0.0
        if 1.2 <= tall <= 6.0:
            score += min(tall, 3.0)
        if 500 <= verts <= 20000:
            score += 1.5
        if len(subs) >= 2:
            score += 1.0
        if data.get("textures"):
            score += 1.0
        name = os.path.basename(path)
        h = name.split("_")[1]
        return (h, round(score, 2), round(dy, 1), round(dx, 1), round(dz, 1),
                verts, len(subs), len(data.get("textures", [])), path)
    except Exception:
        return None


def main():
    export_dir, out_csv = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    seen = set()
    rows = []
    if os.path.exists(out_csv):
        with open(out_csv) as f:
            for row in csv.reader(f):
                if row and row[0] != "hash":
                    seen.add(row[0])
                    rows.append(row)

    todo = []
    with os.scandir(export_dir) as it:
        for e in it:
            if e.name.startswith("model_0x") and e.name.endswith("_gwmb.json"):
                h = e.name.split("_")[1]
                if h not in seen:
                    todo.append(e.path)

    print(f"scanning {len(todo)} new JSONs ({len(seen)} already scanned)")
    with Pool(workers) as pool:
        for r in pool.imap_unordered(scan_one, todo, chunksize=64):
            if r:
                rows.append([str(x) for x in r])

    rows.sort(key=lambda r: -float(r[1]))
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hash", "score", "height", "dx", "dz", "verts", "submodels",
                    "textures", "path"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out_csv}")


if __name__ == "__main__":
    main()
