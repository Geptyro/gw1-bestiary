#!/usr/bin/env python3
"""Fetch all 64x64 PNG icons from the official Guild Wars wiki (wiki.guildwars.com).

Phase 1 of icon->name matching: enumerate file metadata via the MediaWiki API,
keep only 64x64 PNGs (the game's inventory-icon format), download them politely.

Resumable: already-downloaded files are skipped; the manifest is rewritten each run.

Usage: fetch_wiki_icons.py <out-dir>
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://wiki.guildwars.com/api.php"
UA = "gw1-fan-asset-tools/1.0 (personal fan project; contact: dessallescedric@gmail.com)"


def api(params):
    qs = urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)

    # 1. enumerate all images, keep 64x64 PNGs
    icons = []
    aifrom = None
    pages = 0
    while True:
        params = {"action": "query", "list": "allimages", "ailimit": "500",
                  "aiprop": "url|size|mime"}
        if aifrom:
            params["aifrom"] = aifrom
        data = api(params)
        for img in data.get("query", {}).get("allimages", []):
            if (img.get("mime") == "image/png" and img.get("width") == 64
                    and img.get("height") == 64):
                icons.append((img["name"], img["url"]))
        pages += 1
        if pages % 20 == 0:
            print(f"enumerated {pages} pages, {len(icons)} 64x64 PNGs so far", flush=True)
        cont = data.get("continue", {}).get("aicontinue")
        if not cont:
            break
        aifrom = cont
        time.sleep(0.3)

    print(f"enumeration done: {len(icons)} candidate icons", flush=True)
    with open(os.path.join(out_dir, "_manifest.csv"), "w") as f:
        f.write("name,url\n")
        for name, url in icons:
            f.write(f'"{name}","{url}"\n')

    # 2. download missing ones
    done = 0
    skipped = 0
    failed = 0
    for name, url in icons:
        safe = re.sub(r'[^A-Za-z0-9._\'() %!+,-]', "_", name)
        path = os.path.join(out_dir, safe)
        if os.path.exists(path):
            skipped += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                blob = r.read()
            with open(path, "wb") as f:
                f.write(blob)
            done += 1
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {e}", flush=True)
        if (done + failed) % 200 == 0 and done + failed:
            print(f"downloaded {done}, failed {failed}, skipped {skipped}", flush=True)
        time.sleep(0.25)

    print(f"DONE: downloaded {done}, failed {failed}, already had {skipped}", flush=True)


if __name__ == "__main__":
    main()
