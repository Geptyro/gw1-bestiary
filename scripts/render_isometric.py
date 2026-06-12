"""
render_isometric.py — Batch isometric sprite renderer for Blender 4.x (headless).

Renders every model in --input (recursive) to transparent-background PNG sprites
using an orthographic camera at a classic isometric angle.

Supported inputs:
  .glb / .gltf  (preferred: textures embedded in .glb)
  .obj          (+ .mtl + textures next to it)
  .json         (GuildWarsMapBrowser native model export; requires --gwmb-addon
                 pointing at GWMB's blender_addons/model_import_addon/import_model.py.
                 Texture PNGs named <file_hash>.png must sit next to the .json.)

Usage:
  blender --background --factory-startup --python render_isometric.py -- \
      --input  /data/gw1_models \
      --output /data/gw1_sprites \
      --res 512 --style dimetric --directions 8 \
      --engine auto --normalize per-model --fix-normals

Styles (both use a 45 deg azimuth and an orthographic camera):
  isometric : true isometric. Camera elevation 35.264 deg above horizon
              (rotation_euler.x = 54.7356 deg = atan(sqrt(2))). Equal foreshortening
              on all three axes; a unit cube's top face renders as a regular hexagon outline.
  dimetric  : game-style "2:1 pixel" isometric. Camera elevation 30 deg
              (rotation_euler.x = 60 deg). Tile edges run at 2:1 pixel slopes,
              matching classic isometric game art (Diablo/AoE style).

Normalization:
  per-model : each model is auto-framed (fit ortho_scale to its bounding box).
              Good for icons. Relative sizes between models are LOST.
  global    : fixed ortho_scale (--global-scale, world units across the frame).
              Consistent pixels-per-world-unit across all models. Good for
              in-world sprites. Models larger than the frame get cropped.

Lighting (--light-mode):
  camera : the light rig rotates with the camera azimuth, so all 8 directions of a
           model are lit identically (classic pre-rendered-sprite workflow).
  world  : lights stay fixed in world space; the shading direction changes per
           facing (sun-consistent, e.g. for buildings on a map).

Engines:
  auto      : EEVEE (handles 4.0/4.1 'BLENDER_EEVEE', 4.2-4.4 'BLENDER_EEVEE_NEXT',
              4.5+ 'BLENDER_EEVEE'), falling back to Cycles if unavailable.
  cycles    : CPU-safe; use on headless boxes with no GPU (EEVEE/Workbench need a
              GPU context even in --background).
  workbench : flat texture shading, ignores normals/lights; fastest, most
              "sprite-like", but ignores node-based multi-texture materials.
"""

import argparse
import importlib.util
import math
import sys
import traceback
from math import radians
from pathlib import Path

import bpy
from mathutils import Euler, Vector

MODEL_EXTS = {".glb", ".gltf", ".obj", ".json"}

# Camera X rotation per style (Blender camera at rotation 0 looks straight down -Z;
# rotation_euler.x tilts it up toward the horizon).
STYLE_X_ROT = {
    "isometric": math.degrees(math.atan(math.sqrt(2.0))),  # 54.7356 -> 35.264 elevation
    "dimetric": 60.0,                                      # 30 deg elevation, 2:1 pixel ratio
}


# --------------------------------------------------------------------------- args
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="render_isometric")
    p.add_argument("--input", required=True, help="folder scanned recursively for models")
    p.add_argument("--output", required=True, help="output root (input subtree is mirrored)")
    p.add_argument("--res", type=int, default=512, help="square render resolution in px")
    p.add_argument("--style", choices=list(STYLE_X_ROT), default="dimetric")
    p.add_argument("--directions", type=int, default=1, choices=[1, 2, 4, 8],
                   help="number of azimuth steps (8 = classic 8-way sprite)")
    p.add_argument("--base-azimuth", type=float, default=45.0,
                   help="azimuth (deg) of the first direction")
    p.add_argument("--margin", type=float, default=1.08,
                   help="empty border factor around the fitted bounding box")
    p.add_argument("--engine", choices=["auto", "cycles", "workbench"], default="auto")
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--normalize", choices=["per-model", "global"], default="per-model")
    p.add_argument("--global-scale", type=float, default=10.0,
                   help="ortho_scale (world units across frame) when --normalize global")
    p.add_argument("--light-mode", choices=["camera", "world"], default="camera")
    p.add_argument("--fix-normals", action="store_true",
                   help="recalculate consistent outward normals on all imported meshes")
    p.add_argument("--obj-up", choices=["Y", "Z"], default="Y",
                   help="up axis used by the .obj files (game exports are usually Y-up)")
    p.add_argument("--gwmb-addon", default="",
                   help="path to GWMB's model_import_addon/import_model.py (enables .json input)")
    p.add_argument("--overwrite", action="store_true", help="re-render existing PNGs")
    p.add_argument("--limit", type=int, default=0, help="stop after N models (smoke tests)")
    p.add_argument("--files", default="",
                   help="text file with one model path per line (overrides --input scan; "
                        "--input is still used as the root for mirroring output paths)")
    p.add_argument("--bloom", action="store_true",
                   help="compositor bloom/glare pass (glowing textures radiate)")
    p.add_argument("--bloom-threshold", type=float, default=1.0,
                   help="luminance above which pixels bloom")
    p.add_argument("--bloom-strength", type=float, default=1.0)
    return p.parse_args(argv)


# --------------------------------------------------------------------- scene setup
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(scene, args):
    scene.render.resolution_x = args.res
    scene.render.resolution_y = args.res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.filter_size = 1.0          # crisper sprite edges than the 1.5 default
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    # Game-accurate colors: AgX/Filmic tone mapping desaturates diffuse textures.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    if args.bloom:
        scene.use_nodes = True
        tree = scene.node_tree
        tree.nodes.clear()
        rl = tree.nodes.new("CompositorNodeRLayers")
        glare = tree.nodes.new("CompositorNodeGlare")
        try:
            glare.glare_type = "BLOOM"          # Blender 4.4+
        except TypeError:
            glare.glare_type = "FOG_GLOW"       # closest equivalent on older 4.x
        glare.quality = "HIGH"
        glare.threshold = args.bloom_threshold
        if hasattr(glare, "strength"):
            glare.strength = args.bloom_strength
        elif hasattr(glare, "mix"):
            glare.mix = min(1.0, args.bloom_strength) - 1.0
        out = tree.nodes.new("CompositorNodeComposite")
        tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
        tree.links.new(glare.outputs["Image"], out.inputs["Image"])
        if "Alpha" in out.inputs:  # removed in Blender 4.5 (alpha travels with Image)
            tree.links.new(rl.outputs["Alpha"], out.inputs["Alpha"])

    if args.engine == "workbench":
        scene.render.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading
        sh.light = "FLAT"
        sh.color_type = "TEXTURE"
        sh.show_backface_culling = False
        scene.display.render_aa = "8"
        return
    if args.engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
        scene.cycles.transparent_max_bounces = 16   # stacked foliage alpha
        return
    # auto: EEVEE under its 4.x-version-dependent id, else Cycles.
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    if scene.render.engine.startswith("BLENDER_EEVEE"):
        try:
            scene.eevee.taa_render_samples = args.samples
        except AttributeError:
            pass
    elif scene.render.engine == "CYCLES":
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True


def make_world(scene, strength=0.22):
    world = bpy.data.worlds.new("SpriteWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        bg.inputs[1].default_value = strength   # flat ambient fill; film stays transparent
    scene.world = world


def make_camera(scene):
    cam_data = bpy.data.cameras.new("SpriteCam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("SpriteCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def make_sun(scene, name, energy, x_deg, use_shadow=True, angle_deg=3.0):
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.angle = radians(angle_deg)
    data.use_shadow = use_shadow
    try:
        data.cycles.cast_shadow = use_shadow
    except AttributeError:
        pass
    obj = bpy.data.objects.new(name, data)
    obj.rotation_euler = Euler((radians(x_deg), 0.0, 0.0), "XYZ")
    scene.collection.objects.link(obj)
    return obj


def build_light_rig(scene):
    """3-point sun rig. Z rotation (azimuth) is set per shot by aim_lights()."""
    key = make_sun(scene, "Key", energy=2.2, x_deg=45, use_shadow=True)
    fill = make_sun(scene, "Fill", energy=0.7, x_deg=70, use_shadow=False)
    rim = make_sun(scene, "Rim", energy=1.1, x_deg=60, use_shadow=False)
    return key, fill, rim


def aim_lights(rig, cam_az_deg):
    key, fill, rim = rig
    key.rotation_euler.z = radians(cam_az_deg - 40)    # upper-left of camera
    fill.rotation_euler.z = radians(cam_az_deg + 60)   # soft right fill
    rim.rotation_euler.z = radians(cam_az_deg + 180)   # back edge separation


# ------------------------------------------------------------------------- import
_gwmb_module = None


def load_gwmb_module(path):
    global _gwmb_module
    if _gwmb_module is None:
        spec = importlib.util.spec_from_file_location("gwmb_import_model", path)
        _gwmb_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_gwmb_module)
    return _gwmb_module


def import_model(path: Path, args):
    """Import one model file; return the list of newly created objects."""
    before = set(bpy.data.objects)
    ext = path.suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path),
                              up_axis=args.obj_up,
                              forward_axis="NEGATIVE_Z")
    elif ext == ".json":
        if not args.gwmb_addon:
            raise RuntimeError(".json input needs --gwmb-addon /path/to/import_model.py")
        # Call the GWMB addon's import function directly; this bypasses bl_info
        # version gating (the shipped addon declares Blender 5.0 minimum).
        mod = load_gwmb_module(args.gwmb_addon)
        mod.create_mesh_from_json(bpy.context, str(path.parent), path.name)
    else:
        raise ValueError(f"unsupported extension: {ext}")
    return [o for o in bpy.data.objects if o not in before]


# --------------------------------------------------------------------- mesh fixes
def fix_materials(objs):
    for obj in objs:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            mat.use_backface_culling = False        # game meshes: inconsistent winding
            # EEVEE Next (4.2+): per-material render method replaces blend_method.
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "DITHERED"
            # Legacy EEVEE (4.0/4.1): hard alpha clip avoids depth-sorting artifacts.
            try:
                if getattr(mat, "blend_method", None) == "BLEND":
                    mat.blend_method = "CLIP"
            except TypeError:
                pass
            try:
                mat.shadow_method = "CLIP"          # removed in 4.2+, harmless before
            except (AttributeError, TypeError):
                pass
            wire_obj_alpha(mat)


def wire_obj_alpha(mat):
    """OBJ/MTL imports often leave texture alpha unconnected. If the Base Color
    image has an alpha channel and Principled Alpha is unlinked, link it."""
    if not mat.use_nodes:
        return
    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if principled is None:
        return
    alpha_in = principled.inputs.get("Alpha")
    base_in = principled.inputs.get("Base Color")
    if alpha_in is None or alpha_in.is_linked or base_in is None or not base_in.is_linked:
        return
    src = base_in.links[0].from_node
    if src.type == "TEX_IMAGE" and src.image and src.image.depth in (32, 64, 128):
        nt.links.new(src.outputs["Alpha"], alpha_in)


def recalc_normals(objs):
    meshes = [o for o in objs if o.type == "MESH"]
    if not meshes:
        return
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


# ------------------------------------------------------------------ framing math
def world_bbox(objs):
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts.extend(o.matrix_world @ Vector(c) for c in o.bound_box)
    if not pts:
        return None
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi, pts


def required_ortho_scale(rot: Euler, center: Vector, pts, margin: float):
    """Smallest ortho_scale (square sensor/render) that contains all pts when the
    camera has rotation `rot` and looks at `center`. Ortho projection: extent of
    the points in camera-local X/Y."""
    r_inv = rot.to_matrix().transposed()    # world -> camera-local
    half_w = half_h = 0.0
    for p in pts:
        q = r_inv @ (p - center)
        half_w = max(half_w, abs(q.x))
        half_h = max(half_h, abs(q.y))
    return 2.0 * max(half_w, half_h) * margin


def place_camera(cam, center, diag, az_deg, x_rot_deg, ortho_scale):
    rot = Euler((radians(x_rot_deg), 0.0, radians(az_deg)), "XYZ")
    cam.rotation_euler = rot
    direction = rot.to_matrix() @ Vector((0.0, 0.0, 1.0))   # camera local +Z, world space
    dist = diag * 2.0 + 1.0
    cam.location = center + direction * dist
    cam.data.ortho_scale = ortho_scale
    cam.data.clip_start = max(0.001, dist - diag * 1.5)
    cam.data.clip_end = dist + diag * 1.5


# --------------------------------------------------------------------------- main
def render_one(path: Path, out_dir: Path, args):
    reset_scene()
    scene = bpy.context.scene
    setup_render(scene, args)
    make_world(scene)
    cam = make_camera(scene)
    rig = build_light_rig(scene)

    objs = import_model(path, args)
    if args.fix_normals:
        recalc_normals(objs)
    fix_materials(objs)

    bbox = world_bbox(objs)
    if bbox is None:
        raise RuntimeError("no mesh objects after import")
    lo, hi, pts = bbox
    center = (lo + hi) * 0.5
    diag = (hi - lo).length
    if diag <= 1e-8:
        raise RuntimeError("degenerate (zero-size) bounding box")

    x_rot = STYLE_X_ROT[args.style]
    step = 360.0 / args.directions
    azimuths = [args.base_azimuth + i * step for i in range(args.directions)]

    if args.normalize == "global":
        ortho = args.global_scale
    else:
        # One scale for ALL directions of this model, or sprite size pops between facings.
        ortho = max(
            required_ortho_scale(Euler((radians(x_rot), 0, radians(az)), "XYZ"),
                                 center, pts, args.margin)
            for az in azimuths
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    world_light_az = args.base_azimuth
    for i, az in enumerate(azimuths):
        suffix = "" if args.directions == 1 else f"_d{i}"
        out_file = out_dir / f"{path.stem}{suffix}.png"
        if out_file.exists() and not args.overwrite:
            continue
        place_camera(cam, center, diag, az, x_rot, ortho)
        aim_lights(rig, az if args.light_mode == "camera" else world_light_az)
        scene.render.filepath = str(out_file)
        bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    in_root = Path(args.input).resolve()
    out_root = Path(args.output).resolve()
    if args.files:
        files = [Path(line.strip()) for line in Path(args.files).read_text().splitlines()
                 if line.strip()]
    else:
        files = sorted(p for p in in_root.rglob("*")
                       if p.suffix.lower() in MODEL_EXTS and p.is_file())
    if args.limit:
        files = files[: args.limit]
    print(f"[iso] {len(files)} model files under {in_root}")

    failures = []
    for n, path in enumerate(files, 1):
        rel = path.parent.relative_to(in_root)
        print(f"[iso] ({n}/{len(files)}) {path.name}")
        try:
            render_one(path, out_root / rel, args)
        except Exception as exc:
            failures.append((str(path), repr(exc)))
            traceback.print_exc()

    print(f"[iso] done. {len(files) - len(failures)} ok, {len(failures)} failed")
    for f, e in failures:
        print(f"[iso] FAILED {f}: {e}")


if __name__ == "__main__":
    main()
