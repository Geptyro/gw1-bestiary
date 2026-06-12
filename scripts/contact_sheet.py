#!/usr/bin/env python3
"""Build labeled contact sheets from a folder of sprite PNGs.

Usage: <blender-python> contact_sheet.py <sprites-dir> <out-dir> [cols] [rows] [cell]
Each sheet is a cols x rows grid; under every sprite its model hash is printed,
plus a grid coordinate (A1..) so a reviewer can reference cells unambiguously.
"""
import os
import sys

from PIL import Image, ImageDraw

LABEL_H = 22


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    cell = int(sys.argv[5]) if len(sys.argv) > 5 else 192

    os.makedirs(out_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.endswith(".png"))
    per_sheet = cols * rows
    n_sheets = (len(files) + per_sheet - 1) // per_sheet

    for s in range(n_sheets):
        chunk = files[s * per_sheet:(s + 1) * per_sheet]
        W, H = cols * cell, rows * (cell + LABEL_H)
        sheet = Image.new("RGB", (W, H), (40, 40, 46))
        draw = ImageDraw.Draw(sheet)
        for i, name in enumerate(chunk):
            cx, cy = i % cols, i // cols
            x, y = cx * cell, cy * (cell + LABEL_H)
            try:
                im = Image.open(os.path.join(src, name)).convert("RGBA")
                im.thumbnail((cell, cell))
                bg = Image.new("RGBA", (cell, cell), (72, 72, 80, 255))
                bg.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2), im)
                sheet.paste(bg.convert("RGB"), (x, y))
            except Exception:
                draw.rectangle([x, y, x + cell, y + cell], fill=(90, 30, 30))
            label = name.replace("model_", "").replace("_gwmb.png", "")
            coord = f"{chr(65 + cy)}{cx + 1}"
            draw.text((x + 3, y + cell + 3), f"{coord} {label}", fill=(230, 230, 230))
        path = os.path.join(out_dir, f"sheet_{s:03d}.png")
        sheet.save(path)
        print(path, f"({len(chunk)} sprites)")


if __name__ == "__main__":
    main()
