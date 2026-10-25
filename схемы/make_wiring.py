"""Харви «Компакт мини» — схемы проводки (WireViz) и интерфейса шины приводов (schemdraw).

Источник чисел — заметки/Компакт мини.md, заметки/Комплектация мини.md, заметки/Питание и проводка.md
и даташит STS3032-C036 (документы/). Запуск: make_schemes.bat или
    C:\\venvs\\harvey-schemes\\Scripts\\python.exe make_wiring.py
Пишет mini_power.yml / mini_bus.yml и рядом .svg, .png, .html и .bom.tsv (спецификация жгутов) + bus_buffer.svg/.png.
"""
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
OPT = {"fontname": "Arial", "bgcolor": "WH", "bgcolor_node": "WH", "bgcolor_connector": "WH", "bgcolor_cable": "WH",
       "color_mode": "full", "mini_bom_mode": False}
SERVO = {"type": "STS3032-C036", "subtype": "6 В; упор 1,2 А, номинал 0,4 А", "pinlabels": ["GND", "+6 В", "DATA"]}
G3 = ["BK", "RD", "YE"]                       # GND, +6 В, DATA — как провода Feetech


# ------------------------------------------------------------------ лист 1: питание и логика
def power_sheet():
    c, w, x = {}, {}, []
    c["BAT"] = {"type": "Батарея 2S", "subtype": "2 × 18650 (Molicel P28A / Samsung 30Q), 7,4 В, ~22 Вт·ч",
                "pinlabels": ["B−", "BM (середина)", "B+"]}
    c["BMS"] = {"type": "BMS 2S, 10–15 А", "subtype": "с балансировкой", "pinlabels": ["B−", "BM", "B+", "P−", "P+"]}
    c["XT30"] = {"type": "XT30", "subtype": "батарея съёмная", "pinlabels": ["+", "−"]}
    c["PWR"] = {"type": "Плата питания", "subtype": "F1 10 А · INA226 (шунт 10 мОм) · «звезда» GND · 1000 мкФ",
                "pinlabels": ["BAT+ (до F1)", "BAT−", "CHG+ (после F1, до SW)", "CHG−", "→ SW", "SW →",
                              "V6 IN+ (после шунта)", "V6 IN−", "V5 IN+ (после шунта)", "V5 IN−",
                              "INA226 SDA", "INA226 SCL", "INA226 3V3", "INA226 GND"],
                "notes": "Заряд — до выключателя: робот заряжается и выключенным.<br/>Шунт INA226 в «+» после выключателя: видит весь ток робота."}
    c["SW"] = {"type": "Выключатель", "subtype": "≥ 10 А (мини-тумблеры на 3 А не годятся)", "pinlabels": ["1", "2"]}
    c["CHG"] = {"type": "Модуль заряда IP2326", "subtype": "вход 5 В → 2S, 15 Вт", "pinlabels": ["VIN+", "VIN−", "BAT+", "BAT−"]}
    c["PADS"] = {"type": "Пластины на брюхе", "subtype": "латунь 40 × 12 мм ← pogo станции 5 В 3 А", "pinlabels": ["+5 В", "GND"]}
    c["DC6"] = {"type": "DC-DC 6,0 В", "subtype": "≥ 6 А длительно, пик 8–10 А, ~17 × 23 мм",
                "pinlabels": ["IN+", "IN−", "OUT+ 6 В", "OUT−"]}
    c["DC5"] = {"type": "DC-DC 5 В 3 А", "subtype": "Mini560 или аналог", "pinlabels": ["IN+", "IN−", "OUT+ 5 В", "OUT−"]}
    c["HUB"] = {"type": "Плата шин", "subtype": "3 × буфер полудуплекса (см. bus_buffer) · 1000 мкФ на 6 В",
                "pinlabels": ["+6 В", "GND сил.", "+3,3 В", "GND лог.", "TXD A", "RXD A", "TXD B", "RXD B", "TXD C", "RXD C"],
                "notes": "Выходы A1–A3, B1–B3, C1–C3 — лист «Шины приводов»"}
    c["PI"] = {"type": "Raspberry Pi Zero 2 W", "subtype": "«голова»: Wi-Fi, камера, глаза, звук",
               "pinlabels": ["пин 2 · 5 В", "пин 6 · GND", "USB OTG VBUS", "USB OTG D−", "USB OTG D+", "USB OTG GND"],
               "notes": "У входа 5 В — конденсатор 470 мкФ"}
    c["RP"] = {"type": "RP2350-Zero", "subtype": "«спинной мозг»: шины, датчики края, IMU, заряд",
               "pinlabels": ["USB VBUS", "USB D−", "USB D+", "USB GND", "3V3 (выход)", "GND",
                             "GP0 UART0 TX", "GP1 UART0 RX", "GP4 UART1 TX", "GP5 UART1 RX",
                             "GP8 PIO TX", "GP9 PIO RX", "GP12 I2C0 SDA", "GP13 I2C0 SCL"]}

    def cab(name, n, gauge, length, colors, note, typ=None):
        w[name] = {"wirecount": n, "gauge": gauge, "length": length, "colors": colors, "notes": note}
        if typ:
            w[name]["type"] = typ

    cab("W1", 3, "18 AWG", 0.05, ["BK", "WH", "RD"], "Сборка батареи. BM — балансир, 26 AWG")
    cab("W2", 2, "18 AWG", 0.05, ["RD", "BK"], "7,4 В · ср. 1,5–2 А, пик ~10 А · защита BMS 15 А")
    cab("W3", 2, "18 AWG", 0.08, ["RD", "BK"], "7,4 В · весь ток робота")
    cab("W4", 2, "18 AWG", 0.06, ["RD", "RD"], "через выключатель — весь ток робота, пик ~10 А")
    cab("W5", 2, "22 AWG", 0.08, ["RD", "BK"], "заряд 2S · до 1,8 А (15 Вт)")
    cab("W6", 2, "20 AWG", 0.06, ["RD", "BK"], "5 В со станции · до 3 А (pogo — минимум 2 на полюс!)")
    cab("W7", 2, "18 AWG", 0.05, ["RD", "BK"], "7,4 В → 6 В · ср. 1–1,5 А, пик ~9 А")
    cab("W8", 2, "18 AWG", 0.08, ["RD", "BK"], "6 В на все 28 приводов · ход: ср. 1–2 А, пик 8–10 А")
    cab("W9", 2, "22 AWG", 0.05, ["RD", "BK"], "7,4 В → 5 В · ≤ 1,2 А")
    cab("W10", 2, "22 AWG", 0.08, ["RD", "BK"], "5 В: Pi Zero 2 W + камера + дисплеи + звук · 0,5–1,5 А")
    cab("W11", 4, "28 AWG", 0.10, ["RD", "WH", "GN", "BK"], "USB micro-B ↔ USB-C: питание RP2350 + связь Pi ↔ RP2350 (USB CDC)",
        typ="USB 2.0")
    cab("W12", 8, "28 AWG", 0.10, ["OG", "BK", "YE", "GN", "BU", "VT", "WH", "GY"], "логика 3,3 В · шины A, B, C по 1 Мбит/с")
    cab("W13", 4, "28 AWG", 0.10, ["OG", "BK", "BU", "YE"], "I2C 400 кГц · на этой же шине BMI270 и 6 × VL53L4CD")

    x += [[{"BAT": [1, 2, 3]}, {"W1": [1, 2, 3]}, {"BMS": [1, 2, 3]}],
          [{"BMS": [5, 4]}, {"W2": [1, 2]}, {"XT30": [1, 2]}],
          [{"XT30": [1, 2]}, {"W3": [1, 2]}, {"PWR": [1, 2]}],
          [{"PWR": [5, 6]}, {"W4": [1, 2]}, {"SW": [1, 2]}],
          [{"PADS": [1, 2]}, {"W6": [1, 2]}, {"CHG": [1, 2]}],
          [{"CHG": [3, 4]}, {"W5": [1, 2]}, {"PWR": [3, 4]}],
          [{"PWR": [7, 8]}, {"W7": [1, 2]}, {"DC6": [1, 2]}],
          [{"DC6": [3, 4]}, {"W8": [1, 2]}, {"HUB": [1, 2]}],
          [{"PWR": [9, 10]}, {"W9": [1, 2]}, {"DC5": [1, 2]}],
          [{"DC5": [3, 4]}, {"W10": [1, 2]}, {"PI": [1, 2]}],
          [{"PI": [3, 4, 5, 6]}, {"W11": [1, 2, 3, 4]}, {"RP": [1, 2, 3, 4]}],
          [{"RP": [5, 6, 7, 8, 9, 10, 11, 12]}, {"W12": [1, 2, 3, 4, 5, 6, 7, 8]}, {"HUB": [3, 4, 5, 6, 7, 8, 9, 10]}],
          [{"RP": [5, 6, 13, 14]}, {"W13": [1, 2, 3, 4]}, {"PWR": [13, 14, 11, 12]}]]
    return {"metadata": {"title": "Харви «Компакт мини» — питание и логика"}, "options": OPT,
            "connectors": c, "cables": w, "connections": x}


# ------------------------------------------------------------------ лист 2: шины приводов
LIMBS = [  # (имя, шина, выход, суставы, длина до первого привода, пик тока, ср. ток)
    ("LF", "A", 1, ["поворот", "бедро", "колено"], 0.10, "3,6", "0,1–0,6"),
    ("LM", "A", 2, ["поворот", "бедро", "колено"], 0.08, "3,6", "0,1–0,6"),
    ("LB", "A", 3, ["поворот", "бедро", "колено"], 0.10, "3,6", "0,1–0,6"),
    ("RF", "B", 1, ["поворот", "бедро", "колено"], 0.10, "3,6", "0,1–0,6"),
    ("RM", "B", 2, ["поворот", "бедро", "колено"], 0.08, "3,6", "0,1–0,6"),
    ("RB", "B", 3, ["поворот", "бедро", "колено"], 0.10, "3,6", "0,1–0,6"),
    ("CL", "C", 1, ["поворот плеча", "подъём", "локоть", "захват"], 0.10, "4,8", "0,1–0,3"),
    ("CR", "C", 2, ["поворот плеча", "подъём", "локоть", "захват"], 0.10, "4,8", "0,1–0,3"),
    ("EY", "C", 3, ["глаз левый", "глаз правый"], 0.08, "2,4", "до 0,1"),
]
LIMB_RU = {"LF": "левая передняя нога", "LM": "левая средняя нога", "LB": "левая задняя нога",
           "RF": "правая передняя нога", "RM": "правая средняя нога", "RB": "правая задняя нога",
           "CL": "левая клешня", "CR": "правая клешня", "EY": "глаза"}
LIMB_ID = {"LF": 10, "LM": 20, "LB": 30, "RF": 40, "RM": 50, "RB": 60, "CL": 70, "CR": 80, "EY": 90}


def bus_sheet():
    c, w, x = {}, {}, []
    for bus, what in (("A", "левые ноги, 9 приводов"), ("B", "правые ноги, 9 приводов"), ("C", "клешни и глаза, 10 приводов")):
        lab = []
        for k in (1, 2, 3):
            lab += [f"{bus}{k} GND", f"{bus}{k} +6 В", f"{bus}{k} DATA"]
        c[f"HUB_{bus}"] = {"type": f"Плата шин — шина {bus}", "subtype": what, "pinlabels": lab,
                           "notes": "питание к каждой конечности — своим проводом («звезда»);<br/>DATA — общая для шины"}
    for n, bus, k, joints, ln, peak, avg in LIMBS:
        base = (k - 1) * 3
        prev = f"HUB_{bus}"
        prev_pins = [base + 1, base + 2, base + 3]
        for j, jn in enumerate(joints, 1):
            sid = LIMB_ID[n] + j
            cn = f"{n}{j}"
            c[cn] = dict(SERVO, type=f"{n} · {jn}", subtype=f"STS3032-C036 · ID {sid}")
            wn = f"W_{n}{j}"
            if j == 1:
                left = len(joints)
                w[wn] = {"wirecount": 3, "gauge": "22 AWG", "length": ln, "colors": G3,
                         "notes": f"{LIMB_RU[n]}: ток {left} приводов · ср. {avg} А, пик {peak} А"}
            else:
                left = len(joints) - j + 1
                w[wn] = {"wirecount": 3, "gauge": "28 AWG", "length": 0.15, "colors": G3,
                         "type": "1,25 мм, 3-pin (из комплекта привода)",
                         "notes": f"ток {left} {'привода' if left < 5 else 'приводов'} · пик {1.2 * left:.1f} А".replace(".", ",")}
            x.append([{prev: prev_pins}, {wn: [1, 2, 3]}, {cn: [1, 2, 3]}])
            prev, prev_pins = cn, [1, 2, 3]
    return {"metadata": {"title": "Харви «Компакт мини» — шины приводов"}, "options": OPT,
            "connectors": c, "cables": w, "connections": x}


# ------------------------------------------------------------------ интерфейс шины (schemdraw)
def bus_buffer():
    """Интерфейс одной шины по схеме Feetech (даташит STS3032-C036, п. 12): два буфера и автопереключение направления."""
    import schemdraw
    import schemdraw.elements as elm
    schemdraw.use("matplotlib")
    schemdraw.config(font="Arial", fontsize=11)
    d = schemdraw.Drawing(show=False)
    L = lambda a, b: elm.Line().at(a).to(b)
    with d:
        u1 = elm.Ic(pins=[elm.IcPin(name="A", pin="2", side="left", slot="2/2"), elm.IcPin(name="OE", pin="1", side="left", slot="1/2"),
                          elm.IcPin(name="Y", pin="4", side="right"), elm.IcPin(name="VCC", pin="5", side="top"),
                          elm.IcPin(name="GND", pin="3", side="bot")],
                    size=(4.6, 2.6), label="U1 SN74LVC1G126\nпередача").at((0, 0))
        d += u1
        u2 = elm.Ic(pins=[elm.IcPin(name="Y", pin="4", side="left", slot="2/2"), elm.IcPin(name="OE̅", anchorname="nOE", pin="1", side="left", slot="1/2"),
                          elm.IcPin(name="A", pin="2", side="right"), elm.IcPin(name="VCC", pin="5", side="top"),
                          elm.IcPin(name="GND", pin="3", side="bot")],
                    size=(4.6, 2.6), label="U2 SN74LVC1G125\nприём").at((0, -8.5))
        d += u2
        for u in (u1, u2):
            d += elm.Line().up(0.7).at(u.VCC); d += elm.Vdd().label("+3,3 В")
            d += elm.Line().down(0.5).at(u.GND); d += elm.Ground()
        # TXD → U1.A, отвод на базу Q1
        xa, ya = u1.A
        d += L((xa - 7.5, ya), (xa, ya))
        d += elm.Dot(open=True).at((xa - 7.5, ya)).label("TXD ← RP2350 (GP0)", "left")
        d += elm.Dot().at((xa - 5.5, ya))
        d += elm.Resistor().down(3.0).at((xa - 5.5, ya)).label("R1\n10 кОм", loc="top")
        q = elm.BjtPnp(circle=True).right().anchor("base").label("Q1\nPNP", loc="right")
        d += q
        d += elm.Line().up(0.4).at(q.emitter); d += elm.Vdd().label("+3,3 В")
        d += elm.Line().down(0.6).at(q.collector)
        txen = d.here
        d += elm.Dot()
        d += elm.Resistor().down(2.0).label("R2\n20 кОм", loc="bottom"); d += elm.Ground()
        # TXEN → U1.OE и U2.OE̅
        xo, yo = u1.OE
        xj = xo - 1.4
        d += L(txen, (xj, txen[1])); d += elm.Label().at(((txen[0] + xj) / 2, txen[1] + 0.35)).label("TXEN")
        d += elm.Dot().at((xj, txen[1]))
        d += L((xj, txen[1]), (xj, yo)); d += L((xj, yo), (xo, yo))
        xn, yn = u2.nOE
        d += L((xj, txen[1]), (xj, yn)); d += L((xj, yn), (xn, yn))
        # U2.Y → RXD
        xy, yy = u2.Y
        d += L((xy, yy), (xa - 7.5, yy)); d += elm.Dot(open=True).at((xa - 7.5, yy)).label("RXD → RP2350 (GP1)", "left")
        # DATA: U1.Y и U2.A, подтяжка, разъём
        x1, y1 = u1.Y; x2, y2 = u2.A
        xd = x1 + 1.6
        d += L((x1, y1), (xd + 3.2, y1)); d += elm.Dot().at((xd, y1))
        d += L((xd, y1), (xd, y2)); d += L((xd, y2), (x2, y2))
        d += elm.Dot().at((xd + 1.6, y1))
        d += elm.Resistor().up(2.0).at((xd + 1.6, y1)).label("R3\n10 кОм", loc="bottom"); d += elm.Vdd().label("+3,3 В")
        d += elm.Dot(open=True).at((xd + 3.2, y1)).label("DATA → шина (контакт 3 разъёма привода)", "right")
        d += elm.Label().at((xa - 9.0, y2 - 4.4)).label(
            "Одна из трёх шин (A, B, C) — схема Feetech, даташит STS3032-C036, п. 12. C1, C2 — 100 нФ у выводов VCC U1 и U2.\n"
            "TXD в покое = 1 → Q1 закрыт → TXEN = 0: U1 отключён, U2 передаёт DATA на RXD — приём.\n"
            "TXD = 0 (стартовый бит) → Q1 открыт → TXEN = 1: U1 передаёт TXD на DATA, U2 отключён — передача.\n"
            "Буферы — именно LVC: их входы выдерживают 5 В с шины. Питание буферов 3,3 В — от RP2350.",
            halign="left", valign="top")
    return d


def render(name, data):
    path = os.path.join(HERE, name + ".yml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    exe = os.path.join(os.path.dirname(sys.executable), "wireviz.exe")
    subprocess.run([exe if os.path.exists(exe) else "wireviz", "-f", "hpst", path], check=True)
    print("готово:", name)


if __name__ == "__main__":
    os.environ["PATH"] = r"C:\Program Files\Graphviz\bin;" + os.environ.get("PATH", "")
    render("mini_power", power_sheet())
    render("mini_bus", bus_sheet())
    d = bus_buffer()
    d.save(os.path.join(HERE, "bus_buffer.svg"))
    d.save(os.path.join(HERE, "bus_buffer.png"), dpi=150)
    print("готово: bus_buffer")
