"""Харви: токи по шинам питания из симуляции (12 В — STS3215, 6 В — STS3032 и насос). Запуск: python harvey_power.py"""
import sys as _s
try:
    _s.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, math, json
import harvey_teleop as TP, harvey_sim as H
KT15=2.94/2.7; KT32=0.44/1.2
def currents(tp):
    s=tp.sim; d=s.d; tq=s.tq
    legs=sum(0.03+abs(t)/KT15+0.15*abs(w)/H.W0 for k,(t,w) in tq.items() if k[1]!="_")
    claw15=sum(0.03+abs(t)/KT15+0.15*abs(w)/H.W0 for k,(t,w) in tq.items() if k[1]=="_" and k[2] in "pe")
    s32=sum(0.02+abs(t)/KT32+0.1*abs(w)/H.W32 for k,(t,w) in tq.items() if k[1]=="_" and k[2] in "yrs")
    tail15=0; tail32=0
    for j in "pe":
        jt=s.m.joint(f"T_{j}"); tau=d.ctrl[s.m.actuator(f"m_T_{j}").id]; w=d.qvel[jt.dofadr[0]]
        tail15+=0.03+abs(tau)/KT15+0.15*abs(w)/H.W0
    for j in "yw":
        jt=s.m.joint(f"T_{j}"); tau=d.ctrl[s.m.actuator(f"m_T_{j}").id]; w=d.qvel[jt.dofadr[0]]
        tail32+=0.02+abs(tau)/KT32+0.1*abs(w)/H.W32
    grip=sum(0.02+abs(d.ctrl[s.m.actuator(f"m_{n}_g").id])/KT32 for n in "LR")
    pump=0.6 if d.ctrl[s.suck]>0 else 0.0
    return dict(legs=legs, claws12=claw15, tail12=tail15, s32=s32+tail32+grip+0.02, pump=pump)
def run(label, actions):
    tp=TP.Teleop(); rows=[]
    for act,sec in actions:
        if act: (tp.key(act,hold=True) if act in tp.MOVE else tp.key(act))
        for i in range(int(sec/TP.DT)):
            tp.step(); rows.append(currents(tp))
        if act in tp.MOVE: tp.release(act)
    r={k:np.array([x[k] for x in rows]) for k in rows[0]}
    rail12=r["legs"]+r["claws12"]+r["tail12"]; rail6=r["s32"]+r["pump"]
    # пики по окнам 1 мс (2 шага) и 99-й перцентиль
    def st(a): 
        w=np.convolve(a,np.ones(2)/2,mode="valid")
        return dict(mean=round(float(a.mean()),2),p99=round(float(np.percentile(a,99)),2),peak=round(float(w.max()),2))
    out=dict(rail12=st(rail12), legs=st(r["legs"]), claws12=st(r["claws12"]), tail12=st(r["tail12"]), rail6=st(rail6))
    print(label, json.dumps(out,ensure_ascii=False), flush=True)
    return out
res={}
res["стоит"]=run("стоит",[(None,3.0)])
res["ходьба комфорт"]=run("ходьба",[("W",6.0)])
res["ходьба быстро"]=run("быстро",[("F",0.01),("W",5.0)])
res["хвост: телефон на спину"]=run("хвост",[("T",18.5)])
res["поза: лечь и встать"]=run("лечь-встать",[("R",2.0),("R",2.5)])
res["клешни: к столу и на спину"]=run("клешни",[("2",2.5),("3",2.5),("1",2.5)])
json.dump(res,open('power_results.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
