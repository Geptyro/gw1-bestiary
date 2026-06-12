#!/usr/bin/env python3
"""Fetch wiki categories for every file in the icon manifest (batched, polite).

Output: <out-csv> with columns name,categories ('|'-joined, 'File:' prefixes and
'Category:' prefixes stripped).
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request

API = "https://wiki.guildwars.com/api.php"
UA = "gw1-fan-asset-tools/1.0 (personal fan project; contact: dessallescedric@gmail.com)"


def main():
    manifest, out_csv = sys.argv[1], sys.argv[2]
    names = [r["name"] for r in csv.DictReader(open(manifest))]
    rows = []
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        qs = urllib.parse.urlencode({
            "action": "query", "titles": "|".join("File:" + n for n in batch),
            "prop": "categories", "cllimit": "500", "format": "json"})
        req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except Exception as e:
            print(f"batch {i} failed: {e}", flush=True)
            time.sleep(2)
            continue
        norm = {}
        for nz in data.get("query", {}).get("normalized", []):
            norm[nz["to"]] = nz["from"]
        for p in data.get("query", {}).get("pages", {}).values():
            title = p.get("title", "")
            orig = norm.get(title, title).replace("File:", "")
            cats = [c["title"].replace("Category:", "")
                    for c in p.get("categories", [])]
            rows.append((orig, "|".join(cats)))
        if (i // 50) % 20 == 0:
            print(f"{i}/{len(names)}", flush=True)
        time.sleep(0.3)

    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "categories"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out_csv}", flush=True)


if __name__ == "__main__":
    main()
