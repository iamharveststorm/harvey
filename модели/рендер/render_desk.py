"""Харви на уютном рабочем столе — фотореалистичные рендеры (Blender 5.2, Cycles), 3 ракурса × 2 варианта корпуса.
Всё в реальном масштабе 1 : 1: стол 1,6 × 1,0 м, предметы Poly Haven — в своих размерах (проверено: лист A4 210 × 290,
ручки 131–161, карандаш 194, зажигалка 39 × 53, стакан Ø84 мм), лежат на столе или друг на друге, не пересекаются.
Сначала: python export_robot.py  (детали по материалам в parts/)
«Компакт мини»: модели/мини/export_render.py (parts_mini/), затем HARVEY_ROBOT=mini — кадры Мини_1…3.png.
Потом:   render_desk.bat  (или blender --background --python render_desk.py с переменной HARVEY_RENDER_DIR)
Переменные: HARVEY_VARIANTS=tech,soft  HARVEY_VIEWS=1,2,3  HARVEY_SAMPLES=256  HARVEY_RES=1920
Ресурсы Poly Haven (CC0): C:/harvey-assets/polyhaven — HDRI lythwood_room, дуб oak_veneer_01, модели реквизита."""
import os, math, json
import bpy
from mathutils import Vector, Matrix, Euler

D = os.environ.get("HARVEY_RENDER_DIR") or os.path.dirname(os.path.abspath(__file__))
A = os.environ.get("HARVEY_ASSETS", "C:/harvey-assets/polyhaven")
VARIANTS = os.environ.get("HARVEY_VARIANTS", "tech,soft").split(",")
VIEWS = os.environ.get("HARVEY_VIEWS", "1,2,3").split(",")
SAMPLES = int(os.environ.get("HARVEY_SAMPLES", "256"))
RES = int(os.environ.get("HARVEY_RES", "1920"))
ROBOT_KIND = os.environ.get("HARVEY_ROBOT", "kompakt")
MINI = ROBOT_KIND == "mini"
PARTS = "parts_mini" if MINI else "parts"
if MINI and "HARVEY_VARIANTS" not in os.environ:
    VARIANTS = ["tech"]
META = json.load(open(os.path.join(D, PARTS, "scene.json"), encoding="utf-8"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"


# ---------------- материалы ----------------
def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mat(name, color, rough=0.45, metal=0.0, coat=0.0, trans=0.0, ior=1.45, sss=0.0, emit=None, emit_k=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key, val in (("Coat Weight", coat), ("Transmission Weight", trans), ("IOR", ior), ("Subsurface Weight", sss)):
        if key in b.inputs: b.inputs[key].default_value = val
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_k
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def image_mat(name, path, emit_k=0.0, rough=0.3, base=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(path)
    if base: nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    if emit_k > 0:
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = emit_k
    b.inputs["Roughness"].default_value = rough
    return m


M = {
    "orange": mat("PETG оранжевый", srgb("#E2581B"), 0.34, 0, 0.15, sss=0.03),
    "grey": mat("PETG графит", srgb("#33383E"), 0.42, 0, 0.08),
    "case": mat("Корпуса приводов", srgb("#16171A"), 0.5, 0.0, 0.05),
    "metal": mat("Алюминий фланцев", srgb("#BFC3C8"), 0.25, 1.0),
    "tpu": mat("TPU", srgb("#121212"), 0.78),
    "silicone": mat("Присоска", srgb("#C9CED3"), 0.35, trans=0.6, ior=1.4),
    "glass": mat("Линза ПК", srgb("#F2F6F8"), 0.02, trans=1.0, ior=1.58),
    "pcb": mat("Платы", srgb("#1F5E3A"), 0.4, 0.1),
    "battery": mat("Банки 21700", srgb("#1E6F8A"), 0.3, 0.0, 0.3),
    "dark": mat("Электроника", srgb("#202224"), 0.5),
    "red": mat("Кнопка стоп", srgb("#D21F1F"), 0.3, 0, 0.2),
    "shell": mat("Панцирь — графит soft-touch", srgb("#2B2F35"), 0.55, 0, 0.35),
}

# ---------------- мир: комната (HDRI) ----------------
w = bpy.data.worlds.new("Комната"); scene.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(f"{A}/hdri/lythwood_room_4k.hdr")
mp = nt.nodes.new("ShaderNodeMapping"); tc = nt.nodes.new("ShaderNodeTexCoord")
nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
mp.inputs["Rotation"].default_value = (0, 0, math.radians(200))
bg.inputs["Strength"].default_value = 0.55

# ---------------- стол (дуб) ----------------
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.08, 0.05, -0.016))
desk = bpy.context.active_object; desk.name = "Стол"; desk.scale = (1.0, 1.6, 0.032)
bpy.ops.object.transform_apply(scale=True)
bev = desk.modifiers.new("Фаска", "BEVEL"); bev.width = 0.003; bev.segments = 3
oak = bpy.data.materials.new("Дуб"); oak.use_nodes = True
nt = oak.node_tree; b = nt.nodes["Principled BSDF"]
tcn = nt.nodes.new("ShaderNodeTexCoord"); mpn = nt.nodes.new("ShaderNodeMapping"); mpn.inputs["Scale"].default_value = (1.4, 1.4, 1.4)
nt.links.new(tcn.outputs["Object"], mpn.inputs["Vector"])
for kind in ("Diffuse", "Rough", "nor_gl"):
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(f"{A}/textures/oak_veneer_01/oak_veneer_01_{kind}_2k.jpg")
    t.projection = "BOX"; t.projection_blend = 0.2
    nt.links.new(mpn.outputs["Vector"], t.inputs["Vector"])
    if kind == "Diffuse":
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        t.image.colorspace_settings.name = "Non-Color"
        if kind == "Rough":
            mr = nt.nodes.new("ShaderNodeMath"); mr.operation = "MULTIPLY"; mr.inputs[1].default_value = 0.85
            nt.links.new(t.outputs["Color"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
        else:
            nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.6
            nt.links.new(t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 0.25
desk.data.materials.append(oak)

# ---------------- Харви ----------------
rig = bpy.data.objects.new("Харви", None); scene.collection.objects.link(rig)
ROBOT = {}
for variant in ("tech", "soft"):
    if not os.path.isdir(os.path.join(D, PARTS, variant)):
        continue
    for f in sorted(os.listdir(os.path.join(D, PARTS, variant))):
        key = f[:-4]
        if variant == "soft" and key != "shell":
            continue
        bpy.ops.wm.stl_import(filepath=os.path.join(D, PARTS, variant, f), global_scale=0.001)
        o = bpy.context.selected_objects[0]; o.name = f"{variant}_{key}"
        o.data.materials.append(M[key])
        bpy.ops.object.shade_auto_smooth(angle=math.radians(32))
        if key == "case":
            bv = o.modifiers.new("Фаска", "BEVEL"); bv.width = 0.0007; bv.segments = 2; bv.limit_method = "ANGLE"
        if key == "shell":
            sub = o.modifiers.new("Сглаживание", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
        o.parent = rig
        ROBOT[(variant, key)] = o
for s in ("L", "R"):                             # экраны глаз
    sc = META["screens"][s]
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=sc["radius"] * 0.001, fill_type="NGON")
    o = bpy.context.active_object; o.name = f"экран_{s}"
    n = Vector(sc["normal"]).normalized(); up = Vector(sc["up"]).normalized()
    xax = up.cross(n).normalized()
    R = Matrix((xax, up, n)).transposed().to_4x4()
    o.matrix_world = Matrix.Translation(Vector(sc["center"]) * 0.001) @ R
    me = o.data; uv = me.uv_layers.new(name="UV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (0.5 + v.x / (2 * sc["radius"] * 0.001), 0.5 + v.y / (2 * sc["radius"] * 0.001))
    o.data.materials.append(image_mat(f"Глаз {s}", os.path.join(D, "tex", f"eye_{s}.png"), emit_k=2.2, rough=0.15))
    o.parent = rig
rig.rotation_euler = (0, 0, math.radians(14 if not MINI else 18)); rig.location = (0.02, 0.0, 0.0) if not MINI else (0.04, -0.03, 0.0)


# ---------------- реквизит Poly Haven ----------------
def import_gltf(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f"{A}/models/{name}/{name}_2k.gltf")
    return [o for o in bpy.data.objects if o not in before]


def bbox(objs):
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH": continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
    return mn, mx


def place(objs, xy, yaw=0.0, scale=1.0, z=0.0, name="группа"):
    """Группа объектов: центр по низу — в точку (x, y, z), поворот вокруг вертикали, масштаб."""
    root = bpy.data.objects.new(name, None); scene.collection.objects.link(root)
    mn, mx = bbox(objs); c = (mn + mx) / 2
    for o in objs:
        if o.parent is None:
            o.parent = root; o.matrix_parent_inverse = Matrix.Translation(-Vector((c.x, c.y, mn.z)))
    root.scale = (scale,) * 3; root.rotation_euler = (0, 0, math.radians(yaw)); root.location = (xy[0], xy[1], z)
    bpy.context.view_layer.update()
    return root


def keep(objs, names):
    k = []
    for o in objs:
        if o.type == "MESH" and not any(n in o.name for n in names):
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            k.append(o)
    return [o for o in k if o.name in bpy.data.objects]


note = import_gltf("office_notepads")
pad = keep([o for o in note], ["a4_stack", "yellow_pad", "sticky_stack"])
notes = {n: [o for o in pad if n in o.name] for n in ("a4_stack", "yellow_pad", "sticky_stack")}
place(notes["a4_stack"], (-0.22, 0.32), 15, name="стопка A4")
place(notes["yellow_pad"], (0.11, 0.44), -10, name="жёлтый блокнот")
place(notes["sticky_stack"], (0.31, 0.24), 25, name="стикеры")
st = import_gltf("stationery_supplies")
_drop = [o for o in st if o.type == "MESH" and any(n in o.name for n in ("pencil_new_b", "pencil_old"))]
st = [o for o in st if o not in _drop]
for o in _drop:                                                    # лишние карандаши набора — убрать
    bpy.data.objects.remove(o, do_unlink=True)
CUP = (-0.40, 0.58)
cup = [o for o in st if "pencilcup" in o.name]
place(cup, CUP, 0, name="стакан")
pens = {n: [o for o in st if n in o.name] for n in ("pen_blue", "pen_red", "pen_fancy", "pencil_new_a", "pencil_used", "eraser")}
place(pens["pen_blue"], (-0.22, 0.31), 70, z=0.010, name="синяя ручка")      # лежит на стопке A4 (высота 10 мм)
place(pens["pen_red"], (0.11, 0.43), 40, z=0.010, name="красная ручка")      # на жёлтом блокноте (10 мм)
place(pens["pen_fancy"], (0.29, 0.07), -35, name="ручка")                      # на столе
for i, (n, tilt, yaw) in enumerate((("pencil_new_a", 9, 40), ("pencil_used", 12, 200))):   # карандаши в стакане:
    r = place(pens[n], (0, 0), 0, name=f"карандаш {i + 1}")        # низ — на дне стакана (6 мм), наклон к стенке
    L = bbox(pens[n])[1].x - bbox(pens[n])[0].x
    t, y_ = math.radians(tilt), math.radians(yaw)
    u = Vector((math.sin(t) * math.cos(y_), math.sin(t) * math.sin(y_), math.cos(t)))
    lower = Vector((CUP[0] + 0.012 * math.cos(y_ + math.pi), CUP[1] + 0.012 * math.sin(y_ + math.pi), 0.006))
    r.rotation_euler = (0, math.radians(-(90 - tilt)), y_); r.location = lower + u * (L / 2)
place(pens["eraser"], (0.03, 0.21), 15, name="ластик")
place(import_gltf("vintage_lighter"), (0.31, -0.07), 120, name="зажигалка")
place(import_gltf("round_spectacles"), (-0.12, -0.38), 160, name="очки")
place(import_gltf("standing_picture_frame_01"), (-0.44, -0.36), 35, name="рамка")
# potted_plant_02 — напольное растение (горшок Ø47 см, высота 63 см): на стол в реальном масштабе не помещается — убрано
lamp = place(import_gltf("desk_lamp_arm_01"), (-0.50, 0.78), -130, name="лампа")   # лампа на кронштейне, 89 см — как есть


# ---------------- телефон, наушники, кружка (свои модели) ----------------
def rbox(name, size, loc, r, material, segs=6):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    b_ = o.modifiers.new("Скругление", "BEVEL"); b_.width = r; b_.segments = segs
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


phone = bpy.data.objects.new("телефон", None); scene.collection.objects.link(phone)
alu = mat("Рамка телефона", srgb("#2A2C30"), 0.3, 1.0)
glass_dark = mat("Стекло телефона", srgb("#050608"), 0.05, 0, 0.6)
p1 = rbox("корпус телефона", (0.0715, 0.147, 0.0078), (0, 0, 0.0039), 0.006, alu); p1.parent = phone
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.00785))
scr = bpy.context.active_object; scr.scale = (0.066, 0.141, 1); bpy.ops.object.transform_apply(scale=True)
scr.data.materials.append(image_mat("Экран телефона", os.path.join(D, "tex", "phone_wall.png"), emit_k=0.9, rough=0.05))
scr.parent = phone
phone.location = (0.25, -0.44, 0); phone.rotation_euler = (0, 0, math.radians(-28 + 90))

acryl = mat("Прозрачный кейс", srgb("#F4F6F8"), 0.04, 0, 0, trans=1.0, ior=1.49)
white = mat("Белый пластик", srgb("#EDEDEB"), 0.35)
red = mat("Красная точка", srgb("#E2231A"), 0.3)
buds = bpy.data.objects.new("наушники в кейсе", None); scene.collection.objects.link(buds)
c1 = rbox("кейс", (0.0555, 0.0555, 0.022), (0, 0, 0.011), 0.008, acryl, 8); c1.parent = buds
bpy.context.view_layer.objects.active = c1; bpy.ops.object.modifier_apply(modifier="Скругление")
sol = c1.modifiers.new("Стенка", "SOLIDIFY"); sol.thickness = 0.0016; sol.offset = -1     # тонкостенный прозрачный корпус
c2 = rbox("вкладыш кейса", (0.046, 0.046, 0.009), (0, 0, 0.0055), 0.005, white, 4); c2.parent = buds
for sy in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0065, location=(0.006, sy * 0.011, 0.0135))
    h = bpy.context.active_object; h.scale = (1.0, 0.85, 0.7); h.data.materials.append(acryl); bpy.ops.object.shade_smooth(); h.parent = buds
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0032, depth=0.026, location=(-0.010, sy * 0.011, 0.0115), rotation=(0, math.radians(90), 0))
    s_ = bpy.context.active_object; s_.data.materials.append(white); bpy.ops.object.shade_smooth(); s_.parent = buds
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0022, depth=0.003, location=(0.004, sy * 0.011, 0.0175))
    d_ = bpy.context.active_object; d_.data.materials.append(white); d_.parent = buds
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0012, location=(0.0255, 0.0, 0.0175))
rd = bpy.context.active_object; rd.data.materials.append(red); rd.parent = buds
buds.location = (0.26, -0.22, 0); buds.rotation_euler = (0, 0, math.radians(18))

cer = mat("Керамика", srgb("#EDE4D3"), 0.25, 0, 0.3)
coffee = mat("Кофе", srgb("#2B160B"), 0.08)
bpy.ops.mesh.primitive_cylinder_add(radius=0.041, depth=0.092, location=(0, 0, 0.046), vertices=64)
mug = bpy.context.active_object; mug.name = "кружка"
bpy.ops.mesh.primitive_cylinder_add(radius=0.0365, depth=0.09, location=(0, 0, 0.052), vertices=64)
inner = bpy.context.active_object
bo = mug.modifiers.new("Полость", "BOOLEAN"); bo.object = inner; bo.operation = "DIFFERENCE"
bpy.context.view_layer.objects.active = mug; bpy.ops.object.modifier_apply(modifier=bo.name)
bpy.data.objects.remove(inner, do_unlink=True)
bv = mug.modifiers.new("Фаска", "BEVEL"); bv.width = 0.0015; bv.segments = 3
mug.data.materials.append(cer); bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
bpy.ops.mesh.primitive_torus_add(major_radius=0.022, minor_radius=0.0055, location=(0.045, 0, 0.048), rotation=(math.radians(90), 0, 0))
hd = bpy.context.active_object; hd.data.materials.append(cer); bpy.ops.object.shade_smooth()
hd.parent = mug; hd.matrix_parent_inverse = mug.matrix_world.inverted()      # ручка остаётся там, где создана
bpy.ops.mesh.primitive_cylinder_add(radius=0.0364, depth=0.002, location=(0, 0, 0.078), vertices=64)
cf = bpy.context.active_object; cf.data.materials.append(coffee)
cf.parent = mug; cf.matrix_parent_inverse = mug.matrix_world.inverted()      # кофе — внутри, на 14 мм ниже края
mug.location = (-0.10, 0.62, 0.046); mug.rotation_euler = (0, 0, math.radians(-35))   # центр кружки на 46 мм — дно на столе


# ---------------- свет ----------------
def light(name, kind, loc, target, energy, color=(1, 1, 1), size=0.2, spot=None):
    bpy.ops.object.light_add(type=kind, location=loc)
    l = bpy.context.active_object; l.name = name; l.data.energy = energy; l.data.color = color
    if kind == "AREA": l.data.size = size
    if kind == "SPOT":
        l.data.spot_size = math.radians(spot or 70); l.data.spot_blend = 0.6; l.data.shadow_soft_size = 0.03
    l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return l


warm = (1.0, 0.70, 0.42)
light("Настольная лампа", "SPOT", (-0.28, 0.42, 0.52), (0.02, 0.02, 0.05), 38, warm, spot=75)
light("Мягкий ключевой", "AREA", (0.55, -0.55, 0.65), (0.0, 0.0, 0.08), 22, (1.0, 0.93, 0.85), 0.6)
light("Контровой", "AREA", (-0.55, -0.15, 0.40), (0.0, 0.0, 0.12), 9, (0.85, 0.9, 1.0), 0.3)

# ---------------- камеры ----------------
CAMS = {
    "1": dict(loc=(0.74, -0.52, 0.20), tgt=(0.02, -0.01, 0.095), lens=45, f=3.2),
    "2": dict(loc=(0.12, 0.66, 0.27), tgt=(-0.03, 0.0, 0.08), lens=32, f=4.0),
    "3": dict(loc=(-0.52, -0.50, 0.52), tgt=(0.04, -0.03, 0.06), lens=38, f=4.5),
}
if MINI:   # мини втрое меньше по объёму — камеры ближе, кадр «как с телефона над столом»
    CAMS = {
        "1": dict(loc=(0.44, -0.30, 0.13), tgt=(0.05, -0.02, 0.05), lens=50, f=2.8),
        "2": dict(loc=(0.42, 0.38, 0.19), tgt=(0.05, 0.0, 0.07), lens=40, f=3.5),
        "3": dict(loc=(-0.48, -0.46, 0.46), tgt=(0.02, 0.04, 0.03), lens=30, f=5.6),
    }
cams = {}
for k, c in CAMS.items():
    cd = bpy.data.cameras.new(f"Камера {k}"); cd.lens = c["lens"]
    cd.dof.use_dof = True; cd.dof.aperture_fstop = c["f"]
    co = bpy.data.objects.new(f"Камера {k}", cd); scene.collection.objects.link(co)
    co.location = c["loc"]; co.rotation_euler = (Vector(c["tgt"]) - Vector(c["loc"])).to_track_quat("-Z", "Y").to_euler()
    cd.dof.focus_distance = (Vector(c["tgt"]) - Vector(c["loc"])).length
    cams[k] = co

# ---------------- проверка реализма: предметы не пересекаются, ничего не висит и не утоплено в стол ----------------
def _top_level():
    out = {}
    for o in scene.objects:
        if o.parent is None and o.type in ("EMPTY", "MESH") and o.name not in ("Стол", "лампа") and not o.name.startswith("Камера"):
            kids = [c for c in o.children_recursive if c.type == "MESH"] + ([o] if o.type == "MESH" else [])
            if kids: out[o.name] = bbox(kids)
    return out
bpy.context.view_layer.update()
_bb = _top_level()
for a_, (amn, amx) in _bb.items():
    if amn.z < -0.0015: print(f"ВНИМАНИЕ: {a_} ниже стола на {(-amn.z) * 1000:.1f} мм")
names_ = list(_bb)
for i in range(len(names_)):
    for j in range(i + 1, len(names_)):
        (amn, amx), (bmn, bmx) = _bb[names_[i]], _bb[names_[j]]
        ov = [min(amx[k], bmx[k]) - max(amn[k], bmn[k]) for k in range(3)]
        pair = {names_[i].split(".")[0], names_[j].split(".")[0]}
        if pair in ({"стакан", "карандаш 1"}, {"стакан", "карандаш 2"}, {"карандаш 1", "карандаш 2"}, {"стопка A4", "синяя ручка"},
                    {"жёлтый блокнот", "красная ручка"}): continue       # так и задумано: в стакане, на блокноте
        if min(ov) > 0.002: print(f"пересечение габаритов: {names_[i]} × {names_[j]}: {[round(v * 1000) for v in ov]} мм")

# ---------------- рендер ----------------
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
scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True
scene.cycles.caustics_reflective = False; scene.cycles.caustics_refractive = False
scene.render.resolution_x, scene.render.resolution_y = RES, int(RES * 2 / 3)
scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.3

for variant in VARIANTS:
    for (v, key), o in ROBOT.items():
        show = (v == "tech") if variant == "tech" else ((v == "soft") or key not in ("pcb", "battery", "dark", "grey"))
        if variant == "soft" and v == "tech" and key == "grey":
            show = True                                  # графитовые стойки клешней и хвоста — видны и в мягком варианте
        o.hide_render = not show
    for view in VIEWS:
        scene.camera = cams[view]
        name = f"Мини_{view}.png" if MINI else f"Харви_{'открытый' if variant == 'tech' else 'мягкий'}_{view}.png"
        scene.render.filepath = os.path.join(D, name)
        bpy.ops.render.render(write_still=True)
        print("Рендер:", scene.render.filepath, flush=True)
