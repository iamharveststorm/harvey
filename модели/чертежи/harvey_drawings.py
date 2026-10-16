"""Харви: чертежи деталей по ГОСТ (A3, основная надпись) из FreeCAD 1.1.
Параметры берутся из тех же скриптов, что делают STL (модели/стенд ноги/harvey_leg_parts.py,
модели/стенд кисти/harvey_hand_parts.py), — чертёж и печатная деталь не расходятся.
Запуск (откроется и закроется окно FreeCAD — так он выгружает PDF):
    "C:\\Users\\iamha\\AppData\\Local\\Programs\\FreeCAD 1.1\\bin\\freecad.exe" harvey_drawings.py
Результат в этой папке: PDF чертежей, FCStd (открыть и править в FreeCAD), STEP моделей (для Onshape),
_проверка.txt — объёмы для сверки с моделью STL."""
import os, math, ast, traceback, datetime
import FreeCAD as App, Part, TechDraw
from FreeCAD import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG = open(os.path.join(HERE, "_проверка.txt"), "a" if App.GuiUp else "w", encoding="utf-8")
TEMPLATE = App.getResourceDir() + "Mod/TechDraw/Templates/ISO/localized/ru/Leading/Landscape_A3.svg"
TODAY = datetime.date.today().strftime("%d.%m.%y")


def log(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n"); LOG.flush()


def read_P(path):
    """Словарь P = dict(...) из скрипта детали, без запуска самого скрипта."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "P":
            return {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
    raise RuntimeError("нет P в " + path)


LEG = read_P(os.path.join(ROOT, "стенд ноги", "harvey_leg_parts.py"))
HAND = read_P(os.path.join(ROOT, "стенд кисти", "harvey_hand_parts.py"))


# ---------------- примитивы ----------------
def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cylx(r, x0, x1, y, z):
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def cyly(r, y0, y1, x, z):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cylz(r, z0, z1, x, y):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def roty(s, deg, cx, cz):
    s = s.copy(); s.rotate(V(cx, 0, cz), V(0, 1, 0), deg); return s


def rot_pt(x, z, deg, cx, cz):
    a = math.radians(deg)   # как Part.rotate вокруг +y: x' = x·cos + z·sin, z' = −x·sin + z·cos
    dx, dz = x - cx, z - cz
    return cx + dx * math.cos(a) + dz * math.sin(a), cz - dx * math.sin(a) + dz * math.cos(a)


def hull_xz(pts, y0, y1):
    """Выпуклая оболочка точек (x, z), вытянутая по y от y0 до y1."""
    pts = sorted(set((round(x, 9), round(z, 9)) for x, z in pts))
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    w = Part.makePolygon([V(x, y0, z) for x, z in h] + [V(h[0][0], y0, h[0][1])])
    return Part.Face(w).extrude(V(0, y1 - y0, 0))


def fuse(shapes):
    s = shapes[0]
    for t in shapes[1:]:
        s = s.fuse(t)
    return s.removeSplitter()


def cut(s, tools):
    for t in tools:
        s = s.cut(t)
    return s.removeSplitter()


# ---------------- рычаг 100 мм (стенд ноги) ----------------
def lever():
    t, r1, r2, d = 6.0, 15.0, 6.0, 112.0
    a = math.acos((r1 - r2) / d)
    p1, p2 = V(r1 * math.cos(a), r1 * math.sin(a), 0), V(d + r2 * math.cos(a), r2 * math.sin(a), 0)
    p3, p4 = V(d + r2 * math.cos(a), -r2 * math.sin(a), 0), V(r1 * math.cos(a), -r1 * math.sin(a), 0)
    edges = [Part.LineSegment(p1, p2).toShape(),
             Part.ArcOfCircle(Part.Circle(V(d, 0, 0), V(0, 0, 1), r2), -a, a).toShape(),
             Part.LineSegment(p3, p4).toShape(),
             Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), r1), a, 2 * math.pi - a).toShape()]
    m = Part.Face(Part.Wire(Part.__sortEdges__(edges))).extrude(V(0, 0, t))
    tools = [cylz(LEG["flange_D"] / 2 + 0.3, -0.01, 1.3, 0, 0), cylz(3.6, -1, t + 1, 0, 0)]
    for k in range(4):
        ang = math.radians(45 + 90 * k)
        pa = (5.5 * math.cos(ang), 5.5 * math.sin(ang)); pb = (9.5 * math.cos(ang), 9.5 * math.sin(ang))
        rr = LEG["m3"] / 2
        slot = fuse([cylz(rr, -1, t + 1, *pa), cylz(rr, -1, t + 1, *pb)])
        b = Part.makeBox(4.0, 2 * rr, t + 2, V(0, -rr, -1)); b.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(ang)); b.translate(V(*pa, 0))
        tools.append(fuse([slot, b]))
    tools += [cylz(LEG["m3"] / 2, -1, t + 1, 100, 0), box(107, 117, -1.75, 1.75, -1, t + 1)]
    return cut(m, tools)


# ---------------- ладонь кисти (стенд кисти) ----------------
H = HAND
X0 = -(H["body_L"] - H["shaft_from_end"]); X1 = H["shaft_from_end"]
G_X = 45.0
G_S = H["horn_top"] + H["jaw_w"] / 2
CONTACT_Z, PIVOT_X = -8.5, 56.0
HALF = H["jaw_w"] / 2


def finger_bar(z0, z1):
    b = H["bend"]
    root = box(PIVOT_X - 2, PIVOT_X, -HALF, HALF, z0, z1)
    tip = roty(box(PIVOT_X, PIVOT_X + H["finger"], -HALF, HALF, z0, z1), b, PIVOT_X, CONTACT_Z)
    pts = [(PIVOT_X - 2, z0), (PIVOT_X - 2, z1), (PIVOT_X, z0), (PIVOT_X, z1)]
    pts += [rot_pt(x, z, b, PIVOT_X, CONTACT_Z) for x in (PIVOT_X, PIVOT_X + 2) for z in (z0, z1)]
    joint = hull_xz(pts, -HALF, HALF)
    end = roty(cyly((z1 - z0) / 2, -HALF, HALF, PIVOT_X + H["finger"], (z0 + z1) / 2), b, PIVOT_X, CONTACT_Z)
    return fuse([root, tip, joint, end])


def palm():
    lower_top = CONTACT_Z - H["pad"] - 0.5
    px0, px1 = G_X + X0 - 2.0, G_X + X1 + 2.3
    body = fuse([
        cylx(8.0, 0, 4.0, 0, 0),                                          # диск на качалку запястья
        box(px0, px1, G_S - 3, G_S, -11, 11),                             # пластина привода 22
        box(2, G_X + X0 - 2.0 + 0.5, 3.8, 6.8, -9.5, 9.5),                # стенка
        box(2, G_X + X0, -1, 6.8, 7.3, 9.5), box(2, G_X + X0, -1, 6.8, -9.5, -7.3),   # рёбра
        box(G_X - 5, PIVOT_X, -HALF, 6.8, lower_top - 5.5, lower_top),     # мост к нижнему пальцу
        box(G_X + 1, PIVOT_X, 3.8, 6.8, lower_top - 5.5, -7.5),
        finger_bar(lower_top - 4, lower_top)])
    hr, cr = H["m2"] / 2, H["m2_head"] / 2
    tools = [cylx(2.3, -1, 5, 0, 0)]
    for y, z in [(0, 5), (-5, 0), (0, -5)]:                               # 3 винта в качалку запястья
        tools += [cylx(hr, -1, 5, y, z), cylx(cr, 2.8, 4.01, y, z)]
    tools.append(cyly(H["horn_D"] / 2 + 0.5, G_S - 3.5, G_S + 0.5, G_X, 0))   # окно под качалку привода 22
    for hx in H["holes_x"][:2]:
        for z in (H["holes_y"], -H["holes_y"]):
            tools += [cyly(hr, G_S - 3.5, G_S + 0.5, G_X + hx, z), cyly(cr, G_S - 3.01, G_S - 3 + 1.6, G_X + hx, z)]
    g = box(PIVOT_X + 2, PIVOT_X + H["finger"] - 1, -HALF + 0.6, HALF - 0.6, lower_top - 0.5, lower_top + 0.001)
    tools.append(roty(g, H["bend"], PIVOT_X, CONTACT_Z))                  # паз под накладку TPU
    return cut(body, tools)


# ---------------- оформление листов ----------------
class Sheet:
    def __init__(self, doc, name, title, number, material, scale_txt, mass_g):
        self.doc = doc
        self.page = doc.addObject("TechDraw::DrawPage", name)
        tpl = doc.addObject("TechDraw::DrawSVGTemplate", name + "_tpl")
        tpl.Template = TEMPLATE
        self.page.Template = tpl
        f = dict(tpl.EditableTexts)
        f.update({"Название": title, "Номер": number, "Масштаб": scale_txt, "Масса": "%.0f г" % mass_g,
                  "Материал1": material, "Материал2": "", "Материал3": "",
                  "Организация1": "", "Организация2": "Проект «Харви»", "Организация3": "",
                  "Разработал": "Claude", "Проверил": "", "Утвердил": "",
                  "Дата_разработки": TODAY, "Дата_проверки": "", "Дата_утверждения": "",
                  "Лист": "1", "Листов": "1", "Информация": ""})
        tpl.EditableTexts = f
        self.n = 0

    def view(self, obj, direction, xdir, x, y, scale, hidden=True):
        self.n += 1
        v = self.doc.addObject("TechDraw::DrawViewPart", "%s_v%d" % (self.page.Name, self.n))
        self.page.addView(v)
        v.Source = [obj]; v.Direction = direction; v.XDirection = xdir
        v.ScaleType = "Custom"; v.Scale = scale; v.X, v.Y = x, y
        v.HardHidden = hidden; v.SmoothVisible = True
        return v

    def text(self, lines, x, y, size=3.5):
        self.n += 1
        a = self.doc.addObject("TechDraw::DrawViewAnnotation", "%s_t%d" % (self.page.Name, self.n))
        self.page.addView(a)
        a.Text = lines; a.TextSize = size; a.X, a.Y = x, y
        a.Font = "osifont"
        return a


def edges_of(v):
    out, i = [], 0
    while True:
        try:
            out.append((i, v.getEdgeByIndex(i)))
        except Exception:
            return out
        i += 1


def find_circle(v, r, cx=None, cy=None, tol=0.05):
    """Имя кромки-окружности радиуса r (в мм детали) с центром около (cx, cy) в координатах вида."""
    s = v.getScale()
    best = None
    for i, e in edges_of(v):
        c = e.Curve
        if not hasattr(c, "Radius"):
            continue
        for k in (1.0, s):
            if abs(c.Radius - r * k) < tol * k:
                dist = 0 if cx is None else math.hypot(c.Center.x - cx * k, c.Center.y - cy * k)
                if best is None or dist < best[0]:
                    best = (dist, "Edge%d" % i)
    if best is None:
        raise RuntimeError("не найдена окружность r=%s в %s" % (r, v.Name))
    return best[1]


def proj(v, p):
    """Точка детали → точка вида без масштаба, от центра габарита вида (так отсчитываются вершины вида)."""
    c = v.Source[0].Shape.BoundBox.Center
    q, q0 = v.projectPoint(p), v.projectPoint(c)
    return V(q.x - q0.x, q.y - q0.y, 0)


def n_vertices(v):
    i = 0
    while True:
        try:
            v.getVertexByIndex(i)
        except Exception:
            return i
        i += 1


def vertex_at(v, p):
    """Имя вершины вида в точке детали p: ставит косметическую вершину (она добавляется в конец списка).
    У косметических вершин ось y вида перевёрнута относительно геометрии — ставим 2D-вершину и, если
    она легла зеркально, переставляем с обратным знаком y; в конце проверяем, что она там, где точка детали."""
    t = proj(v, p)
    for sy in (1, -1):
        n0 = n_vertices(v)
        tag = v.makeCosmeticVertex(V(t.x, sy * t.y, 0))
        v.Document.recompute()
        q = v.getVertexByIndex(n0).Point
        if math.hypot(q.x - t.x, q.y - t.y) < 0.05:
            return "Vertex%d" % n0
        v.removeCosmeticVertex(tag); v.Document.recompute()
    raise RuntimeError("вершина не на месте: %s в %s, ждали %s" % (p, v.Name, t))


def vpos(v, p, dx=0, dy=0):
    """Положение на листе (относительно центра вида, мм листа) для точки детали p со сдвигом."""
    t = proj(v, p); s = v.getScale()
    return t.x * s + dx, t.y * s + dy


def dim_circle(sheet, v, kind, r, cx=None, cy=None, fmt=None, dx=0, dy=0):
    d = sheet.doc.addObject("TechDraw::DrawViewDimension", "Dim")
    d.Type = kind; d.MeasureType = "Projected"
    sheet.page.addView(d)
    d.References2D = [(v, find_circle(v, r, cx, cy))]
    if fmt: d.FormatSpec = fmt
    d.X, d.Y = dx, dy
    return d


def dim_pts(sheet, v, kind, a, b, x=None, y=None, fmt=None):
    ra, rb = vertex_at(v, a), vertex_at(v, b)
    d = sheet.doc.addObject("TechDraw::DrawViewDimension", "Dim")
    d.Type = kind; d.MeasureType = "Projected"
    sheet.page.addView(d)
    d.References2D = [(v, ra), (v, rb)]
    if fmt: d.FormatSpec = fmt
    if x is not None: d.X = x
    if y is not None: d.Y = y
    return d


# ---------------- листы ----------------
def sheet_lever(doc):
    s = lever()
    obj = doc.addObject("Part::Feature", "Рычаг_100мм"); obj.Shape = s
    log("рычаг: объём %.1f мм³, габарит %s, valid %s" % (s.Volume, s.BoundBox, s.isValid()))
    sh = Sheet(doc, "Лист_рычаг", "Рычаг 100 мм", "ХАРВИ.01.001", "PETG", "2:1", s.Volume / 1000 * 1.27)
    main = sh.view(obj, V(0, 0, 1), V(1, 0, 0), 175, 205, 2.0)         # главный вид — сверху на рычаг
    side = sh.view(obj, V(0, 1, 0), V(1, 0, 0), 175, 145, 2.0)         # вид на кромку (ГОСТ, 1-й угол — под главным)
    sh.view(obj, V(1, -1, 1), V(1, 1, 0), 325, 105, 0.8, hidden=False)  # изометрия
    doc.recompute()
    P0 = lambda x, y=0.0, z=6.0: V(x, y, z)
    dim_pts(sh, main, "DistanceX", P0(-15), P0(118), x=vpos(main, P0(51.5))[0], y=48)
    dim_pts(sh, main, "DistanceX", P0(0), P0(100), x=vpos(main, P0(50))[0], y=38)
    ux, uy = vpos(main, P0(15 * math.cos(math.radians(135)), 15 * math.sin(math.radians(135))))
    dim_circle(sh, main, "Radius", 15, dx=ux - 12, dy=uy + 10)
    dim_circle(sh, main, "Radius", 6, dx=vpos(main, P0(118, 4))[0] + 10, dy=vpos(main, P0(118, 4))[1] + 14)
    h = proj(main, P0(100))
    dim_circle(sh, main, "Diameter", LEG["m3"] / 2, h.x, h.y, fmt="⌀%.1w сквозное", dx=vpos(main, P0(100))[0] - 6, dy=-30)
    dim_circle(sh, main, "Diameter", 3.6, fmt="⌀%.1w", dx=vpos(main, P0(0))[0] + 4, dy=-42)
    dim_pts(sh, main, "DistanceY", P0(117, -1.75), P0(117, 1.75), x=vpos(main, P0(118))[0] + 12, fmt="%.1w")
    dim_pts(sh, main, "DistanceX", P0(107, -1.75), P0(117, -1.75), x=vpos(main, P0(112))[0], y=-22)
    S0 = lambda x, z: V(x, 0, z)
    dim_pts(sh, side, "DistanceY", S0(118, 0), S0(118, 6), x=vpos(side, S0(118, 3))[0] + 10)
    dim_pts(sh, side, "DistanceX", S0(-10.3, 0), S0(10.3, 0), x=vpos(side, S0(0, 0))[0], y=-16, fmt="⌀%.1w")
    dim_pts(sh, side, "DistanceY", S0(-10.3, 0), S0(-10.3, 1.3), x=vpos(side, S0(-15, 0))[0] - 10, fmt="%.1w")
    sh.text(["Технические требования",
             "1. Печать: PETG, слой 0,2 мм, 3 периметра, заполнение 40 %,",
             "   плашмя, гнездом под фланец вниз.",
             "2. Отверстие ⌀3,4 — ровно 100 мм от оси привода: по нему",
             "   считается момент (замер 3) и вешается груз 1 кг (замер 7).",
             "3. Гнездо ⌀20,6 глубиной 1,3 — посадка на фланец привода;",
             "   4 радиальных паза шириной 3,4 на радиусах 5,5–9,5 под 45° —",
             "   под винты M3 × 8 при любом шаге отверстий фланца.",
             "4. Паз 10 × 3,5 у конца — под стяжку лазерной указки (замер 5).",
             "5. Размеры для справок; модель — harvey_leg_parts.py."], 110, 80, 3.5)
    return sh.page, obj


def sheet_palm(doc):
    s = palm()
    obj = doc.addObject("Part::Feature", "Ладонь_кисти"); obj.Shape = s
    log("ладонь: объём %.1f мм³, габарит %s, valid %s" % (s.Volume, s.BoundBox, s.isValid()))
    sh = Sheet(doc, "Лист_ладонь", "Ладонь кисти", "ХАРВИ.02.002", "PETG", "2:1", s.Volume / 1000 * 1.27)
    main = sh.view(obj, V(0, -1, 0), V(1, 0, 0), 120, 205, 2.0)        # главный вид — со стороны пальцев
    top = sh.view(obj, V(0, 0, 1), V(1, 0, 0), 120, 117, 2.0)           # вид сверху — под главным
    left = sh.view(obj, V(-1, 0, 0), V(0, -1, 0), 262, 205, 2.0)        # вид слева — справа от главного
    sh.view(obj, V(1, -1, 1), V(1, 1, 0), 350, 150, 1.0, hidden=False)  # изометрия
    doc.recompute()
    lt = CONTACT_Z - H["pad"] - 0.5
    hx0, hx1, hy = G_X + H["holes_x"][0], G_X + H["holes_x"][1], H["holes_y"]
    M = lambda x, z: V(x, -HALF, z)
    dim_pts(sh, main, "DistanceX", M(0, 0), M(G_X, 0), x=vpos(main, M(G_X / 2, 0))[0], y=54)
    dim_pts(sh, main, "DistanceX", M(hx0, hy), M(hx1, hy), x=vpos(main, M((hx0 + hx1) / 2, 0))[0], y=45)
    dim_pts(sh, main, "DistanceY", M(hx0, hy), M(hx0, -hy), x=vpos(main, M(G_X + X0 - 2.0, 0))[0] - 6)
    ux, uy = vpos(main, M(G_X, 0))
    dim_circle(sh, main, "Diameter", H["horn_D"] / 2 + 0.5, fmt="⌀%.1w", dx=ux + 20, dy=uy + 26)
    c = proj(main, M(hx0, -hy)); ux, uy = vpos(main, M(hx0, -hy))
    dim_circle(sh, main, "Diameter", H["m2"] / 2, c.x, c.y, fmt="4 отв. ⌀%.1w", dx=ux - 14, dy=uy - 30)
    a = rot_pt(PIVOT_X, lt, H["bend"], PIVOT_X, CONTACT_Z); b = rot_pt(PIVOT_X + H["finger"], lt, H["bend"], PIVOT_X, CONTACT_Z)
    ux, uy = vpos(main, M((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    dim_pts(sh, main, "Distance", M(*a), M(*b), x=ux - 6, y=uy - 11, fmt="%.0w")
    dim_pts(sh, main, "DistanceY", M(PIVOT_X, 0), M(PIVOT_X, CONTACT_Z), x=vpos(main, M(78.5, 0))[0] + 10, fmt="%.1w")
    L = lambda y, z: V(0, y, z)
    ux, uy = vpos(left, L(0, 0))
    dim_circle(sh, left, "Diameter", 8.0, fmt="⌀%.0w", dx=ux - 24, dy=uy + 24)
    c = proj(left, L(-5, 0)); ux, uy = vpos(left, L(-5, 0))
    dim_circle(sh, left, "Diameter", H["m2"] / 2, c.x, c.y, fmt="3 отв. ⌀%.1w на ⌀10", dx=ux + 30, dy=uy + 30)
    T = lambda x, y: V(x, y, 11)
    dim_pts(sh, top, "DistanceY", T(30, G_S - 3), T(30, G_S), x=vpos(top, T(30, 0))[0], fmt="%.0w")
    dim_pts(sh, top, "DistanceY", T(70, -HALF), T(70, HALF), x=vpos(top, T(78.5, 0))[0] + 8, fmt="%.0w")
    dim_pts(sh, top, "DistanceY", T(0, -8), T(0, 8), x=vpos(top, T(0, 0))[0] - 10, fmt="%.0w")
    try:                                                                 # угол изгиба пальца 30°
        lines = [(i, e) for i, e in edges_of(main) if type(e.Curve).__name__ == "Line"]
        def ang(e):
            p, q = e.Vertexes[0].Point, e.Vertexes[-1].Point
            return math.degrees(math.atan2(q.y - p.y, q.x - p.x)) % 180
        yt = proj(main, M(50, lt)).y; ytt = proj(main, M(*a)).y
        flat = min((i for i, e in lines if abs(ang(e)) < 0.5 or abs(ang(e) - 180) < 0.5),
                   key=lambda i: abs(main.getEdgeByIndex(i).Vertexes[0].Point.y - yt))
        bent = [i for i, e in lines if abs(ang(e) - (180 - H["bend"])) < 0.5]
        bent = min(bent, key=lambda i: min(abs(vv.Point.y - ytt) for vv in main.getEdgeByIndex(i).Vertexes))
        d = doc.addObject("TechDraw::DrawViewDimension", "Dim"); d.Type = "Angle"; d.MeasureType = "Projected"
        sh.page.addView(d); d.References2D = [(main, "Edge%d" % flat), (main, "Edge%d" % bent)]
        doc.recompute()
        raw = d.getRawValue()
        log("угол между кромками: %.2f°" % raw)
        if abs(raw - (180 - H["bend"])) < 0.5:                           # FreeCAD меряет смежный угол — подписываем изгиб
            d.Arbitrary = True; d.FormatSpec = "%g°" % H["bend"]
        elif abs(raw - H["bend"]) > 0.5:
            raise RuntimeError("угол не тот: %.2f" % raw)
        ux, uy = vpos(main, M(PIVOT_X + 8, lt))
        d.X, d.Y = ux + 6, uy + 4
    except Exception:
        log("угол 30°: не поставлен\n" + traceback.format_exc())
    sh.text(["Технические требования",
             "1. Печать: PETG, слой 0,2 мм, 3 периметра, заполнение 40 %,",
             "   стенкой (плоскость пластины привода) на стол, поддержки под пальцем.",
             "2. Диск ⌀16 — на качалку привода 21 (запястье): 3 винта M2 × 6",
             "   в резьбу качалки, головки утоплены; 4-е место закрыто стенкой.",
             "3. Пластина — на торец привода 22 (захват): 4 винта M2 × 6",
             "   в резьбу корпуса; окно ⌀14 — под качалку.",
             "4. Нижний палец 26 мм согнут вниз на 30°; плоскость смыкания —",
             "   8,5 мм ниже оси привода 22; паз 0,5 мм под накладку TPU.",
             "5. Размеры для справок; модель — harvey_hand_parts.py."], 110, 52, 3.2)
    return sh.page, obj


FCSTD = os.path.join(HERE, "Харви_чертежи.FCStd")
NAMES = {"Лист_рычаг": "ХАРВИ.01.001 Рычаг 100 мм", "Лист_ладонь": "ХАРВИ.02.002 Ладонь кисти"}


def build():
    """Шаг 1 (консольный FreeCAD): модели, виды, размеры → FCStd и STEP."""
    doc = App.newDocument("Harvey_drawings")
    pages = [sheet_lever(doc), sheet_palm(doc)]
    doc.recompute()
    doc.saveAs(FCSTD)
    for page, obj in pages:
        obj.Shape.exportStep(os.path.join(HERE, obj.Label + ".step"))
    log("FCStd и STEP сохранены")


def export_all():
    """Шаг 2 (окно FreeCAD): открыть FCStd и выгрузить каждый лист в PDF."""
    import FreeCADGui, TechDrawGui
    from PySide import QtGui, QtCore
    doc = App.openDocument(FCSTD)
    names = NAMES
    queue = [doc.getObject(n) for n in NAMES]

    def nxt():
        try:
            if not queue:
                log("готово"); LOG.close(); os._exit(0)
            p = queue.pop(0)
            p.ViewObject.doubleClicked()
            def do():
                try:
                    for _ in range(30): QtGui.QApplication.processEvents()
                    TechDrawGui.exportPageAsPdf(p, os.path.join(HERE, names[p.Name] + ".pdf"))
                    log("PDF:", names[p.Name])
                except Exception:
                    log(traceback.format_exc())
                QtCore.QTimer.singleShot(300, nxt)
            QtCore.QTimer.singleShot(3000, do)
        except Exception:
            log(traceback.format_exc()); LOG.close(); os._exit(1)
    QtCore.QTimer.singleShot(500, nxt)


try:
    if App.GuiUp:
        export_all()
    else:
        build(); LOG.close()
except Exception:
    log(traceback.format_exc()); LOG.close()
    if App.GuiUp:
        os._exit(1)
