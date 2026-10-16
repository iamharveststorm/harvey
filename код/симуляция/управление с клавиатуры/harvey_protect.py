"""Проверка рефлекса защиты глаз Харви: робота опрокидывают вбок или через нос,
IMU замечает падение, глаза складываются наружу до упора (−105°, ниже арки хвоста), клешни встают щитом.
Сравнивается сила удара по дисплеям с рефлексом и без. Запуск: python harvey_protect.py"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import math, numpy as np, mujoco
import harvey_sim as H, harvey_scenarios as S
DT=S.DT
SHIELD={"L":np.array([0.185,0.030,0.008]),"R":np.array([0.185,-0.030,0.008])}   # компоновка v2: плечи (105; ±30)
EYE_FOLD=math.radians(-105)

def eye_force(s):
    m,d=s.m,s.d; ids={m.geom("L_disp").id,m.geom("R_disp").id}; f=0.0; who=set()
    for i in range(d.ncon):
        c=d.contact[i]
        if c.geom1 in ids or c.geom2 in ids:
            f6=np.zeros(6); mujoco.mj_contactForce(m,d,i,f6); f+=abs(f6[0])
            other=c.geom2 if c.geom1 in ids else c.geom1
            who.add(mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,other) or mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,m.geom_bodyid[other]))
    return f,who

def trial(reflex, push=(18.0,0.25), axis=0, label="", smart=False):
    side=None
    s=S.Sim3(0.0)
    q=H.pose_targets(H.REACH_WORK,H.ZJ)
    arm={n:H.Sim2.tuck(n) for n in "LR"}; eye=0.0
    t_trig=t_eye=t_claw=t_flip=None; peak=0; hits=set(); armq=None
    for i in range(int(3.0/DT)):
        t=i*DT
        tb=s.d.body("torso").id
        # «кот» толкает: момент вокруг продольной оси (опрокидывание вбок) или поперечной (через нос)
        if 0.5<=t<0.5+push[1]:
            s.d.xfrc_applied[tb][3+axis]=push[0]
            s.d.xfrc_applied[tb][2]=0
        else:
            s.d.xfrc_applied[tb][:]=0
        tilt=s.tilt()
        w=np.linalg.norm(s.d.qvel[3:6])
        if reflex and t_trig is None and (tilt>35 or w>4.0):
            t_trig=t
        if t_trig is not None:
            arm=SHIELD
            if smart:   # глаз на стороне, куда падаем, — внутрь (вверх от стола), второй — наружу до упора
                if side is None:
                    Rm=s.d.body("torso").xmat.reshape(3,3); side=("L" if Rm[2,1]<0 else "R") if abs(Rm[2,1])>0.05 else "front"
                eye=EYE_FOLD if side=="front" else {side:math.radians(20),("R" if side=="L" else "L"):EYE_FOLD}
            else:
                eye=EYE_FOLD
        s.step(q,arm,eye)
        if t_trig is not None:
            tg=eye if isinstance(eye,dict) else {"L":eye,"R":eye}
            if t_eye is None and abs(s.d.qpos[s.jid["L_s"]]-tg["L"])<math.radians(10) and abs(s.d.qpos[s.jid["R_s"]]-tg["R"])<math.radians(10): t_eye=t
            if t_claw is None and max(np.linalg.norm(s.tip(n)-SHIELD[n]) for n in "LR")<0.02: t_claw=t
        R=s.d.body("torso").xmat.reshape(3,3)
        if t_flip is None and R[2,2]<0: t_flip=t   # корпус лёг больше чем на 90°
        f,who=eye_force(s); peak=max(peak,f); hits|=who
    up=s.d.body("torso").xmat.reshape(3,3)[2,2]
    fmt=lambda x:"—" if x is None else f"{(x-0.5)*1000:.0f} мс"
    print(f"{label}: рефлекс={('по стороне' if smart else 'да') if reflex else 'нет'}; срабатывание {fmt(t_trig)}; глаза сложены {fmt(t_eye)}; клешни-щит {fmt(t_claw)}; "
          f"корпус за 90° {fmt(t_flip)}; итог {'на спине' if up<-0.5 else ('на боку' if up<0.5 else 'на ногах')}; "
          f"макс. сила на дисплеи {peak:.1f} Н; кто касался глаз: {sorted(hits) if hits else 'никто'}", flush=True)

for lbl,ax,F in (("Вбок, резкий удар 18 Н·м",0,18.0),("Вбок, толчок 7 Н·м",0,7.0),("Через нос, резкий −14 Н·м",1,-14.0),("Через нос, толчок −6 Н·м",1,-6.0)):
    trial(False,axis=ax,push=(F,0.25),label=lbl)
    trial(True,axis=ax,push=(F,0.25),label=lbl)
    trial(True,axis=ax,push=(F,0.25),label=lbl,smart=True)
