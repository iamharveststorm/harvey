# Харви — «спинной мозг» на RP2350: опрос датчиков, рефлексы, цели суставов на три шины, телеметрия для Pi.
# Устройства передаются снаружи (main.py собирает настоящие, тесты — имитацию), любого может не быть (None):
# робот работает с тем, что есть, а в телеметрии видно, чего не хватает.

import link
import reflex
from compat import ticks_diff, ticks_ms
from imu_events import ImuEvents

GOAL_POS = (42, 2)                                       # регистр цели STS (код/прошивка/pico/sts_bus.py)
PRESENT_POS = (56, 2)                                    # текущая позиция STS (там же, STATE: 56–57 — позиция)
CHARGE_A = -0.05                                         # ток через шунт ниже −50 мА — идёт заряд (знак проверить на стенде)


class Spine:
    def __init__(self, port, buses, edge=None, imu=None, ina=None, beacon=None, cfg=None, clock=ticks_ms):
        self.port, self.buses = port, buses               # buses: {"A": Bus, "B": Bus, "C": Bus}
        self.edge, self.imu, self.ina, self.beacon = edge, imu, ina, beacon
        self.cfg = cfg or {}
        self.clock = clock
        self.reader = link.LineReader()
        self.events = ImuEvents()
        self.far = [False] * 6
        self.dist = [0] * 6
        self.acc, self.gyr, self.tilt = (0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 0.0)
        self.bat = (0.0, 0.0)
        self.bat_level, self.docked, self.relaxed, self.was_blocked, self.was_lifted = "unknown", False, False, False, False
        self.ir, self.beacon_dir, self.axis = ((0, 0), (0, 0), (0, 0)), "none", "none"
        now = clock()
        self.t_imu = self.t_slow = self.t_tel = now

    # ---------- связь ----------
    def send(self, msg):
        self.port.write(link.encode(msg))

    def event(self, name, info=None):
        self.send({"t": "ev", "ev": name, "info": info})

    # ---------- датчики ----------
    def _read_edge(self):
        if self.edge is None:
            return
        self.dist = [d for d, _ in self.edge.read()]
        self.far = self.edge.flags()
        lifted = reflex.lifted(self.far)
        if lifted and not self.was_lifted:
            self.event("lifted")
            self.relax_all()
        self.was_lifted = lifted

    def _read_imu(self, now):
        if self.imu is None:
            return []
        acc, gyr = self.imu.read()
        new, self.tilt = self.events.update(acc, gyr, ticks_diff(now, self.t_imu))
        self.acc, self.gyr, self.t_imu = acc, gyr, now
        for name in new:
            self.event(name)
        if "fall" in new:
            self.relax_all()
        return new

    def _read_slow(self):
        """10 раз в секунду: батарея и маяк."""
        if self.ina is not None:
            self.bat = (self.ina.volts(), self.ina.amps())
            level = reflex.battery_level(self.bat[0], self.cfg.get("bat_low", 6.8), self.cfg.get("bat_critical", 6.4))
            if level != self.bat_level and level in ("low", "critical"):
                self.event("bat_" + level, round(self.bat[0], 2))
            self.bat_level = level
            docked = self.bat[1] < CHARGE_A
            if docked and not self.docked:
                self.event("docked", round(self.bat[1], 2))
            self.docked = docked
        if self.beacon is not None:
            from beacon import axis_side, bearing
            self.ir = self.beacon.take()
            self.beacon_dir = bearing(max(self.ir[0]), max(self.ir[2]))     # по самому заметному светодиоду
            self.axis = axis_side(*self.ir[1])

    # ---------- приводы ----------
    def relax_all(self):
        for bus in self.buses.values():
            try:
                bus.release_all()
            except Exception as e:                       # обрыв одной шины не должен останавливать остальные
                self.send({"t": "err", "msg": "relax: %s" % e})
        self.relaxed = True

    def _forward(self, q):
        per_bus = {}
        for sid, pos in q.items():
            name = reflex.bus_of(int(sid))
            if name in self.buses:
                per_bus.setdefault(name, {})[int(sid)] = max(0, min(4095, int(pos)))
        for name, values in per_bus.items():
            self.buses[name].sync_write(GOAL_POS, values)
        self.relaxed = False

    def _joints(self, msg, imu_new):
        v = tuple(msg.get("v", (0.0, 0.0, 0.0)))
        action = reflex.decide(v, self.far, imu_new, self.bat_level)
        stationary = all(abs(x) <= reflex.DEADBAND for x in v)
        if action == "go" or (action == "sit" and stationary):
            self._forward(msg.get("q", {}))
            self.was_blocked = False
        elif action == "stop" and not self.was_blocked:
            self.event("edge", [n for n, f in zip(self.cfg.get("edge_names", ()), self.far) if f])
            self.was_blocked = True
        return action

    def handle(self, msg, imu_new=()):
        t = msg.get("t")
        if t == "j":
            return self._joints(msg, imu_new)
        if t == "relax":
            self.relax_all()
        elif t == "cal" and self.edge is not None:
            self.send({"t": "cal", "base": self.edge.calibrate()})
        elif t == "pos?":
            self.send(self.positions(msg.get("ids", ())))
        elif t == "hello":
            self.send({"t": "hello", "v": link.VERSION, "missing": self.missing()})
        return t

    def positions(self, ids):
        """Где сейчас приводы (для калибровки нулей): {"t": "pos", "q": {id: позиция}, "missing": [молчащие]}."""
        q, missing = {}, []
        for sid in ids:
            bus = self.buses.get(reflex.bus_of(int(sid)))
            try:
                data = bus.read(int(sid), PRESENT_POS)
                q[str(sid)] = data[0] | (data[1] << 8)
            except Exception:                            # нет шины, привод молчит или битый ответ
                missing.append(sid)
        return {"t": "pos", "q": q, "missing": missing}

    def missing(self):
        out = [name for name, dev in (("edge", self.edge), ("imu", self.imu), ("ina", self.ina), ("beacon", self.beacon))
               if dev is None]
        if self.edge is not None:
            out += ["edge_" + n for n in self.edge.missing]
        return out

    # ---------- один проход цикла ----------
    def step(self):
        now = self.clock()
        self._read_edge()
        imu_new = self._read_imu(now)
        if ticks_diff(now, self.t_slow) >= 100:
            self._read_slow()
            self.t_slow = now
        for msg in self.reader.feed(self.port.read()):
            self.handle(msg, imu_new)
        if ticks_diff(now, self.t_tel) >= self.cfg.get("telemetry_ms", 50):
            self.send(self.telemetry(now))
            self.t_tel = now

    def telemetry(self, now):
        return {"t": "tel", "ms": now, "edge": self.dist, "far": [int(f) for f in self.far],
                "tilt": [round(a, 1) for a in self.tilt], "acc": [round(a, 3) for a in self.acc],
                "gyr": [round(g, 1) for g in self.gyr],
                "bat": [round(self.bat[0], 2), round(self.bat[1], 3)], "ir": [list(c) for c in self.ir], "beacon": self.beacon_dir,
                "axis": self.axis,
                "relaxed": int(self.relaxed)}
