# Graph Report - Harvey  (2026-11-02)

## Corpus Check
- 95 files · ~2,535,594 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 239 file(s) not represented in the graph (top: .stl 219, .bat 9, (none) 3)

## Summary
- 1747 nodes · 3767 edges · 82 communities (66 shown, 16 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 496 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8e26dc84`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Teleop
- MiniTeleop
- harvey_claw_parts.py
- harvey_hand_parts.py
- harvey_drawings.py
- harvey_mini.py
- boxr
- Журнал решений
- Комплектация «Компакт мини» — что купить и что напечатать
- Харви — главная заметка
- Харви — проверка совместимости и сценарии
- harvey_layout.py
- harvey_leg_parts.py
- harvey_sim.py
- Модель Харви «Компакт мини» в MuJoCo (шесть ног, две клешни, глаза-стебельки, без хвоста)
- harvey_mini_parts.py
- sts.py
- sts_bus.py
- Leg
- numpy
- make_wiring.py
- math
- Bench
- harvey_eye_parts.py
- claw_assembly
- result
- FakeBus
- harvey_world.py
- bench.py
- harvey_grasp.py
- Харви — управление в симуляции (README)
- Харви 1.0 — питание и проводка
- harvey_tail_parts.py
- disk_on_horn
- harvey_scenarios.py
- AdaptiveGait
- test_bench_main.py
- Raspberry Pi AI HAT+ (13/26 TOPS)
- Рендеры и сетки для визуализаций (README)
- Харви — детали стенда одной ноги (PDF)
- test_bench.py
- harvey_terrain.py
- Terrain
- check
- export_robot.py
- conftest.py
- FakeServo
- SerialBus
- «Компакт мини» — компоновка, 4 вида (перспектива, сверху, спереди, сбоку)
- PhotoView
- Харви — комплектация и бюджет v0.2
- render_desk.py
- Харви — этап 1: покупки и стенд одной ноги
- RemoteTeleop
- export_sim
- LegGeometry
- leg.py
- LegCal
- mini_objects.py
- harvey_teleop.py
- Управление мини с клавиатуры (harvey_mini_teleop.py, run_mini_windows.bat): Filament PBR, физика в отдельном процессе
- Feetech — протокол связи (SCS/SMS)
- Харви «Компакт мини»
- check_dock
- test_leg.py
- run_gui
- Feetech — таблица регистров (конвертирована)
- Компакт мини — детали и компоновка (README)
- Компакт мини — симуляция (README)
- Привод Feetech STS3215-C018 (12 В, 30 кг·см)
- ._macro_pick
- harvey_mini_teleop.py
- mini_actions
- Pico 2 — даташит
- Рендер Харви «Компакт», вариант «открытый» (основной) — спереди, поза «привет»
- run_test
- run_bench_linux.sh
- Стенд одной ноги (README)
- soft_cover
- test_heat_stops_at_70_degrees

## God Nodes (most connected - your core abstractions)
1. `Журнал решений` - 58 edges
2. `boxr()` - 53 edges
3. `result()` - 47 edges
4. `Bench` - 36 edges
5. `answer()` - 35 edges
6. `Leg` - 34 edges
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
- `Приводы STS3032 в симуляции мини: ограничение момента и падение момента со скоростью` --conceptually_related_to--> `STS3032-C036 — даташит Feetech (6 В)`  [INFERRED]
  код/симуляция/мини/README.md → документы/STS3032-C036 — даташит Feetech (6 В).pdf

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

## Communities (82 total, 16 thin omitted)

### Community 0 - "Teleop"
Cohesion: 0.06
Nodes (18): currents(), run(), KeyReader, run_gui(), act(), close(), keyname(), norm() (+10 more)

### Community 1 - "MiniTeleop"
Cohesion: 0.18
Nodes (3): _child(), MiniTeleop, run_grip_test()

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
Cohesion: 0.11
Nodes (23): arm_fk(), arm_ik(), build_xml(), claw_ok(), dock_xml(), joint_names(), leg_ik(), load_assets() (+15 more)

### Community 6 - "boxr"
Cohesion: 0.08
Nodes (22): run(), belly(), camera_assembly(), camera_mount(), check(), test(), claw_base_world(), deck() (+14 more)

### Community 7 - "Журнал решений"
Cohesion: 0.07
Nodes (5): Окружения Python в C:\venvs (harvey, harvey-bench, harvey-cad), Планка-фиксатор привода бедра (harvey_coxa_strap.stl), Журнал решений, Перепроверка 15.10: перепечатать 4 детали, новая стойка ноги, Боковые датчики края с наклоном луча 3,5 : 1

### Community 8 - "Комплектация «Компакт мини» — что купить и что напечатать"
Cohesion: 0.06
Nodes (43): Сейчас: этап 1 — для мини всё заказано, детали 19–31 октября 2026, STS3032-C036 — даташит Feetech (6 В), FE-URT-1 — адаптер шины (xlsx), Feetech — таблица регистров (xlsx), Комплектация «Компакт мини» — что купить и что напечатать, 3D-печать мини: 41 деталь, ≈ 157 г (PLA / PETG / TPU), Размеры horn_top (4,8 мм) и shaft_from_end (5,7 мм) — измерить до печати, STS3032-C036 — 3 280 ₽ (Feetech Official Store), 4 170 ₽ (Ozon) (+35 more)

### Community 9 - "Харви — главная заметка"
Cohesion: 0.10
Nodes (31): README папки проекта Харви, Obsidian-хранилище на всю папку harvey, Онлайн-версии документов (артефакты claude.ai), Документы — даташиты и PDF, Харви — галерея, Компоновка v2 — вид сверху (цвета по узлам), Режим «фото» (Filament PBR): песок со следами, галька, трава, Рендеры «Компакт мини» на столе 1 : 1 (Blender, Cycles) (+23 more)

### Community 10 - "Харви — проверка совместимости и сценарии"
Cohesion: 0.09
Nodes (28): reSpeaker XVF3800 (USB, 4 микрофона), Порядок закупки в 4 этапа, Шесть ног, Харви — проверка совместимости и сценарии, MuJoCo (физический движок), PyBullet (физический движок), Датчики края — между клешнями, ~25 мм от центра, Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения (+20 more)

### Community 11 - "harvey_layout.py"
Cohesion: 0.08
Nodes (20): check(), claw(), claw_ok(), claw_parts_chassis(), eye(), eye_ok(), flat(), inter() (+12 more)

### Community 12 - "harvey_leg_parts.py"
Cohesion: 0.06
Nodes (26): to_trimesh(), coxa_case(), coxa_metal(), leg(), s15_case_y(), s15_metal_y(), tower(), box() (+18 more)

### Community 13 - "harvey_sim.py"
Cohesion: 0.07
Nodes (27): inertial(), PB, stand(), urdf(), walk(), arm_ik(), arm_xml(), build_xml() (+19 more)

### Community 14 - "Модель Харви «Компакт мини» в MuJoCo (шесть ног, две клешни, глаза-стебельки, без хвоста)"
Cohesion: 0.22
Nodes (10): Скриншот: вид глазами Харви (мини), Камера Module 3 Wide — вид глазами Харви (клавиша V), Скриншот: мини на столе среди предметов, Реквизит рабочего стола (ручки, карандаш, блокнот, кейс наушников, книга, лампа, ноутбук), Скриншот: приветствие правой клешнёй (мини), Жест «привет» — клешня поднята вверх, Скриншот: Компакт мини на рабочем столе, Модель Харви «Компакт мини» в MuJoCo (шесть ног, две клешни, глаза-стебельки, без хвоста) (+2 more)

### Community 15 - "harvey_mini_parts.py"
Cohesion: 0.11
Nodes (16): chassis(), coxa_servo_leg(), coxa_servos(), edge_sensors(), electronics(), eye_servo_body(), eye_servos(), fixed_parts() (+8 more)

### Community 16 - "sts.py"
Cohesion: 0.15
Nodes (17): checksum(), make_packet(), parse_status(), State, to_signed(), test_amps_from_register_or_from_load(), _status(), test_echo_is_recognisable() (+9 more)

### Community 17 - "sts_bus.py"
Cohesion: 0.09
Nodes (12): now_s(), run(), FakeUart, main(), Bus, BusError, checksum(), find_status() (+4 more)

### Community 18 - "Leg"
Cohesion: 0.13
Nodes (3): clamp(), Leg, test_center_all_with_empty_bus_records_nothing()

### Community 19 - "numpy"
Cohesion: 0.12
Nodes (11): main(), add(), material(), add(), body_map(), leg_map(), main(), pack() (+3 more)

### Community 20 - "make_wiring.py"
Cohesion: 0.18
Nodes (4): bus_buffer(), pi_sheet(), power_sheet(), render()

### Community 21 - "math"
Cohesion: 0.16
Nodes (12): build_tail(), legs_push(), rel(), T, tail_ik(), tail_move(), test_handover(), test_pick_place() (+4 more)

### Community 23 - "harvey_eye_parts.py"
Cohesion: 0.15
Nodes (13): back_cover(), bumper(), display(), eye_center(), horn_adapter(), housing(), housing_radius(), housing_x() (+5 more)

### Community 24 - "claw_assembly"
Cohesion: 0.23
Nodes (9): claw_assembly(), T_ay(), T_fore(), T_hand(), T_up(), export_stl(), fixed_jaw(), lift_servo_arm() (+1 more)

### Community 25 - "result"
Cohesion: 0.08
Nodes (32): answer(), result(), test_assign_id_renumbers_the_only_servo(), test_backlash_not_measured(), test_backlash_over_one_degree_fails(), test_heat_mean_current_over_norm_fails(), test_heat_stops_after_five_seconds_of_overcurrent(), test_repeatability_fails_when_returns_scatter() (+24 more)

### Community 26 - "FakeBus"
Cohesion: 0.13
Nodes (6): FakeBus, Servo, u16(), test_fake_bus_set_id_and_move(), test_set_middle_makes_position_2048(), test_state_block_read_matches_single_registers()

### Community 27 - "harvey_world.py"
Cohesion: 0.13
Nodes (9): apply(), asset_xml(), grab_equalities(), load_assets(), pbr_material(), props_xml(), _ramp(), robot_visual() (+1 more)

### Community 29 - "bench.py"
Cohesion: 0.10
Nodes (6): open_bench(), parse_args(), release(), run_menu(), _header(), write()

### Community 30 - "harvey_grasp.py"
Cohesion: 0.21
Nodes (12): build(), build_cup(), finger_mid(), G, obj_forces(), path(), pen_test(), phone_test() (+4 more)

### Community 31 - "Харви — управление в симуляции (README)"
Cohesion: 0.14
Nodes (15): Харви — управление в симуляции (README), Датчики края стола (защита края), MuJoCo-симуляция Харви (компоновка v2), Сценарии проверки (harvey_scenarios.py all), Режим «фото»: рендер Filament, физика в отдельном процессе, Физика веществ: деформируемый песок, гравий и галька, трава, Скриншот: полоса препятствий на полу (поверхности), Доска-спуск 20° со стола на пол (+7 more)

### Community 32 - "Харви 1.0 — питание и проводка"
Cohesion: 0.11
Nodes (21): Питание мини: 2 × 18650 (2S, ~22 Вт·ч), DC-DC 6 В 6 А, Датчик тока INA226, Батарея 3S из банок 21700 (~50 Вт·ч), Waveshare Bus Servo Adapter (A) — шина от Pico по UART, Буферы именно LVC (SN74LVC1G125/126) — входы выдерживают 5 В, Харви 1.0 — питание и проводка, BMS 3S 40 А с балансировкой, DC-DC 6 В на 8 А (а не 5 А) (+13 more)

### Community 33 - "harvey_tail_parts.py"
Cohesion: 0.15
Nodes (11): arm_plate(), base(), cup(), cup_holder(), elbow_sleeve(), forearm(), j2_cols(), link_parts() (+3 more)

### Community 34 - "disk_on_horn"
Cohesion: 0.14
Nodes (10): coxa_bracket(), disk_on_horn(), femur_link(), forearm(), hull(), plate_on_face(), rod(), tibia() (+2 more)

### Community 35 - "harvey_scenarios.py"
Cohesion: 0.17
Nodes (18): trial(), edge_sensor(), feet_x(), sc_battery(), sc_edge(), sc_failure(), sc_obstacles(), sc_push() (+10 more)

### Community 37 - "test_bench_main.py"
Cohesion: 0.25
Nodes (10): main(), report(), test_compact_auto_runs_every_servo_test_and_saves_report(), test_compact_menu_single_test_uses_typed_servo_number(), test_ctrl_c_releases_every_servo_and_returns_1(), test_mini_auto_runs_servo_and_leg_program(), test_mini_menu_tests_the_servo_found_by_scan(), test_unknown_choice_is_ignored_and_zero_saves() (+2 more)

### Community 38 - "Raspberry Pi AI HAT+ (13/26 TOPS)"
Cohesion: 0.25
Nodes (9): AI HAT+ — краткое описание, Raspberry Pi AI HAT+ (13/26 TOPS), Ускоритель Hailo-8 / Hailo-8L (NPU), Связь AI HAT+ по PCIe Gen 3, Питание Pico 2: VSYS 1,8–5,5 В, SMPS RT6150, 3V3 ≤ 300 мА, Raspberry Pi 5 — краткое описание, PCIe 2.0 x1 у Raspberry Pi 5, Питание Pi 5: 5 В / 5 А через USB-C с PD (+1 more)

### Community 39 - "Рендеры и сетки для визуализаций (README)"
Cohesion: 0.27
Nodes (12): Версия корпуса «Компакт», Панцирь 150 × 140 × 70 мм и поднос на спине 87 × 105 мм, Рендеры и сетки для визуализаций (README), Исправления 16.10: кружка, лампа, цветок, карандаши; робот по нижней точке, Масштаб 1 : 1 для обоих роботов и предметов, Рендер Харви «Компакт», вариант «мягкий» (кожух) — спереди-сбоку на столе, Графитовый панцирь soft-touch закрывает электронику (вариант «мягкий»), Рендер Харви «Компакт», вариант «мягкий» — сверху сзади, весь стол (+4 more)

### Community 40 - "Харви — детали стенда одной ноги (PDF)"
Cohesion: 0.20
Nodes (10): Харви — детали стенда одной ноги (PDF), Кронштейн основания (harvey_coxa_bracket.stl), Держатель привода валом вверх (harvey_cradle_servo.stl), Пластина бедра ×2 (harvey_femur_plate_x2.stl), Стопа TPU 95A (harvey_foot_TPU.stl), Обхват привода колена (harvey_knee_sleeve.stl), Рычаг 100 мм (harvey_lever_100mm.stl), Печать и крепёж: PETG 0,2 мм, 40% гироид, вставки M3, зазор 0,3 мм (+2 more)

### Community 41 - "test_bench.py"
Cohesion: 0.09
Nodes (19): measure_servo(), big(), make(), mini(), released(), test_assign_id_refuses_with_two_servos(), test_backlash_from_laser_spot(), test_broken_calibration_file_keeps_defaults() (+11 more)

### Community 42 - "harvey_terrain.py"
Cohesion: 0.16
Nodes (8): grass_assets(), grass_geoms(), sand_heights(), settle(), stone_assets(), _stone_list(), stones_xml(), _tuft_mesh()

### Community 44 - "check"
Cohesion: 0.15
Nodes (7): check(), claw_ok(), claw_points(), display(), eye_assembly(), eye_stalk(), _flat()

### Community 45 - "export_robot.py"
Cohesion: 0.29
Nodes (11): claws(), coxa_servo_split(), eyes(), frame(), leg_servo_split(), legs(), robot(), s15_split() (+3 more)

### Community 47 - "conftest.py"
Cohesion: 0.18
Nodes (7): FakeLegBus, Режим без железа (SIM): имитация привода, bench(), bus(), calibrated(), in_tmp(), leg()

### Community 49 - "SerialBus"
Cohesion: 0.23
Nodes (3): BusError, le16(), SerialBus

### Community 50 - "«Компакт мини» — компоновка, 4 вида (перспектива, сверху, спереди, сбоку)"
Cohesion: 0.22
Nodes (10): «Компакт мини» — компоновка, 4 вида (перспектива, сверху, спереди, сбоку), Компакт мини: шесть ног, две клешни, глаза-стебельки с круглыми дисплеями, без хвоста, «Компакт мини» на том же столе: export_render.py → parts_mini/, HARVEY_ROBOT=mini, Мини_1 — крупный план «Компакт мини» на столе, клешня поднята, Глаза-дисплеи с нарисованными зрачками (выражение «характера»), Мини_2 — «Компакт мини» спереди в тёплом интерьере, клешня над головой, Мини_3 — «Компакт мини» на рабочем столе среди кружки, блокнотов, ручек (масштаб), Масштаб: робот размером с кружку на столе (+2 more)

### Community 52 - "Харви — комплектация и бюджет v0.2"
Cohesion: 0.10
Nodes (29): CLAUDE.md — контекст проекта Харви, Pi 5 + AI HAT+ («голова») и Pico 2 («спинной мозг»), Приводы — шинные Feetech STS (STS3215 C018 на ногах, STS3032 на кистях), Структура папки проекта (заметки, визуализация, модели, документы, фото, код), FE-URT-1 — адаптер шины (таблица, конвертирована), FE-URT-1 — USB → TTL/RS485 программатор шины Feetech, Аппаратное автоматическое переключение направления полудуплекса, Драйвер CH340C (+21 more)

### Community 53 - "render_desk.py"
Cohesion: 0.18
Nodes (4): bbox(), light(), place(), _top_level()

### Community 54 - "Харви — этап 1: покупки и стенд одной ноги"
Cohesion: 0.16
Nodes (15): STS3215-C018 — даташит Feetech (12 В), Feetech STS3215-C018 (12 В, 30 кг·см), Первые тесты мини: 4 × STS3032, URT-1, стенд одной ноги (~25 г печати), Нога: основание, бедро, колено (звенья 40 / 51 / 70 мм), Харви — этап 1: покупки и стенд одной ноги, Архив Harvey_leg_CAD.zip (детали стенда ноги), Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS, Замер люфта лазерной указкой (1° ≈ 17 мм на 1 м) (+7 more)

### Community 56 - "export_sim"
Cohesion: 0.16
Nodes (14): elbow_servo_up(), export_sim(), put(), femur_servo_coxa(), foot(), grip_servo_hand(), knee_servo_femur(), leg_assembly() (+6 more)

### Community 58 - "leg.py"
Cohesion: 0.09
Nodes (15): abort_reason(), gait_ok(), parse_grams(), stance_ok(), test_calibrate_current_ignores_small_or_missing_reading(), test_heat_case_norm_65(), test_precheck_voltage_window_and_temperature(), test_stall_norm_2_4_to_3_0_amps() (+7 more)

### Community 59 - "LegCal"
Cohesion: 0.30
Nodes (7): LegCal, test_broken_calibration_file_falls_back_to_defaults(), test_calibration_makes_pose_g_the_middle_and_saves(), test_calibration_survives_save_and_load(), test_missing_checked_flag_means_not_checked(), test_to_pos_uses_offset_and_direction(), test_leg_calibration_mapping()

### Community 60 - "mini_objects.py"
Cohesion: 0.32
Nodes (4): assets(), bodies(), _hex_mesh(), _hex_tip_mesh()

### Community 61 - "harvey_teleop.py"
Cohesion: 0.09
Nodes (10): main(), world_model(), Скриншот: протирка салфеткой (мини), Протирка стола салфеткой (мини), eye_force(), edge_seen(), Управление с клавиатуры и панель управления, Рефлекс защиты глаз при опрокидывании (складывание до −105°) (+2 more)

### Community 63 - "Feetech — протокол связи (SCS/SMS)"
Cohesion: 0.16
Nodes (15): Цель: позиция, время, скорость (адреса 42–46), Feetech — протокол связи (SCS/SMS), Широковещательный ID 254 (0xFE), Порядок байт SMS/STS: младший байт первым, Контрольная сумма ~(ID+Len+Instr+Params) & 0xFF, Регистр цели 0x2A: позиция, время, скорость (6 байт), Регистр ID (адрес 5) и блокировка EPROM, Пакет инструкции 0xFF 0xFF ID Len Instr Params Checksum (+7 more)

### Community 64 - "Харви «Компакт мини»"
Cohesion: 0.14
Nodes (15): Ветки kompakt (v2-kompakt) и kompakt-mini, Версии: kompakt «Компакт» и kompakt-mini «Компакт мини», Версии Харви, v2 «Компакт» (метка v2-kompakt, ветка kompakt), сохранена 16.10.2026, «Компакт мини» (ветка kompakt-mini, в работе), Харви «Компакт мини», Бюджет мини ≈ 115–158 тыс. ₽ (почти как «Компакт»), Задачи мини: протереть стол, подать ручку, общаться, сам заряжаться (+7 more)

### Community 65 - "check_dock"
Cohesion: 0.13
Nodes (9): check_dock(), check_stand(), dock_pad(), dock_pogo(), dock_tower(), inter(), leg_pose_for_drop(), leg_stand() (+1 more)

### Community 66 - "test_leg.py"
Cohesion: 0.08
Nodes (8): step_pose(), test_calibration_swings_each_joint_ten_degrees_when_asking(), test_gait_logs_temperatures_and_estimates_battery(), test_gait_stops_on_low_voltage(), test_gait_stops_when_femur_overheats(), test_step_pose_closes_the_cycle(), test_step_pose_support_then_swing(), test_step_pose_swing_lifts_proportionally()

### Community 67 - "run_gui"
Cohesion: 0.16
Nodes (8): keyname(), RemoteMini, run_gui(), close(), press(), release(), tick(), toggle_view()

### Community 68 - "Feetech — таблица регистров (конвертирована)"
Cohesion: 0.29
Nodes (10): Feetech — таблица регистров (конвертирована), Блокировка записи EPROM (адрес 48), Защита от перегрузки (регистры 37–39: момент, время, порог 80%), Максимальный момент (адрес 16), Включение момента (адрес 40), Регистр ID (адрес 5; 254 — широковещательный), Регистр скорости шины (адрес 6; 0 = 1 Мбит/с), Обратная связь: позиция, скорость, нагрузка, напряжение, температура (56–63) (+2 more)

### Community 69 - "Компакт мини — детали и компоновка (README)"
Cohesion: 0.22
Nodes (8): Безопасность стенда: пределы напряжения, температуры, время упора, Компакт мини — детали и компоновка (README), Компакт мини: 893 г, корпус 114×88×39, 28 × STS3032, Правила движения мини (клешни, глаза, ноги, передняя кромка x ≤ 67 мм, поза «поджато»), Станция зарядки мини: площадка с подпружиненными контактами, башенка с AprilTag и ИК-маяком, Электроника мини в три этажа: 2 × 18650, Pi Zero 2 W, RP2350-Zero, Сетки для браузерных визуализаций: export_web.py («Компакт») и export_web_mini.py (двойник мини), Визуализация в браузере: 3D-модель и двойник «Компакта», двойник мини (переключатель версий)

### Community 70 - "Компакт мини — симуляция (README)"
Cohesion: 0.15
Nodes (14): Зарядка мини: латунные пластины на брюхе + станция с AprilTag и ИК-маяком, Питание мини: 2 × 18650 (2S, ~22 Вт·ч), BMS 2S, IP2326, DC-DC 6 В ≥ 6 А и 5 В 3 А, Станция-«гнездо» мини: USB-C 5 В 3 А, ИК-маяк 940 нм / 38 кГц, метка AprilTag, Компакт мини — симуляция (README), Вид глазами Харви: неподвижная Camera Module 3 Wide, наклон корпусом ±12°, Выбор движка: MuJoCo + Filament вместо Isaac Sim, Unreal/Unity, Genesis, Gazebo, Захват губками с пределом момента (как Torque Limit STS3032), --grip-test, Модель батареи 22 Вт·ч и заряд 12 Вт на станции (+6 more)

### Community 71 - "Привод Feetech STS3215-C018 (12 В, 30 кг·см)"
Cohesion: 0.22
Nodes (11): Порядок сборки ноги: ID 1/2/3, середина 2048, ось бедра 55 мм над столом, Размеры привода для сверки (servo_L 45,2, W 24,7, H 32, shaft_from_end 12,5, flange_D 20), Защиты STS3032: перегрузка, напряжение 4–7,4 В, 70 °C, Привод Feetech STS3032-C036 (6 В, 4,5 кг·см), 12-битный магнитный энкодер: 4096 отсчётов, 0,088°, середина 2048, Калибровка середины: 128 в адрес 40, Режимы 0–3: серво, скорость замкн./разомкн., шаговый; многооборотный ±7, Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C (+3 more)

### Community 75 - "Pico 2 — даташит"
Cohesion: 0.33
Nodes (7): Полудуплексная асинхронная шина 8N1, Pico 2 — даташит, Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3), MicroPython на Pico 2, Микроконтроллер RP2350, Pico 2 — краткое описание, Raspberry Pi Pico 2

### Community 76 - "Рендер Харви «Компакт», вариант «открытый» (основной) — спереди, поза «привет»"
Cohesion: 0.25
Nodes (8): Круглые дисплеи-глаза GC9A01 1,28″, Две мощные многосуставные клешни, Глаза на стебельках с магнитной муфтой, Клешня с пятью суставами (звенья 54 / 60 / ≈43 мм), Рендер Харви «Компакт», вариант «открытый» (основной) — спереди, поза «привет», Глаза-дисплеи на стебельках (круглые экраны с голубой радужкой) на передних углах, Две многосуставные клешни с пальцами и присоской-захватом, Шесть трёхсуставных ног с шаровыми стопами

### Community 77 - "run_test"
Cohesion: 0.67
Nodes (3): run_test(), note(), pos()

### Community 79 - "Стенд одной ноги (README)"
Cohesion: 0.14
Nodes (14): Стенд кисти STS3032-C036 (README), Перед печатью измерить STS3032: shaft_from_end ~5,7 мм, horn_top ~4,8 мм, Кисть стенда: запястье (привод 21) и захват (привод 22), пальцы 26 мм под 30°, Стенд одной ноги (README), Полная проверка ноги leg_check.py (ходы, стойка, цикл шага), Рендер стенда ноги: две стойки-держателя и нога из трёх приводов, Две серые вертикальные стойки на плите — держатели привода основания, Нога: основание → бедро (пластины) → колено, голень-вилка (+6 more)

## Ambiguous Edges - Review These
- `Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS` → `Таблица регистров SCS15 (прошивка SCServo1.1)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to
- `Рычаг-качалка 25 мм (grip_lever)` → `Сервопривод Feetech STS3032-C036`  [AMBIGUOUS]
  модели/стенд кисти/детали кисти.png · relation: conceptually_related_to
- `Связь AI HAT+ по PCIe Gen 3` → `PCIe 2.0 x1 у Raspberry Pi 5`  [AMBIGUOUS]
  документы/AI HAT+ — краткое описание.pdf · relation: conceptually_related_to
- `Таблица регистров SCS15 (прошивка SCServo1.1)` → `Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to

## Knowledge Gaps
- **80 isolated node(s):** `Датчики края — между клешнями, ~25 мм от центра`, `Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения`, `Походка на пяти ногах (при отказе ноги)`, `Протирка стола с ограничением усилия по току привода`, `Более 40 смоделированных сценариев` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 565 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Харви — главная заметка` connect `Харви — главная заметка` to `Харви «Компакт мини»`, `Харви 1.0 — питание и проводка`, `Компакт мини — детали и компоновка (README)`, `Компакт мини — симуляция (README)`, `Журнал решений`, `Комплектация «Компакт мини» — что купить и что напечатать`, `Харви — детали стенда одной ноги (PDF)`, `Харви — проверка совместимости и сценарии`, `Рендеры и сетки для визуализаций (README)`, `Стенд одной ноги (README)`, `Харви — комплектация и бюджет v0.2`, `Харви — этап 1: покупки и стенд одной ноги`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `boxr()` (e.g. with `stalk()` and `base()`) actually correct?**
  _`boxr()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Датчики края — между клешнями, ~25 мм от центра`, `Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения`, `Походка на пяти ногах (при отказе ноги)` to the rest of the system?**
  _80 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Teleop` be split into smaller, more focused modules?**
  _Cohesion score 0.06493506493506493 - nodes in this community are weakly interconnected._
- **Why does `Харви — стенд привода и ноги (README)` connect `Комплектация «Компакт мини» — что купить и что напечатать` to `Компакт мини — детали и компоновка (README)`, `Харви — главная заметка`, `conftest.py`, `sts.py`, `Харви — этап 1: покупки и стенд одной ноги`, `bench.py`, `Feetech — протокол связи (SCS/SMS)`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS` and `Таблица регистров SCS15 (прошивка SCServo1.1)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Рычаг-качалка 25 мм (grip_lever)` and `Сервопривод Feetech STS3032-C036`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._