"""Реалистичные ручки и карандаш для стола «Компакт мини»: форма, масса и центр тяжести, трение — как у настоящих.

| Предмет | Форма | Размер | Масса | Как ведёт себя |
| --- | --- | --- | --- | --- |
| pen — шариковая ручка с колпачком | цилиндр Ø9,6 + колпачок Ø10,4 с клипом + конус с наконечником | 140 мм | 11 г, центр тяжести смещён к колпачку на 9 мм | клип не даёт укатиться |
| pen2 — гелевая ручка | гладкий цилиндр Ø11 + резиновая зона хвата | 145 мм | 14 г | катится по столу |
| pencil — карандаш HB | шестигранник 7,2 мм под ключ + заточка + ластик в металлической обойме | 182 мм | 7 г | не катится, ложится на грань |

Трение (коэффициенты сухого трения): пластик по лакированному дубу 0,35, дерево карандаша по лаку 0,40,
резина хвата 0,7; накладки губок TPU по пластику 0,9. В MuJoCo в паре берётся большее трение из двух, поэтому у предметов
приоритет 1 (их трение решает с другим столом), у губок — приоритет 2 (их трение решает в губках).
Трение кручения и качения (condim 6) — чтобы ручка в губках не вертелась и по столу катилась, а не скользила вечно."""
import math

PEN_MAT = '<material name="m_pen_clip" rgba="0.80 0.82 0.85 1" specular="0.9" shininess="0.9"/>' \
          '<material name="m_pen_tip" rgba="0.70 0.70 0.72 1" specular="0.9" shininess="0.9"/>' \
          '<material name="m_gel" rgba="0.08 0.08 0.10 1" specular="0.6" shininess="0.8"/>' \
          '<material name="m_gel_grip" rgba="0.15 0.15 0.17 1" specular="0.05"/>' \
          '<material name="m_wood_tip" rgba="0.86 0.70 0.50 1" specular="0.1"/>' \
          '<material name="m_graphite" rgba="0.18 0.18 0.20 1" specular="0.6"/>' \
          '<material name="m_ferrule" rgba="0.78 0.74 0.60 1" specular="0.9" shininess="0.8"/>' \
          '<material name="m_eraser" rgba="0.92 0.55 0.60 1" specular="0.05"/>'

PLASTIC = 'friction="0.35 0.005 0.0004" condim="6" priority="1" solref="0.004 1"'
WOOD = 'friction="0.40 0.005 0.0006" condim="6" priority="1" solref="0.004 1"'
RUBBER = 'friction="0.70 0.005 0.0008" condim="6" priority="1" solref="0.004 1"'


def _hex_mesh(name, x0, x1, af):
    """Шестигранная призма вдоль x, af — размер под ключ; вершины по бокам, грани сверху и снизу (лежит на грани)."""
    R = af / 2 / math.cos(math.radians(30))
    pts = []
    for x in (x0, x1):
        for k in range(6):
            a = math.radians(60 * k)
            pts.append((x, R * math.cos(a), R * math.sin(a)))
    return f'<mesh name="{name}" vertex="{" ".join(f"{v:.5f}" for p in pts for v in p)}"/>'


def _hex_tip_mesh(name, x0, x1, af, r_tip):
    R = af / 2 / math.cos(math.radians(30)); pts = []
    for k in range(6):
        a = math.radians(60 * k); pts.append((x0, R * math.cos(a), R * math.sin(a)))
    for k in range(6):
        a = math.radians(60 * k); pts.append((x1, r_tip * math.cos(a), r_tip * math.sin(a)))
    return f'<mesh name="{name}" vertex="{" ".join(f"{v:.5f}" for p in pts for v in p)}"/>'


def assets():
    return PEN_MAT + _hex_mesh("pencil_body", -0.0820, 0.0700, 0.0072) + _hex_tip_mesh("pencil_cone", 0.0700, 0.0900, 0.0072, 0.0012)


def bodies(pen=(0.25, 0.18, 0.0), pen2=(0.12, -0.25, 15.0), pencil=(0.55, 0.05, -60.0)):
    """Тела на столе: (x, y, поворот°). Высота — по форме: лежат на столе, не висят и не утоплены."""
    b = []
    x, y, a = pen   # шариковая ручка: корпус Ø9,6, колпачок Ø10,4 с клипом (клип сверху), наконечник
    b.append(f'''<body name="pen" pos="{x} {y} 0.0052" euler="0 0 {a}"><freejoint/>
      <geom name="pen_g" type="cylinder" euler="0 90 0" size="0.0048 0.0480" pos="0.008 0 -0.0004" mass="0.0060" material="m_pen_b" {PLASTIC}/>
      <geom name="pen_cap" type="cylinder" euler="0 90 0" size="0.0052 0.0170" pos="-0.0530 0 0" mass="0.0032" material="m_pen_b" {PLASTIC}/>
      <geom name="pen_clip" type="box" size="0.0150 0.0012 0.0007" pos="-0.0560 0 0.0059" mass="0.0006" material="m_pen_clip" {PLASTIC}/>
      <geom name="pen_tip" type="capsule" fromto="0.0560 0 -0.0004 0.0700 0 -0.0004" size="0.0022" mass="0.0012" material="m_pen_tip" {PLASTIC}/>
    </body>''')
    x, y, a = pen2  # гелевая ручка: гладкий корпус Ø11, резиновая зона хвата у кончика
    b.append(f'''<body name="pen2" pos="{x} {y} 0.0057" euler="0 0 {a}"><freejoint/>
      <geom name="pen2_g" type="cylinder" euler="0 90 0" size="0.0055 0.0500" pos="-0.0120 0 0" mass="0.0090" material="m_gel" {PLASTIC}/>
      <geom name="pen2_grip" type="cylinder" euler="0 90 0" size="0.0057 0.0150" pos="0.0530 0 0" mass="0.0035" material="m_gel_grip" {RUBBER}/>
      <geom name="pen2_tip" type="capsule" fromto="0.0680 0 0 0.0780 0 0" size="0.0020" mass="0.0015" material="m_pen_tip" {PLASTIC}/>
    </body>''')
    x, y, a = pencil  # карандаш HB: шестигранник, заточка, обойма и ластик
    b.append(f'''<body name="pencil" pos="{x} {y} 0.0036" euler="0 0 {a}"><freejoint/>
      <geom name="pencil_g" type="mesh" mesh="pencil_body" mass="0.0058" material="m_pencil" {WOOD}/>
      <geom name="pencil_cone" type="mesh" mesh="pencil_cone" mass="0.0004" material="m_wood_tip" {WOOD}/>
      <geom type="sphere" size="0.0012" pos="0.0900 0 0" mass="0.00005" material="m_graphite" contype="0" conaffinity="0"/>
      <geom name="pencil_ferrule" type="cylinder" size="0.0039 0.0040" pos="-0.0860 0 0" euler="0 90 0" mass="0.0004" material="m_ferrule" {WOOD}/>
      <geom name="pencil_eraser" type="cylinder" size="0.0036 0.0035" pos="-0.0935 0 0" euler="0 90 0" mass="0.0004" material="m_eraser" {RUBBER}/>
    </body>''')
    return "".join(b)


MASS_G = {"pen": 11.0, "pen2": 14.0, "pencil": 7.0}
NAME_RU = {"pen": "ручку", "pen2": "гелевую ручку", "pencil": "карандаш"}

EXTENT = {"pen": (-0.070, 0.0722), "pen2": (-0.062, 0.080), "pencil": (-0.097, 0.0912)}   # концы вдоль оси x тела, м
