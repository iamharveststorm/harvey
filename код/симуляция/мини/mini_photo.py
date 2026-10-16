"""Фотореалистичные кадры «Компакт мини» на рабочем столе (рендер Filament, PBR) — для галереи и сравнения размеров.
Стол, комната и предметы — из мира «Компакта» (../управление с клавиатуры/harvey_world.py), детали робота — из CAD.
    python mini_photo.py            # кадры mini_*.png в эту папку"""
import os, sys, math
import numpy as np
import mujoco
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "управление с клавиатуры"))
import harvey_mini as H
import harvey_world as W
import harvey_terrain as TR


def world_model():
    geoms = "\n    ".join(W.world_geoms())
    props = W.props_xml().replace(TR.stones_xml(), "")                       # камни полосы препятствий не нужны
    xml = H.build_xml(pen=False, napkin=True, world_xml=geoms + W.LIGHTS + props, visual=True)
    xml = xml.replace('<visual><global offwidth="1920" offheight="1080"/><quality shadowsize="4096"/></visual>', W.VISUAL + W.asset_xml(robot=False))
    xml = xml.replace('<light pos="0.2 -0.3 1" dir="-0.2 0.3 -1" castshadow="true"/>', "")
    assets = {k: v for k, v in W.load_assets().items() if k.startswith("world/")}; assets.update(H.load_assets())
    return xml, assets


def main():
    from mujoco.experimental.studio import renderer
    xml, assets = world_model()
    s = H.Mini.__new__(H.Mini)
    s.m = mujoco.MjModel.from_xml_string(xml, assets); s.d = mujoco.MjData(s.m)
    # инициализация как в Mini.__init__, но со своей моделью
    s.j = {k: (s.m.joint(k).qposadr[0], s.m.joint(k).dofadr[0], s.m.actuator(f"m_{k}").id) for k in H.joint_names()}
    s.kp = {"c": 3.0, "f": 4.0, "k": 4.0, "y": 2.0, "p": 3.0, "e": 3.0, "g": 1.0, "s": 1.0}; s.kd = 0.03; s.grip_lim = 0.12
    s.q = {k: 0.0 for k in s.j}; s.tq = {k: [] for k in s.j}; s.viol = 0
    tb = s.m.body("torso").jntadr[0]; qa = s.m.jnt_qposadr[tb]
    s.d.qpos[qa:qa + 3] = [0.10, -0.05, H.ZJ + 0.003]; yaw = math.radians(-20)
    s.d.qpos[qa + 3:qa + 7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
    st = s.stand_q(); s.q.update(st)
    for k, v in st.items(): s.d.qpos[s.j[k][0]] = v
    for sd in "LR":
        for jj, v in zip("ype", (math.radians(a) for a in H.TUCK_Q)): s.q[f"{sd}_{jj}"] = v; s.d.qpos[s.j[f"{sd}_{jj}"][0]] = v
    nb = s.m.body("napkin").jntadr[0]; na = s.m.jnt_qposadr[nb]
    s.d.qpos[na:na + 3] = [0.10 + 0.118 * math.cos(yaw) - H.ARM_S["L"][1] * math.sin(yaw), -0.05 + 0.118 * math.sin(yaw) + H.ARM_S["L"][1] * math.cos(yaw), 0.0008]
    s.d.qpos[na + 3:na + 7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
    mujoco.mj_forward(s.m, s.d)
    r = renderer.Renderer("opengl_headless"); r.Init(s.m)
    opt = mujoco.MjvOption(); opt.geomgroup[1] = 0
    def shot(name, az, el, dist, look=None):
        r.Init(s.m)
        cam = mujoco.MjvCamera(); cam.lookat[:] = look if look is not None else s.d.body("torso").xpos + [0.02, 0, 0.01]
        cam.distance = dist; cam.azimuth = az; cam.elevation = el
        px = r.Render(s.m, s.d, None, cam, opt, 1920, 1080)
        Image.frombytes("RGB", (1920, 1080), px).save(os.path.join(HERE, name)); print("кадр", name, flush=True)
    s.run(1.0, record=False)
    shot("mini_стол.png", 200, -18, 0.42)
    shot("mini_и_предметы.png", 235, -32, 0.75, s.d.body("torso").xpos + [0.12, 0.10, 0])
    # салфетка: присесть, прижать, провести
    s.q["L_g"] = 0.15; s.crouch(0.016)
    nap = s.d.body("napkin").xpos.copy(); press = s.to_body([nap[0], nap[1], -0.0005])
    s.move_arm("L", s.to_body(nap + [0, 0, 0.03]), 0.8, H.JAW_END); s.move_arm("L", press, 0.6, H.JAW_END)
    s.move_arm("L", press + np.array([-0.018, 0, 0]), 0.6, H.JAW_END)
    shot("mini_салфетка.png", 160, -22, 0.40)
    # правую клешню — поприветствовать (вверх, глаз наружу по правилу 2)
    s.crouch(0.0); s.set_arm("R", (math.radians(20), math.radians(80), math.radians(-30))); s.q["L_s"] = math.radians(10)
    s.run(1.2)
    shot("mini_привет.png", 205, -10, 0.45)


if __name__ == "__main__":
    main()
