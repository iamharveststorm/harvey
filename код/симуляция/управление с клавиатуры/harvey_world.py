"""Мир для управления Харви: комната, рабочий стол (старт), реквизит, доска-спуск и полоса препятствий на полу.

Стол — стартовая площадка: его поверхность на высоте z = 0 (как «стол» во всех сценариях), пол комнаты — на −0,75 м.
На столе: телефон (сзади, для хвоста), ручки, карандаш, блокнот, кружка, кейс наушников, зажигалка, стикеры, книга,
ноутбук и лампа. С переднего края стола — доска-спуск 20° на пол. На полу по порядку (вдоль x):
трава (кочки), песок (дюны, мягкий и скользкий грунт), гравий, галька, четыре склона 10/15/20/25°, косой склон 15°,
ступени 15/30/45 мм, асфальт с кабелем и книгами.

Текстуры — Poly Haven (CC0), подготовлены скриптом модели/рендер/export_world_assets.py; видимые детали робота —
модели/рендер/export_mujoco.py. Все файлы передаются в MuJoCo из памяти (assets), путь с кириллицей не мешает.
Физика робота не меняется: детали из CAD только рисуются (группа 2), сталкиваются простые формы (группа 1)."""
import os, re, json, math
import numpy as np
import harvey_terrain as TR

HERE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(HERE, "assets")
G = -0.75            # пол комнаты
ZJ = 0.0526          # высота осей бедра в стойке (как в harvey_sim)


def have_assets():
    return os.path.isdir(os.path.join(ADIR, "world")) and os.path.isfile(os.path.join(ADIR, "robot", "robot_visual.json"))


def load_assets():
    """Все PNG и STL — словарём для mujoco.MjModel.from_xml_string(xml, assets)."""
    out = {}
    for sub in ("world", "robot"):
        d = os.path.join(ADIR, sub)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().endswith((".png", ".stl")):
                    out[f"{sub}/{f}"] = open(os.path.join(d, f), "rb").read()
    return out


# ---------------- оформление ----------------
VISUAL = """
  <visual>
    <global offwidth="1920" offheight="1080" fovy="40"/>
    <quality shadowsize="8192" offsamples="8" numslices="40" numstacks="40"/>
    <map znear="0.002" zfar="40" shadowclip="2.5" shadowscale="0.45" haze="0.12" fogstart="8" fogend="30"/>
    <headlight ambient="0.20 0.20 0.22" diffuse="0.22 0.22 0.22" specular="0.03 0.03 0.03"/>
    <rgba haze="0.86 0.88 0.92 1" fog="0.86 0.88 0.92 1"/>
  </visual>"""

TEXTURES = {"parquet": 1.6, "wall": 1.2, "oak": 1.4, "grass": 2.0, "sand": 1.6, "gravel": 3.0, "pebbles": 2.4,
            "concrete": 1.2, "asphalt": 1.5}


# материал, текстура, повтор, specular, shininess, reflectance, emission
PBR = [("m_parquet", "parquet", 1.6, 0.35, 0.5, 0.08, 0), ("m_wall", "wall", 1.2, 0.05, 0.1, 0, 0.35),
       ("m_oak", "oak", 1.4, 0.4, 0.6, 0.06, 0), ("m_grass", "grass", 2.5, 0.05, 0.1, 0, 0),
       ("m_sand", "sand", 1.6, 0.08, 0.1, 0, 0), ("m_gravel", "gravel", 3.0, 0.1, 0.2, 0, 0),
       ("m_pebbles", "pebbles", 2.4, 0.25, 0.4, 0, 0), ("m_concrete", "concrete", 1.2, 0.1, 0.2, 0, 0),
       ("m_asphalt", "asphalt", 1.5, 0.1, 0.2, 0, 0)]


def pbr_material(name, tex, rep, spec, shin, refl, emis):
    """Материал с цветом, нормалями и ORM (если карты есть): классический рендер берёт цвет, Filament — всё."""
    attrs = f'texuniform="true" texrepeat="{rep} {rep}" specular="{spec}" shininess="{shin}" reflectance="{refl}" emission="{emis}"'
    if not os.path.isfile(os.path.join(ADIR, "world", f"{tex}_n.png")):
        return f'<material name="{name}" texture="t_{tex}" {attrs}/>'
    return (f'<material name="{name}" {attrs}><layer texture="t_{tex}" role="rgb"/>'
            f'<layer texture="t_{tex}_n" role="normal"/><layer texture="t_{tex}_orm" role="orm"/></material>')


def asset_xml(robot=True):
    a = ['<texture name="sky" type="skybox" builtin="gradient" rgb1="0.80 0.88 0.97" rgb2="0.98 0.96 0.92" width="512" height="3072"/>']
    for t, rep in TEXTURES.items():
        a.append(f'<texture name="t_{t}" type="2d" file="world/{t}.png"/>')
        for suf in ("n", "orm"):            # карты PBR для рендера Filament (режим «фото»)
            if os.path.isfile(os.path.join(ADIR, "world", f"{t}_{suf}.png")):
                a.append(f'<texture name="t_{t}_{suf}" type="2d" file="world/{t}_{suf}.png" colorspace="linear"/>')
    if os.path.isfile(os.path.join(ADIR, "world", "phone_wall.png")):
        a.append('<texture name="t_phone" type="2d" file="world/phone_wall.png"/>')
        a.append('<material name="m_phone_screen" texture="t_phone" emission="0.7" specular="0.6" shininess="0.9" reflectance="0.05"/>')
    a += [pbr_material(*args) for args in PBR]
    a += [
        '<material name="m_board" rgba="0.72 0.56 0.38 1" specular="0.2" shininess="0.3"/>',
        '<material name="m_steel" rgba="0.18 0.19 0.21 1" specular="0.6" shininess="0.7" reflectance="0.05" roughness="0.35" metallic="0.9"/>',
        '<material name="m_window" rgba="0.92 0.96 1.0 1" emission="1.0"/>',
        '<material name="m_frame" rgba="0.95 0.95 0.93 1" specular="0.2"/>',
        '<material name="m_paper" rgba="0.95 0.94 0.90 1" specular="0.05"/>',
        '<material name="m_yellow" rgba="0.98 0.88 0.35 1" specular="0.05"/>',
        '<material name="m_ceramic" rgba="0.93 0.89 0.82 1" specular="0.5" shininess="0.8" roughness="0.15" metallic="0"/>',
        '<material name="m_coffee" rgba="0.17 0.09 0.04 1" specular="0.6" shininess="0.9"/>',
        '<material name="m_acrylic" rgba="0.92 0.95 0.97 0.45" specular="0.8" shininess="0.9"/>',
        '<material name="m_blackglass" rgba="0.04 0.04 0.05 1" specular="0.8" shininess="0.95" reflectance="0.1"/>',
        '<material name="m_book_r" rgba="0.55 0.14 0.12 1" specular="0.1"/>',
        '<material name="m_book_b" rgba="0.14 0.24 0.45 1" specular="0.1"/>',
        '<material name="m_lighter" rgba="0.72 0.6 0.38 1" specular="0.9" shininess="0.9" roughness="0.25" metallic="1"/>',
        '<material name="m_pen_b" rgba="0.12 0.25 0.7 1" specular="0.6" shininess="0.8"/>',
        '<material name="m_pen_r" rgba="0.75 0.12 0.1 1" specular="0.6" shininess="0.8"/>',
        '<material name="m_pencil" rgba="0.95 0.75 0.15 1" specular="0.3"/>',
        '<material name="m_cable" rgba="0.1 0.1 0.1 1" specular="0.3"/>',
        '<material name="m_lampshade" rgba="0.2 0.2 0.22 1" specular="0.5" shininess="0.6"/>',
        '<material name="m_bulb" rgba="1 0.9 0.7 1" emission="1"/>',
        '<hfield name="h_grass" file="world/grass_h.png" size="0.50 0.45 0.014 0.01"/>',
        TR.sand_asset(),                       # песок — рельеф задаёт и меняет harvey_terrain во время симуляции
        '<hfield name="h_gravel" file="world/gravel_h.png" size="0.45 0.45 0.010 0.01"/>',
        '<hfield name="h_pebbles" file="world/pebbles_h.png" size="0.45 0.45 0.016 0.01"/>',
    ] + TR.grass_assets()
    if robot:
        a += [
            '<material name="r_orange" rgba="0.90 0.36 0.12 1" specular="0.35" shininess="0.45"/>',
            '<material name="r_grey" rgba="0.20 0.22 0.25 1" specular="0.25" shininess="0.35"/>',
            '<material name="r_servo" rgba="0.07 0.07 0.08 1" specular="0.3" shininess="0.5"/>',
            '<material name="r_metal" rgba="0.76 0.78 0.81 1" specular="0.9" shininess="0.9" reflectance="0.08"/>',
            '<material name="r_tpu" rgba="0.06 0.06 0.06 1" specular="0.05"/>',
            '<material name="r_pcb" rgba="0.10 0.36 0.21 1" specular="0.3"/>',
            '<material name="r_battery" rgba="0.11 0.42 0.53 1" specular="0.6" shininess="0.6"/>',
            '<material name="r_red" rgba="0.82 0.11 0.11 1" specular="0.4"/>',
            '<material name="r_cup" rgba="0.86 0.88 0.90 0.8" specular="0.6"/>',
            '<material name="r_eye" rgba="0.36 0.90 1.0 1" emission="0.9"/>',
            '<material name="r_iris" rgba="0.04 0.16 0.22 1" emission="0.2"/>',
            '<material name="r_glint" rgba="1 1 1 1" emission="1"/>',
        ]
        man = json.load(open(os.path.join(ADIR, "robot", "robot_visual.json"), encoding="utf-8"))
        seen = set()
        for body, items in man["bodies"].items():
            for f, mat in items:
                if f not in seen:
                    a.append(f'<mesh name="{f[:-4]}" file="robot/{f}"/>'); seen.add(f)
    return "\n    <asset>\n      " + "\n      ".join(a) + "\n    </asset>"


# ---------------- геометрия мира ----------------
def _ramp(name, x0, x1, y, h0, h1, half_w, mat, thick=0.012):
    """Наклонная плита от (x0, h0) к (x1, h1) — верх по этой линии."""
    L = math.hypot(x1 - x0, h1 - h0); a = math.degrees(math.atan2(h1 - h0, x1 - x0))
    n = np.array([-math.sin(math.radians(a)), 0, math.cos(math.radians(a))])
    c = np.array([(x0 + x1) / 2, y, (h0 + h1) / 2]) - n * thick
    return (f'<geom name="{name}" type="box" size="{L / 2:.4f} {half_w:.3f} {thick:.3f}" pos="{c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" '
            f'euler="0 {-a:.3f} 0" material="{mat}" friction="0.9 0.01 0.001"/>')


def world_geoms():
    g = []
    # комната: пол, две стены, окно
    g.append(f'<geom name="ground" type="plane" size="8 4 0.1" pos="5.5 0.5 {G}" material="m_parquet" friction="0.8 0.01 0.001"/>')
    g.append(f'<geom name="wall_back" type="box" size="0.05 3.5 1.3" pos="-1.10 0.5 {G + 1.3}" material="m_wall"/>')
    g.append(f'<geom name="wall_left" type="box" size="6.8 0.05 1.3" pos="5.7 2.6 {G + 1.3}" material="m_wall"/>')
    g.append(f'<geom name="window" type="box" size="0.012 0.75 0.55" pos="-1.045 -0.2 {G + 1.45}" material="m_window" contype="0" conaffinity="0"/>')
    for dy, dz, sx, sy in ((0, 0.55, 0.78, 0.03), (0, -0.55, 0.78, 0.03), (0.75, 0, 0.03, 0.58), (-0.75, 0, 0.03, 0.58), (0, 0, 0.78, 0.012)):
        g.append(f'<geom type="box" size="0.02 {sx if sx < 0.1 else sx:.3f} {sy:.3f}" pos="-1.03 {-0.2 + dy:.3f} {G + 1.45 + dz:.3f}" '
                 f'material="m_frame" contype="0" conaffinity="0"/>' if sx > 0.1 else
                 f'<geom type="box" size="0.02 {sx:.3f} {sy:.3f}" pos="-1.03 {-0.2 + dy:.3f} {G + 1.45 + dz:.3f}" material="m_frame" contype="0" conaffinity="0"/>')
    # стол: столешница (это «пол» всех сценариев), ножки, царга
    g.append('<geom name="floor" type="box" size="0.75 0.45 0.015" pos="0.2 0 -0.015" material="m_oak" friction="0.8 0.01 0.001"/>')
    for x in (-0.5, 0.9):
        for y in (-0.4, 0.4):
            g.append(f'<geom type="box" size="0.022 0.022 {(0.75 - 0.03) / 2:.3f}" pos="{x} {y} {G + (0.75 - 0.03) / 2:.3f}" material="m_steel"/>')
    g.append('<geom type="box" size="0.68 0.38 0.03" pos="0.2 0 -0.06" material="m_steel" contype="0" conaffinity="0"/>')
    # доска-спуск 20° с переднего края стола и бортики
    x0, x1 = 0.93, 0.93 + 0.75 / math.tan(math.radians(20))
    g.append(_ramp("ramp", x0, x1, 0.0, 0.0, G, 0.17, "m_board", 0.008))
    for s in (1, -1):
        g.append(_ramp(f"ramp_rail_{'l' if s > 0 else 'r'}", x0, x1, s * 0.176, 0.012, G + 0.012, 0.006, "m_board", 0.012))
    # полоса препятствий на полу
    g.append(f'<geom name="grass" type="hfield" hfield="h_grass" pos="3.85 0 {G - 0.001}" material="m_grass" friction="0.9 0.01 0.001" solref="0.03 1"/>')
    g.append(TR.sand_geom())
    g.append(f'<geom name="gravel" type="hfield" hfield="h_gravel" pos="6.0 0 {G - 0.001}" material="m_gravel" friction="0.7 0.01 0.001"/>')
    g.append(f'<geom name="pebbles" type="hfield" hfield="h_pebbles" pos="6.95 0 {G - 0.001}" material="m_pebbles" friction="0.6 0.01 0.001"/>')
    g += TR.grass_geoms()                          # стебли травы (видны, не сталкиваются; сопротивление — в harvey_terrain)
    h = 0.08
    for i, (y, ang) in enumerate(((-0.75, 10), (-0.25, 15), (0.25, 20), (0.75, 25))):
        xa = 7.6; xb = xa + h / math.tan(math.radians(ang)); xc = xb + 0.35; xd = xc + h / math.tan(math.radians(10))
        g.append(_ramp(f"slope{ang}_up", xa, xb, y, G, G + h, 0.22, "m_concrete"))
        g.append(f'<geom name="slope{ang}_top" type="box" size="0.175 0.22 {h / 2:.3f}" pos="{xb + 0.175:.3f} {y} {G + h / 2:.3f}" material="m_concrete"/>')
        g.append(_ramp(f"slope{ang}_down", xc, xd, y, G + h, G, 0.22, "m_concrete"))
    g.append(f'<geom name="side_slope" type="box" size="0.6 0.25 0.01" pos="8.2 1.45 {G + 0.25 * math.sin(math.radians(15)):.3f}" '
             f'euler="15 0 0" material="m_concrete" friction="0.9 0.01 0.001"/>')
    for i, hh in enumerate((0.015, 0.030, 0.045)):
        g.append(f'<geom name="step{i + 1}" type="box" size="0.125 0.5 {hh / 2:.4f}" pos="{9.4 + 0.25 * i:.3f} 0 {G + hh / 2:.4f}" material="m_concrete"/>')
    g.append(f'<geom name="step_top" type="box" size="0.2 0.5 0.0225" pos="10.35 0 {G + 0.0225:.4f}" material="m_concrete"/>')
    for i, hh in enumerate((0.030, 0.015)):
        g.append(f'<geom name="stepd{i + 1}" type="box" size="0.125 0.5 {hh / 2:.4f}" pos="{10.675 + 0.25 * i:.3f} 0 {G + hh / 2:.4f}" material="m_concrete"/>')
    g.append(f'<geom name="asphalt" type="box" size="0.7 0.6 0.002" pos="11.9 0 {G + 0.002:.4f}" material="m_asphalt" friction="0.95 0.01 0.001"/>')
    g.append(f'<geom name="floor_cable" type="capsule" fromto="11.6 -0.6 {G + 0.008} 11.7 0.6 {G + 0.008}" size="0.004" material="m_cable"/>')
    g.append(f'<geom name="floor_book1" type="box" size="0.11 0.16 0.0125" pos="12.1 -0.2 {G + 0.0165}" euler="0 0 12" material="m_book_r"/>')
    g.append(f'<geom name="floor_book2" type="box" size="0.1 0.15 0.02" pos="12.3 0.3 {G + 0.024}" euler="0 0 -20" material="m_book_b"/>')
    # настольная лампа (только видна) и ноутбук
    g.append('<geom name="lamp_base" type="cylinder" size="0.065 0.01" pos="-0.42 -0.34 0.01" material="m_lampshade"/>')
    g.append('<geom type="capsule" fromto="-0.42 -0.34 0.02 -0.36 -0.30 0.30" size="0.007" material="m_steel" contype="0" conaffinity="0"/>')
    g.append('<geom type="capsule" fromto="-0.36 -0.30 0.30 -0.20 -0.18 0.40" size="0.007" material="m_steel" contype="0" conaffinity="0"/>')
    g.append('<geom type="cylinder" size="0.05 0.035" pos="-0.17 -0.16 0.38" euler="35 25 0" material="m_lampshade" contype="0" conaffinity="0"/>')
    g.append('<geom type="sphere" size="0.02" pos="-0.155 -0.15 0.355" material="m_bulb" contype="0" conaffinity="0"/>')
    g.append('<geom name="laptop" type="box" size="0.15 0.105 0.009" pos="-0.36 0.27 0.009" euler="0 0 -8" material="m_steel"/>')
    return g


def props_xml():
    """Подвижные предметы на столе (телефон добавляет harvey_teleop — он сзади, для хвоста)."""
    p = [
        '<body name="pen" pos="0.25 0.18 0.0047"><freejoint/><geom name="pen_g" type="capsule" fromto="-0.07 0 0 0.07 0 0" size="0.0045" mass="0.015" material="m_pen_b" friction="0.6 0.01 0.002" condim="6"/></body>',
        '<body name="pen2" pos="0.42 -0.30 0.0047" euler="0 0 35"><freejoint/><geom name="pen2_g" type="capsule" fromto="-0.07 0 0 0.07 0 0" size="0.0045" mass="0.015" material="m_pen_r" friction="0.6 0.01 0.002" condim="6"/></body>',
        '<body name="pencil" pos="0.55 0.05 0.0042" euler="0 0 -60"><freejoint/><geom name="pencil_g" type="capsule" fromto="-0.08 0 0 0.08 0 0" size="0.0038" mass="0.006" material="m_pencil" friction="0.6 0.01 0.002" condim="6"/></body>',
        '<body name="notebook" pos="0.40 0.28 0.004" euler="0 0 8"><freejoint/><geom name="notebook_g" type="box" size="0.105 0.074 0.004" mass="0.25" material="m_paper" friction="0.6 0.01 0.001"/></body>',
        '<body name="mug" pos="0.66 0.30 0.048"><freejoint/><geom name="mug_g" type="cylinder" size="0.041 0.046" mass="0.33" material="m_ceramic" friction="0.6 0.01 0.001"/>'
        '<geom type="cylinder" size="0.036 0.001" pos="0 0 0.039" material="m_coffee" contype="0" conaffinity="0" mass="0"/>'
        '<geom name="mug_handle" type="capsule" fromto="0.041 0 0.025 0.06 0 0.0" size="0.006" mass="0.01" material="m_ceramic"/>'
        '<geom type="capsule" fromto="0.06 0 0.0 0.041 0 -0.025" size="0.006" mass="0.01" material="m_ceramic" contype="0" conaffinity="0"/></body>',
        '<body name="earbuds" pos="0.30 -0.18 0.011" euler="0 0 18"><freejoint/><geom name="earbuds_g" type="box" size="0.0278 0.0278 0.011" mass="0.05" material="m_acrylic" friction="0.5 0.01 0.001"/>'
        '<geom type="box" size="0.023 0.023 0.004" pos="0 0 -0.006" rgba="0.95 0.95 0.94 1" contype="0" conaffinity="0" mass="0"/>'
        '<geom type="capsule" fromto="-0.012 0.011 0.002 0.006 0.011 0.002" size="0.003" rgba="0.97 0.97 0.97 1" contype="0" conaffinity="0" mass="0"/>'
        '<geom type="capsule" fromto="-0.012 -0.011 0.002 0.006 -0.011 0.002" size="0.003" rgba="0.97 0.97 0.97 1" contype="0" conaffinity="0" mass="0"/>'
        '<geom type="sphere" size="0.0013" pos="0.0275 0 0.006" rgba="0.9 0.1 0.08 1" contype="0" conaffinity="0" mass="0"/></body>',
        '<body name="lighter" pos="0.62 -0.10 0.006" euler="0 0 110"><freejoint/><geom name="lighter_g" type="box" size="0.019 0.03 0.006" mass="0.05" material="m_lighter" friction="0.4 0.01 0.001"/></body>',
        '<body name="sticky" pos="0.15 -0.34 0.008" euler="0 0 -10"><freejoint/><geom name="sticky_g" type="box" size="0.038 0.038 0.008" mass="0.03" material="m_yellow" friction="0.7 0.01 0.001"/></body>',
        '<body name="book" pos="0.78 -0.26 0.0125" euler="0 0 20"><freejoint/><geom name="book_g" type="box" size="0.075 0.11 0.0125" mass="0.40" material="m_book_r" friction="0.7 0.01 0.001"/></body>',
        '<geom name="desk_cable" type="capsule" fromto="0.62 0.42 0.004 0.70 -0.05 0.004" size="0.003" material="m_cable"/>',
    ]
    p.append(TR.stones_xml())     # камни гравия и гальки — отдельные тела (после робота: его свободное сочленение — первое в qpos)
    return "".join(p)


GRASPABLE = ["pen", "pen2", "pencil", "notebook", "mug", "earbuds", "lighter", "sticky", "book", "phone"]

LIGHTS = f"""
    <light name="sun" directional="true" pos="3 -2 4" dir="-0.45 0.35 -0.82" diffuse="0.78 0.74 0.66" specular="0.25 0.25 0.22" castshadow="true"/>
    <light name="desk_lamp" pos="-0.155 -0.15 0.34" dir="0.45 0.35 -1" diffuse="0.95 0.72 0.45" specular="0.3 0.25 0.2"
           cutoff="55" exponent="6" attenuation="1 0.4 0.3" castshadow="true"/>
    <light name="fill" directional="true" pos="6 -3 4" dir="-0.2 0.45 -0.87" diffuse="0.28 0.30 0.34" specular="0 0 0" castshadow="false"/>"""

ZONES = [  # имя, (x, y, высота поверхности под роботом)
    ("стол", (0.0, 0.0, 0.0)), ("низ доски", (3.2, 0.0, G)), ("трава", (3.6, 0.0, G + 0.006)), ("песок", (4.55, 0.0, G + 0.012)),
    ("гравий", (5.7, 0.0, G + 0.004)), ("галька", (6.65, 0.0, G + 0.006)), ("склон 10°", (7.35, -0.75, G)),
    ("склон 15°", (7.35, -0.25, G)), ("склон 20°", (7.35, 0.25, G)), ("склон 25°", (7.35, 0.75, G)),
    ("косой склон 15°", (7.8, 1.45, G + 0.075)), ("ступени", (9.05, 0.0, G)), ("асфальт, кабель, книги", (11.35, 0.0, G + 0.004)),
]


def zone_at(x, y, z):
    if z > -0.3:
        return "стол"
    if 0.9 < x < 3.0 and abs(y) < 0.3:
        return "доска-спуск"
    for name, (x0, x1) in (("трава", (3.35, 4.35)), ("песок", (4.4, 5.5)), ("гравий", (5.55, 6.45)), ("галька", (6.5, 7.4))):
        if x0 < x < x1 and abs(y) < 0.45:
            return name
    if 7.5 < x < 9.0:
        return "склоны"
    if 9.2 < x < 11.0:
        return "ступени"
    if x > 11.1:
        return "асфальт"
    return "пол комнаты"


def robot_visual(xml):
    """Вставить видимые детали из CAD в тела модели (группа 2: рисуются, не сталкиваются, без массы)."""
    man = json.load(open(os.path.join(ADIR, "robot", "robot_visual.json"), encoding="utf-8"))
    def geoms(key):
        return "".join(f'<geom type="mesh" mesh="{f[:-4]}" material="r_{mat}" group="2" contype="0" conaffinity="0" mass="0"/>'
                       for f, mat in man["bodies"].get(key, []))
    targets = {"torso": "torso", "T_base": "T_base", "T_up": "T_up", "T_fore": "T_fore", "T_wr": "T_wr", "T_cup": "T_cup"}
    for n in ("LF", "LM", "LB", "RF", "RM", "RB"):
        targets[f"{n}_coxa"] = "leg_coxa"; targets[f"{n}_femur"] = "leg_femur"; targets[f"{n}_tibia"] = "leg_tibia"
    for s in "LR":
        for a, b in (("ay", "ay"), ("up", "up"), ("fore", "fore"), ("hand", "hand"), ("eye", "eye")):
            targets[f"{s}_{a}"] = f"{s}_{b}"
    for body, key in targets.items():
        m = re.search(rf'<body name="{body}"[^>]*>', xml)
        if m:
            add = geoms(key)
            if body.endswith("_eye"):
                sc = man["eye_screen"]
                add += (f'<geom type="cylinder" size="{sc["r"]:.4f} 0.0004" pos="{sc["x"]:.4f} 0 {sc["z"]:.4f}" euler="0 90 0" material="r_eye" group="2" contype="0" conaffinity="0" mass="0"/>'
                        f'<geom type="cylinder" size="0.0068 0.0004" pos="{sc["x"] + 0.0005:.4f} 0 {sc["z"]:.4f}" euler="0 90 0" material="r_iris" group="2" contype="0" conaffinity="0" mass="0"/>'
                        f'<geom type="sphere" size="0.0022" pos="{sc["x"] + 0.0008:.4f} 0.004 {sc["z"] + 0.005:.4f}" material="r_glint" group="2" contype="0" conaffinity="0" mass="0"/>')
            xml = xml[:m.end()] + add + xml[m.end():]
    return xml


def grab_equalities(hands=("L", "R")):
    eq = "".join(f'<weld name="grab_{h}_{o}" body1="{h}_hand" body2="{o}" active="false"/>' for h in hands for o in GRASPABLE)
    return f"\n  <equality>{eq}</equality>"


def apply(xml, robot=True):
    """Из модели harvey_sim/harvey_tail сделать мир: свет, комната, стол, спуск, полоса препятствий, детали робота."""
    xml = xml.replace('<geom name="floor" type="plane" size="3 3 0.1" friction="0.8 0.01 0.001"/>', "\n    ".join(world_geoms()))
    xml = xml.replace('<light pos="0 0 1"/>', LIGHTS + '\n    <geom name="skyfix" type="sphere" size="0.001" pos="0 0 -5" contype="0" conaffinity="0" rgba="0 0 0 0"/>')
    xml = xml.replace('<mujoco model="harvey">', '<mujoco model="harvey">' + VISUAL + asset_xml(robot), 1)
    # сон MuJoCo: неподвижные камни и предметы не считаются, пока их не тронут; робот не засыпает никогда
    xml = xml.replace('<option timestep="0.0005" integrator="implicitfast"/>',
                      '<option timestep="0.0005" integrator="implicitfast" sleep_tolerance="0.01"><flag sleep="enable"/></option>')
    xml = xml.replace('<body name="torso" ', '<body name="torso" sleep="never" ', 1)
    if robot:
        xml = robot_visual(xml)
    xml = xml.replace("</mujoco>", grab_equalities() + "\n</mujoco>")
    return xml
