#!/usr/bin/env python3
"""Auto-mark animated models as validated NPCs (user prunes false positives).

Reads the single-pass anim-index CSV (chunk,file_hash,hash0,hash1):
  BB9/FA1 chunks = animation side, FA0/BB8 chunks = a model's own signature.
A model is 'animated' iff its signature pair appears in some BB9/FA1 chunk.

Marks animated models that have a rendered sprite via the gallery API
(POST /api/state merge), so they appear in the 'validated' chip immediately.
"""
import csv
import json
import os
import sys
import urllib.request

INDEX = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/gwmb-batch/anim-index.csv"
API = "http://localhost:5301/api/state"  # SvelteKit app
SCAN = "/workspace/pro/gw1-sprites/out/scan"


def main():
    # MODEL rows carry the real parsed geometry signature + rigged flag; the
    # animation side comes from BB9/FA1 chunk headers in files WITHOUT geometry.
    model_sig, rigged_set, has_geo = {}, set(), set()
    rows = []
    with open(INDEX) as f:
        for r in csv.DictReader(f):
            if r["chunk"].startswith("#"):
                continue
            h = "0x" + r["file_hash"].upper()
            if r["chunk"] == "MODEL":
                model_sig[h] = (r["hash0"], r["hash1"])
                has_geo.add(h)
                if r.get("rigged") == "1":
                    rigged_set.add(h)
            else:
                rows.append((h, r["chunk"], (r["hash0"], r["hash1"])))

    anim_pairs = set()
    for h, chunk, pair in rows:
        if pair == ("0", "0"):
            continue
        if chunk in ("BB9", "FA1") and h not in has_geo:
            anim_pairs.add(pair)

    has_anim = {h for h, p in model_sig.items() if p in anim_pairs and p != ("0", "0")}
    animated = rigged_set | has_anim
    print(f"{len(model_sig)} parsed models, {len(rigged_set)} rigged, "
          f"{len(anim_pairs)} anim pairs, {len(has_anim)} matched to animations, "
          f"{len(animated)} total animated")

    have_sprite = set()
    for f in os.listdir(SCAN):
        if f.endswith("_gwmb.png") and "_posed" not in f:
            have_sprite.add(f.replace("model_", "").replace("_gwmb.png", "").upper())

    with open("/workspace/pro/gw1-sprites/out/validation.json") as f:
        state = json.load(f)
    already = {h.upper() for h in state.get("npcOk", {})}

    to_mark = sorted(h for h in animated
                     if h.upper() in have_sprite and h.upper() not in already)
    print(f"{len(to_mark)} animated models with sprites not yet validated")

    with open("/workspace/pro/gw1-sprites/out/animated_candidates.txt", "w") as f:
        f.write("\n".join(to_mark))
    print("candidates written to out/animated_candidates.txt")

    if "--apply" not in sys.argv:
        print("DRY RUN (pass --apply to merge into the validated set)")
        return

    if to_mark:
        body = json.dumps({"merge": {"npcOk": {h: 1 for h in to_mark}}}).encode()
        req = urllib.request.Request(API, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            print("API:", r.read().decode())


if __name__ == "__main__":
    main()
