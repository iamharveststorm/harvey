"""Текстуры и рельеф для мира симуляции (MuJoCo читает PNG): из ресурсов Poly Haven (CC0) в C:/harvey-assets/polyhaven.
    python export_world_assets.py   → код/симуляция/управление с клавиатуры/assets/world/*.png
Текстуры — 8-битные RGB 1024 px; рельеф (hfield) — серые PNG 160 × 160 из карт высот Poly Haven, у песка добавлены дюны."""
import os
import numpy as np
from PIL import Image

SRC = "C:/harvey-assets/polyhaven/textures"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "код", "симуляция", "управление с клавиатуры", "assets", "world")
os.makedirs(OUT, exist_ok=True)

TEX = {"parquet": "herringbone_parquet", "wall": "beige_wall_001", "grass": "leafy_grass", "sand": "coast_sand_01",
       "gravel": "gravel_floor", "pebbles": "pebbles", "concrete": "concrete_floor_01", "asphalt": "asphalt_02"}
for name, src in TEX.items():
    im = Image.open(f"{SRC}/{src}/{src}_Diffuse_1k.png")
    im = Image.fromarray((np.asarray(im).astype(np.float64) / (257.0 if np.asarray(im).dtype == np.uint16 else 1.0)).clip(0, 255).astype(np.uint8)) if np.asarray(im).dtype == np.uint16 else im
    im.convert("RGB").resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, f"{name}.png"), optimize=True)
    print("текстура", name)
oak = Image.open(f"{SRC}/oak_veneer_01/oak_veneer_01_Diffuse_2k.jpg").convert("RGB").resize((1024, 1024), Image.LANCZOS)
oak.save(os.path.join(OUT, "oak.png"), optimize=True); print("текстура oak")

# Карты для PBR (рендер Filament, режим «фото»): нормали OpenGL и ORM (R — затенение, G — шероховатость, B — металл).
# Классический рендер MuJoCo их не использует, но и не мешает. 512 px — детали рельефа видны, папка остаётся лёгкой.
for name, src in dict(TEX, oak="oak_veneer_01").items():
    for mp, suf in (("nor_gl", "n"), ("arm", "orm")):
        f = f"{SRC}/{src}/{src}_{mp}_1k.jpg"
        if os.path.isfile(f):
            Image.open(f).convert("RGB").resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, f"{name}_{suf}.png"), optimize=True)
    print("PBR", name)


def height(src, n=160, smooth=1):
    a = np.asarray(Image.open(f"{SRC}/{src}/{src}_Displacement_1k.png")).astype(np.float64)
    if a.ndim == 3:
        a = a[..., 0]
    im = Image.fromarray(((a - a.min()) / (np.ptp(a) or 1) * 255).astype(np.uint8)).resize((n, n), Image.BILINEAR)
    return np.asarray(im).astype(np.float64) / 255.0


def save_h(name, h):
    h = (h - h.min()) / (np.ptp(h) or 1)
    n = h.shape[0]; t = np.minimum(np.arange(n), np.arange(n)[::-1]) / (0.12 * n)      # к краям рельеф плавно сходит на уровень пола
    w = np.clip(t, 0, 1); w = w * w * (3 - 2 * w)
    h = (0.15 + 0.85 * h) * np.outer(w, w)          # внутри рельеф не опускается до уровня пола (иначе пол просвечивает)
    Image.fromarray((h * 255).astype(np.uint8), "L").save(os.path.join(OUT, f"{name}_h.png"))
    print("рельеф", name)


rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:160, 0:160] / 159.0
save_h("grass", height("leafy_grass") * 0.7 + 0.3 * np.sin(xx * 9 + 1) * np.sin(yy * 7) ** 2)                      # кочки
dunes = 0.6 * (np.sin(xx * 7.5 + 0.8 * np.sin(yy * 4)) * 0.5 + 0.5) + 0.25 * (np.sin(yy * 5 + 2) * 0.5 + 0.5)
save_h("sand", dunes + 0.15 * height("coast_sand_01"))                                                             # дюны
save_h("gravel", height("gravel_floor"))
save_h("pebbles", height("pebbles"))
print("готово:", OUT)
