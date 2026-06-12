"""Import several GWMB model-part JSONs into ONE scene and render isometric views.

For multi-part GW1 models (NPCs split into head/torso/arms/legs files) whose parts
are modeled in a shared model space — importing them together reassembles the figure.

Usage:
  blender --background --factory-startup --python combine_render.py -- \
      --files parts.txt --gwmb-addon import_model.py --output outdir \
      [--name combined] [--res 512] [--samples 48] [--azimuths 135,225,45,315]
"""
import argparse
import importlib.util
import math
import sys

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--files", required=True)
    p.add_argument("--gwmb-addon", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--name", default="combined")
    p.add_argument("--res", type=int, default=512)
    p.add_argument("--samples", type=int, default=48)
    p.add_argument("--elevation", type=float, default=60.0, help="camera X rotation (60=2:1 dimetric)")
    p.add_argument("--azimuths", default="135,225,45,315")
    return p.parse_args(argv)


def main():
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    spec = importlib.util.spec_from_file_location("gwmb_model", args.gwmb_addon)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import os
    files = [l.strip() for l in open(args.files) if l.strip()]
    for f in files:
        mod.create_mesh_from_json(bpy.context, os.path.dirname(f), os.path.basename(f))

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("no meshes imported")
    print(f"[combine] {len(meshes)} mesh objects from {len(files)} part files")

    for mat in bpy.data.materials:
        mat.use_backface_culling = False
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"

    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector((min(p[i] for p in pts) for i in range(3)))
    hi = Vector((max(p[i] for p in pts) for i in range(3)))
    center = (lo + hi) / 2
    diag = (hi - lo).length

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = args.res
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.render.filter_size = 1.0

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    elev = math.radians(args.elevation)
    azimuths = [float(a) for a in args.azimuths.split(",")]

    # fit ortho scale across all azimuths so size is constant
    ortho = 0.0
    for az in azimuths:
        rot = (elev, 0.0, math.radians(az))
        cam.rotation_euler = rot
        bpy.context.view_layer.update()
        m = cam.rotation_euler.to_matrix().transposed()
        for p in pts:
            q = m @ (p - center)
            ortho = max(ortho, 2.05 * abs(q.x), 2.05 * abs(q.y))
    cam_data.ortho_scale = ortho
    dist = 2.0 * diag
    cam_data.clip_start = max(0.01, dist - 2 * diag)
    cam_data.clip_end = dist + 2 * diag

    def add_sun(name, az_deg, elev_deg, energy, shadow):
        light = bpy.data.lights.new(name, "SUN")
        light.energy = energy
        light.use_shadow = shadow
        light.angle = math.radians(3)
        ob = bpy.data.objects.new(name, light)
        scene.collection.objects.link(ob)
        ob.rotation_euler = (math.radians(90 - elev_deg), 0, math.radians(az_deg))
        return ob

    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 0.22

    suns = []
    import os
    os.makedirs(args.output, exist_ok=True)
    for d, az in enumerate(azimuths):
        cam.rotation_euler = (elev, 0.0, math.radians(az))
        bpy.context.view_layer.update()
        direction = cam.rotation_euler.to_matrix() @ Vector((0, 0, 1))
        cam.location = center + direction * dist
        for s in suns:
            bpy.data.objects.remove(s, do_unlink=True)
        suns = [
            add_sun("key", az + 35, 50, 2.2, True),
            add_sun("fill", az - 50, 25, 0.7, False),
            add_sun("rim", az + 180, 35, 1.1, False),
        ]
        scene.render.filepath = os.path.join(args.output, f"{args.name}_d{d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[combine] saved {scene.render.filepath}")


main()
