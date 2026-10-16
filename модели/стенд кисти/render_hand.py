"""Фотореалистичный рендер стенда кисти в Blender (Cycles).
Сначала: python export_render_parts.py   (части сборки → render_parts/)
Потом:   blender --background --python render_hand.py
Результат: «рендер кисти.png» в этой папке."""
import os, math
import bpy
from mathutils import Vector

HERE = os.environ.get("HARVEY_HAND_DIR") or os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "render_parts")
OUT = os.path.join(HERE, "рендер кисти.png")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"


def mat(name, color, rough=0.45, metal=0.0, coat=0.0, sss=0.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    if "Subsurface Weight" in b.inputs: b.inputs["Subsurface Weight"].default_value = sss
    if "Transmission Weight" in b.inputs: b.inputs["Transmission Weight"].default_value = transmission
    return m


def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


M = {
    "petg_orange": mat("PETG оранжевый", srgb("#E05A1C"), rough=0.32, coat=0.12),
    "petg_grey": mat("PETG графит", srgb("#3A3F45"), rough=0.38, coat=0.1),
    "tpu": mat("TPU чёрный", srgb("#151515"), rough=0.8),
    "alu_dark": mat("Алюминий анодированный", srgb("#2B2D31"), rough=0.35, metal=1.0),
    "alu_horn": mat("Алюминий качалки", srgb("#C9CCD1"), rough=0.22, metal=1.0),
}
ASSIGN = {"stand": "petg_grey", "palm": "petg_orange", "jaw": "petg_orange", "pad_low": "tpu", "pad_up": "tpu",
          "servo21_case": "alu_dark", "servo22_case": "alu_dark", "servo21_horns": "alu_horn", "servo22_horns": "alu_horn"}

objs = []
for name, mname in ASSIGN.items():
    bpy.ops.wm.stl_import(filepath=os.path.join(PARTS, name + ".stl"), global_scale=0.001)
    o = bpy.context.selected_objects[0]
    o.name = name
    o.data.materials.append(M[mname])
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    if name.endswith("_case"):                                    # корпус привода — с фаской, как настоящий
        bev = o.modifiers.new("Фаска", "BEVEL"); bev.width = 0.0008; bev.segments = 3; bev.limit_method = "ANGLE"
    objs.append(o)

# стол: светлый матовый фон-циклорама
bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.05, 0, 0))
floor = bpy.context.active_object
floor.data.materials.append(mat("Стол", srgb("#E9E6E1"), rough=0.6))
bpy.ops.mesh.primitive_plane_add(size=2.0, location=(-0.35, 0, 0.4), rotation=(0, math.radians(90), 0))
wall = bpy.context.active_object
wall.data.materials.append(mat("Фон", srgb("#E9E6E1"), rough=0.7))

# свет: студийный — большой софтбокс, контровой и заполняющий
def area(name, loc, size, energy, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.active_object; l.name = name
    l.data.size = size; l.data.energy = energy; l.data.color = color
    d = Vector((0.045, 0, 0.035)) - l.location
    l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l

area("Ключевой", (0.25, -0.30, 0.35), 0.35, 14)
area("Заполняющий", (-0.10, -0.35, 0.12), 0.40, 4, (0.92, 0.95, 1.0))
area("Контровой", (0.05, 0.35, 0.30), 0.20, 9, (1.0, 0.95, 0.9))
scene.world = bpy.data.worlds.new("Мир")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.8, 0.82, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08

# камера: три четверти спереди-сбоку, вся сборка в кадре, фокус на кисти
bpy.ops.object.camera_add(location=(0.27, -0.25, 0.17))
cam = bpy.context.active_object
target = Vector((0.026, 0.004, 0.033))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 95
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = (Vector((0.05, 0, 0.035)) - cam.location).length
cam.data.dof.aperture_fstop = 16
scene.camera = cam

scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.refresh_devices() if hasattr(prefs, "refresh_devices") else prefs.get_devices()
    for dev_type in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = dev_type
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices: d.use = True
                scene.cycles.device = "GPU"; break
        except TypeError:
            continue
except Exception as e:
    print("GPU не найден, считаю на процессоре:", e)
scene.cycles.samples = 160
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1920, 1200
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -1.0
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("Рендер:", OUT, "устройство:", scene.cycles.device)
