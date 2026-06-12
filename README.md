# gw1-sprites

Isometric NPC sprite library extracted from Guild Wars 1 game data, for the
[guildwars3 fan site](../guildwars3). Personal fan project — assets are
ArenaNet's; extracted from a locally-owned install, not redistributed beyond
fan use ([ArenaNet's informal stance](https://wiki.guildwars.com/wiki/Player-made_Modifications)).

**Scope: NPCs only.** Items are wiki-sourced (the official wiki hosts the same
64×64 inventory icons, pre-named and pre-linked) and belong to the site
pipeline — see `scripts/wiki/` until that moves out.

## Pipeline

```
Gw.dat ──(GWMB fork, Windows)──> model JSONs + textures   C:\gwmb-export
       └─(--export-icons-dir)──> inventory icons          C:\gwmb-icons
model JSONs ──(Blender headless)──> isometric sprites     out/scan (256px), out/hires (512px)
sprites ──(classify + human validation in app)──> validated set   out/validation.json
validated set ──(build_dist.py)──> deliverable            dist/npc.jsonl + dist/npc/
```

- **Extraction**: fork of [GuildWarsMapBrowser](https://github.com/Jonathan-Greve/GuildWarsMapBrowser)
  at `C:\gwmb-batch\src` with CLI batch export (`--dat`, `--export-models-dir`,
  `--export-icons-dir`, `--export-posed`, `--dump-anim-index`, `--exit-when-done`,
  crash-resilient). Windows-only (DirectX 11); build Release|Win32 with VS Build
  Tools, `/p:PlatformToolset=v143`.
- **Rendering**: `scripts/render_isometric.py` via headless Blender
  (`/workspace/tools/blender`). Standards: 2:1 dimetric (60°), `--base-azimuth 135`
  (front, facing right), light rig key 2.2 / fill 0.7 / rim 1.1 / ambient 0.22,
  `--bloom` for emissive glow, Cycles CPU. Final quality: 512px / 48 samples.
  GWMB Blender addon (patched copy) in `gwmb_addon/`.
- **Admin app**: `app/` (SvelteKit, `npm run dev` → http://localhost:5301):
  gallery + validation at `/`, wiki-link editor at `/link`.
  Owns `out/validation.json` and `out/links.json`.
- **Build**: `python3 build_dist.py` → `dist/npc.jsonl` (one NPC per line,
  stable uuid5 ids) + `dist/npc/*.png` (hires preferred).

## Decisions of record

- Bind pose (T-pose) sprites — pose-baked idle exists in the fork but frozen
  animation frames look worse than neutral bind pose.
- Manual validation only — no reliable offline "is a creature" signal in the
  dat (bone markers exist on everything; animation signatures collapse into
  shared rig families).
- Armor pieces, capes, and modular multi-part units are out of scope (dye
  textures and unit composition are runtime/server data).
- 512px finals; 256px for triage scans.

## Layout

```
build_dist.py        build the deliverable from validated state
app/                 SvelteKit admin (gallery + wiki linking)
gwmb_addon/          patched GWMB Blender import addon
scripts/             pipeline tools (render, scan, classify, contact sheets)
scripts/wiki/        wiki icon corpus tooling (items — site-bound)
scripts/legacy/      retired (python gallery server, auto-validation dead end)
out/                 working state: validation.json, links.json, *.csv (tracked);
                     scan/, hires/ sprite caches (untracked)
dist/                deliverable (untracked, regenerable)
wiki-icons/          downloaded wiki icon corpus (untracked)
```
