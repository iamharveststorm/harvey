# Харви — рендеры и сетки для визуализаций

- `export_robot.py` — весь робот (компоновка v2) по материалам в позе «привет» → `parts/tech`, `parts/soft` (не печатать).
- `render_desk.py` — фотореалистичная сцена в Blender 5.2 (Cycles): дубовый стол в комнате, тёплый свет лампы, блокнот, ручки, телефон, кейс наушников, зажигалка, очки, кружка, растение. 3 ракурса × 2 варианта корпуса.
- `export_web.py` — сетки звеньев для `визуализация/3D-модель.html` и `визуализация/Интерактивный двойник.html` (`визуализация/lib/harvey_meshes.js`).

![[Харви_открытый_1.png]]

| | Открытый (основной) | Мягкий (кожух) |
| --- | --- | --- |
| Спереди | ![[Харви_открытый_1.png]] | ![[Харви_мягкий_1.png]] |
| Слева, весь стол | ![[Харви_открытый_2.png]] | ![[Харви_мягкий_2.png]] |
| Сверху сзади | ![[Харви_открытый_3.png]] | ![[Харви_мягкий_3.png]] |

## Как пересобрать

```bash
python export_robot.py
```

Потом в Blender (пути с кириллицей — через переменную):

```bash
set HARVEY_RENDER_DIR=C:\Users\iamha\OneDrive\Документы\Harvey\модели\рендер
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python render_desk.py
```

Ресурсы Poly Haven (CC0) — в `C:\harvey-assets\polyhaven`: HDRI `lythwood_room`, текстура дуба `oak_veneer_01`, модели `office_notepads`, `stationery_supplies`, `vintage_lighter`, `desk_lamp_arm_01`, `potted_plant_02`, `round_spectacles`, `standing_picture_frame_01`. Телефон, кейс наушников в стиле Nothing Ear (2) (прозрачный корпус, белые вкладыши, без логотипов) и кружку сцена строит сама. Картинки глаз и экрана телефона — `tex/`.
