"""«Компакт мини» для рендера в Blender: детали в рабочей позе, сгруппированные по материалам, система стола (мм).
    C:\\venvs\\harvey-cad\\Scripts\\python.exe export_render.py   → ../рендер/parts_mini/tech/<материал>.stl + scene.json
Потом:  set HARVEY_ROBOT=mini  и  blender --background --python ../рендер/render_desk.py  (кадры Мини_1…3.png)."""
import os, sys, json, math
import numpy as np
import harvey_mini_parts as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "рендер", "parts_mini")
ZJ = M.G["tib"] - M.G["fem"] * math.sin(math.radians(20))       # оси бедра над столом в стойке

# поза: стойка, левая клешня машет (поднята, глаз наружу по правилу 2), правая поджата; глаза чуть набок — «интерес»
POSE = {"legs": {n: (0.0, 20.0, -110.0) for n in M.G["mounts"]},
        "claw": {"L": (25.0, 75.0, -55.0, -30.0), "R": (0.0, 15.0, -115.0, 10.0)},
        "eye": {"L": -45.0, "R": 10.0}}

MAT = {"chassis": "grey", "lid": "grey", "coxa_bracket": "orange", "femur_link": "orange", "tibia": "orange", "foot": "tpu",
       "yaw_bracket": "grey", "upper_arm": "orange", "forearm": "orange", "fixed_jaw": "tpu", "moving_jaw": "tpu",
       "eye_stalk": "orange", "display": "dark"}


def material(name):
    if "servo" in name: return "case"
    if name in MAT: return MAT[name]
    if "18650" in name: return "battery"
    if "камера" in name: return "dark"
    if name.startswith("edge"): return "pcb"
    return "pcb"


def main():
    groups = {}
    def add(name, m):
        groups.setdefault(material(name), []).append(m.translate([0, 0, ZJ]))
    for k, m in M.fixed_parts().items():
        add(k, m)
    for n, q in POSE["legs"].items():
        for parts in M.leg_assembly(n, *q).values():
            for nm, m in parts: add(nm, m)
    for s, q in POSE["claw"].items():
        for parts in M.claw_assembly(s, *q).values():
            for nm, m in parts: add(nm, m)
    screens = {}
    for s, qs in POSE["eye"].items():
        for nm, m in M.eye_assembly(s, qs)["eye"]: add(nm, m)
        sg = 1 if s == "L" else -1
        a = math.radians(qs)
        c_local = np.array([-4 + 1 + M.G["disp_t"] + 0.25, 0.0, M.G["stalk"] + M.G["disp_d"] / 2])
        R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        c = R @ c_local; up = R @ np.array([0, 0, 1.0])
        c[1] *= sg; up[1] *= sg
        c = c + np.array(M.G["eye"][s]) + [0, 0, ZJ]
        screens[s] = {"center": c.tolist(), "normal": [1.0, 0.0, 0.0], "up": up.tolist(), "radius": 9.0}   # экран 0,71″ — Ø18
    d = os.path.join(OUT, "tech"); os.makedirs(d, exist_ok=True)
    for f in os.listdir(d): os.remove(os.path.join(d, f))
    for k, ms in groups.items():
        M.to_tm(M.U(ms)).export(os.path.join(d, k + ".stl"))
    json.dump({"tech": {"materials": sorted(groups)}, "screens": screens, "pose": POSE},
              open(os.path.join(OUT, "scene.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("материалы:", sorted(groups), "→", OUT)


if __name__ == "__main__":
    main()
