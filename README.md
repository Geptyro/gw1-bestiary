# gw1-bestiary

Isometric NPC sprite library extracted from Guild Wars 1 game data, for the
guildwars3 fan site and shared for community tooling.

> **Attribution & takedown**: all extracted artwork (sprites in `npc/`) is
> © ArenaNet / NCSoft, derived from Guild Wars game data via
> [GuildWarsMapBrowser](https://github.com/Jonathan-Greve/GuildWarsMapBrowser).
> Non-commercial fan project in the spirit of the community's long-standing
> practice ([ArenaNet's informal stance](https://wiki.guildwars.com/wiki/Player-made_Modifications));
> assets will be removed immediately on request from the rights holder.
> Tooling (scripts, app, fork patches) is the author's own.

**Scope: NPCs only.** Items are handled site-side from the official wiki's
icon corpus (same 64×64 originals, pre-named and pre-linked) — no extraction
or icon tooling lives here.

## Install

```
npm install @geptyro/gw1-bestiary
```

```js
import npc from '@geptyro/gw1-bestiary/npc.jsonl'; // or read the file directly
// sprites: node_modules/@geptyro/gw1-bestiary/npc/<model>.png
```

## Contents

```
npc.jsonl   one NPC per line: { id, model, title, name, wiki, sprite, tags, categories, stats, duplicates? }
npc/        isometric sprites, 512px PNG, transparent background, 2:1 dimetric
```

- `id` — stable UUID (never changes between releases)
- `model` — Gw.dat file hash of the 3D model (e.g. `0x1C817`)
- `name`/`wiki` — every published NPC has a confirmed wiki identity
- `sprite` — relative path to the PNG, e.g. `npc/0x1C817.png`
- `duplicates` — (optional) model hashes of byte-identical / re-posed variants
  collapsed into this canonical entry
- Sprites are bind-pose, front-facing, rendered from the original game geometry
  and textures (high LOD, emissive glow layers included)

This published package contains only NPCs with a confirmed wiki link; it is a
linked-only build generated from a larger validated master. Produced by a
private pipeline (GWMB-fork batch extraction → headless Blender → human
validation → wiki linking) out of ~34k models in the dat.

## Releases

Published to npm on a version tag push (`git tag vX.Y.Z && git push --tags`),
which a GitHub Action verifies against `package.json` and publishes. The data +
sprites are regenerated from the master by the private `build_public.py`.
