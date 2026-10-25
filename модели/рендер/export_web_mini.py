"""Сетки «Компакт мини» для визуализации three.js — визуализация/lib/harvey_mini_meshes.js.
Берёт те же детали, что симуляция (код/симуляция/мини/assets, выгружает модели/мини/harvey_mini_parts.py),
в системах тел MuJoCo: x — вперёд, y — влево, z — вверх, мм. Координаты — Int16, base64, как в harvey_meshes.js.
    (окружение CAD) python export_web_mini.py"""
import base64
import json
import os

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(HERE, "..", "..", "код", "симуляция", "мини", "assets")
OUT = os.path.join(HERE, "..", "..", "визуализация", "lib", "harvey_mini_meshes.js")
MAT = {"orange": "printed", "grey": "grey", "servo": "servo", "tpu": "tpu", "pcb": "pcb", "battery": "battery", "screen": "screen"}


def pack(path, mat):
    m = trimesh.load(path, force="mesh")
    p = (np.asarray(m.vertices) * 1000.0)[np.asarray(m.faces)].reshape(-1, 3)      # м → мм, без индексов: плоские нормали
    s = float(np.abs(p).max()) / 32000.0 or 1.0
    q = np.round(p / s).astype(np.int16)
    return {"s": s, "n": int(len(m.faces)), "m": MAT.get(mat, "printed"), "v": base64.b64encode(q.tobytes()).decode("ascii")}


def main():
    cad = json.load(open(os.path.join(ADIR, "mini_visual.json"), encoding="utf-8"))
    meshes, tri = {}, 0
    for body, items in cad["bodies"].items():
        if body == "dock":
            continue
        meshes[body] = [pack(os.path.join(ADIR, f), mat) for f, mat in items]
        tri += sum(d["n"] for d in meshes[body])
    geo = {"G": cad["G"], "GX": cad["GX"], "GY": cad["GY"], "masses": cad["masses"], "belly_y": cad["belly_y"]}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Сгенерировано модели/рендер/export_web_mini.py из деталей симуляции мини. Не править вручную.\n")
        f.write("window.HARVEY_MINI=" + json.dumps({"geo": geo, "meshes": meshes}, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"{OUT}: {len(meshes)} тел, {tri} треугольников, {os.path.getsize(OUT) / 1e6:.2f} МБ")


if __name__ == "__main__":
    main()
