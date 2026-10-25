# Graph Report - Harvey  (2026-10-25)

## Corpus Check
- Large corpus: 131 files · ~2,347,892 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1544 nodes · 3317 edges · 80 communities (65 shown, 15 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 475 edges (avg confidence: 0.86)
- Token cost: 216,618 input · 0 output

## Community Hubs (Navigation)
- Teleop «Компакт»
- Teleop мини
- CAD клешней
- CAD кисти (стенд)
- Чертежи ГОСТ
- Симуляция мини
- CAD корпуса v2
- Журнал решений
- Комплектация и стенд мини
- Главная и README моделей
- Концепция и совместимость
- Компоновка v2
- CAD стенда ноги
- Сценарии harvey_sim
- Симуляция мини: README и снимки
- CAD мини
- Тесты драйвера и калибровка
- Прошивка: шина Pico
- Нога на стенде (Leg)
- Экспорт для веба
- Стенд: README и модули
- Сценарии и защита
- Меню стенда (Bench)
- CAD глаз
- Экспорт для симуляции мини
- Захват (grasp)
- Servo: операции
- Мир симуляции
- Рендеры Blender стендов
- Бюджет v0.2 и мозги
- CAD хвоста
- Управление и фото-режим
- Питание и проводка
- Хвост: тесты
- CAD детали ноги мини
- Имитация и проверка Pico
- Адаптивная походка
- Экспорт робота
- Документы и платы
- Сценарии Sim2
- Протокол Feetech
- PyBullet-сверка
- Рельеф: камни и трава
- Рельеф: песок
- Проверки CAD мини
- Версии Харви
- Окно PhotoView
- Проверка ноги «Компакта»
- Имитация привода
- Последовательная шина
- Рендеры мини
- Сцена рендера на столе
- Адаптер FE-URT-1 и приводы
- Детали стенда ноги (PDF)
- Этап 1
- Удалённый teleop
- Имитация шины и ноги
- Геометрия ноги
- Таблица регистров
- Приводы Feetech
- README мини и визуализация
- Рендеры «Компакт»
- Рендеры: README
- Стенд ноги: README
- Станция зарядки мини
- Рендер стенда ноги
- Ручки и карандаш
- Станции зарядки
- Детали на рендерах
- Глаз-стебелёк
- Сборка ноги мини
- Даташит STS3215 и замеры
- Компоновка v2: вид сверху
- Рефлекс защиты глаз
- Пути хвоста
- Оценка тока
- Скрипт Linux стенда
- Пустая заметка

## God Nodes (most connected - your core abstractions)
1. `Журнал решений` - 57 edges
2. `boxr()` - 53 edges
3. `Харви — главная заметка` - 32 edges
4. `Харви — этап 1: покупки и стенд одной ноги` - 28 edges
5. `Teleop` - 27 edges
6. `export_sim()` - 26 edges
7. `Харви «Компакт мини»` - 25 edges
8. `Харви 1.0 — питание и проводка` - 25 edges
9. `Компакт мини — симуляция (README)` - 25 edges
10. `Харви — стенд привода и ноги (README)` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Регистр ID (адрес 5; 254 — широковещательный)` --semantically_similar_to--> `Регистр ID (адрес 5) и блокировка EPROM`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Встроенная защита STS3215 (70 °C, 2 А / 2 с, 4–14 В)` --semantically_similar_to--> `Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C`  [INFERRED] [semantically similar]
  заметки/Питание и проводка.md → документы/STS3215-C018 — даташит Feetech (12 В).pdf
- `Цель: позиция, время, скорость (адреса 42–46)` --semantically_similar_to--> `Регистр цели 0x2A: позиция, время, скорость (6 байт)`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Протирка стола салфеткой (мини)` --semantically_similar_to--> `sc_wipe()`  [INFERRED] [semantically similar]
  код/симуляция/мини/mini_салфетка.png → код/симуляция/управление с клавиатуры/harvey_scenarios.py
- `Приводы — шинные Feetech STS (STS3215 C018 на ногах, STS3032 на кистях)` --semantically_similar_to--> `Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре)`  [INFERRED] [semantically similar]
  CLAUDE.md → заметки/Комплектация и бюджет v0.2.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Защита питания Харви** — заметки_питание_и_проводка_аварийная_отсечка_приводов, заметки_питание_и_проводка_мёртвые_контакты_идеальный_диод, заметки_питание_и_проводка_порядок_включения, заметки_питание_и_проводка_пороги_напряжения_pico, заметки_питание_и_проводка_отдельные_dc_dc_и_звезда_земли [EXTRACTED 1.00]
- **Шина Feetech: драйвер стенда, драйвер Pico, имитации** — код_стенд_привода_harvey_bench_sts, код_прошивка_pico_sts_bus, код_прошивка_pico_readme_замер_12_шина_от_pico, код_стенд_привода_readme_sim_mode, код_прошивка_pico_readme_проверка_на_пк_без_железа [INFERRED 0.85]
- **Правила движения v2: CAD-проверка, симуляция и прошивка** — модели_корпус_readme_правила_движения, модели_корпус_harvey_layout, код_симуляция_управление_с_клавиатуры_readme_mujoco_simulation, код_прошивка_прошивка, модели_клешни_readme_клешня_5_суставов, модели_хвост_readme_хвост_с_присоской, модели_глаза_readme_глаз_стебелёк_gc9a01 [EXTRACTED 1.00]
- **Параметрический скрипт → STL → чертёж ГОСТ** — модели_стенд_ноги_harvey_leg_parts, модели_стенд_кисти_harvey_hand_parts, модели_чертежи_readme_чертежи_гост_freecad, модели_чертежи_харви_01_001_рычаг_100_мм, модели_чертежи_харви_02_002_ладонь_кисти [EXTRACTED 1.00]
- **Детали стенда одной ноги этапа 1** — документы_harvey_stage1_parts_cradle_servo, документы_harvey_stage1_parts_coxa_bracket, документы_harvey_stage1_parts_coxa_strap, документы_harvey_stage1_parts_femur_plate, документы_harvey_stage1_parts_knee_sleeve, документы_harvey_stage1_parts_tibia_fork, документы_harvey_stage1_parts_foot_tpu, документы_harvey_stage1_parts_lever_100mm [EXTRACTED 1.00]
- **Обзор камеры мини: вид V, поза «поджато», телеуправление** — код_симуляция_мини_mini_глазами_харви_camera_view, код_симуляция_мини_mini_глазами_харви_tucked_pose, код_симуляция_мини_harvey_mini_teleop [INFERRED 0.85]
- **Кадры mini_photo.py: стол, предметы, салфетка, привет** — код_симуляция_мини_mini_photo, код_симуляция_мини_mini_стол, код_симуляция_мини_mini_и_предметы, код_симуляция_мини_mini_салфетка, код_симуляция_мини_mini_привет [INFERRED 0.95]
- **Полоса препятствий на полу (harvey_world)** — код_симуляция_управление_с_клавиатуры_harvey_world, код_симуляция_управление_с_клавиатуры_мир_полоса_ramp_board, код_симуляция_управление_с_клавиатуры_мир_полоса_surface_zones, код_симуляция_управление_с_клавиатуры_мир_склоны_slopes_zone [INFERRED 0.85]
- **Режим «фото»: Харви на поверхностях физики веществ (песок, галька, трава, склон)** — код_симуляция_управление_с_клавиатуры_фото_песок_следы, код_симуляция_управление_с_клавиатуры_фото_галька, код_симуляция_управление_с_клавиатуры_фото_трава, код_симуляция_управление_с_клавиатуры_фото_склон, код_симуляция_управление_с_клавиатуры_harvey_terrain, код_симуляция_управление_с_клавиатуры_harvey_photo [INFERRED 0.85]
- **Подвижные узлы компоновки v2 и их зоны движения** — модели_корпус_компоновка_вид_сверху_зоны_движения, модели_корпус_компоновка_вид_сверху_глаза_на_углах, модели_корпус_компоновка_вид_сверху_плечи_клешней, модели_корпус_компоновка_вид_сверху_хвост_за_подносом [INFERRED 0.85]
- **Blender-рендеры «Компакт мини» на столе (render_desk.py, HARVEY_ROBOT=mini)** — модели_рендер_мини_1, модели_рендер_мини_2, модели_рендер_мини_3, модели_рендер_render_desk, модели_мини_export_render [EXTRACTED 1.00]
- **Рендеры «Компакта» на столе: 2 варианта корпуса (открытый/мягкий) × ракурсы из render_desk.py** — модели_рендер_харви_мягкий_2, модели_рендер_харви_мягкий_3, модели_рендер_харви_открытый_1, модели_рендер_харви_открытый_2, модели_рендер_харви_открытый_3, модели_рендер_render_desk [INFERRED 0.95]
- **Узнаваемые части «Компакт» v2 на рендере: глаза-стебельки, клешни, шесть ног, хвост** — модели_рендер_харви_открытый_1_глаза_стебельки, модели_рендер_харви_открытый_1_клешни, модели_рендер_харви_открытый_1_шесть_ног, модели_рендер_харви_открытый_3_хвост [INFERRED 0.85]
- **Сборка клешни: ладонь + челюсть + накладки TPU** — модели_стенд_кисти_детали_кисти_palm, модели_стенд_кисти_детали_кисти_jaw, модели_стенд_кисти_детали_кисти_pad_tpu [INFERRED 0.85]
- **Оснастка стенда: стойка запястья, люлька STS3032, рычаг 25 мм** — модели_стенд_кисти_детали_кисти_wrist_stand, модели_стенд_кисти_детали_кисти_cradle_sts3032, модели_стенд_кисти_детали_кисти_grip_lever [INFERRED 0.75]
- **Кинематическая цепь кисти: стойка → запястье #21 → ладонь → захват #22 → челюсть против пальца** — модели_стенд_кисти_сборка_кисти_стойка_запястья, модели_стенд_кисти_сборка_кисти_привод_запястья_21, модели_стенд_кисти_сборка_кисти_ладонь, модели_стенд_кисти_сборка_кисти_привод_захвата_22, модели_стенд_кисти_сборка_кисти_верхняя_челюсть, модели_стенд_кисти_сборка_кисти_нижний_палец [EXTRACTED 1.00]
- **Функции harvey_hand_parts.py, порождающие сборку на рендере** — модели_стенд_кисти_harvey_hand_parts_wrist_stand, модели_стенд_кисти_harvey_hand_parts_palm, модели_стенд_кисти_harvey_hand_parts_jaw, модели_стенд_кисти_harvey_hand_parts_assembly, модели_стенд_кисти_сборка_кисти [INFERRED 0.95]
- **Рендеры стендов этапа 1: кисть клешни и одна нога** — модели_стенд_кисти_рендер_кисти, модели_стенд_ноги_рендер_ног, модели_стенд_кисти_harvey_hand_parts, модели_стенд_ноги_harvey_leg_parts [INFERRED 0.85]
- **Стенд ноги «Компакт мини»: закупка → замер размеров → печать → замеры Н1–Н5** — заметки_чек_лист_стенда_мини, заметки_комплектация_мини_horn_top_shaft_from_end, заметки_журнал_решений_печать_после_замера_horn_top, код_стенд_привода_readme_режим_компакт_мини, код_стенд_привода_readme_нога_замеры_н1_н5, документы_sts3032_c036_даташит_feetech_6_в [INFERRED 0.85]
- **Неподвижная камера мини и поза «поджато» ради обзора** — заметки_журнал_решений_мини_камера_неподвижна, код_симуляция_мини_readme_поза_поджато_для_камеры, код_симуляция_мини_readme_вид_глазами_харви [INFERRED 0.85]
- **Варианты полудуплексной шины от Pico 2: Waveshare адаптер или буферы LVC** — заметки_комплектация_мини_waveshare_bus_servo_adapter, заметки_комплектация_мини_буферы_lvc_5в, заметки_чек_лист_стенда_мини_pico_2_h, код_прошивка_pico_readme [INFERRED 0.85]

## Communities (80 total, 15 thin omitted)

### Community 0 - "Teleop «Компакт»"
Cohesion: 0.06
Nodes (20): currents(), run(), edge_seen(), KeyReader, run_gui(), act(), close(), keyname() (+12 more)

### Community 1 - "Teleop мини"
Cohesion: 0.06
Nodes (17): _child(), keyname(), MiniTeleop, near_plane(), RemoteMini, run_grip_test(), run_gui(), close() (+9 more)

### Community 2 - "CAD клешней"
Cohesion: 0.06
Nodes (37): pad_pair(), s15_case(), s15_metal(), s32_case(), s32_metal(), scene(), arm_plate(), base() (+29 more)

### Community 3 - "CAD кисти (стенд)"
Cohesion: 0.07
Nodes (40): assembly(), box(), check(), cyl(), finger_bar(), grip_lever(), horn_disk(), jaw() (+32 more)

### Community 4 - "Чертежи ГОСТ"
Cohesion: 0.09
Nodes (29): box(), build(), cut(), cylx(), cyly(), cylz(), dim_circle(), dim_pts() (+21 more)

### Community 5 - "Симуляция мини"
Cohesion: 0.11
Nodes (23): arm_fk(), arm_ik(), build_xml(), claw_ok(), dock_xml(), joint_names(), leg_ik(), load_assets() (+15 more)

### Community 6 - "CAD корпуса v2"
Cohesion: 0.08
Nodes (21): belly(), camera_assembly(), camera_mount(), check(), claw_base_world(), deck(), edge_sensors(), electronics() (+13 more)

### Community 7 - "Журнал решений"
Cohesion: 0.07
Nodes (5): Окружения Python в C:\venvs (harvey, harvey-bench, harvey-cad), Планка-фиксатор привода бедра (harvey_coxa_strap.stl), Журнал решений, Перепроверка 15.10: перепечатать 4 детали, новая стойка ноги, Боковые датчики края с наклоном луча 3,5 : 1

### Community 8 - "Комплектация и стенд мини"
Cohesion: 0.09
Nodes (29): STS3032-C036 — даташит Feetech (6 В), FE-URT-1 — адаптер шины (xlsx), Комплектация «Компакт мини» — что купить и что напечатать, 3D-печать мини: 41 деталь, ≈ 157 г (PLA / PETG / TPU), Размеры horn_top (4,8 мм) и shaft_from_end (5,7 мм) — измерить до печати, STS3032-C036 — 3 280 ₽ (Feetech Official Store), 4 170 ₽ (Ozon), Waveshare Bus Servo Adapter (A) — шина от Pico по UART, Буферы именно LVC (SN74LVC1G125/126) — входы выдерживают 5 В (+21 more)

### Community 9 - "Главная и README моделей"
Cohesion: 0.10
Nodes (30): README папки проекта Харви, Obsidian-хранилище на всю папку harvey, Онлайн-версии документов (артефакты claude.ai), Сейчас: этап 1 — для мини всё заказано, детали 19–31 октября 2026, Харви — галерея, Компоновка v2 — вид сверху (цвета по узлам), Режим «фото» (Filament PBR): песок со следами, галька, трава, Рендеры «Компакт мини» на столе 1 : 1 (Blender, Cycles) (+22 more)

### Community 10 - "Концепция и совместимость"
Cohesion: 0.09
Nodes (31): reSpeaker XVF3800 (USB, 4 микрофона), Харви — концепция, Две мощные многосуставные клешни, Добрый характер (ориентир — ВАЛЛ-И), Шесть ног, Харви — проверка совместимости и сценарии, MuJoCo (физический движок), PyBullet (физический движок) (+23 more)

### Community 11 - "Компоновка v2"
Cohesion: 0.10
Nodes (14): check(), claw(), claw_ok(), claw_parts_chassis(), eye(), eye_ok(), flat(), inter() (+6 more)

### Community 12 - "CAD стенда ноги"
Cohesion: 0.13
Nodes (16): box(), coxa_bracket(), cradle(), cyl(), femur_plate(), flange_cut(), foot(), knee_sleeve() (+8 more)

### Community 13 - "Сценарии harvey_sim"
Cohesion: 0.14
Nodes (15): arm_xml(), build_xml(), eye_xml(), ik(), neutral(), pose_targets(), power(), reach_table() (+7 more)

### Community 14 - "Симуляция мини: README и снимки"
Cohesion: 0.12
Nodes (22): main(), world_model(), Скриншот: вид глазами Харви (мини), Камера Module 3 Wide — вид глазами Харви (клавиша V), Скриншот: мини на столе среди предметов, Реквизит рабочего стола (ручки, карандаш, блокнот, кейс наушников, книга, лампа, ноутбук), Скриншот: приветствие правой клешнёй (мини), Жест «привет» — клешня поднята вверх (+14 more)

### Community 15 - "CAD мини"
Cohesion: 0.13
Nodes (14): chassis(), coxa_servo_leg(), coxa_servos(), edge_sensors(), electronics(), eye_servos(), fixed_parts(), _leg_tf() (+6 more)

### Community 16 - "Тесты драйвера и калибровка"
Cohesion: 0.14
Nodes (16): LegCal, checksum(), make_packet(), parse_status(), _status(), test_echo_is_recognisable(), test_leg_calibration_mapping(), test_leg_ik_fk_roundtrip_and_stance() (+8 more)

### Community 17 - "Прошивка: шина Pico"
Cohesion: 0.15
Nodes (8): Bus, BusError, checksum(), find_status(), le16(), make_packet(), signed(), u16()

### Community 19 - "Экспорт для веба"
Cohesion: 0.15
Nodes (10): add(), body_map(), leg_map(), main(), pack(), pack(), height(), save_h() (+2 more)

### Community 20 - "Стенд: README и модули"
Cohesion: 0.12
Nodes (7): _header(), write(), Харви — стенд привода и ноги (README), Режим без железа (SIM): имитация привода, Адреса регистров — таблица Feetech SMS/STS (как в LeRobot), масштаб тока 6,5 мА/ед., Кабель адаптер→привод без красного провода, 12 В отдельно в привод, Калибровка ноги в позе «Г» (leg_calibration.json)

### Community 21 - "Сценарии и защита"
Cohesion: 0.19
Nodes (15): edge_sensor(), feet_x(), sc_battery(), sc_edge(), sc_failure(), sc_obstacles(), sc_push(), sc_random() (+7 more)

### Community 22 - "Меню стенда (Bench)"
Cohesion: 0.27
Nodes (3): Bench, main(), measure_servo()

### Community 23 - "CAD глаз"
Cohesion: 0.16
Nodes (12): back_cover(), bumper(), display(), eye_center(), horn_adapter(), housing(), housing_radius(), housing_x() (+4 more)

### Community 24 - "Экспорт для симуляции мини"
Cohesion: 0.14
Nodes (18): claw_assembly(), T_ay(), T_fore(), T_hand(), T_up(), elbow_servo_up(), export_sim(), put() (+10 more)

### Community 25 - "Захват (grasp)"
Cohesion: 0.21
Nodes (12): build(), build_cup(), finger_mid(), G, obj_forces(), path(), pen_test(), phone_test() (+4 more)

### Community 26 - "Servo: операции"
Cohesion: 0.16
Nodes (6): Servo, to_signed(), u16(), test_fake_bus_set_id_and_move(), test_set_middle_makes_position_2048(), test_state_block_read_matches_single_registers()

### Community 27 - "Мир симуляции"
Cohesion: 0.13
Nodes (11): apply(), asset_xml(), grab_equalities(), pbr_material(), props_xml(), _ramp(), robot_visual(), world_geoms() (+3 more)

### Community 29 - "Бюджет v0.2 и мозги"
Cohesion: 0.13
Nodes (19): CLAUDE.md — контекст проекта Харви, Pi 5 + AI HAT+ («голова») и Pico 2 («спинной мозг»), Структура папки проекта (заметки, визуализация, модели, документы, фото, код), Pi Zero 2 W + RP2350-Zero («спинной мозг»), Без ПК — «сонный питомец»: ходит, не падает, эмоции, сам заряжается, Харви — комплектация и бюджет v0.2, AI HAT+ 26 TOPS (Hailo-8), Raspberry Pi Camera Module 3 Wide (+11 more)

### Community 30 - "CAD хвоста"
Cohesion: 0.16
Nodes (11): arm_plate(), base(), cup(), cup_holder(), elbow_sleeve(), forearm(), j2_cols(), link_parts() (+3 more)

### Community 31 - "Управление и фото-режим"
Cohesion: 0.14
Nodes (15): Харви — управление в симуляции (README), Датчики края стола (защита края), MuJoCo-симуляция Харви (компоновка v2), Сценарии проверки (harvey_scenarios.py all), Режим «фото»: рендер Filament, физика в отдельном процессе, Рефлекс защиты глаз при опрокидывании (складывание до −105°), Физика веществ: деформируемый песок, гравий и галька, трава, мир_стол.png — Харви на столе (обычное окно MuJoCo) (+7 more)

### Community 32 - "Питание и проводка"
Cohesion: 0.12
Nodes (19): Питание мини: 2 × 18650 (2S, ~22 Вт·ч), DC-DC 6 В 6 А, Датчик тока INA226, Батарея 3S из банок 21700 (~50 Вт·ч), Питание мини: 2 × 18650 (2S, ~22 Вт·ч), BMS 2S, IP2326, DC-DC 6 В ≥ 6 А и 5 В 3 А, Харви 1.0 — питание и проводка, BMS 3S 40 А с балансировкой, DC-DC 6 В на 8 А (а не 5 А), Аварийная отсечка приводов (силовой ключ 40 А + кнопка-стоп) (+11 more)

### Community 33 - "Хвост: тесты"
Cohesion: 0.19
Nodes (11): build_tail(), legs_push(), rel(), T, tail_ik(), tail_move(), test_handover(), test_pick_place() (+3 more)

### Community 34 - "CAD детали ноги мини"
Cohesion: 0.14
Nodes (10): coxa_bracket(), disk_on_horn(), femur_link(), forearm(), hull(), plate_on_face(), rod(), tibia() (+2 more)

### Community 35 - "Имитация и проверка Pico"
Cohesion: 0.14
Nodes (5): now_s(), run(), FakeUart, main(), Замер 12: три привода на шине от Pico 2, 10 мин, обмен ≤ 1 мс

### Community 36 - "Адаптивная походка"
Cohesion: 0.14
Nodes (3): AdaptiveGait, Скриншот: склоны и ступени полосы препятствий, Склоны 10°/15°/20°/25°, косой склон 15° и ступени

### Community 37 - "Экспорт робота"
Cohesion: 0.20
Nodes (12): claws(), coxa_servo_split(), eyes(), frame(), leg_servo_split(), legs(), robot(), s15_split() (+4 more)

### Community 38 - "Документы и платы"
Cohesion: 0.15
Nodes (17): AI HAT+ — краткое описание, Raspberry Pi AI HAT+ (13/26 TOPS), Ускоритель Hailo-8 / Hailo-8L (NPU), Связь AI HAT+ по PCIe Gen 3, Pico 2 — даташит, Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3), MicroPython на Pico 2, Питание Pico 2: VSYS 1,8–5,5 В, SMPS RT6150, 3V3 ≤ 300 мА (+9 more)

### Community 39 - "Сценарии Sim2"
Cohesion: 0.25
Nodes (6): arm_ik(), run_carry(), run_extend_hold(), run_square(), Sim2, smooth()

### Community 40 - "Протокол Feetech"
Cohesion: 0.16
Nodes (15): Цель: позиция, время, скорость (адреса 42–46), Feetech — протокол связи (SCS/SMS), Широковещательный ID 254 (0xFE), Порядок байт SMS/STS: младший байт первым, Контрольная сумма ~(ID+Len+Instr+Params) & 0xFF, Регистр цели 0x2A: позиция, время, скорость (6 байт), Регистр ID (адрес 5) и блокировка EPROM, Пакет инструкции 0xFF 0xFF ID Len Instr Params Checksum (+7 more)

### Community 41 - "PyBullet-сверка"
Cohesion: 0.23
Nodes (7): inertial(), PB, stand(), urdf(), walk(), Сверка во втором движке PyBullet, requirements-extra.txt (pybullet ≥3.2.6)

### Community 42 - "Рельеф: камни и трава"
Cohesion: 0.17
Nodes (7): grass_assets(), grass_geoms(), settle(), stone_assets(), _stone_list(), stones_xml(), _tuft_mesh()

### Community 44 - "Проверки CAD мини"
Cohesion: 0.14
Nodes (8): check(), check_stand(), claw_ok(), claw_points(), _flat(), inter(), leg_stand(), U()

### Community 45 - "Версии Харви"
Cohesion: 0.18
Nodes (12): Ветки kompakt (v2-kompakt) и kompakt-mini, Версии: kompakt «Компакт» и kompakt-mini «Компакт мини», Версии Харви, «Компакт мини» (ветка kompakt-mini, в работе), Харви «Компакт мини», Бюджет мини ≈ 115–158 тыс. ₽ (почти как «Компакт»), Задачи мини: протереть стол, подать ручку, общаться, сам заряжаться, Масса мини 893 г (560 г — приводы); цель ≤ 0,8 кг не достигнута (+4 more)

### Community 47 - "Проверка ноги «Компакта»"
Cohesion: 0.19
Nodes (5): coxa_servo(), ik(), links(), plates(), servo()

### Community 49 - "Последовательная шина"
Cohesion: 0.23
Nodes (3): BusError, le16(), SerialBus

### Community 50 - "Рендеры мини"
Cohesion: 0.22
Nodes (11): main(), add(), material(), «Компакт мини» — компоновка, 4 вида (перспектива, сверху, спереди, сбоку), Компакт мини: шесть ног, две клешни, глаза-стебельки с круглыми дисплеями, без хвоста, «Компакт мини» на том же столе: export_render.py → parts_mini/, HARVEY_ROBOT=mini, Мини_1 — крупный план «Компакт мини» на столе, клешня поднята, Глаза-дисплеи с нарисованными зрачками (выражение «характера») (+3 more)

### Community 51 - "Сцена рендера на столе"
Cohesion: 0.18
Nodes (4): bbox(), light(), place(), _top_level()

### Community 52 - "Адаптер FE-URT-1 и приводы"
Cohesion: 0.21
Nodes (12): Приводы — шинные Feetech STS (STS3215 C018 на ногах, STS3032 на кистях), FE-URT-1 — адаптер шины (таблица, конвертирована), FE-URT-1 — USB → TTL/RS485 программатор шины Feetech, Аппаратное автоматическое переключение направления полудуплекса, Драйвер CH340C, Порты SMS (RS485, 5264-4AW) и SCS (TTL, 5264-3AW), 28 × STS3032 (ноги 6 × 3, клешни 2 × 4, глаза 2), Feetech STS3032 (6 В, 4,5 кг·см) (+4 more)

### Community 53 - "Детали стенда ноги (PDF)"
Cohesion: 0.20
Nodes (10): Харви — детали стенда одной ноги (PDF), Кронштейн основания (harvey_coxa_bracket.stl), Держатель привода валом вверх (harvey_cradle_servo.stl), Пластина бедра ×2 (harvey_femur_plate_x2.stl), Стопа TPU 95A (harvey_foot_TPU.stl), Обхват привода колена (harvey_knee_sleeve.stl), Рычаг 100 мм (harvey_lever_100mm.stl), Печать и крепёж: PETG 0,2 мм, 40% гироид, вставки M3, зазор 0,3 мм (+2 more)

### Community 54 - "Этап 1"
Cohesion: 0.24
Nodes (11): Первые тесты мини: 4 × STS3032, URT-1, стенд одной ноги (~25 г печати), Харви — этап 1: покупки и стенд одной ноги, Архив Harvey_leg_CAD.zip (детали стенда ноги), Библиотека Feetech на Python (стенд с ноутбука), Замер люфта лазерной указкой (1° ≈ 17 мм на 1 м), Замер момента: рычаг 100 мм на кухонные весы, Лабораторный блок питания с ограничением тока, Назначение ID приводов: 1–3 нога, 21–22 кисть (+3 more)

### Community 58 - "Таблица регистров"
Cohesion: 0.25
Nodes (11): Feetech — таблица регистров (конвертирована), Блокировка записи EPROM (адрес 48), Защита от перегрузки (регистры 37–39: момент, время, порог 80%), Максимальный момент (адрес 16), Включение момента (адрес 40), Регистр ID (адрес 5; 254 — широковещательный), Регистр скорости шины (адрес 6; 0 = 1 Мбит/с), Обратная связь: позиция, скорость, нагрузка, напряжение, температура (56–63) (+3 more)

### Community 59 - "Приводы Feetech"
Cohesion: 0.24
Nodes (11): Полудуплексная асинхронная шина 8N1, Порядок сборки ноги: ID 1/2/3, середина 2048, ось бедра 55 мм над столом, Размеры привода для сверки (servo_L 45,2, W 24,7, H 32, shaft_from_end 12,5, flange_D 20), Защиты STS3032: перегрузка, напряжение 4–7,4 В, 70 °C, Привод Feetech STS3032-C036 (6 В, 4,5 кг·см), 12-битный магнитный энкодер: 4096 отсчётов, 0,088°, середина 2048, Калибровка середины: 128 в адрес 40, Режимы 0–3: серво, скорость замкн./разомкн., шаговый; многооборотный ±7 (+3 more)

### Community 60 - "README мини и визуализация"
Cohesion: 0.22
Nodes (8): Безопасность стенда: пределы напряжения, температуры, время упора, Компакт мини — детали и компоновка (README), Компакт мини: 893 г, корпус 114×88×39, 28 × STS3032, Правила движения мини (клешни, глаза, ноги, передняя кромка x ≤ 67 мм, поза «поджато»), Станция зарядки мини: площадка с подпружиненными контактами, башенка с AprilTag и ИК-маяком, Электроника мини в три этажа: 2 × 18650, Pi Zero 2 W, RP2350-Zero, Сетки для браузерных визуализаций: export_web.py («Компакт») и export_web_mini.py (двойник мини), Визуализация в браузере: 3D-модель и двойник «Компакта», двойник мини (переключатель версий)

### Community 62 - "Рендеры «Компакт»"
Cohesion: 0.33
Nodes (9): v2 «Компакт» (метка v2-kompakt, ветка kompakt), сохранена 16.10.2026, Версия корпуса «Компакт», Панцирь 150 × 140 × 70 мм и поднос на спине 87 × 105 мм, Рендер Харви «Компакт», вариант «мягкий» (кожух) — спереди-сбоку на столе, Графитовый панцирь soft-touch закрывает электронику (вариант «мягкий»), Рендер Харви «Компакт», вариант «мягкий» — сверху сзади, весь стол, Красная круглая кнопка на задней стенке корпуса (выключатель или аварийный стоп — не подписано), Рендер Харви «Компакт», вариант «открытый» — сверху сзади, видна плата (+1 more)

### Community 63 - "Рендеры: README"
Cohesion: 0.25
Nodes (7): Управление мини с клавиатуры (harvey_mini_teleop.py, run_mini_windows.bat): Filament PBR, физика в отдельном процессе, Рендеры и сетки для визуализаций (README), Исправления 16.10: кружка, лампа, цветок, карандаши; робот по нижней точке, Масштаб 1 : 1 для обоих роботов и предметов, Фотореалистичная сцена рабочего стола в Blender 5.2 (Cycles, Poly Haven CC0), Харви_мягкий_1 — «Компакт», вариант «мягкий», вид спереди на столе, Вариант рендера «мягкий» (soft): закрытый панцирь, скрыта плата и батарея

### Community 64 - "Стенд ноги: README"
Cohesion: 0.25
Nodes (8): Разъёмы STS3215 могут упереться в пластины — измерить при получении приводов, Стенд одной ноги (README), Полная проверка ноги leg_check.py (ходы, стойка, цикл шага), Рендер стенда ноги: две стойки-держателя и нога из трёх приводов, Две серые вертикальные стойки на плите — держатели привода основания, Нога: основание → бедро (пластины) → колено, голень-вилка, Стопа — чёрный шар на конической ножке, Этап 1 — стенды: стенд ноги (перепечатать 4 детали), стенд кисти, чертежи ГОСТ

### Community 65 - "Станция зарядки мини"
Cohesion: 0.22
Nodes (5): check_dock(), dock_pad(), dock_pogo(), dock_tower(), leg_pose_for_drop()

### Community 66 - "Рендер стенда ноги"
Cohesion: 0.33
Nodes (6): coxa_case(), coxa_metal(), leg(), s15_case_y(), s15_metal_y(), tower()

### Community 67 - "Ручки и карандаш"
Cohesion: 0.32
Nodes (4): assets(), bodies(), _hex_mesh(), _hex_tip_mesh()

### Community 68 - "Станции зарядки"
Cohesion: 0.33
Nodes (6): Зарядка мини: латунные пластины на брюхе + станция с AprilTag и ИК-маяком, Станция-гнездо: зарядка 12,6 В 3 А, метка ArUco, Станция-«гнездо» мини: USB-C 5 В 3 А, ИК-маяк 940 нм / 38 кГц, метка AprilTag, Контактная станция-«гнездо», Мёртвые контакты на брюхе (идеальный диод), Подход к станции зарядки с коррекцией по AprilTag или ИК-маяку

### Community 69 - "Детали на рендерах"
Cohesion: 0.33
Nodes (7): Круглые дисплеи-глаза GC9A01 1,28″, Глаза на стебельках с магнитной муфтой, Рендер Харви «Компакт», вариант «открытый» (основной) — спереди, поза «привет», Глаза-дисплеи на стебельках (круглые экраны с голубой радужкой) на передних углах, Две многосуставные клешни с пальцами и присоской-захватом, Шесть трёхсуставных ног с шаровыми стопами, Рендер Харви «Компакт», вариант «открытый» — спереди-сбоку, оранжевый поднос сверху

### Community 70 - "Глаз-стебелёк"
Cohesion: 0.29
Nodes (4): display(), eye_assembly(), eye_servo_body(), eye_stalk()

### Community 71 - "Сборка ноги мини"
Cohesion: 0.38
Nodes (5): foot(), leg_assembly(), T_fem(), T_leg(), T_tib()

### Community 72 - "Даташит STS3215 и замеры"
Cohesion: 0.33
Nodes (5): STS3215-C018 — даташит Feetech (12 В), Проверка на стенде мини: размеры, нога на весах 3–4 Н, 10 мин шага, ток, Измерения: мультиметр с термопарой K, каптон, штангенциркуль, весы, лазерная указка, Замеры 1–7 стенда «Компакт» (связь, ток, момент, скорость, люфт, точность, нагрев), Замеры ноги Н1–Н5: позы, стойка на весах, момент бедра ≥ 0,36 Н·м, шаг 10 мин ≤ 60 °C, батарея

### Community 73 - "Компоновка v2: вид сверху"
Cohesion: 0.33
Nodes (6): Компоновка v2, вид сверху (поза «стоит, клешни поджаты»), Глаза-стебельки на передних углах рамы (~x 90, y ±80 мм), Зоны движения: ноги ±20° в основании, клешни поворот ±15°, хвост ±60°, Плечи клешней спереди (x≈105, y≈±30 мм), Хвост позади рамы (x≈−80 мм), Электроника в центре рамы (жёлтые блоки)

## Ambiguous Edges - Review These
- `Таблица регистров SCS15 (прошивка SCServo1.1)` → `Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to
- `Таблица регистров SCS15 (прошивка SCServo1.1)` → `Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to
- `Связь AI HAT+ по PCIe Gen 3` → `PCIe 2.0 x1 у Raspberry Pi 5`  [AMBIGUOUS]
  документы/AI HAT+ — краткое описание.pdf · relation: conceptually_related_to
- `Рычаг-качалка 25 мм (grip_lever)` → `Сервопривод Feetech STS3032-C036`  [AMBIGUOUS]
  модели/стенд кисти/детали кисти.png · relation: conceptually_related_to

## Knowledge Gaps
- **81 isolated node(s):** `Структура папки проекта (заметки, визуализация, модели, документы, фото, код)`, `Включение момента (адрес 40)`, `Рендеры на столе: открытая рама и мягкий кожух`, `Режим «фото» (Filament PBR): песок со следами, галька, трава`, `Рендеры «Компакт мини» на столе 1 : 1 (Blender, Cycles)` (+76 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 499 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Харви — главная заметка` connect `Главная и README моделей` to `Питание и проводка`, `Стенд ноги: README`, `Документы и платы`, `Журнал решений`, `Комплектация и стенд мини`, `Концепция и совместимость`, `Версии Харви`, `Симуляция мини: README и снимки`, `Стенд: README и модули`, `Детали стенда ноги (PDF)`, `Этап 1`, `README мини и визуализация`, `Бюджет v0.2 и мозги`, `Рендеры: README`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `boxr()` (e.g. with `stalk()` and `base()`) actually correct?**
  _`boxr()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Структура папки проекта (заметки, визуализация, модели, документы, фото, код)`, `Включение момента (адрес 40)`, `Рендеры на столе: открытая рама и мягкий кожух` to the rest of the system?**
  _81 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Teleop «Компакт»` be split into smaller, more focused modules?**
  _Cohesion score 0.05625 - nodes in this community are weakly interconnected._
- **Why does `Харви — стенд привода и ноги (README)` connect `Стенд: README и модули` to `Документы и платы`, `Комплектация и стенд мини`, `Главная и README моделей`, `Протокол Feetech`, `Даташит STS3215 и замеры`, `Этап 1`, `README мини и визуализация`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Таблица регистров SCS15 (прошивка SCServo1.1)` and `Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Таблица регистров SCS15 (прошивка SCServo1.1)` and `Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._