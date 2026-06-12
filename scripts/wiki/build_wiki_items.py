#!/usr/bin/env python3
"""Build the wiki-sourced item list: filter icon corpus by category, verify pages.

Inputs:  wiki-icons/_manifest.csv, wiki-icons/_categories.csv
Output:  out/wiki_items.csv (file,name,wiki,categories)

Include: armor/weapon/item/trophy/quest item/miniature/weapon-type icon categories.
Exclude: skill icons and icon redirects (exclusion wins).
Page verification: derived name must be an existing wiki article, else wiki="".
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://wiki.guildwars.com/api.php"
UA = "gw1-fan-asset-tools/1.0 (personal fan project; contact: dessallescedric@gmail.com)"

INCLUDE = re.compile(
    r"(armor|weapon|item|trophy|quest item|miniature|staff|bow|sword|wand|shield|"
    r"focus|axe|hammer|dagger|scythe|spear|salvage|material|key) icons", re.I)
EXCLUDE = re.compile(r"(skill icons|icon redirects)", re.I)


def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cats = {}
    with open(os.path.join(root, "wiki-icons", "_categories.csv")) as f:
        for r in csv.DictReader(f):
            cats[r["name"]] = r["categories"]

    kept = []
    for name, cstr in cats.items():
        if EXCLUDE.search(cstr):
            continue
        if INCLUDE.search(cstr):
            kept.append((name, cstr))
    print(f"{len(kept)} item icons kept of {len(cats)} categorized files")

    # derive article names and verify existence in batches
    def article(name):
        n = os.path.splitext(name)[0].replace("_", " ").strip()
        n = re.sub(r"\s*\((icon|item|inventory icon)\)$", "", n, flags=re.I)
        return n

    names = sorted({article(n) for n, _ in kept})
    exists = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        qs = urllib.parse.urlencode({"action": "query", "titles": "|".join(batch),
                                     "redirects": "1", "format": "json"})
        req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except Exception as e:
            print(f"verify batch {i} failed: {e}", flush=True)
            time.sleep(2)
            continue
        q = data.get("query", {})
        # map back through normalization and redirects
        fwd = {}
        for nz in q.get("normalized", []):
            fwd[nz["from"]] = nz["to"]
        rd = {}
        for z in q.get("redirects", []):
            rd[z["from"]] = z["to"]
        ok_titles = {p["title"] for pid, p in q.get("pages", {}).items() if int(pid) > 0}
        for nm in batch:
            t = fwd.get(nm, nm)
            t = rd.get(t, t)
            exists[nm] = t if t in ok_titles else ""
        if (i // 50) % 10 == 0:
            print(f"verified {i}/{len(names)}", flush=True)
        time.sleep(0.3)

    out = os.path.join(root, "out", "wiki_items.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "name", "wiki", "categories"])
        for name, cstr in sorted(kept):
            art = article(name)
            target = exists.get(art, "")
            url = ("https://wiki.guildwars.com/wiki/" +
                   urllib.parse.quote(target.replace(" ", "_"))) if target else ""
            w.writerow([name, art, url, cstr])
    linked = sum(1 for n, _ in kept if exists.get(article(n)))
    print(f"wrote {len(kept)} items ({linked} with verified pages) -> {out}")


if __name__ == "__main__":
    main()
