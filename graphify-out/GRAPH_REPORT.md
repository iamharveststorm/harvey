# Graph Report - Harvey  (2026-11-02)

## Corpus Check
- 95 files · ~2,536,015 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 239 file(s) not represented in the graph (top: .stl 219, .bat 9, (none) 3)

## Summary
- 1759 nodes · 3792 edges · 77 communities (64 shown, 13 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 498 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0d5d5317`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Teleop
- MiniTeleop
- harvey_claw_parts.py
- harvey_hand_parts.py
- harvey_drawings.py
- harvey_mini.py
- harvey_body_parts.py
- Журнал решений
- Комплектация «Компакт мини» — что купить и что напечатать
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
- numpy
- make_wiring.py
- harvey_tail.py
- Bench
- harvey_eye_parts.py
- claw_assembly
- result
- Servo
- harvey_world.py
- bench.py
- harvey_grasp.py
- Харви — управление в симуляции (README)
- Харви 1.0 — питание и проводка
- math
- boxr
- harvey_scenarios.py
- AdaptiveGait
- test_bench_main.py
- Raspberry Pi AI HAT+ (13/26 TOPS)
- render_desk.py
- Харви — детали стенда одной ноги (PDF)
- test_bench.py
- harvey_terrain.py
- Terrain
- check
- export_robot.py
- conftest.py
- FakeServo
- SerialBus
- harvey_pybullet.py
- PhotoView
- STS3215-C018 — даташит Feetech (12 В)
- ring
- Харви — этап 1: покупки и стенд одной ноги
- RemoteTeleop
- export_sim
- LegGeometry
- parametrize
- LegCal
- FakeBus
- os
- стенд ноги/export_render_parts.py
- Feetech — протокол связи (SCS/SMS)
- Харви «Компакт мини»
- check_dock
- test_leg.py
- eye_stalk
- Feetech — таблица регистров (конвертирована)
- Компакт мини — детали и компоновка (README)
- leg_assembly
- Привод Feetech STS3215-C018 (12 В, 30 кг·см)
- Компоновка v2, вид сверху (поза «стоит, клешни поджаты»)
- harvey_gait.py
- Pico 2 — даташит
- run_bench_linux.sh

## God Nodes (most connected - your core abstractions)
1. `Журнал решений` - 58 edges
2. `boxr()` - 53 edges
3. `result()` - 48 edges
4. `Bench` - 39 edges
5. `answer()` - 35 edges
6. `Leg` - 34 edges
7. `Харви — главная заметка` - 32 edges
8. `Харви — этап 1: покупки и стенд одной ноги` - 28 edges
9. `Teleop` - 27 edges
10. `export_sim()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Регистр ID (адрес 5; 254 — широковещательный)` --semantically_similar_to--> `Регистр ID (адрес 5) и блокировка EPROM`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Цель: позиция, время, скорость (адреса 42–46)` --semantically_similar_to--> `Регистр цели 0x2A: позиция, время, скорость (6 байт)`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Встроенная защита STS3215 (70 °C, 2 А / 2 с, 4–14 В)` --semantically_similar_to--> `Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C`  [INFERRED] [semantically similar]
  заметки/Питание и проводка.md → документы/STS3215-C018 — даташит Feetech (12 В).pdf
- `Протирка стола салфеткой (мини)` --semantically_similar_to--> `sc_wipe()`  [INFERRED] [semantically similar]
  код/симуляция/мини/mini_салфетка.png → код/симуляция/управление с клавиатуры/harvey_scenarios.py
- `Замеры 1–7 стенда «Компакт» (связь, ток, момент, скорость, люфт, точность, нагрев)` --conceptually_related_to--> `STS3215-C018 — даташит Feetech (12 В)`  [INFERRED]
  код/стенд привода/README.md → документы/STS3215-C018 — даташит Feetech (12 В).pdf

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

## Communities (77 total, 13 thin omitted)

### Community 0 - "Teleop"
Cohesion: 0.07
Nodes (17): edge_seen(), KeyReader, run_gui(), act(), close(), keyname(), norm(), on_press_track() (+9 more)

### Community 1 - "MiniTeleop"
Cohesion: 0.06
Nodes (16): _child(), keyname(), MiniTeleop, near_plane(), RemoteMini, run_grip_test(), run_gui(), close() (+8 more)

### Community 2 - "harvey_claw_parts.py"
Cohesion: 0.06
Nodes (37): pad_pair(), s15_case(), s15_metal(), s32_case(), s32_metal(), scene(), arm_plate(), base() (+29 more)

### Community 3 - "harvey_hand_parts.py"
Cohesion: 0.08
Nodes (36): assembly(), box(), check(), cyl(), finger_bar(), grip_lever(), horn_disk(), jaw() (+28 more)

### Community 4 - "harvey_drawings.py"
Cohesion: 0.08
Nodes (29): box(), build(), cut(), cylx(), cyly(), cylz(), dim_circle(), dim_pts() (+21 more)

### Community 5 - "harvey_mini.py"
Cohesion: 0.11
Nodes (23): arm_fk(), arm_ik(), build_xml(), claw_ok(), dock_xml(), joint_names(), leg_ik(), load_assets() (+15 more)

### Community 6 - "harvey_body_parts.py"
Cohesion: 0.09
Nodes (14): run(), camera_assembly(), camera_mount(), check(), test(), claw_base_world(), deck(), edge_sensors() (+6 more)

### Community 7 - "Журнал решений"
Cohesion: 0.07
Nodes (5): Окружения Python в C:\venvs (harvey, harvey-bench, harvey-cad), Планка-фиксатор привода бедра (harvey_coxa_strap.stl), Журнал решений, Перепроверка 15.10: перепечатать 4 детали, новая стойка ноги, Боковые датчики края с наклоном луча 3,5 : 1

### Community 8 - "Комплектация «Компакт мини» — что купить и что напечатать"
Cohesion: 0.07
Nodes (41): STS3032-C036 — даташит Feetech (6 В), Документы — даташиты и PDF, FE-URT-1 — адаптер шины (xlsx), Feetech — таблица регистров (xlsx), Комплектация «Компакт мини» — что купить и что напечатать, 3D-печать мини: 41 деталь, ≈ 157 г (PLA / PETG / TPU), Размеры horn_top (4,8 мм) и shaft_from_end (5,7 мм) — измерить до печати, STS3032-C036 — 3 280 ₽ (Feetech Official Store), 4 170 ₽ (Ozon) (+33 more)

### Community 9 - "Харви — главная заметка"
Cohesion: 0.08
Nodes (37): CLAUDE.md — контекст проекта Харви, Ветки kompakt (v2-kompakt) и kompakt-mini, Структура папки проекта (заметки, визуализация, модели, документы, фото, код), README папки проекта Харви, Obsidian-хранилище на всю папку harvey, Онлайн-версии документов (артефакты claude.ai), Версии: kompakt «Компакт» и kompakt-mini «Компакт мини», Сейчас: этап 1 — для мини всё заказано, детали 19–31 октября 2026 (+29 more)

### Community 10 - "Харви — проверка совместимости и сценарии"
Cohesion: 0.09
Nodes (28): Без ПК — «сонный питомец»: ходит, не падает, эмоции, сам заряжается, Порядок закупки в 4 этапа, Шесть ног, Харви — проверка совместимости и сценарии, MuJoCo (физический движок), PyBullet (физический движок), Датчики края — между клешнями, ~25 мм от центра, Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения (+20 more)

### Community 11 - "harvey_layout.py"
Cohesion: 0.10
Nodes (14): check(), claw(), claw_ok(), claw_parts_chassis(), eye(), eye_ok(), flat(), inter() (+6 more)

### Community 12 - "harvey_leg_parts.py"
Cohesion: 0.07
Nodes (26): to_trimesh(), box(), coxa_bracket(), cradle(), cyl(), femur_plate(), flange_cut(), foot() (+18 more)

### Community 13 - "harvey_sim.py"
Cohesion: 0.10
Nodes (20): arm_ik(), arm_xml(), build_xml(), eye_xml(), ik(), neutral(), pose_targets(), power() (+12 more)

### Community 14 - "Компакт мини — симуляция (README)"
Cohesion: 0.12
Nodes (22): Питание мини: 2 × 18650 (2S, ~22 Вт·ч), BMS 2S, IP2326, DC-DC 6 В ≥ 6 А и 5 В 3 А, Скриншот: вид глазами Харви (мини), Камера Module 3 Wide — вид глазами Харви (клавиша V), Скриншот: мини на столе среди предметов, Реквизит рабочего стола (ручки, карандаш, блокнот, кейс наушников, книга, лампа, ноутбук), Скриншот: приветствие правой клешнёй (мини), Жест «привет» — клешня поднята вверх, Скриншот: протирка салфеткой (мини) (+14 more)

### Community 15 - "harvey_mini_parts.py"
Cohesion: 0.13
Nodes (14): chassis(), coxa_servo_leg(), coxa_servos(), edge_sensors(), electronics(), eye_servos(), fixed_parts(), _leg_tf() (+6 more)

### Community 16 - "sts.py"
Cohesion: 0.17
Nodes (13): checksum(), make_packet(), parse_status(), _status(), test_echo_is_recognisable(), test_leg_ik_fk_roundtrip_and_stance(), test_packet_ping_matches_reference(), test_packet_read_position() (+5 more)

### Community 17 - "sts_bus.py"
Cohesion: 0.09
Nodes (12): now_s(), run(), FakeUart, main(), Bus, BusError, checksum(), find_status() (+4 more)

### Community 18 - "Leg"
Cohesion: 0.13
Nodes (3): clamp(), Leg, test_center_all_with_empty_bus_records_nothing()

### Community 19 - "numpy"
Cohesion: 0.18
Nodes (8): add(), body_map(), leg_map(), main(), pack(), pack(), height(), save_h()

### Community 20 - "make_wiring.py"
Cohesion: 0.18
Nodes (4): bus_buffer(), pi_sheet(), power_sheet(), render()

### Community 21 - "harvey_tail.py"
Cohesion: 0.19
Nodes (11): build_tail(), legs_push(), rel(), T, tail_ik(), tail_move(), test_handover(), test_pick_place() (+3 more)

### Community 22 - "Bench"
Cohesion: 0.13
Nodes (5): Bench, compact_actions(), measure_servo(), mini_actions(), Session

### Community 23 - "harvey_eye_parts.py"
Cohesion: 0.15
Nodes (13): back_cover(), bumper(), display(), eye_center(), horn_adapter(), housing(), housing_radius(), housing_x() (+5 more)

### Community 24 - "claw_assembly"
Cohesion: 0.23
Nodes (9): claw_assembly(), T_ay(), T_fore(), T_hand(), T_up(), export_stl(), fixed_jaw(), moving_jaw() (+1 more)

### Community 25 - "result"
Cohesion: 0.08
Nodes (30): answer(), result(), test_assign_id_renumbers_the_only_servo(), test_backlash_not_measured(), test_backlash_over_one_degree_fails(), test_heat_case_default_is_sensor_minus_three(), test_heat_mean_current_over_norm_fails(), test_heat_stops_after_five_seconds_of_overcurrent() (+22 more)

### Community 26 - "Servo"
Cohesion: 0.13
Nodes (9): Servo, State, to_signed(), u16(), test_amps_from_register_or_from_load(), test_fake_bus_set_id_and_move(), test_set_middle_makes_position_2048(), test_sign_magnitude() (+1 more)

### Community 27 - "harvey_world.py"
Cohesion: 0.10
Nodes (13): world_model(), apply(), asset_xml(), grab_equalities(), load_assets(), pbr_material(), props_xml(), _ramp() (+5 more)

### Community 29 - "bench.py"
Cohesion: 0.09
Nodes (7): heat_ok(), open_bench(), parse_args(), release(), run_menu(), _header(), write()

### Community 30 - "harvey_grasp.py"
Cohesion: 0.21
Nodes (12): build(), build_cup(), finger_mid(), G, obj_forces(), path(), pen_test(), phone_test() (+4 more)

### Community 31 - "Харви — управление в симуляции (README)"
Cohesion: 0.13
Nodes (16): Харви — управление в симуляции (README), Датчики края стола (защита края), Управление с клавиатуры и панель управления, MuJoCo-симуляция Харви (компоновка v2), Сценарии проверки (harvey_scenarios.py all), Режим «фото»: рендер Filament, физика в отдельном процессе, Рефлекс защиты глаз при опрокидывании (складывание до −105°), Физика веществ: деформируемый песок, гравий и галька, трава (+8 more)

### Community 32 - "Харви 1.0 — питание и проводка"
Cohesion: 0.08
Nodes (36): Pi 5 + AI HAT+ («голова») и Pico 2 («спинной мозг»), Pi Zero 2 W + RP2350-Zero («спинной мозг»), Питание мини: 2 × 18650 (2S, ~22 Вт·ч), DC-DC 6 В 6 А, Харви — комплектация и бюджет v0.2, AI HAT+ 26 TOPS (Hailo-8), Raspberry Pi Camera Module 3 Wide, IMU BMI270 / ICM-42688, Датчик тока INA226 (+28 more)

### Community 33 - "math"
Cohesion: 0.10
Nodes (16): assets(), bodies(), _hex_mesh(), _hex_tip_mesh(), arm_plate(), base(), cup(), cup_holder() (+8 more)

### Community 34 - "boxr"
Cohesion: 0.14
Nodes (12): coxa_bracket(), disk_on_horn(), femur_link(), forearm(), hull(), pads(), plate_on_face(), rod() (+4 more)

### Community 35 - "harvey_scenarios.py"
Cohesion: 0.18
Nodes (16): eye_force(), trial(), edge_sensor(), feet_x(), sc_battery(), sc_edge(), sc_failure(), sc_obstacles() (+8 more)

### Community 37 - "test_bench_main.py"
Cohesion: 0.25
Nodes (10): main(), report(), test_compact_auto_runs_every_servo_test_and_saves_report(), test_compact_menu_single_test_uses_typed_servo_number(), test_ctrl_c_releases_every_servo_and_returns_1(), test_mini_auto_runs_servo_and_leg_program(), test_mini_menu_tests_the_servo_found_by_scan(), test_unknown_choice_is_ignored_and_zero_saves() (+2 more)

### Community 38 - "Raspberry Pi AI HAT+ (13/26 TOPS)"
Cohesion: 0.25
Nodes (9): AI HAT+ — краткое описание, Raspberry Pi AI HAT+ (13/26 TOPS), Ускоритель Hailo-8 / Hailo-8L (NPU), Связь AI HAT+ по PCIe Gen 3, Питание Pico 2: VSYS 1,8–5,5 В, SMPS RT6150, 3V3 ≤ 300 мА, Raspberry Pi 5 — краткое описание, PCIe 2.0 x1 у Raspberry Pi 5, Питание Pi 5: 5 В / 5 А через USB-C с PD (+1 more)

### Community 39 - "render_desk.py"
Cohesion: 0.06
Nodes (38): v2 «Компакт» (метка v2-kompakt, ветка kompakt), сохранена 16.10.2026, Круглые дисплеи-глаза GC9A01 1,28″, Хвост — третья рука с присоской, Версия корпуса «Компакт», Две мощные многосуставные клешни, Глаза на стебельках с магнитной муфтой, Клешня с пятью суставами (звенья 54 / 60 / ≈43 мм), Панцирь 150 × 140 × 70 мм и поднос на спине 87 × 105 мм (+30 more)

### Community 40 - "Харви — детали стенда одной ноги (PDF)"
Cohesion: 0.20
Nodes (10): Харви — детали стенда одной ноги (PDF), Кронштейн основания (harvey_coxa_bracket.stl), Держатель привода валом вверх (harvey_cradle_servo.stl), Пластина бедра ×2 (harvey_femur_plate_x2.stl), Стопа TPU 95A (harvey_foot_TPU.stl), Обхват привода колена (harvey_knee_sleeve.stl), Рычаг 100 мм (harvey_lever_100mm.stl), Печать и крепёж: PETG 0,2 мм, 40% гироид, вставки M3, зазор 0,3 мм (+2 more)

### Community 41 - "test_bench.py"
Cohesion: 0.08
Nodes (23): big(), make(), mini(), released(), test_assign_id_refuses_with_two_servos(), test_backlash_from_laser_spot(), test_broken_calibration_file_keeps_defaults(), test_current_idle_and_stall_on_sts3215() (+15 more)

### Community 42 - "harvey_terrain.py"
Cohesion: 0.12
Nodes (9): main(), world_model(), grass_assets(), grass_geoms(), settle(), stone_assets(), _stone_list(), stones_xml() (+1 more)

### Community 44 - "check"
Cohesion: 0.13
Nodes (9): check(), check_stand(), claw_ok(), claw_points(), put(), _flat(), inter(), leg_stand() (+1 more)

### Community 45 - "export_robot.py"
Cohesion: 0.20
Nodes (12): claws(), coxa_servo_split(), eyes(), frame(), leg_servo_split(), legs(), robot(), s15_split() (+4 more)

### Community 47 - "conftest.py"
Cohesion: 0.18
Nodes (7): FakeLegBus, Режим без железа (SIM): имитация привода, bench(), bus(), calibrated(), in_tmp(), leg()

### Community 50 - "harvey_pybullet.py"
Cohesion: 0.23
Nodes (7): inertial(), PB, stand(), urdf(), walk(), Сверка во втором движке PyBullet, requirements-extra.txt (pybullet ≥3.2.6)

### Community 52 - "STS3215-C018 — даташит Feetech (12 В)"
Cohesion: 0.18
Nodes (13): Приводы — шинные Feetech STS (STS3215 C018 на ногах, STS3032 на кистях), FE-URT-1 — адаптер шины (таблица, конвертирована), FE-URT-1 — USB → TTL/RS485 программатор шины Feetech, Аппаратное автоматическое переключение направления полудуплекса, Драйвер CH340C, Порты SMS (RS485, 5264-4AW) и SCS (TTL, 5264-3AW), STS3215-C018 — даташит Feetech (12 В), 28 × STS3032 (ноги 6 × 3, клешни 2 × 4, глаза 2) (+5 more)

### Community 53 - "ring"
Cohesion: 0.19
Nodes (7): belly(), leg_post(), ring(), ring_outline(), sleeve_leg(), sleeves_world(), to_leg()

### Community 54 - "Харви — этап 1: покупки и стенд одной ноги"
Cohesion: 0.15
Nodes (17): Первые тесты мини: 4 × STS3032, URT-1, стенд одной ноги (~25 г печати), Харви — этап 1: покупки и стенд одной ноги, Архив Harvey_leg_CAD.zip (детали стенда ноги), Замер люфта лазерной указкой (1° ≈ 17 мм на 1 м), Замер момента: рычаг 100 мм на кухонные весы, Лабораторный блок питания с ограничением тока, Назначение ID приводов: 1–3 нога, 21–22 кисть, Протокол стенда: 12 замеров (+9 more)

### Community 56 - "export_sim"
Cohesion: 0.29
Nodes (8): elbow_servo_up(), export_sim(), femur_servo_coxa(), grip_servo_hand(), knee_servo_femur(), lift_servo_arm(), servo_at(), servo_sym()

### Community 58 - "parametrize"
Cohesion: 0.17
Nodes (10): heat_abort(), test_calibrate_current_ignores_small_or_missing_reading(), test_heat_abort_by_temperature_and_long_overcurrent(), test_heat_case_norm_65(), test_heat_ok_norms(), test_precheck_voltage_window_and_temperature(), test_stall_norm_2_4_to_3_0_amps(), test_clamp_keeps_angles_inside_motion_rules() (+2 more)

### Community 59 - "LegCal"
Cohesion: 0.30
Nodes (7): LegCal, test_broken_calibration_file_falls_back_to_defaults(), test_calibration_makes_pose_g_the_middle_and_saves(), test_calibration_survives_save_and_load(), test_missing_checked_flag_means_not_checked(), test_to_pos_uses_offset_and_direction(), test_leg_calibration_mapping()

### Community 61 - "os"
Cohesion: 0.10
Nodes (6): currents(), run(), run_linux.sh script, main(), add(), material()

### Community 62 - "стенд ноги/export_render_parts.py"
Cohesion: 0.33
Nodes (6): coxa_case(), coxa_metal(), leg(), s15_case_y(), s15_metal_y(), tower()

### Community 63 - "Feetech — протокол связи (SCS/SMS)"
Cohesion: 0.16
Nodes (15): Цель: позиция, время, скорость (адреса 42–46), Feetech — протокол связи (SCS/SMS), Широковещательный ID 254 (0xFE), Порядок байт SMS/STS: младший байт первым, Контрольная сумма ~(ID+Len+Instr+Params) & 0xFF, Регистр цели 0x2A: позиция, время, скорость (6 байт), Регистр ID (адрес 5) и блокировка EPROM, Пакет инструкции 0xFF 0xFF ID Len Instr Params Checksum (+7 more)

### Community 64 - "Харви «Компакт мини»"
Cohesion: 0.10
Nodes (18): Харви «Компакт мини», Бюджет мини ≈ 115–158 тыс. ₽ (почти как «Компакт»), Задачи мини: протереть стол, подать ручку, общаться, сам заряжаться, Зарядка мини: латунные пластины на брюхе + станция с AprilTag и ИК-маяком, Масса мини 893 г (560 г — приводы); цель ≤ 0,8 кг не достигнута, Проверить на стенде до заказа 30 приводов: нагрев бедра, размеры, ток, дисплей, видео, CAD-проверка мини (harvey_mini_parts.py): 0 столкновений, 332 позы клешни, Симуляция мини (harvey_mini.py): ходьба 6,2 см/с, ручка, салфетка, станция (+10 more)

### Community 65 - "check_dock"
Cohesion: 0.22
Nodes (5): check_dock(), dock_pad(), dock_pogo(), dock_tower(), leg_pose_for_drop()

### Community 66 - "test_leg.py"
Cohesion: 0.06
Nodes (16): abort_reason(), gait_ok(), parse_grams(), stance_ok(), step_pose(), test_abort_reason_heat_then_voltage(), test_calibration_swings_each_joint_ten_degrees_when_asking(), test_gait_logs_temperatures_and_estimates_battery() (+8 more)

### Community 67 - "eye_stalk"
Cohesion: 0.29
Nodes (4): display(), eye_assembly(), eye_servo_body(), eye_stalk()

### Community 68 - "Feetech — таблица регистров (конвертирована)"
Cohesion: 0.29
Nodes (10): Feetech — таблица регистров (конвертирована), Блокировка записи EPROM (адрес 48), Защита от перегрузки (регистры 37–39: момент, время, порог 80%), Максимальный момент (адрес 16), Включение момента (адрес 40), Регистр ID (адрес 5; 254 — широковещательный), Регистр скорости шины (адрес 6; 0 = 1 Мбит/с), Обратная связь: позиция, скорость, нагрузка, напряжение, температура (56–63) (+2 more)

### Community 69 - "Компакт мини — детали и компоновка (README)"
Cohesion: 0.17
Nodes (10): Управление мини с клавиатуры (harvey_mini_teleop.py, run_mini_windows.bat): Filament PBR, физика в отдельном процессе, Безопасность стенда: пределы напряжения, температуры, время упора, Компакт мини — детали и компоновка (README), Компакт мини: 893 г, корпус 114×88×39, 28 × STS3032, Правила движения мини (клешни, глаза, ноги, передняя кромка x ≤ 67 мм, поза «поджато»), Станция зарядки мини: площадка с подпружиненными контактами, башенка с AprilTag и ИК-маяком, Электроника мини в три этажа: 2 × 18650, Pi Zero 2 W, RP2350-Zero, Сетки для браузерных визуализаций: export_web.py («Компакт») и export_web_mini.py (двойник мини) (+2 more)

### Community 70 - "leg_assembly"
Cohesion: 0.38
Nodes (5): foot(), leg_assembly(), T_fem(), T_leg(), T_tib()

### Community 71 - "Привод Feetech STS3215-C018 (12 В, 30 кг·см)"
Cohesion: 0.22
Nodes (11): Порядок сборки ноги: ID 1/2/3, середина 2048, ось бедра 55 мм над столом, Размеры привода для сверки (servo_L 45,2, W 24,7, H 32, shaft_from_end 12,5, flange_D 20), Защиты STS3032: перегрузка, напряжение 4–7,4 В, 70 °C, Привод Feetech STS3032-C036 (6 В, 4,5 кг·см), 12-битный магнитный энкодер: 4096 отсчётов, 0,088°, середина 2048, Калибровка середины: 128 в адрес 40, Режимы 0–3: серво, скорость замкн./разомкн., шаговый; многооборотный ±7, Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C (+3 more)

### Community 72 - "Компоновка v2, вид сверху (поза «стоит, клешни поджаты»)"
Cohesion: 0.33
Nodes (6): Компоновка v2, вид сверху (поза «стоит, клешни поджаты»), Глаза-стебельки на передних углах рамы (~x 90, y ±80 мм), Зоны движения: ноги ±20° в основании, клешни поворот ±15°, хвост ±60°, Плечи клешней спереди (x≈105, y≈±30 мм), Хвост позади рамы (x≈−80 мм), Электроника в центре рамы (жёлтые блоки)

### Community 75 - "Pico 2 — даташит"
Cohesion: 0.33
Nodes (7): Полудуплексная асинхронная шина 8N1, Pico 2 — даташит, Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3), MicroPython на Pico 2, Микроконтроллер RP2350, Pico 2 — краткое описание, Raspberry Pi Pico 2

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 570 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Харви — главная заметка` connect `Харви — главная заметка` to `Харви 1.0 — питание и проводка`, `Харви «Компакт мини»`, `Компакт мини — детали и компоновка (README)`, `Журнал решений`, `Комплектация «Компакт мини» — что купить и что напечатать`, `Харви — детали стенда одной ноги (PDF)`, `Харви — проверка совместимости и сценарии`, `render_desk.py`, `harvey_leg_parts.py`, `Компакт мини — симуляция (README)`, `Харви — этап 1: покупки и стенд одной ноги`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `boxr()` (e.g. with `stalk()` and `base()`) actually correct?**
  _`boxr()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Датчики края — между клешнями, ~25 мм от центра`, `Компоновка v2 на настоящих деталях: 0 столкновений при правилах движения`, `Походка на пяти ногах (при отказе ноги)` to the rest of the system?**
  _80 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Teleop` be split into smaller, more focused modules?**
  _Cohesion score 0.06531986531986532 - nodes in this community are weakly interconnected._
- **Why does `Харви — стенд привода и ноги (README)` connect `Комплектация «Компакт мини» — что купить и что напечатать` to `Компакт мини — детали и компоновка (README)`, `Харви — главная заметка`, `conftest.py`, `sts.py`, `Харви — этап 1: покупки и стенд одной ноги`, `bench.py`, `Feetech — протокол связи (SCS/SMS)`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Рычаг-качалка 25 мм (grip_lever)` and `Сервопривод Feetech STS3032-C036`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Связь AI HAT+ по PCIe Gen 3` and `PCIe 2.0 x1 у Raspberry Pi 5`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._