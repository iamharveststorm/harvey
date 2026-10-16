# Graph Report - Harvey  (2026-10-14)

## Corpus Check
- 56 files · ~57,657 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: .bat 3, (none) 2, .command 1)

## Summary
- 597 nodes · 1398 edges · 27 communities (24 shown, 3 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 191 edges (avg confidence: 0.86)
- Token cost: 435,045 input · 0 output

## Community Hubs (Navigation)
- Симуляция: токи, защита, PyBullet
- CAD кисти (код)
- Управление с клавиатуры
- Модель MuJoCo и сценарии
- Стенд привода: замеры
- CAD ноги (код)
- Визуализация three.js
- Печатные детали ноги и кисти
- Захват пальцами и безопасность
- Проверка в симуляции и Onshape
- Электроника и комплектация
- Тесты драйвера шины
- Концепция и главные документы
- Платы Raspberry Pi и Pico
- Питание и проводка
- Стенд: модули и имитация
- Драйвер шины SerialBus
- Стенд привода: подключение
- Протокол Feetech: команды
- Приводы STS: паспорт и защиты
- Этап 1: закупка и протокол
- Приводы и манипуляторы
- Имитация привода FakeBus
- Отчёт стенда в Excel
- Таблица регистров SCS15
- Адаптер шины FE-URT-1
- Скрипт запуска стенда

## God Nodes (most connected - your core abstractions)
1. `Харви — проверка совместимости и сценарии` - 27 edges
2. `Харви — комплектация и бюджет v0.2` - 25 edges
3. `Харви — главная заметка` - 24 edges
4. `Харви 1.0 — питание и проводка` - 24 edges
5. `Харви — этап 1: покупки и стенд одной ноги` - 24 edges
6. `Харви «Компакт» — сборка в Onshape и физическая проверка` - 23 edges
7. `Харви — стенд привода STS3215-C018 (README)` - 21 edges
8. `Teleop` - 20 edges
9. `Bench` - 20 edges
10. `Харви — управление в симуляции (README)` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Замеры 1–7 стенда: связь, ток, момент, скорость, люфт, точность возврата, нагрев` --semantically_similar_to--> `Порядок сборки ноги: ID 1/2/3, середина 2048, ось бедра 55 мм над столом`  [INFERRED] [semantically similar]
  код/стенд привода/README.md → документы/harvey-stage1-parts.pdf
- `Безопасность стенда: 10–13 В, <60 °C, упор ≤2 с, стоп при 70 °C или >2,2 А 5 с` --semantically_similar_to--> `Защиты STS3215: перегрузка, ток >2 А, напряжение 4–14 В, 70 °C`  [INFERRED] [semantically similar]
  код/стенд привода/README.md → документы/STS3215-C018 — даташит Feetech (12 В).pdf
- `Рычаг 25 мм для замера силы захвата (замер 10)` --semantically_similar_to--> `Рычаг 100 мм (harvey_lever_100mm.stl)`  [INFERRED] [semantically similar]
  модели/стенд кисти/README.md → документы/harvey-stage1-parts.pdf
- `Держатель STS3032 валом вверх (harvey_hand_cradle_sts3032.stl)` --semantically_similar_to--> `Держатель привода валом вверх (harvey_cradle_servo.stl)`  [INFERRED] [semantically similar]
  модели/стенд кисти/README.md → документы/harvey-stage1-parts.pdf
- `Измерить перед печатью: shaft_from_end ~5,7 мм, horn_top ~4,8 мм` --semantically_similar_to--> `Размеры привода для сверки (servo_L 45,2, W 24,7, H 32, shaft_from_end 12,5, flange_D 20)`  [INFERRED] [semantically similar]
  модели/стенд кисти/README.md → документы/harvey-stage1-parts.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Пять решений по питанию Харви** — заметки_питание_и_проводка_питание_звездой_данные_цепочкой, заметки_питание_и_проводка_отдельные_dc_dc_и_звезда_земли, заметки_питание_и_проводка_dc_dc_6в_8а, заметки_питание_и_проводка_аварийная_отсечка_приводов, заметки_питание_и_проводка_мёртвые_контакты_идеальный_диод [EXTRACTED 1.00]
- **Иерархия мозгов: большой мозг — голова — спинной мозг** — заметки_концепция_большой_мозг, заметки_комплектация_и_бюджет_v0_2_raspberry_pi_5, заметки_комплектация_и_бюджет_v0_2_ai_hat_plus_26_tops, заметки_комплектация_и_бюджет_v0_2_pico_2 [EXTRACTED 1.00]
- **Проверка механики в MuJoCo и PyBullet** — заметки_проверка_совместимости_и_сценарии_mujoco, заметки_проверка_совместимости_и_сценарии_pybullet, код_симуляция_управление_с_клавиатуры_harvey_sim, код_симуляция_управление_с_клавиатуры_harvey_scenarios, код_симуляция_управление_с_клавиатуры_harvey_pybullet [EXTRACTED 1.00]
- **Стек шины Feetech на стенде привода** — документы_feetech_протокол_связи_packet_format, документы_feetech_протокол_связи_serial_frame, код_стенд_привода_harvey_bench_sts, код_стенд_привода_readme_fe_urt_1, код_стенд_привода_readme_register_table, документы_sts3215_c018_даташит_feetech_12_в_sts3215_c018 [INFERRED 0.85]
- **Детали стенда одной ноги этапа 1** — документы_harvey_stage1_parts_cradle_servo, документы_harvey_stage1_parts_coxa_bracket, документы_harvey_stage1_parts_coxa_strap, документы_harvey_stage1_parts_femur_plate, документы_harvey_stage1_parts_knee_sleeve, документы_harvey_stage1_parts_tibia_fork, документы_harvey_stage1_parts_foot_tpu, документы_harvey_stage1_parts_lever_100mm [EXTRACTED 1.00]
- **Бортовая электроника Харви: голова, спинной мозг, приводы** — документы_raspberry_pi_5_краткое_описание_raspberry_pi_5, документы_ai_hat_краткое_описание_ai_hat_plus, документы_pico_2_краткое_описание_pico_2, документы_sts3215_c018_даташит_feetech_12_в_sts3215_c018, документы_sts3032_c036_даташит_feetech_6_в_sts3032_c036 [INFERRED 0.85]
- **Сборка клешни: ладонь + челюсть + накладки TPU** — модели_стенд_кисти_детали_кисти_palm, модели_стенд_кисти_детали_кисти_jaw, модели_стенд_кисти_детали_кисти_pad_tpu [INFERRED 0.85]
- **Оснастка стенда: стойка запястья, люлька STS3032, рычаг 25 мм** — модели_стенд_кисти_детали_кисти_wrist_stand, модели_стенд_кисти_детали_кисти_cradle_sts3032, модели_стенд_кисти_детали_кисти_grip_lever [INFERRED 0.75]
- **Кинематическая цепь кисти: стойка → запястье #21 → ладонь → захват #22 → челюсть против пальца** — модели_стенд_кисти_сборка_кисти_стойка_запястья, модели_стенд_кисти_сборка_кисти_привод_запястья_21, модели_стенд_кисти_сборка_кисти_ладонь, модели_стенд_кисти_сборка_кисти_привод_захвата_22, модели_стенд_кисти_сборка_кисти_верхняя_челюсть, модели_стенд_кисти_сборка_кисти_нижний_палец [EXTRACTED 1.00]
- **Функции harvey_hand_parts.py, порождающие сборку на рендере** — модели_стенд_кисти_harvey_hand_parts_wrist_stand, модели_стенд_кисти_harvey_hand_parts_palm, модели_стенд_кисти_harvey_hand_parts_jaw, модели_стенд_кисти_harvey_hand_parts_assembly, модели_стенд_кисти_сборка_кисти [INFERRED 0.95]

## Communities (27 total, 3 thin omitted)

### Community 0 - "Симуляция: токи, защита, PyBullet"
Cohesion: 0.06
Nodes (44): Симуляция — заглушка (harvey_sim, harvey_scenarios, harvey_pybullet), currents(), run(), eye_force(), trial(), inertial(), PB, stand() (+36 more)

### Community 1 - "CAD кисти (код)"
Cohesion: 0.08
Nodes (34): assembly(), box(), boxr(), check(), cyl(), finger_bar(), grip_lever(), horn_disk() (+26 more)

### Community 2 - "Управление с клавиатуры"
Cohesion: 0.09
Nodes (14): KeyReader, run_gui(), act(), close(), keyname(), norm(), on_press_track(), on_release_track() (+6 more)

### Community 3 - "Модель MuJoCo и сценарии"
Cohesion: 0.11
Nodes (19): arm_ik(), arm_xml(), build_xml(), eye_xml(), ik(), pose_targets(), power(), reach_table() (+11 more)

### Community 4 - "Стенд привода: замеры"
Cohesion: 0.14
Nodes (6): Bench, main(), Servo, to_signed(), u16(), test_fake_bus_set_id_and_move()

### Community 5 - "CAD ноги (код)"
Cohesion: 0.11
Nodes (17): to_trimesh(), check(), servo_dummy(), vol(), box(), coxa_bracket(), cradle(), cyl() (+9 more)

### Community 6 - "Визуализация three.js"
Cohesion: 0.13
Nodes (25): Структура папки проекта (заметки, визуализация, модели, документы, фото, код), Obsidian-хранилище на всю папку harvey, Харви «Компакт» — 3D-модель (three.js), apply() — применение позы ног, armIK() — обратная кинематика клешни, claw() — построение клешни, goArm() — смена позы клешней, goTail() — смена позы хвоста (+17 more)

### Community 7 - "Печатные детали ноги и кисти"
Cohesion: 0.10
Nodes (24): Файлы, выданные в чатах (скрипты симуляции, CAD-архивы), Харви — детали стенда одной ноги (PDF), Кронштейн основания (harvey_coxa_bracket.stl), Планка-фиксатор привода бедра (harvey_coxa_strap.stl), Держатель привода валом вверх (harvey_cradle_servo.stl), Пластина бедра ×2 (harvey_femur_plate_x2.stl), Стопа TPU 95A (harvey_foot_TPU.stl), Обхват привода колена (harvey_knee_sleeve.stl) (+16 more)

### Community 8 - "Захват пальцами и безопасность"
Cohesion: 0.21
Nodes (12): build(), build_cup(), finger_mid(), G, obj_forces(), path(), pen_test(), phone_test() (+4 more)

### Community 9 - "Проверка в симуляции и Onshape"
Cohesion: 0.16
Nodes (19): Параметры спецификации v0.6 (LEG, ARM, CAM, TL, LIM), Время работы: ходьба ~30 мин, стоя ~1 ч, лёжа ~3 ч, Харви — проверка совместимости и сценарии, MuJoCo (физический движок), PyBullet (физический движок), Обучение в симуляции (RL), Походка на пяти ногах (при отказе ноги), Более 40 смоделированных сценариев (+11 more)

### Community 10 - "Электроника и комплектация"
Cohesion: 0.19
Nodes (15): CLAUDE.md — контекст проекта Харви, Режим «Показать начинку» (x-ray), Харви — комплектация и бюджет v0.2, AI HAT+ 26 TOPS (Hailo-8), Raspberry Pi Camera Module 3 Wide, IMU BMI270 / ICM-42688, Raspberry Pi Pico 2 — «спинной мозг», Raspberry Pi 5 8 ГБ — «голова» (+7 more)

### Community 11 - "Тесты драйвера шины"
Cohesion: 0.21
Nodes (12): checksum(), make_packet(), parse_status(), _status(), test_echo_is_recognisable(), test_packet_ping_matches_reference(), test_packet_read_position(), test_packet_rejects_bad_id() (+4 more)

### Community 12 - "Концепция и главные документы"
Cohesion: 0.20
Nodes (17): README папки проекта Харви, Онлайн-версии документов (артефакты claude.ai), Raspberry Pi 5 — краткое описание, STS3032-C036 — даташит Feetech (6 В), STS3215-C018 — даташит Feetech (12 В), документы/ — ПОЛОЖИ СЮДА, Журнал решений, Харви — концепция (+9 more)

### Community 13 - "Платы Raspberry Pi и Pico"
Cohesion: 0.16
Nodes (16): AI HAT+ — краткое описание, Raspberry Pi AI HAT+ (13/26 TOPS), Ускоритель Hailo-8 / Hailo-8L (NPU), Связь AI HAT+ по PCIe Gen 3, Pico 2 — даташит, Служебные GPIO23/24/25/29 (SMPS PS, VBUS sense, LED, VSYS/3), MicroPython на Pico 2, Питание Pico 2: VSYS 1,8–5,5 В, SMPS RT6150, 3V3 ≤ 300 мА (+8 more)

### Community 14 - "Питание и проводка"
Cohesion: 0.21
Nodes (12): Датчик тока INA226, Батарея 3S из банок 21700 (~50 Вт·ч), Харви 1.0 — питание и проводка, Аварийная отсечка приводов (силовой ключ 40 А + кнопка-стоп), Шесть замеров питания на стенде, Полудуплексные буферы 74LVC1G125 / 74LVC1G126, Пороги напряжения на Pico по INA226 (9,0 / 9,9 / 10,5 В), Порядок включения и самопроверка перед ключом приводов (+4 more)

### Community 16 - "Драйвер шины SerialBus"
Cohesion: 0.21
Nodes (3): BusError, le16(), SerialBus

### Community 17 - "Стенд привода: подключение"
Cohesion: 0.19
Nodes (10): Рычаг 100 мм (harvey_lever_100mm.stl), Библиотека Feetech на Python (стенд с ноутбука), Симуляция Харви в MuJoCo (спецификация v1.0), requirements.txt симуляции (mujoco ≥3.1.6, numpy ≥1.24), Харви — стенд привода STS3215-C018 (README), Замеры 1–7 стенда: связь, ток, момент, скорость, люфт, точность возврата, нагрев, Масштаб тока 6,5 мА/ед. с калибровкой (bench_calibration.json), Адаптер шины FE-URT-1 (USB, драйвер CH340/CH341) (+2 more)

### Community 18 - "Протокол Feetech: команды"
Cohesion: 0.18
Nodes (13): Feetech — протокол связи (SCS/SMS), Широковещательный ID 254 (0xFE), Регистр цели 0x2A: позиция, время, скорость (6 байт), Регистр ID (адрес 5) и блокировка EPROM, PING (0x01) — запрос состояния, Регистр текущей позиции 0x38 (2 байта), READ DATA (0x02) — чтение таблицы памяти, REG WRITE (0x04) + ACTION (0x05) — отложенная запись (+5 more)

### Community 19 - "Приводы STS: паспорт и защиты"
Cohesion: 0.23
Nodes (11): Порядок байт SMS/STS: младший байт первым, Контрольная сумма ~(ID+Len+Instr+Params) & 0xFF, Пакет инструкции 0xFF 0xFF ID Len Instr Params Checksum, Полудуплексная асинхронная шина 8N1, Защиты STS3032: перегрузка, напряжение 4–7,4 В, 70 °C, Привод Feetech STS3032-C036 (6 В, 4,5 кг·см), 12-битный магнитный энкодер: 4096 отсчётов, 0,088°, середина 2048, Калибровка середины: 128 в адрес 40 (+3 more)

### Community 20 - "Этап 1: закупка и протокол"
Cohesion: 0.29
Nodes (10): Порядок закупки в 4 этапа, Что симуляция не покажет (люфт, нагрев, гибкость деталей, реальный ток), Харви — этап 1: покупки и стенд одной ноги, Замер люфта лазерной указкой (1° ≈ 17 мм на 1 м), Замер момента: рычаг 100 мм на кухонные весы, Назначение ID приводов: 1–3 нога, 21–22 кисть, Протокол стенда: 12 замеров, Решение по итогам стенда (+2 more)

### Community 21 - "Приводы и манипуляторы"
Cohesion: 0.25
Nodes (7): Feetech STS3032 (6 В, 4,5 кг·см), Feetech STS3215-C018 (12 В, 30 кг·см), Шинный протокол Feetech STS (TTL, обратная связь по положению, нагрузке, температуре), Хвост — третья рука с присоской, Две мощные многосуставные клешни, Глаза на стебельках с магнитной муфтой, Клешня с пятью суставами (звенья 45 / 60 / 35 мм)

### Community 23 - "Отчёт стенда в Excel"
Cohesion: 0.22
Nodes (4): _header(), write(), Отчёт bench_results_<дата>.xlsx/.json (листы «Результаты», «Нагрев»), requirements.txt стенда (pyserial ≥3.5, openpyxl ≥3.1)

### Community 24 - "Таблица регистров SCS15"
Cohesion: 0.42
Nodes (9): Feetech — таблица регистров (конвертирована), Блокировка записи EPROM (адрес 48), Защита от перегрузки (регистры 37–39: момент, время, порог 80%), Максимальный момент (адрес 16), Включение момента (адрес 40), Регистр ID (адрес 5; 254 — широковещательный), Регистр скорости шины (адрес 6; 0 = 1 Мбит/с), Обратная связь: позиция, скорость, нагрузка, напряжение, температура (56–63) (+1 more)

### Community 25 - "Адаптер шины FE-URT-1"
Cohesion: 0.70
Nodes (5): FE-URT-1 — адаптер шины (таблица, конвертирована), FE-URT-1 — USB → TTL/RS485 программатор шины Feetech, Аппаратное автоматическое переключение направления полудуплекса, Драйвер CH340C, Порты SMS (RS485, 5264-4AW) и SCS (TTL, 5264-3AW)

## Ambiguous Edges - Review These
- `Feetech STS3215-C018 (12 В, 30 кг·см)` → `Таблица регистров SCS15 (прошивка SCServo1.1)`  [AMBIGUOUS]
  graphify-out/converted/Feetech — таблица регистров_c742f36f.md · relation: conceptually_related_to
- `Связь AI HAT+ по PCIe Gen 3` → `PCIe 2.0 x1 у Raspberry Pi 5`  [AMBIGUOUS]
  документы/AI HAT+ — краткое описание.pdf · relation: conceptually_related_to
- `Замеры 1–7 стенда: связь, ток, момент, скорость, люфт, точность возврата, нагрев` → `Рычаг 25 мм для замера силы захвата (замер 10)`  [AMBIGUOUS]
  модели/стенд кисти/README.md · relation: conceptually_related_to
- `Рычаг-качалка 25 мм (grip_lever)` → `Сервопривод Feetech STS3032-C036`  [AMBIGUOUS]
  модели/стенд кисти/детали кисти.png · relation: conceptually_related_to

## Knowledge Gaps
- **19 isolated node(s):** `фото/ — ПОЛОЖИ СЮДА`, `Онлайн-версии документов (артефакты claude.ai)`, `Бюджет 105–175 тыс. ₽`, `Настройки печати PETG / TPU`, `Ускоритель Hailo-8 / Hailo-8L (NPU)` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 128 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Харви — главная заметка` connect `Концепция и главные документы` to `Симуляция: токи, защита, PyBullet`, `Визуализация three.js`, `Печатные детали ноги и кисти`, `Проверка в симуляции и Onshape`, `Электроника и комплектация`, `Платы Raspberry Pi и Pico`, `Питание и проводка`, `Стенд привода: подключение`, `Протокол Feetech: команды`, `Этап 1: закупка и протокол`, `Таблица регистров SCS15`, `Адаптер шины FE-URT-1`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._
- **What connects `фото/ — ПОЛОЖИ СЮДА`, `Онлайн-версии документов (артефакты claude.ai)`, `Бюджет 105–175 тыс. ₽` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Симуляция: токи, защита, PyBullet` be split into smaller, more focused modules?**
  _Cohesion score 0.05581395348837209 - nodes in this community are weakly interconnected._
- **Why does `Харви — стенд привода STS3215-C018 (README)` connect `Стенд привода: подключение` to `Печатные детали ноги и кисти`, `Концепция и главные документы`, `Стенд: модули и имитация`, `Протокол Feetech: команды`, `Приводы STS: паспорт и защиты`, `Этап 1: закупка и протокол`, `Отчёт стенда в Excel`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Should `CAD кисти (код)` be split into smaller, more focused modules?**
  _Cohesion score 0.083710407239819 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Feetech STS3215-C018 (12 В, 30 кг·см)` and `Таблица регистров SCS15 (прошивка SCServo1.1)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Связь AI HAT+ по PCIe Gen 3` and `PCIe 2.0 x1 у Raspberry Pi 5`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._