"""Выгрузка сборки кисти по частям (каждая — своим материалом) для рендера в Blender.
    python export_render_parts.py [запястье° захват°]   → папка render_parts/ рядом
Затем: blender --background --python ../render/render_hand.py"""
import os, sys
import harvey_hand_parts as hp
from manifold3d import Manifold

wrist = float(sys.argv[1]) if len(sys.argv) > 1 else -15.0
grip = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
P, t = hp.P, hp.P["horn_top"]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_parts")
os.makedirs(out, exist_ok=True)


def hand(m):
    return m.rotate([wrist, 0, 0]).translate([t, 0, P["wrist_h"]])


def opened(m):
    return m.translate([-hp.G_X, 0, 0]).rotate([0, -grip, 0]).translate([hp.G_X, 0, 0])


lower_top = hp.CONTACT_Z - P["pad"] - 0.5
upper_bot = hp.CONTACT_Z + P["pad"] + 0.5
pad = hp.pad()
pad_low = hp.rot_y(pad.translate([hp.PIVOT_X + 2, 0, lower_top - 0.5]), P["bend"], hp.PIVOT_X, hp.CONTACT_Z)
pad_up = hp.rot_y(pad.mirror([0, 0, 1]).translate([hp.PIVOT_X + 2, 0, upper_bot + 0.5]), P["bend"], hp.PIVOT_X, hp.CONTACT_Z)

body = hp.servo_body()                                       # корпус и обе качалки вместе
case = hp.boxr(hp.X0, hp.X1, -P["body_T"] / 2, P["body_T"] / 2, -P["body_D"], 0)
horns = body - case
parts = {
    "stand": hp.wrist_stand(),
    "palm": hand(hp.palm()),
    "jaw": hand(opened(hp.jaw())),
    "pad_low": hand(pad_low),
    "pad_up": hand(opened(pad_up)),
    "servo21_case": hp.place(case, hp.W_COLS, hp.W_T),
    "servo21_horns": hp.place(horns, hp.W_COLS, hp.W_T),
    "servo22_case": hand(hp.place(case, hp.G_COLS, hp.G_T)),
    "servo22_horns": hand(hp.place(horns, hp.G_COLS, hp.G_T)),
}
for name, m in parts.items():
    hp.to_trimesh(m).export(os.path.join(out, name + ".stl"))
print("ok:", ", ".join(parts), "→", out)
