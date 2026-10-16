"""Фотореалистичный рендер обеих клешней на подставках (Blender, Cycles).
Сначала: python export_render_parts.py; потом: blender --background --python render_claws.py"""
import os, math
import bpy
from mathutils import Vector

HERE = os.environ.get("HARVEY_CLAW_DIR") or os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "render_parts")
OUT = os.path.join(HERE, "рендер клешней.png")
FLOOR = -0.1163

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mat(name, color, rough=0.45, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    return m


M = {"petg_orange": mat("PETG оранжевый", srgb("#E05A1C"), 0.32, 0, 0.12),
     "petg_grey": mat("PETG графит", srgb("#3A3F45"), 0.38, 0, 0.1),
     "case": mat("Корпуса приводов", srgb("#1E1F22"), 0.4, 0.6),
     "metal": mat("Фланцы и качалки", srgb("#C9CCD1"), 0.22, 1.0),
     "tpu": mat("TPU", srgb("#151515"), 0.8)}
for name in M:
    bpy.ops.wm.stl_import(filepath=os.path.join(PARTS, name + ".stl"), global_scale=0.001)
    o = bpy.context.selected_objects[0]; o.name = name
    o.data.materials.append(M[name])
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    if name == "case":
        bev = o.modifiers.new("Фаска", "BEVEL"); bev.width = 0.0008; bev.segments = 3; bev.limit_method = "ANGLE"

bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0, 0, FLOOR))
bpy.context.active_object.data.materials.append(mat("Стол", srgb("#E9E6E1"), 0.6))
bpy.ops.mesh.primitive_plane_add(size=3.0, location=(-0.45, 0, FLOOR + 0.5), rotation=(0, math.radians(90), 0))
bpy.context.active_object.data.materials.append(mat("Фон", srgb("#E9E6E1"), 0.7))

target = Vector((0.02, 0.0, 0.004))


def area(name, loc, size, energy, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.active_object; l.name = name
    l.data.size = size; l.data.energy = energy; l.data.color = color
    l.rotation_euler = (target - l.location).to_track_quat("-Z", "Y").to_euler()


area("Ключевой", (0.45, -0.45, 0.45), 0.5, 40)
area("Заполняющий", (-0.10, -0.55, 0.10), 0.6, 12, (0.92, 0.95, 1.0))
area("Контровой", (0.10, 0.50, 0.40), 0.3, 25, (1.0, 0.95, 0.9))
scene.world = bpy.data.worlds.new("Мир"); scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.8, 0.82, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08

bpy.ops.object.camera_add(location=(0.80, -0.62, 0.36))
cam = bpy.context.active_object
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 68
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (target - cam.location).length; cam.data.dof.aperture_fstop = 16
scene.camera = cam

scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.refresh_devices() if hasattr(prefs, "refresh_devices") else prefs.get_devices()
    for t in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = t
            if any(d.type == t for d in prefs.devices):
                for d in prefs.devices: d.use = True
                scene.cycles.device = "GPU"; break
        except TypeError:
            continue
except Exception as e:
    print("GPU не найден:", e)
scene.cycles.samples = 160; scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1920, 1200
scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -1.0
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("Рендер:", OUT)
