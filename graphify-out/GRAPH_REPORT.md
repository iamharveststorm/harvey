# Graph Report - Harvey  (2026-10-17)

## Corpus Check
- 111 files · ~2,347,437 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1541 nodes · 3304 edges · 83 communities (69 shown, 14 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 503 edges (avg confidence: 0.86)
- Token cost: 671,856 input · 0 output

## Community Hubs (Navigation)
- Меню стенда и нога
- CAD клешней
- CAD кисти (стенд)
- Teleop «Компакт»
- Teleop мини
- Чертежи ГОСТ
- Симуляция мини
- CAD стенда ноги
- Сценарии harvey_sim
- Журнал решений
- Утилиты и экспорт
- Компоновка v2
- Мир симуляции
- CAD мини
- Сценарии и защита
- CAD корпуса v2
- Прошивка: драйвер шины
- Бюджет v0.2 и железо
- CAD глаз
- Совместимость и Onshape
- README моделей
- CAD детали ноги мини
- Стенд мини: README и модули
- CAD хвоста
- Экспорт робота
- Захват (grasp)
- Драйвер STS и тесты
- Комплектация мини
- Питание и проводка
- Servo: операции
- Управление и фото-режим
- Хвост: тесты
- Документы и платы
- Экспорт для веба
- Pico: замер 12
- Детали стенда ноги (PDF)
- Проверки CAD мини
- Главная и версии
- PyBullet-сверка
- Этап 1 и кисть
- Приводы Feetech
- Окно PhotoView
- Teleop и походка
- Адаптивная походка
- Рельеф: песок и трава
- Имитация привода
- Последовательная шина
- Сцена рендера на столе
- Протокол Feetech
- Интерактивный двойник
- Рендеры «Компакт»
- Симуляция мини: README
- Удалённый teleop
- Геометрия ноги
- Сборка клешни
- Проверка ноги
- Утилиты мини и хвоста
- Корпус: README
- Таблица регистров
- 3D-модель
- Скриншоты мини
- Экспорт для симуляции
- Концепция и клешни
- Стенды и закупка
- Камера и электроника
- Станция зарядки мини
- Ручки и карандаш
- Галерея
- Имитация шины
- Калибровка ноги
- Глаз-стебелёк
- Сборка ноги мини
- Рендеры мини
- Адаптер FE-URT-1
- Детали на рендерах
- Знаковые регистры
- Палуба клешней
- Рендеры: README
- Станция «Компакта»
- Вид глазами Харви
- Фото-режим Filament
- Скрипт Linux стенда

## God Nodes (most connected - your core abstractions)
1. `boxr()` - 53 edges
2. `Журнал решений` - 46 edges
3. `Харви — этап 1: покупки и стенд одной ноги` - 28 edges
4. `Teleop` - 27 edges
5. `Харви — главная заметка` - 27 edges
6. `export_sim()` - 26 edges
7. `Харви «Компакт мини»` - 26 edges
8. `Харви 1.0 — питание и проводка` - 25 edges
9. `Компакт мини — симуляция (README)` - 25 edges
10. `Харви — комплектация и бюджет v0.2` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Регистр ID (адрес 5; 254 — широковещательный)` --semantically_similar_to--> `Регистр ID (адрес 5) и блокировка EPROM`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Цель: позиция, время, скорость (адреса 42–46)` --semantically_similar_to--> `Регистр цели 0x2A: позиция, время, скорость (6 байт)`  [INFERRED] [semantically similar]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md → документы/Feetech — протокол связи.pdf
- `Встроенная защита STS3215 (70 °C, 2 А / 2 с, 4–14 В)` --semantically_similar_to--> `Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C`  [INFERRED] [semantically similar]
  заметки/Питание и проводка.md → документы/STS3215-C018 — даташит Feetech (12 В).pdf
- `Протирка стола салфеткой (мини)` --semantically_similar_to--> `sc_wipe()`  [INFERRED] [semantically similar]
  код/симуляция/мини/mini_салфетка.png → код/симуляция/управление с клавиатуры/harvey_scenarios.py
- `Переходник разъёмов 5264 ↔ 1,25 мм` --references--> `STS3032-C036 — даташит Feetech (6 В)`  [INFERRED]
  заметки/Этап 1 — покупки и стенд одной ноги.md → документы/STS3032-C036 — даташит Feetech (6 В).pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Детали стенда одной ноги этапа 1** — документы_harvey_stage1_parts_cradle_servo, документы_harvey_stage1_parts_coxa_bracket, документы_harvey_stage1_parts_coxa_strap, документы_harvey_stage1_parts_femur_plate, документы_harvey_stage1_parts_knee_sleeve, документы_harvey_stage1_parts_tibia_fork, документы_harvey_stage1_parts_foot_tpu, документы_harvey_stage1_parts_lever_100mm [EXTRACTED 1.00]
- **Кинематическая цепь кисти: стойка → запястье #21 → ладонь → захват #22 → челюсть против пальца** — модели_стенд_кисти_сборка_кисти_стойка_запястья, модели_стенд_кисти_сборка_кисти_привод_запястья_21, модели_стенд_кисти_сборка_кисти_ладонь, модели_стенд_кисти_сборка_кисти_привод_захвата_22, модели_стенд_кисти_сборка_кисти_верхняя_челюсть, модели_стенд_кисти_сборка_кисти_нижний_палец [EXTRACTED 1.00]
- **Оснастка стенда: стойка запястья, люлька STS3032, рычаг 25 мм** — модели_стенд_кисти_детали_кисти_wrist_stand, модели_стенд_кисти_детали_кисти_cradle_sts3032, модели_стенд_кисти_детали_кисти_grip_lever [INFERRED 0.75]
- **Сборка клешни: ладонь + челюсть + накладки TPU** — модели_стенд_кисти_детали_кисти_palm, модели_стенд_кисти_детали_кисти_jaw, модели_стенд_кисти_детали_кисти_pad_tpu [INFERRED 0.85]
- **Функции harvey_hand_parts.py, порождающие сборку на рендере** — модели_стенд_кисти_harvey_hand_parts_wrist_stand, модели_стенд_кисти_harvey_hand_parts_palm, модели_стенд_кисти_harvey_hand_parts_jaw, модели_стенд_кисти_harvey_hand_parts_assembly, модели_стенд_кисти_сборка_кисти [INFERRED 0.95]
- **Подготовка стенда ноги «Компакт мини»** — заметки_чек_лист_стенда_мини, заметки_комплектация_мини_первые_тесты_этап_1, заметки_журнал_решений_стенд_мини_sts3032_нога_целиком, заметки_журнал_решений_печать_после_замера_horn_top, заметки_комплектация_мини_horn_top_shaft_from_end, код_стенд_привода_readme [INFERRED 0.85]
- **Компоновка v2 и её проверка на совместимость** — заметки_журнал_решений_компоновка_v2, заметки_журнал_решений_правила_движения_rules, заметки_журнал_решений_открытая_рама_14_деталей, заметки_журнал_решений_глаза_стебельки_на_углах, заметки_проверка_совместимости_и_сценарии_компоновка_v2_0_столкновений [INFERRED 0.85]
- **Защита питания Харви** — заметки_питание_и_проводка_аварийная_отсечка_приводов, заметки_питание_и_проводка_мёртвые_контакты_идеальный_диод, заметки_питание_и_проводка_порядок_включения, заметки_питание_и_проводка_пороги_напряжения_pico, заметки_питание_и_проводка_отдельные_dc_dc_и_звезда_земли [EXTRACTED 1.00]
- **Правила движения v2: CAD-проверка, симуляция и прошивка** — модели_корпус_readme_правила_движения, модели_корпус_harvey_layout, код_симуляция_управление_с_клавиатуры_readme_mujoco_simulation, код_прошивка_прошивка, модели_клешни_readme_клешня_5_суставов, модели_хвост_readme_хвост_с_присоской, модели_глаза_readme_глаз_стебелёк_gc9a01 [EXTRACTED 1.00]
- **Шина Feetech: драйвер стенда, драйвер Pico, имитации** — код_стенд_привода_harvey_bench_sts, код_прошивка_pico_sts_bus, код_прошивка_pico_readme_замер_12_шина_от_pico, код_стенд_привода_readme_sim_mode, код_прошивка_pico_readme_проверка_на_пк_без_железа [INFERRED 0.85]
- **Параметрический скрипт → STL → чертёж ГОСТ** — модели_стенд_ноги_harvey_leg_parts, модели_стенд_кисти_harvey_hand_parts, модели_чертежи_readme_чертежи_гост_freecad, модели_чертежи_харви_01_001_рычаг_100_мм, модели_чертежи_харви_02_002_ладонь_кисти [EXTRACTED 1.00]
- **Кадры mini_photo.py: стол, предметы, салфетка, привет** — код_симуляция_мини_mini_photo, код_симуляция_мини_mini_стол, код_симуляция_мини_mini_и_предметы, код_симуляция_мини_mini_салфетка, код_симуляция_мини_mini_привет [INFERRED 0.95]
- **Полоса препятствий на полу (harvey_world)** — код_симуляция_управление_с_клавиатуры_harvey_world, код_симуляция_управление_с_клавиатуры_мир_полоса_ramp_board, код_симуляция_управление_с_клавиатуры_мир_полоса_surface_zones, код_симуляция_управление_с_клавиатуры_мир_склоны_slopes_zone [INFERRED 0.85]
- **Обзор камеры мини: вид V, поза «поджато», телеуправление** — код_симуляция_мини_mini_глазами_харви_camera_view, код_симуляция_мини_mini_глазами_харви_tucked_pose, код_симуляция_мини_harvey_mini_teleop [INFERRED 0.85]
- **Режим «фото»: Харви на поверхностях физики веществ (песок, галька, трава, склон)** — код_симуляция_управление_с_клавиатуры_фото_песок_следы, код_симуляция_управление_с_клавиатуры_фото_галька, код_симуляция_управление_с_клавиатуры_фото_трава, код_симуляция_управление_с_клавиатуры_фото_склон, код_симуляция_управление_с_клавиатуры_harvey_terrain, код_симуляция_управление_с_клавиатуры_harvey_photo [INFERRED 0.85]
- **Blender-рендеры «Компакт мини» на столе (render_desk.py, HARVEY_ROBOT=mini)** — модели_рендер_мини_1, модели_рендер_мини_2, модели_рендер_мини_3, модели_рендер_render_desk, модели_мини_export_render [EXTRACTED 1.00]
- **Подвижные узлы компоновки v2 и их зоны движения** — модели_корпус_компоновка_вид_сверху_зоны_движения, модели_корпус_компоновка_вид_сверху_глаза_на_углах, модели_корпус_компоновка_вид_сверху_плечи_клешней, модели_корпус_компоновка_вид_сверху_хвост_за_подносом [INFERRED 0.85]
- **Рендеры «Компакта» на столе: 2 варианта корпуса (открытый/мягкий) × ракурсы из render_desk.py** — модели_рендер_харви_мягкий_2, модели_рендер_харви_мягкий_3, модели_рендер_харви_открытый_1, модели_рендер_харви_открытый_2, модели_рендер_харви_открытый_3, модели_рендер_render_desk [INFERRED 0.95]
- **Рендеры стендов этапа 1: кисть клешни и одна нога** — модели_стенд_кисти_рендер_кисти, модели_стенд_ноги_рендер_ног, модели_стенд_кисти_harvey_hand_parts, модели_стенд_ноги_harvey_leg_parts [INFERRED 0.85]
- **Узнаваемые части «Компакт» v2 на рендере: глаза-стебельки, клешни, шесть ног, хвост** — модели_рендер_харви_открытый_1_глаза_стебельки, модели_рендер_харви_открытый_1_клешни, модели_рендер_харви_открытый_1_шесть_ног, модели_рендер_харви_открытый_3_хвост [INFERRED 0.85]

## Communities (83 total, 14 thin omitted)

### Community 0 - "Меню стенда и нога"
Cohesion: 0.08
Nodes (10): Bench, main(), measure_servo(), FakeLegBus, clamp(), Leg, _header(), write() (+2 more)

### Community 1 - "CAD клешней"
Cohesion: 0.06
Nodes (37): pad_pair(), s15_case(), s15_metal(), s32_case(), s32_metal(), scene(), arm_plate(), base() (+29 more)

### Community 2 - "CAD кисти (стенд)"
Cohesion: 0.07
Nodes (36): assembly(), box(), check(), cyl(), finger_bar(), grip_lever(), horn_disk(), jaw() (+28 more)

### Community 3 - "Teleop «Компакт»"
Cohesion: 0.06
Nodes (18): currents(), run(), KeyReader, run_gui(), act(), close(), keyname(), norm() (+10 more)

### Community 4 - "Teleop мини"
Cohesion: 0.06
Nodes (15): _child(), keyname(), MiniTeleop, near_plane(), RemoteMini, run_grip_test(), run_gui(), close() (+7 more)

### Community 5 - "Чертежи ГОСТ"
Cohesion: 0.08
Nodes (29): box(), build(), cut(), cylx(), cyly(), cylz(), dim_circle(), dim_pts() (+21 more)

### Community 6 - "Симуляция мини"
Cohesion: 0.11
Nodes (23): arm_fk(), arm_ik(), build_xml(), claw_ok(), dock_xml(), joint_names(), leg_ik(), load_assets() (+15 more)

### Community 7 - "CAD стенда ноги"
Cohesion: 0.08
Nodes (25): Замеры 1–7 стенда «Компакт» (связь, ток, момент, скорость, люфт, точность, нагрев), to_trimesh(), coxa_case(), coxa_metal(), leg(), s15_case_y(), s15_metal_y(), tower() (+17 more)

### Community 8 - "Сценарии harvey_sim"
Cohesion: 0.11
Nodes (19): arm_ik(), arm_xml(), build_xml(), eye_xml(), ik(), neutral(), pose_targets(), power() (+11 more)

### Community 9 - "Журнал решений"
Cohesion: 0.08
Nodes (13): Журнал решений, Харви «Компакт мини», Задачи мини: протереть стол, подать ручку, общаться, сам заряжаться, Зарядка мини: латунные пластины на брюхе + станция с AprilTag и ИК-маяком, Масса мини 893 г (560 г — приводы); цель ≤ 0,8 кг не достигнута, CAD-проверка мини (harvey_mini_parts.py): 0 столкновений, 332 позы клешни, Симуляция мини (harvey_mini.py): ходьба 6,2 см/с, ручка, салфетка, станция, 3D-печать мини: 41 деталь, ≈ 157 г (PLA / PETG / TPU) (+5 more)

### Community 10 - "Утилиты и экспорт"
Cohesion: 0.11
Nodes (12): main(), world_model(), grass_assets(), grass_geoms(), settle(), stone_assets(), _stone_list(), stones_xml() (+4 more)

### Community 11 - "Компоновка v2"
Cohesion: 0.11
Nodes (14): check(), claw(), claw_ok(), claw_parts_chassis(), eye(), eye_ok(), flat(), inter() (+6 more)

### Community 12 - "Мир симуляции"
Cohesion: 0.10
Nodes (13): world_model(), apply(), asset_xml(), grab_equalities(), load_assets(), pbr_material(), props_xml(), _ramp() (+5 more)

### Community 13 - "CAD мини"
Cohesion: 0.13
Nodes (14): chassis(), coxa_servo_leg(), coxa_servos(), edge_sensors(), electronics(), eye_servos(), fixed_parts(), _leg_tf() (+6 more)

### Community 14 - "Сценарии и защита"
Cohesion: 0.18
Nodes (16): eye_force(), trial(), edge_sensor(), feet_x(), sc_battery(), sc_edge(), sc_failure(), sc_obstacles() (+8 more)

### Community 15 - "CAD корпуса v2"
Cohesion: 0.11
Nodes (13): belly(), camera_mount(), edge_sensors(), eye_mount(), frame_parts(), leg_post(), ring(), ring_outline() (+5 more)

### Community 16 - "Прошивка: драйвер шины"
Cohesion: 0.15
Nodes (8): Bus, BusError, checksum(), find_status(), le16(), make_packet(), signed(), u16()

### Community 17 - "Бюджет v0.2 и железо"
Cohesion: 0.12
Nodes (24): Pi 5 + AI HAT+ («голова») и Pico 2 («спинной мозг»), Приводы — шинные Feetech STS (STS3215 C018 на ногах, STS3032 на кистях), Режим «Показать начинку» (x-ray), STS3215-C018 — даташит Feetech (12 В), 28 × STS3032 (ноги 6 × 3, клешни 2 × 4, глаза 2), Pi Zero 2 W + RP2350-Zero («спинной мозг»), Без ПК — «сонный питомец»: ходит, не падает, эмоции, сам заряжается, Харви — комплектация и бюджет v0.2 (+16 more)

### Community 18 - "CAD глаз"
Cohesion: 0.15
Nodes (13): back_cover(), bumper(), display(), eye_center(), horn_adapter(), housing(), housing_radius(), housing_x() (+5 more)

### Community 19 - "Совместимость и Onshape"
Cohesion: 0.11
Nodes (21): Параметры спецификации v0.6 (LEG, ARM, CAM, TL, LIM), Харви — проверка совместимости и сценарии, MuJoCo (физический движок), PyBullet (физический движок), Обучение в симуляции (RL), Походка на пяти ногах (при отказе ноги), Протирка стола с ограничением усилия по току привода, Сверка в двух физических движках (расхождение 10–15%) (+13 more)

### Community 20 - "README моделей"
Cohesion: 0.13
Nodes (16): Хвост берёт телефон и кладёт на спину, Глаза-стебельки (README), Глаз-стебелёк: привод наклона STS3032, дисплей GC9A01 1,28″, бампер TPU, Клешни (README), Клешня 5 суставов: J1 STS3032 → J2, J3 STS3215 → J4, J5 STS3032, Разъёмы STS3215 могут упереться в пластины — измерить при получении приводов, Правила движения v2 (RULES): клешни, хвост, ноги, глаза, Компакт мини — детали и компоновка (README) (+8 more)

### Community 21 - "CAD детали ноги мини"
Cohesion: 0.14
Nodes (12): coxa_bracket(), disk_on_horn(), femur_link(), forearm(), hull(), pads(), plate_on_face(), rod() (+4 more)

### Community 22 - "Стенд мини: README и модули"
Cohesion: 0.11
Nodes (9): Библиотека Feetech на Python (стенд с ноутбука), pc_check.py — имитация трёх STS3032 с эхом и без, Харви — стенд привода и ноги (README), Режим без железа (SIM): имитация привода, Адреса регистров — таблица Feetech SMS/STS (как в LeRobot), масштаб тока 6,5 мА/ед., Безопасность стенда: пределы напряжения, температуры, время упора, Калибровка ноги в позе «Г» (leg_calibration.json), Режим «Компакт мини»: STS3032-C036 6 В и нога целиком (Н1–Н5) (+1 more)

### Community 23 - "CAD хвоста"
Cohesion: 0.15
Nodes (11): arm_plate(), base(), cup(), cup_holder(), elbow_sleeve(), forearm(), j2_cols(), link_parts() (+3 more)

### Community 24 - "Экспорт робота"
Cohesion: 0.16
Nodes (11): claws(), coxa_servo_split(), frame(), leg_servo_split(), legs(), robot(), s15_split(), s32_split() (+3 more)

### Community 25 - "Захват (grasp)"
Cohesion: 0.22
Nodes (12): build(), build_cup(), finger_mid(), G, obj_forces(), path(), pen_test(), phone_test() (+4 more)

### Community 26 - "Драйвер STS и тесты"
Cohesion: 0.20
Nodes (14): checksum(), make_packet(), parse_status(), _status(), test_echo_is_recognisable(), test_leg_ik_fk_roundtrip_and_stance(), test_packet_ping_matches_reference(), test_packet_read_position() (+6 more)

### Community 27 - "Комплектация мини"
Cohesion: 0.13
Nodes (18): Бюджет мини ≈ 115–158 тыс. ₽ (почти как «Компакт»), Бюджет «Компакт» 107–179 тыс. ₽, Комплектация «Компакт мини» — что купить и что напечатать, Размеры horn_top (4,8 мм) и shaft_from_end (5,7 мм) — измерить до печати, STS3032-C036 — 3 280 ₽ (Feetech Official Store), 4 170 ₽ (Ozon), Waveshare Bus Servo Adapter (A) — шина от Pico по UART, Буферы именно LVC (SN74LVC1G125/126) — входы выдерживают 5 В, Бюджет мини ≈ 116–161 тыс. ₽ (больше 4/5 — приводы) (+10 more)

### Community 28 - "Питание и проводка"
Cohesion: 0.12
Nodes (20): Питание мини: 2 × 18650 (2S, ~22 Вт·ч), DC-DC 6 В 6 А, Датчик тока INA226, Батарея 3S из банок 21700 (~50 Вт·ч), Харви 1.0 — питание и проводка, BMS 3S 40 А с балансировкой, DC-DC 6 В на 8 А (а не 5 А), Аварийная отсечка приводов (силовой ключ 40 А + кнопка-стоп), Время работы: ходьба ~30 мин, стоя ~1 ч, лёжа ~3 ч (+12 more)

### Community 29 - "Servo: операции"
Cohesion: 0.16
Nodes (4): Servo, u16(), test_fake_bus_set_id_and_move(), test_set_middle_makes_position_2048()

### Community 30 - "Управление и фото-режим"
Cohesion: 0.13
Nodes (15): Харви — управление в симуляции (README), Управление с клавиатуры и панель управления, MuJoCo-симуляция Харви (компоновка v2), Сценарии проверки (harvey_scenarios.py all), Рефлекс защиты глаз при опрокидывании (складывание до −105°), Физика веществ: деформируемый песок, гравий и галька, трава, requirements.txt симуляции (mujoco ≥3.1.6, numpy ≥1.24), мир_стол.png — Харви на столе (обычное окно MuJoCo) (+7 more)

### Community 31 - "Хвост: тесты"
Cohesion: 0.19
Nodes (11): build_tail(), legs_push(), rel(), T, tail_ik(), tail_move(), test_handover(), test_pick_place() (+3 more)

### Community 32 - "Документы и платы"
Cohesion: 0.14
Nodes (18): AI HAT+ — краткое описание, Raspberry Pi AI HAT+ (13/26 TOPS), Ускоритель Hailo-8 / Hailo-8L (NPU), Связь AI HAT+ по PCIe Gen 3, Pico 2 — даташит, Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3), MicroPython на Pico 2, Питание Pico 2: VSYS 1,8–5,5 В, SMPS RT6150, 3V3 ≤ 300 мА (+10 more)

### Community 33 - "Экспорт для веба"
Cohesion: 0.17
Nodes (7): sand_heights(), add(), body_map(), leg_map(), pack(), height(), save_h()

### Community 35 - "Pico: замер 12"
Cohesion: 0.15
Nodes (7): now_s(), run(), FakeUart, main(), Pico 2 — шина приводов (README), Замер 12: три привода на шине от Pico 2, 10 мин, обмен ≤ 1 мс, Подключение Pico 2 к Waveshare Bus Servo Adapter (GP0 TX, GP1 RX, перемычки на UART, 6 В 3 А)

### Community 36 - "Детали стенда ноги (PDF)"
Cohesion: 0.15
Nodes (13): Харви — детали стенда одной ноги (PDF), Кронштейн основания (harvey_coxa_bracket.stl), Планка-фиксатор привода бедра (harvey_coxa_strap.stl), Держатель привода валом вверх (harvey_cradle_servo.stl), Пластина бедра ×2 (harvey_femur_plate_x2.stl), Стопа TPU 95A (harvey_foot_TPU.stl), Обхват привода колена (harvey_knee_sleeve.stl), Рычаг 100 мм (harvey_lever_100mm.stl) (+5 more)

### Community 37 - "Проверки CAD мини"
Cohesion: 0.13
Nodes (9): check(), check_stand(), claw_ok(), claw_points(), put(), _flat(), inter(), leg_stand() (+1 more)

### Community 38 - "Главная и версии"
Cohesion: 0.18
Nodes (13): CLAUDE.md — контекст проекта Харви, Ветки kompakt (v2-kompakt) и kompakt-mini, Структура папки проекта (заметки, визуализация, модели, документы, фото, код), README папки проекта Харви, Obsidian-хранилище на всю папку harvey, Окружения Python в C:\venvs (harvey, harvey-bench, harvey-cad), Онлайн-версии документов (артефакты claude.ai), Версии: kompakt «Компакт» и kompakt-mini «Компакт мини» (+5 more)

### Community 39 - "PyBullet-сверка"
Cohesion: 0.23
Nodes (7): inertial(), PB, stand(), urdf(), walk(), Сверка во втором движке PyBullet, requirements-extra.txt (pybullet ≥3.2.6)

### Community 40 - "Этап 1 и кисть"
Cohesion: 0.22
Nodes (14): STS3032-C036 — даташит Feetech (6 В), Проверить на стенде до заказа 30 приводов: нагрев бедра, размеры, ток, дисплей, видео, Проверка на стенде мини: размеры, нога на весах 3–4 Н, 10 мин шага, ток, Харви — этап 1: покупки и стенд одной ноги, Архив Harvey_leg_CAD.zip (детали стенда ноги), Замер люфта лазерной указкой (1° ≈ 17 мм на 1 м), Замер момента: рычаг 100 мм на кухонные весы, Назначение ID приводов: 1–3 нога, 21–22 кисть (+6 more)

### Community 41 - "Приводы Feetech"
Cohesion: 0.19
Nodes (14): Порядок байт SMS/STS: младший байт первым, Контрольная сумма ~(ID+Len+Instr+Params) & 0xFF, Пакет инструкции 0xFF 0xFF ID Len Instr Params Checksum, Полудуплексная асинхронная шина 8N1, Порядок сборки ноги: ID 1/2/3, середина 2048, ось бедра 55 мм над столом, Защиты STS3032: перегрузка, напряжение 4–7,4 В, 70 °C, Привод Feetech STS3032-C036 (6 В, 4,5 кг·см), 12-битный магнитный энкодер: 4096 отсчётов, 0,088°, середина 2048 (+6 more)

### Community 43 - "Teleop и походка"
Cohesion: 0.15
Nodes (4): edge_seen(), run_linux.sh script, Скриншот: склоны и ступени полосы препятствий, Склоны 10°/15°/20°/25°, косой склон 15° и ступени

### Community 47 - "Последовательная шина"
Cohesion: 0.23
Nodes (3): BusError, le16(), SerialBus

### Community 48 - "Сцена рендера на столе"
Cohesion: 0.18
Nodes (4): bbox(), light(), place(), _top_level()

### Community 49 - "Протокол Feetech"
Cohesion: 0.20
Nodes (12): Цель: позиция, время, скорость (адреса 42–46), Feetech — протокол связи (SCS/SMS), Широковещательный ID 254 (0xFE), Регистр цели 0x2A: позиция, время, скорость (6 байт), Регистр ID (адрес 5) и блокировка EPROM, PING (0x01) — запрос состояния, Регистр текущей позиции 0x38 (2 байта), READ DATA (0x02) — чтение таблицы памяти (+4 more)

### Community 50 - "Интерактивный двойник"
Cohesion: 0.32
Nodes (12): Харви — интерактивный двойник (three.js), armIK() — ИК клешни с проверкой пределов, boxDist() — расстояние до корпуса, footsWorld() — положение стоп в мире, legIK() — ИК ноги с проверкой пределов, segDist() — расстояние между отрезками, tailIK() — ИК хвоста с проверкой пределов, update() — пересчёт позы и всех проверок (+4 more)

### Community 51 - "Рендеры «Компакт»"
Cohesion: 0.23
Nodes (10): v2 «Компакт» (метка v2-kompakt, ветка kompakt), сохранена 16.10.2026, Хвост — третья рука с присоской, Версия корпуса «Компакт», Рендер Харви «Компакт», вариант «мягкий» (кожух) — спереди-сбоку на столе, Графитовый панцирь soft-touch закрывает электронику (вариант «мягкий»), Рендер Харви «Компакт», вариант «мягкий» — сверху сзади, весь стол, Красная круглая кнопка на задней стенке корпуса (выключатель или аварийный стоп — не подписано), Рендер Харви «Компакт», вариант «открытый» — сверху сзади, видна плата (+2 more)

### Community 52 - "Симуляция мини: README"
Cohesion: 0.20
Nodes (9): Компакт мини — симуляция (README), Вид глазами Харви: неподвижная Camera Module 3 Wide, наклон корпусом ±12°, Захват губками с пределом момента (как Torque Limit STS3032), --grip-test, Модель батареи 22 Вт·ч и заряд 12 Вт на станции, Приводы STS3032 в симуляции мини: ограничение момента и падение момента со скоростью, Подход к станции зарядки с коррекцией по AprilTag или ИК-маяку, Результаты симуляции мини (масса 893 г из CAD): трипод 6,2 см/с, ручка, салфетка, край стола, станция, Датчики края стола (защита края) (+1 more)

### Community 55 - "Сборка клешни"
Cohesion: 0.23
Nodes (9): claw_assembly(), T_ay(), T_fore(), T_hand(), T_up(), export_stl(), fixed_jaw(), moving_jaw() (+1 more)

### Community 56 - "Проверка ноги"
Cohesion: 0.21
Nodes (5): coxa_servo(), ik(), links(), plates(), servo()

### Community 57 - "Утилиты мини и хвоста"
Cohesion: 0.22
Nodes (4): yaw_of(), reach_table(), eyes(), tail_ik()

### Community 58 - "Корпус: README"
Cohesion: 0.18
Nodes (11): Корпус: компоновка v2 и открытая рама (README), Компоновка v2: точки крепления ног, плеч клешней (105; ±30; 65), хвоста, глаз, камеры, датчиков края, Мягкий вариант: графитовый скруглённый панцирь (soft_cover), Открытая рама из 14 деталей (~180 г PETG), Размещение электроники: Pi 5 + AI HAT+ в центральном канале, 3 банки 21700 раздельно, Pico 2 сзади, Компоновка v2, вид сверху (поза «стоит, клешни поджаты»), Глаза-стебельки на передних углах рамы (~x 90, y ±80 мм), Зоны движения: ноги ±20° в основании, клешни поворот ±15°, хвост ±60° (+3 more)

### Community 59 - "Таблица регистров"
Cohesion: 0.29
Nodes (10): Feetech — таблица регистров (конвертирована), Блокировка записи EPROM (адрес 48), Защита от перегрузки (регистры 37–39: момент, время, порог 80%), Максимальный момент (адрес 16), Включение момента (адрес 40), Регистр ID (адрес 5; 254 — широковещательный), Регистр скорости шины (адрес 6; 0 = 1 Мбит/с), Обратная связь: позиция, скорость, нагрузка, напряжение, температура (56–63) (+2 more)

### Community 60 - "3D-модель"
Cohesion: 0.31
Nodes (10): Харви «Компакт» — 3D-модель (three.js), apply() — применение позы ног, armIK() — обратная кинематика клешни, goArm() — смена позы клешней, goTail() — смена позы хвоста, readout() — габарит, высота, просвет, solve() — кинематика ноги для позы, tailIK() — обратная кинематика хвоста (+2 more)

### Community 61 - "Скриншоты мини"
Cohesion: 0.22
Nodes (10): Скриншот: мини на столе среди предметов, Реквизит рабочего стола (ручки, карандаш, блокнот, кейс наушников, книга, лампа, ноутбук), Скриншот: приветствие правой клешнёй (мини), Жест «привет» — клешня поднята вверх, Скриншот: протирка салфеткой (мини), Протирка стола салфеткой (мини), Скриншот: Компакт мини на рабочем столе, Модель Харви «Компакт мини» в MuJoCo (шесть ног, две клешни, глаза-стебельки, без хвоста) (+2 more)

### Community 62 - "Экспорт для симуляции"
Cohesion: 0.29
Nodes (8): elbow_servo_up(), export_sim(), femur_servo_coxa(), grip_servo_hand(), knee_servo_femur(), lift_servo_arm(), servo_at(), servo_sym()

### Community 63 - "Концепция и клешни"
Cohesion: 0.22
Nodes (7): claw() — построение клешни, Харви — концепция, Две мощные многосуставные клешни, Добрый характер (ориентир — ВАЛЛ-И), Шесть ног, Трипод-походка, Клешня с пятью суставами (звенья 54 / 60 / ≈43 мм)

### Community 64 - "Стенды и закупка"
Cohesion: 0.22
Nodes (8): Порядок закупки в 4 этапа, 5 этапов закупки с контрольными точками (Onshape → нога → голова → всё → станция), Стенд одной ноги и одной кисти, Шесть трёхсуставных ног с шаровыми стопами, Рендер стенда ноги: две стойки-держателя и нога из трёх приводов, Две серые вертикальные стойки на плите — держатели привода основания, Нога: основание → бедро (пластины) → колено, голень-вилка, Стопа — чёрный шар на конической ножке

### Community 65 - "Камера и электроника"
Cohesion: 0.22
Nodes (4): camera_assembly(), check(), electronics(), fixed_hardware()

### Community 66 - "Станция зарядки мини"
Cohesion: 0.22
Nodes (5): check_dock(), dock_pad(), dock_pogo(), dock_tower(), leg_pose_for_drop()

### Community 67 - "Ручки и карандаш"
Cohesion: 0.32
Nodes (4): assets(), bodies(), _hex_mesh(), _hex_tip_mesh()

### Community 68 - "Галерея"
Cohesion: 0.29
Nodes (7): Харви — галерея, Компоновка v2 — вид сверху (цвета по узлам), Режим «фото» (Filament PBR): песок со следами, галька, трава, Рендеры «Компакт мини» на столе 1 : 1 (Blender, Cycles), Рендеры на столе: открытая рама и мягкий кожух, Чертежи ГОСТ: ХАРВИ.01.001 Рычаг 100 мм, ХАРВИ.02.002 Ладонь кисти, Фото и эскизы

### Community 71 - "Глаз-стебелёк"
Cohesion: 0.29
Nodes (4): display(), eye_assembly(), eye_servo_body(), eye_stalk()

### Community 72 - "Сборка ноги мини"
Cohesion: 0.38
Nodes (5): foot(), leg_assembly(), T_fem(), T_leg(), T_tib()

### Community 73 - "Рендеры мини"
Cohesion: 0.33
Nodes (7): «Компакт мини» — компоновка, 4 вида (перспектива, сверху, спереди, сбоку), Компакт мини: шесть ног, две клешни, глаза-стебельки с круглыми дисплеями, без хвоста, Мини_1 — крупный план «Компакт мини» на столе, клешня поднята, Глаза-дисплеи с нарисованными зрачками (выражение «характера»), Мини_2 — «Компакт мини» спереди в тёплом интерьере, клешня над головой, Мини_3 — «Компакт мини» на рабочем столе среди кружки, блокнотов, ручек (масштаб), Масштаб: робот размером с кружку на столе

### Community 74 - "Адаптер FE-URT-1"
Cohesion: 0.70
Nodes (5): FE-URT-1 — адаптер шины (таблица, конвертирована), FE-URT-1 — USB → TTL/RS485 программатор шины Feetech, Аппаратное автоматическое переключение направления полудуплекса, Драйвер CH340C, Порты SMS (RS485, 5264-4AW) и SCS (TTL, 5264-3AW)

### Community 75 - "Детали на рендерах"
Cohesion: 0.50
Nodes (5): Круглые дисплеи-глаза GC9A01 1,28″, Рендер Харви «Компакт», вариант «открытый» (основной) — спереди, поза «привет», Глаза-дисплеи на стебельках (круглые экраны с голубой радужкой) на передних углах, Две многосуставные клешни с пальцами и присоской-захватом, Рендер Харви «Компакт», вариант «открытый» — спереди-сбоку, оранжевый поднос сверху

### Community 78 - "Рендеры: README"
Cohesion: 0.50
Nodes (4): Рендеры и сетки для визуализаций (README), Масштаб 1 : 1 для обоих роботов и предметов, Харви_мягкий_1 — «Компакт», вариант «мягкий», вид спереди на столе, Вариант рендера «мягкий» (soft): закрытый панцирь, скрыта плата и батарея

### Community 79 - "Станция «Компакта»"
Cohesion: 1.00
Nodes (3): Станция-гнездо: зарядка 12,6 В 3 А, метка ArUco, Контактная станция-«гнездо», Мёртвые контакты на брюхе (идеальный диод)

## Ambiguous Edges - Review These
- `Рычаг-качалка 25 мм (grip_lever)` → `Сервопривод Feetech STS3032-C036`  [AMBIGUOUS]
  модели/стенд кисти/детали кисти.png · relation: conceptually_related_to
- `Связь AI HAT+ по PCIe Gen 3` → `PCIe 2.0 x1 у Raspberry Pi 5`  [AMBIGUOUS]
  документы/AI HAT+ — краткое описание.pdf · relation: conceptually_related_to
- `Таблица регистров SCS15 (прошивка SCServo1.1)` → `Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to
- `Таблица регистров SCS15 (прошивка SCServo1.1)` → `Нужна именно версия C018 (не C001 / C044 / C046), STS, а не SCS`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to

## Knowledge Gaps
- **72 isolated node(s):** `requirements-extra.txt (pybullet ≥3.2.6)`, `Добрый характер (ориентир — ВАЛЛ-И)`, `Ускоритель Hailo-8 / Hailo-8L (NPU)`, `Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3)`, `MicroPython на Pico 2` (+67 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 481 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Харви — главная заметка` connect `Главная и версии` to `Документы и платы`, `Галерея`, `Детали стенда ноги (PDF)`, `Этап 1 и кисть`, `Журнал решений`, `3D-модель`, `Бюджет v0.2 и железо`, `Интерактивный двойник`, `Совместимость и Onshape`, `README моделей`, `Стенд мини: README и модули`, `Комплектация мини`, `Питание и проводка`, `Концепция и клешни`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `boxr()` (e.g. with `stalk()` and `base()`) actually correct?**
  _`boxr()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **What connects `requirements-extra.txt (pybullet ≥3.2.6)`, `Добрый характер (ориентир — ВАЛЛ-И)`, `Ускоритель Hailo-8 / Hailo-8L (NPU)` to the rest of the system?**
  _72 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Меню стенда и нога` be split into smaller, more focused modules?**
  _Cohesion score 0.08028846153846154 - nodes in this community are weakly interconnected._
- **Why does `Харви — стенд привода и ноги (README)` connect `Стенд мини: README и модули` to `Меню стенда и нога`, `Pico: замер 12`, `Главная и версии`, `CAD стенда ноги`, `Этап 1 и кисть`, `Драйвер STS и тесты`, `Комплектация мини`, `Питание и проводка`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Рычаг-качалка 25 мм (grip_lever)` and `Сервопривод Feetech STS3032-C036`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Связь AI HAT+ по PCIe Gen 3` and `PCIe 2.0 x1 у Raspberry Pi 5`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._