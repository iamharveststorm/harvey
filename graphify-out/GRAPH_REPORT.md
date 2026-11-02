# Graph Report - Harvey  (2026-11-02)

## Corpus Check
- 96 files · ~2,537,552 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 239 file(s) not represented in the graph (top: .stl 219, .bat 9, (none) 3)

## Summary
- 1826 nodes · 3935 edges · 72 communities (61 shown, 11 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 504 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1709b07c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Teleop
- harvey_mini_teleop.py
- harvey_claw_parts.py
- harvey_hand_parts.py
- harvey_drawings.py
- harvey_mini.py
- boxr
- Журнал решений
- Харви — стенд привода и ноги (README)
- Харви — главная заметка
- Харви — проверка совместимости и сценарии
- harvey_layout.py
- harvey_leg_parts.py
- harvey_sim.py
- Компакт мини — симуляция (README)
- harvey_mini_parts.py
- sts.py
- sts_bus.py
- Leg
- json
- make_wiring.py
- harvey_tail.py
- Bench
- harvey_eye_parts.py
- export_sim
- result
- FakeBus
- harvey_world.py
- math
- test_report.py
- harvey_grasp.py
- Харви — управление в симуляции (README)
- Харви 1.0 — питание и проводка
- render_desk.py
- disk_on_horn
- harvey_scenarios.py
- AdaptiveGait
- bench.py
- Raspberry Pi AI HAT+ (13/26 TOPS)
- Рендеры и сетки для визуализаций (README)
- Харви — детали стенда одной ноги (PDF)
- test_bench.py
- harvey_terrain.py
- Terrain
- leg_assembly
- Pico 2 — даташит
- conftest.py
- FakeServo
- harvey_pybullet.py
- PhotoView
- FE-URT-1 — адаптер шины (таблица, конвертирована)
- Харви — этап 1: покупки и стенд одной ноги
- RemoteTeleop
- sys
- LegGeometry
- LegCal
- os
- Привод Feetech STS3215-C018 (12 В, 30 кг·см)
- Feetech — протокол связи (SCS/SMS)
- Комплектация «Компакт мини» — что купить и что напечатать
- check_dock
- test_leg.py
- eye_stalk
- Feetech — таблица регистров (конвертирована)
- README папки проекта Харви
- numpy
- Харви «Компакт мини»
- leg_check.py
- run_bench_linux.sh

## God Nodes (most connected - your core abstractions)
1. `Журнал решений` - 58 edges
2. `boxr()` - 53 edges
3. `result()` - 50 edges
4. `Bench` - 44 edges
5. `Leg` - 39 edges
6. `answer()` - 37 edges
7. `Харви — главная заметка` - 32 edges
8. `Харви — этап 1: покупки и стенд одной ноги` - 28 edges
9. `Teleop` - 27 edges
10. `export_sim()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Регистр ID (адрес 5; 254 — широковещательный)` --semantically_similar_to--> `Регистр ID (адрес 5) и блокировка EPROM`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Встроенная защита STS3215 (70 °C, 2 А / 2 с, 4–14 В)` --semantically_similar_to--> `Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C`  [INFERRED] [semantically similar]
  заметки/Питание и проводка.md → документы/STS3215-C018 — даташит Feetech (12 В).pdf
- `Цель: позиция, время, скорость (адреса 42–46)` --semantically_similar_to--> `Регистр цели 0x2A: позиция, время, скорость (6 байт)`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Протирка стола салфеткой (мини)` --semantically_similar_to--> `sc_wipe()`  [INFERRED] [semantically similar]
  код/симуляция/мини/mini_салфетка.png → код/симуляция/управление с клавиатуры/harvey_scenarios.py
- `Переходник разъёмов 5264 ↔ 1,25 мм` --references--> `STS3032-C036 — даташит Feetech (6 В)`  [INFERRED]
  заметки/Этап 1 — покупки и стенд одной ноги.md → документы/STS3032-C036 — даташит Feetech (6 В).pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Детали стенда одной ноги этапа 1** — документы_harvey_stage1_parts_cradle_servo, документы_harvey_stage1_parts_coxa_bracket, документы_harvey_stage1_parts_coxa_strap, документы_harvey_stage1_parts_femur_plate, документы_harvey_stage1_parts_knee_sleeve, документы_harvey_stage1_parts_tibia_fork, документы_harvey_stage1_parts_foot_tpu, документы_harvey_stage1_parts_lever_100mm [EXTRACTED 1.00]
- **Защита питания Харви** — заметки_питание_и_проводка_аварийная_отсечка_приводов, заметки_питание_и_проводка_мёртвые_контакты_идеальный_диод, заметки_питание_и_проводка_порядок_включения, заметки_питание_и_проводка_пороги_напряжения_pico, заметки_питание_и_проводка_отдельные_dc_dc_и_звезда_земли [EXTRACTED 1.00]
- **Кинематическая цепь кисти: стойка → запястье #21 → ладонь → захват #22 → челюсть против пальца** — модели_стенд_кисти_сборка_кисти_стойка_запястья, модели_стенд_кисти_сборка_кисти_привод_запястья_21, модели_стенд_кисти_сборка_кисти_ладонь, модели_стенд_кисти_сборка_кисти_привод_захвата_22, модели_стенд_кисти_сборка_кисти_верхняя_челюсть, модели_стенд_кисти_сборка_кисти_нижний_палец [EXTRACTED 1.00]
- **Blender-рендеры «Компакт мини» на столе (render_desk.py, HARVEY_ROBOT=mini)** — модели_рендер_мини_1, модели_рендер_мини_2, модели_рендер_мини_3, модели_рендер_render_desk, модели_мини_export_render [EXTRACTED 1.00]
- **Параметрический скрипт → STL → чертёж ГОСТ** — модели_стенд_ноги_harvey_leg_parts, модели_стенд_кисти_harvey_hand_parts, модели_чертежи_readme_чертежи_гост_freecad, модели_чертежи_харви_01_001_рычаг_100_мм, модели_чертежи_харви_02_002_ладонь_кисти [EXTRACTED 1.00]
- **Правила движения v2: CAD-проверка, симуляция и прошивка** — модели_корпус_readme_правила_движения, модели_корпус_harvey_layout, код_симуляция_управление_с_клавиатуры_readme_mujoco_simulation, код_прошивка_прошивка, модели_клешни_readme_клешня_5_суставов, модели_хвост_readme_хвост_с_присоской, модели_глаза_readme_глаз_стебелёк_gc9a01 [EXTRACTED 1.00]
- **Оснастка стенда: стойка запястья, люлька STS3032, рычаг 25 мм** — модели_стенд_кисти_детали_кисти_wrist_stand, модели_стенд_кисти_детали_кисти_cradle_sts3032, модели_стенд_кисти_детали_кисти_grip_lever [INFERRED 0.75]
- **Сборка клешни: ладонь + челюсть + накладки TPU** — модели_стенд_кисти_детали_кисти_palm, модели_стенд_кисти_детали_кисти_jaw, модели_стенд_кисти_детали_кисти_pad_tpu [INFERRED 0.85]
- **Узнаваемые части «Компакт» v2 на рендере: глаза-стебельки, клешни, шесть ног, хвост** — модели_рендер_харви_открытый_1_глаза_стебельки, модели_рендер_харви_открытый_1_клешни, модели_рендер_харви_открытый_1_шесть_ног, модели_рендер_харви_открытый_3_хвост [INFERRED 0.85]
- **Рендеры стендов этапа 1: кисть клешни и одна нога** — модели_стенд_кисти_рендер_кисти, модели_стенд_ноги_рендер_ног, модели_стенд_кисти_harvey_hand_parts, модели_стенд_ноги_harvey_leg_parts [INFERRED 0.85]
- **Обзор камеры мини: вид V, поза «поджато», телеуправление** — код_симуляция_мини_mini_глазами_харви_camera_view, код_симуляция_мини_mini_глазами_харви_tucked_pose, код_симуляция_мини_harvey_mini_teleop [INFERRED 0.85]
- **Неподвижная камера мини и поза «поджато» ради обзора** — заметки_журнал_решений_мини_камера_неподвижна, код_симуляция_мини_readme_поза_поджато_для_камеры, код_симуляция_мини_readme_вид_глазами_харви [INFERRED 0.85]
- **Полоса препятствий на полу (harvey_world)** — код_симуляция_управление_с_клавиатуры_harvey_world, код_симуляция_управление_с_клавиатуры_мир_полоса_ramp_board, код_симуляция_управление_с_клавиатуры_мир_полоса_surface_zones, код_симуляция_управление_с_клавиатуры_мир_склоны_slopes_zone [INFERRED 0.85]
- **Режим «фото»: Харви на поверхностях физики веществ (песок, галька, трава, склон)** — код_симуляция_управление_с_клавиатуры_фото_песок_следы, код_симуляция_управление_с_клавиатуры_фото_галька, код_симуляция_управление_с_клавиатуры_фото_трава, код_симуляция_управление_с_клавиатуры_фото_склон, код_симуляция_управление_с_клавиатуры_harvey_terrain, код_симуляция_управление_с_клавиатуры_harvey_photo [INFERRED 0.85]
- **Варианты полудуплексной шины от Pico 2: Waveshare адаптер или буферы LVC** — заметки_комплектация_мини_waveshare_bus_servo_adapter, заметки_комплектация_мини_буферы_lvc_5в, заметки_чек_лист_стенда_мини_pico_2_h, код_прошивка_pico_readme [INFERRED 0.85]
- **Стенд ноги «Компакт мини»: закупка → замер размеров → печать → замеры Н1–Н5** — заметки_чек_лист_стенда_мини, заметки_комплектация_мини_horn_top_shaft_from_end, заметки_журнал_решений_печать_после_замера_horn_top, код_стенд_привода_readme_режим_компакт_мини, код_стенд_привода_readme_нога_замеры_н1_н5, документы_sts3032_c036_даташит_feetech_6_в [INFERRED 0.85]
- **Подвижные узлы компоновки v2 и их зоны движения** — модели_корпус_компоновка_вид_сверху_зоны_движения, модели_корпус_компоновка_вид_сверху_глаза_на_углах, модели_корпус_компоновка_вид_сверху_плечи_клешней, модели_корпус_компоновка_вид_сверху_хвост_за_подносом [INFERRED 0.85]
- **Шина Feetech: драйвер стенда, драйвер Pico, имитации** — код_стенд_привода_harvey_bench_sts, код_прошивка_pico_sts_bus, код_прошивка_pico_readme_замер_12_шина_от_pico, код_стенд_привода_readme_sim_mode, код_прошивка_pico_readme_проверка_на_пк_без_железа [INFERRED 0.85]
- **Рендеры «Компакта» на столе: 2 варианта корпуса (открытый/мягкий) × ракурсы из render_desk.py** — модели_рендер_харви_мягкий_2, модели_рендер_харви_мягкий_3, модели_рендер_харви_открытый_1, модели_рендер_харви_открытый_2, модели_рендер_харви_открытый_3, модели_рендер_render_desk [INFERRED 0.95]
- **Кадры mini_photo.py: стол, предметы, салфетка, привет** — код_симуляция_мини_mini_photo, код_симуляция_мини_mini_стол, код_симуляция_мини_mini_и_предметы, код_симуляция_мини_mini_салфетка, код_симуляция_мини_mini_привет [INFERRED 0.95]
- **Функции harvey_hand_parts.py, порождающие сборку на рендере** — модели_стенд_кисти_harvey_hand_parts_wrist_stand, модели_стенд_кисти_harvey_hand_parts_palm, модели_стенд_кисти_harvey_hand_parts_jaw, модели_стенд_кисти_harvey_hand_parts_assembly, модели_стенд_кисти_сборка_кисти [INFERRED 0.95]

## Communities (72 total, 11 thin omitted)

### Community 0 - "Teleop"
Cohesion: 0.05
Nodes (20): currents(), run(), KeyReader, run_gui(), act(), close(), keyname(), norm() (+12 more)

### Community 1 - "harvey_mini_teleop.py"
Cohesion: 0.06
Nodes (17): _child(), keyname(), MiniTeleop, near_plane(), RemoteMini, run_grip_test(), run_gui(), close() (+9 more)

### Community 2 - "harvey_claw_parts.py"
Cohesion: 0.06
Nodes (37): pad_pair(), s15_case(), s15_metal(), s32_case(), s32_metal(), scene(), arm_plate(), base() (+29 more)

### Community 3 - "harvey_hand_parts.py"
Cohesion: 0.08
Nodes (36): assembly(), box(), check(), cyl(), finger_bar(), grip_lever(), horn_disk(), jaw() (+28 more)

### Community 4 - "harvey_drawings.py"
Cohesion: 0.09
Nodes (29): box(), build(), cut(), cylx(), cyly(), cylz(), dim_circle(), dim_pts() (+21 more)

### Community 5 - "harvey_mini.py"
Cohesion: 0.13
Nodes (20): arm_ik(), build_xml(), claw_ok(), dock_xml(), joint_names(), leg_ik(), load_assets(), Mini (+12 more)

### Community 6 - "boxr"
Cohesion: 0.08
Nodes (22): run(), belly(), camera_assembly(), camera_mount(), check(), test(), claw_base_world(), deck() (+14 more)

### Community 7 - "Журнал решений"
Cohesion: 0.07
Nodes (4): Планка-фиксатор привода бедра (harvey_coxa_strap.stl), Журнал решений, Перепроверка 15.10: перепечатать 4 детали, новая стойка ноги, Боковые датчики края с наклоном луча 3,5 : 1

### Community 8 - "Харви — стенд привода и ноги (README)"
Cohesion: 0.09
Nodes (32): STS3032-C036 — даташит Feetech (6 В), Документы — даташиты и PDF, FE-URT-1 — адаптер шины (xlsx), Feetech — таблица регистров (xlsx), STS3032-C036 — 3 280 ₽ (Feetech Official Store), 4 170 ₽ (Ozon), Проверка на стенде мини: размеры, нога на весах 3–4 Н, 10 мин шага, ток, Чек-лист стенда «Компакт мини», FE-URT-1 (vvhobby Store, 1 289 ₽) (+24 more)

### Community 9 - "Харви — главная заметка"
Cohesion: 0.06
Nodes (48): Харви — галерея, Компоновка v2 — вид сверху (цвета по узлам), Режим «фото» (Filament PBR): песок со следами, галька, трава, Рендеры «Компакт мини» на столе 1 : 1 (Blender, Cycles), Рендеры на столе: открытая рама и мягкий кожух, Чертежи ГОСТ: ХАРВИ.01.001 Рычаг 100 мм, ХАРВИ.02.002 Ладонь кисти, Харви «Компакт» — сборка в Onshape и физическая проверка, Variable Studio «Параметры» (#coxa, #femur, #tibia, #body_*) (+40 more)

### Community 10 - "Харви — проверка совместимости и сценарии"
Cohesion: 0.09
Nodes (23): Без ПК — «сонный питомец»: ходит, не падает, эмоции, сам заряжается, reSpeaker XVF3800 (USB, 4 микрофона), Порядок закупки в 4 этапа, Шесть ног, Харви — проверка совместимости и сценарии, MuJoCo (физический движок), PyBullet (физический движок), Датчики края — между клешнями, ~25 мм от центра (+15 more)

### Community 11 - "harvey_layout.py"
Cohesion: 0.06
Nodes (32): check(), claw(), claw_ok(), claw_parts_chassis(), eye(), eye_ok(), flat(), inter() (+24 more)

### Community 12 - "harvey_leg_parts.py"
Cohesion: 0.13
Nodes (15): to_trimesh(), box(), coxa_bracket(), cradle(), cyl(), femur_plate(), flange_cut(), foot() (+7 more)

### Community 13 - "harvey_sim.py"
Cohesion: 0.11
Nodes (18): arm_ik(), arm_xml(), build_xml(), eye_xml(), ik(), pose_targets(), power(), rpy() (+10 more)

### Community 14 - "Компакт мини — симуляция (README)"
Cohesion: 0.11
Nodes (22): Скриншот: вид глазами Харви (мини), Камера Module 3 Wide — вид глазами Харви (клавиша V), Скриншот: мини на столе среди предметов, Реквизит рабочего стола (ручки, карандаш, блокнот, кейс наушников, книга, лампа, ноутбук), Скриншот: приветствие правой клешнёй (мини), Жест «привет» — клешня поднята вверх, Скриншот: протирка салфеткой (мини), Протирка стола салфеткой (мини) (+14 more)

### Community 15 - "harvey_mini_parts.py"
Cohesion: 0.12
Nodes (15): chassis(), coxa_servo_leg(), coxa_servos(), edge_sensors(), electronics(), eye_servos(), fixed_parts(), _leg_tf() (+7 more)

### Community 16 - "sts.py"
Cohesion: 0.09
Nodes (21): BusError, checksum(), le16(), make_packet(), parse_status(), SerialBus, State, to_signed() (+13 more)

### Community 17 - "sts_bus.py"
Cohesion: 0.10
Nodes (11): run(), FakeUart, main(), Bus, BusError, checksum(), find_status(), le16() (+3 more)

### Community 18 - "Leg"
Cohesion: 0.09
Nodes (3): clamp(), Leg, test_center_all_with_empty_bus_records_nothing()

### Community 19 - "json"
Cohesion: 0.21
Nodes (6): add(), body_map(), leg_map(), main(), pack(), pack()

### Community 20 - "make_wiring.py"
Cohesion: 0.18
Nodes (4): bus_buffer(), pi_sheet(), power_sheet(), render()

### Community 21 - "harvey_tail.py"
Cohesion: 0.19
Nodes (11): build_tail(), legs_push(), rel(), T, tail_ik(), tail_move(), test_handover(), test_pick_place() (+3 more)

### Community 23 - "harvey_eye_parts.py"
Cohesion: 0.07
Nodes (24): back_cover(), bumper(), display(), eye_center(), horn_adapter(), housing(), housing_radius(), housing_x() (+16 more)

### Community 24 - "export_sim"
Cohesion: 0.14
Nodes (18): claw_assembly(), T_ay(), T_fore(), T_hand(), T_up(), elbow_servo_up(), export_sim(), put() (+10 more)

### Community 25 - "result"
Cohesion: 0.06
Nodes (38): answer(), result(), test_assign_id_renumbers_the_only_servo(), test_backlash_not_measured(), test_backlash_over_one_degree_fails(), test_heat_case_default_is_sensor_minus_three(), test_heat_mean_current_over_norm_fails(), test_heat_stops_at_70_degrees() (+30 more)

### Community 26 - "FakeBus"
Cohesion: 0.14
Nodes (5): FakeBus, Servo, u16(), test_fake_bus_set_id_and_move(), test_set_middle_makes_position_2048()

### Community 27 - "harvey_world.py"
Cohesion: 0.11
Nodes (12): apply(), asset_xml(), grab_equalities(), load_assets(), pbr_material(), props_xml(), _ramp(), robot_visual() (+4 more)

### Community 28 - "math"
Cohesion: 0.15
Nodes (9): arm_fk(), neutral(), test_edge(), assets(), bodies(), _hex_mesh(), _hex_tip_mesh(), reach_table() (+1 more)

### Community 29 - "test_report.py"
Cohesion: 0.12
Nodes (15): _header(), _log_sheet(), _results_sheet(), verdict_fill(), write(), test_column_widths(), test_default_title_is_the_sts3215_bench(), test_empty_report_still_opens() (+7 more)

### Community 30 - "harvey_grasp.py"
Cohesion: 0.21
Nodes (12): build(), build_cup(), finger_mid(), G, obj_forces(), path(), pen_test(), phone_test() (+4 more)

### Community 31 - "Харви — управление в симуляции (README)"
Cohesion: 0.14
Nodes (15): Харви — управление в симуляции (README), Датчики края стола (защита края), MuJoCo-симуляция Харви (компоновка v2), Сценарии проверки (harvey_scenarios.py all), Режим «фото»: рендер Filament, физика в отдельном процессе, Рефлекс защиты глаз при опрокидывании (складывание до −105°), Физика веществ: деформируемый песок, гравий и галька, трава, мир_стол.png — Харви на столе (обычное окно MuJoCo) (+7 more)

### Community 32 - "Харви 1.0 — питание и проводка"
Cohesion: 0.07
Nodes (39): Pi 5 + AI HAT+ («голова») и Pico 2 («спинной мозг»), Pi Zero 2 W + RP2350-Zero («спинной мозг»), Бюджет мини ≈ 115–158 тыс. ₽ (почти как «Компакт»), Питание мини: 2 × 18650 (2S, ~22 Вт·ч), DC-DC 6 В 6 А, Харви — комплектация и бюджет v0.2, AI HAT+ 26 TOPS (Hailo-8), Raspberry Pi Camera Module 3 Wide, IMU BMI270 / ICM-42688 (+31 more)

### Community 33 - "render_desk.py"
Cohesion: 0.15
Nodes (6): bbox(), light(), place(), _top_level(), Харви_мягкий_1 — «Компакт», вариант «мягкий», вид спереди на столе, Вариант рендера «мягкий» (soft): закрытый панцирь, скрыта плата и батарея

### Community 34 - "disk_on_horn"
Cohesion: 0.14
Nodes (10): coxa_bracket(), disk_on_horn(), femur_link(), forearm(), hull(), plate_on_face(), rod(), tibia() (+2 more)

### Community 35 - "harvey_scenarios.py"
Cohesion: 0.22
Nodes (14): edge_sensor(), feet_x(), sc_battery(), sc_edge(), sc_failure(), sc_obstacles(), sc_push(), sc_random() (+6 more)

### Community 37 - "bench.py"
Cohesion: 0.09
Nodes (17): compact_actions(), main(), mini_actions(), open_bench(), parse_args(), release(), run_menu(), Session (+9 more)

### Community 38 - "Raspberry Pi AI HAT+ (13/26 TOPS)"
Cohesion: 0.25
Nodes (9): AI HAT+ — краткое описание, Raspberry Pi AI HAT+ (13/26 TOPS), Ускоритель Hailo-8 / Hailo-8L (NPU), Связь AI HAT+ по PCIe Gen 3, Питание Pico 2: VSYS 1,8–5,5 В, SMPS RT6150, 3V3 ≤ 300 мА, Raspberry Pi 5 — краткое описание, PCIe 2.0 x1 у Raspberry Pi 5, Питание Pi 5: 5 В / 5 А через USB-C с PD (+1 more)

### Community 39 - "Рендеры и сетки для визуализаций (README)"
Cohesion: 0.13
Nodes (23): v2 «Компакт» (метка v2-kompakt, ветка kompakt), сохранена 16.10.2026, Круглые дисплеи-глаза GC9A01 1,28″, Хвост — третья рука с присоской, Версия корпуса «Компакт», Две мощные многосуставные клешни, Глаза на стебельках с магнитной муфтой, Клешня с пятью суставами (звенья 54 / 60 / ≈43 мм), Панцирь 150 × 140 × 70 мм и поднос на спине 87 × 105 мм (+15 more)

### Community 40 - "Харви — детали стенда одной ноги (PDF)"
Cohesion: 0.20
Nodes (10): Харви — детали стенда одной ноги (PDF), Кронштейн основания (harvey_coxa_bracket.stl), Держатель привода валом вверх (harvey_cradle_servo.stl), Пластина бедра ×2 (harvey_femur_plate_x2.stl), Стопа TPU 95A (harvey_foot_TPU.stl), Обхват привода колена (harvey_knee_sleeve.stl), Рычаг 100 мм (harvey_lever_100mm.stl), Печать и крепёж: PETG 0,2 мм, 40% гироид, вставки M3, зазор 0,3 мм (+2 more)

### Community 41 - "test_bench.py"
Cohesion: 0.05
Nodes (41): heat_abort(), heat_ok(), measure_servo(), model_label(), scaled_lsb(), scan_note(), big(), make() (+33 more)

### Community 42 - "harvey_terrain.py"
Cohesion: 0.17
Nodes (7): grass_assets(), grass_geoms(), settle(), stone_assets(), _stone_list(), stones_xml(), _tuft_mesh()

### Community 44 - "leg_assembly"
Cohesion: 0.11
Nodes (13): check(), check_stand(), claw_ok(), claw_points(), _flat(), foot(), inter(), leg_assembly() (+5 more)

### Community 45 - "Pico 2 — даташит"
Cohesion: 0.33
Nodes (7): Полудуплексная асинхронная шина 8N1, Pico 2 — даташит, Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3), MicroPython на Pico 2, Микроконтроллер RP2350, Pico 2 — краткое описание, Raspberry Pi Pico 2

### Community 47 - "conftest.py"
Cohesion: 0.15
Nodes (7): FakeLegBus, Режим без железа (SIM): имитация привода, bench(), bus(), calibrated(), in_tmp(), leg()

### Community 50 - "harvey_pybullet.py"
Cohesion: 0.23
Nodes (7): inertial(), PB, stand(), urdf(), walk(), Сверка во втором движке PyBullet, requirements-extra.txt (pybullet ≥3.2.6)

### Community 52 - "FE-URT-1 — адаптер шины (таблица, конвертирована)"
Cohesion: 0.31
Nodes (9): Приводы — шинные Feetech STS (STS3215 C018 на ногах, STS3032 на кистях), FE-URT-1 — адаптер шины (таблица, конвертирована), FE-URT-1 — USB → TTL/RS485 программатор шины Feetech, Аппаратное автоматическое переключение направления полудуплекса, Драйвер CH340C, Порты SMS (RS485, 5264-4AW) и SCS (TTL, 5264-3AW), 28 × STS3032 (ноги 6 × 3, клешни 2 × 4, глаза 2), Feetech STS3032 (6 В, 4,5 кг·см) (+1 more)

### Community 54 - "Харви — этап 1: покупки и стенд одной ноги"
Cohesion: 0.15
Nodes (16): STS3215-C018 — даташит Feetech (12 В), Проверить на стенде до заказа 30 приводов: нагрев бедра, размеры, ток, дисплей, видео, Feetech STS3215-C018 (12 В, 30 кг·см), Первые тесты мини: 4 × STS3032, URT-1, стенд одной ноги (~25 г печати), Нога: основание, бедро, колено (звенья 40 / 51 / 70 мм), Харви — этап 1: покупки и стенд одной ноги, Архив Harvey_leg_CAD.zip (детали стенда ноги), Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS (+8 more)

### Community 56 - "sys"
Cohesion: 0.15
Nodes (6): coxa_case(), coxa_metal(), leg(), s15_case_y(), s15_metal_y(), tower()

### Community 59 - "LegCal"
Cohesion: 0.30
Nodes (7): LegCal, test_broken_calibration_file_falls_back_to_defaults(), test_calibration_makes_pose_g_the_middle_and_saves(), test_calibration_survives_save_and_load(), test_missing_checked_flag_means_not_checked(), test_to_pos_uses_offset_and_direction(), test_leg_calibration_mapping()

### Community 61 - "os"
Cohesion: 0.11
Nodes (3): main(), add(), material()

### Community 62 - "Привод Feetech STS3215-C018 (12 В, 30 кг·см)"
Cohesion: 0.15
Nodes (15): Порядок сборки ноги: ID 1/2/3, середина 2048, ось бедра 55 мм над столом, Размеры привода для сверки (servo_L 45,2, W 24,7, H 32, shaft_from_end 12,5, flange_D 20), Защиты STS3032: перегрузка, напряжение 4–7,4 В, 70 °C, Привод Feetech STS3032-C036 (6 В, 4,5 кг·см), 12-битный магнитный энкодер: 4096 отсчётов, 0,088°, середина 2048, Калибровка середины: 128 в адрес 40, Режимы 0–3: серво, скорость замкн./разомкн., шаговый; многооборотный ±7, Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C (+7 more)

### Community 63 - "Feetech — протокол связи (SCS/SMS)"
Cohesion: 0.16
Nodes (15): Цель: позиция, время, скорость (адреса 42–46), Feetech — протокол связи (SCS/SMS), Широковещательный ID 254 (0xFE), Порядок байт SMS/STS: младший байт первым, Контрольная сумма ~(ID+Len+Instr+Params) & 0xFF, Регистр цели 0x2A: позиция, время, скорость (6 байт), Регистр ID (адрес 5) и блокировка EPROM, Пакет инструкции 0xFF 0xFF ID Len Instr Params Checksum (+7 more)

### Community 64 - "Комплектация «Компакт мини» — что купить и что напечатать"
Cohesion: 0.08
Nodes (21): Зарядка мини: латунные пластины на брюхе + станция с AprilTag и ИК-маяком, Комплектация «Компакт мини» — что купить и что напечатать, 3D-печать мини: 41 деталь, ≈ 157 г (PLA / PETG / TPU), Размеры horn_top (4,8 мм) и shaft_from_end (5,7 мм) — измерить до печати, Бюджет мини ≈ 116–161 тыс. ₽ (больше 4/5 — приводы), Крепёж M2: ~250 винтов (нога 24, клешня 34), Удешевление приводов: оптовая цена Feetech, распродажи AliExpress, Питание мини: 2 × 18650 (2S, ~22 Вт·ч), BMS 2S, IP2326, DC-DC 6 В ≥ 6 А и 5 В 3 А (+13 more)

### Community 65 - "check_dock"
Cohesion: 0.22
Nodes (5): check_dock(), dock_pad(), dock_pogo(), dock_tower(), leg_pose_for_drop()

### Community 66 - "test_leg.py"
Cohesion: 0.05
Nodes (23): abort_reason(), direction(), gait_ok(), middle_offset(), parse_grams(), stall_current(), stance_ok(), step_pose() (+15 more)

### Community 67 - "eye_stalk"
Cohesion: 0.29
Nodes (4): display(), eye_assembly(), eye_servo_body(), eye_stalk()

### Community 68 - "Feetech — таблица регистров (конвертирована)"
Cohesion: 0.29
Nodes (10): Feetech — таблица регистров (конвертирована), Блокировка записи EPROM (адрес 48), Защита от перегрузки (регистры 37–39: момент, время, порог 80%), Максимальный момент (адрес 16), Включение момента (адрес 40), Регистр ID (адрес 5; 254 — широковещательный), Регистр скорости шины (адрес 6; 0 = 1 Мбит/с), Обратная связь: позиция, скорость, нагрузка, напряжение, температура (56–63) (+2 more)

### Community 69 - "README папки проекта Харви"
Cohesion: 0.16
Nodes (12): CLAUDE.md — контекст проекта Харви, Ветки kompakt (v2-kompakt) и kompakt-mini, Структура папки проекта (заметки, визуализация, модели, документы, фото, код), README папки проекта Харви, Obsidian-хранилище на всю папку harvey, Окружения Python в C:\venvs (harvey, harvey-bench, harvey-cad), Онлайн-версии документов (артефакты claude.ai), Версии: kompakt «Компакт» и kompakt-mini «Компакт мини» (+4 more)

### Community 73 - "numpy"
Cohesion: 0.13
Nodes (10): main(), world_model(), eye_force(), trial(), neutral(), edge_seen(), Скриншот: склоны и ступени полосы препятствий, Склоны 10°/15°/20°/25°, косой склон 15° и ступени (+2 more)

### Community 75 - "Харви «Компакт мини»"
Cohesion: 0.19
Nodes (13): Харви «Компакт мини», Задачи мини: протереть стол, подать ручку, общаться, сам заряжаться, Масса мини 893 г (560 г — приводы); цель ≤ 0,8 кг не достигнута, CAD-проверка мини (harvey_mini_parts.py): 0 столкновений, 332 позы клешни, Симуляция мини (harvey_mini.py): ходьба 6,2 см/с, ручка, салфетка, станция, «Компакт мини» — компоновка, 4 вида (перспектива, сверху, спереди, сбоку), Компакт мини: шесть ног, две клешни, глаза-стебельки с круглыми дисплеями, без хвоста, «Компакт мини» на том же столе: export_render.py → parts_mini/, HARVEY_ROBOT=mini (+5 more)

### Community 76 - "leg_check.py"
Cohesion: 0.21
Nodes (5): coxa_servo(), ik(), links(), plates(), servo()

## Ambiguous Edges - Review These
- `Рычаг-качалка 25 мм (grip_lever)` → `Сервопривод Feetech STS3032-C036`  [AMBIGUOUS]
  модели/стенд кисти/детали кисти.png · relation: conceptually_related_to
- `Связь AI HAT+ по PCIe Gen 3` → `PCIe 2.0 x1 у Raspberry Pi 5`  [AMBIGUOUS]
  документы/AI HAT+ — краткое описание.pdf · relation: conceptually_related_to
- `Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре)` → `Таблица регистров SCS15 (прошивка SCServo1.1)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to
- `Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS` → `Таблица регистров SCS15 (прошивка SCServo1.1)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to

## Knowledge Gaps
- **80 isolated node(s):** `Датчики края — между клешнями, ~25 мм от центра`, `Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения`, `Походка на пяти ногах (при отказе ноги)`, `Протирка стола с ограничением усилия по току привода`, `Более 40 смоделированных сценариев` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 590 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Харви — стенд привода и ноги (README)` connect `Харви — стенд привода и ноги (README)` to `Комплектация «Компакт мини» — что купить и что напечатать`, `bench.py`, `README папки проекта Харви`, `Харви — главная заметка`, `conftest.py`, `sts.py`, `Харви — этап 1: покупки и стенд одной ноги`, `test_report.py`, `Feetech — протокол связи (SCS/SMS)`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `boxr()` (e.g. with `stalk()` and `base()`) actually correct?**
  _`boxr()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Датчики края — между клешнями, ~25 мм от центра`, `Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения`, `Походка на пяти ногах (при отказе ноги)` to the rest of the system?**
  _80 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Teleop` be split into smaller, more focused modules?**
  _Cohesion score 0.05454545454545454 - nodes in this community are weakly interconnected._
- **Why does `Харви — главная заметка` connect `Харви — главная заметка` to `Харви 1.0 — питание и проводка`, `Комплектация «Компакт мини» — что купить и что напечатать`, `README папки проекта Харви`, `Журнал решений`, `Харви — стенд привода и ноги (README)`, `Харви — детали стенда одной ноги (PDF)`, `Харви — проверка совместимости и сценарии`, `Харви «Компакт мини»`, `Рендеры и сетки для визуализаций (README)`, `Компакт мини — симуляция (README)`, `Харви — этап 1: покупки и стенд одной ноги`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Рычаг-качалка 25 мм (grip_lever)` and `Сервопривод Feetech STS3032-C036`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Связь AI HAT+ по PCIe Gen 3` and `PCIe 2.0 x1 у Raspberry Pi 5`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._