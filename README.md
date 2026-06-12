# gw1-bestiary

Isometric NPC sprite library extracted from Guild Wars 1 game data, for the
guildwars3 fan site and shared for community tooling.

> **Attribution & takedown**: all extracted artwork (sprites in `dist/`) is
> © ArenaNet / NCSoft, derived from Guild Wars game data via
> [GuildWarsMapBrowser](https://github.com/Jonathan-Greve/GuildWarsMapBrowser).
> Non-commercial fan project in the spirit of the community's long-standing
> practice ([ArenaNet's informal stance](https://wiki.guildwars.com/wiki/Player-made_Modifications));
> assets will be removed immediately on request from the rights holder.
> Tooling (scripts, app, fork patches) is the author's own.

**Scope: NPCs only.** Items are handled site-side from the official wiki's
icon corpus (same 64×64 originals, pre-named and pre-linked) — no extraction
or icon tooling lives here.

## Contents

```
npc.jsonl   one NPC per line: { id, model, title, name, wiki, sprite, tags, categories, stats }
npc/        isometric sprites, 512px PNG, transparent background, 2:1 dimetric
```

- `id` — stable UUID (never changes between releases)
- `model` — Gw.dat file hash of the 3D model (e.g. `0x1C817`)
- `name`/`wiki` — filled progressively via community data and manual curation
- Sprites are bind-pose, front-facing, rendered from the original game geometry
  and textures (high LOD, emissive glow layers included)

Produced by a private pipeline (GWMB-fork batch extraction → headless Blender →
human validation). 1,502 NPCs validated by hand out of ~34k models in the dat.
