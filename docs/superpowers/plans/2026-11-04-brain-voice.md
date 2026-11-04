# «Большой мозг» на ПК: голос — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Харви на ПК слышит «Харви» / «wake up Harvey», понимает русскую речь, отвечает голосом с характером (добрый, как ВАЛЛ-И) и командует голове: выражение глаз, «иди домой», «посмотри на меня», «иди ко мне», «отдыхай».

**Architecture:** Новый пакет `код/мозг/harvey_brain` на ПК. Голова (настоящая или в симуляции) — TCP-клиент `BrainLink` (уже есть в `код/голова/harvey_head/links.py`), мозг — TCP-сервер на порту 8765 с тем же форматом «одна строка — один JSON» (`код/прошивка/rp2350/link.py`, без копии). Поток: звук → VAD → распознавание → слово пробуждения → быстрые команды или LLM (Ollama, ответ JSON по схеме) → голос + команды голове. Этап A — вся логика без загрузок (текстовый режим, Ollama уже стоит); этап B — настоящий звук (sherpa-onnx), только после разрешения на загрузки.

**Tech Stack:** Python 3.12, stdlib (asyncio, urllib, json), pytest; Ollama (локально, `http://127.0.0.1:11434`); этап B: sherpa-onnx (Silero VAD, GigaAM v2 CTC int8, Piper VITS ru_RU), sounddevice, numpy.

**Spec:** этот документ (вопросы пользователь пропустил; решения ниже — решения ведущего).

## Решения
- Слово пробуждения в v1 — по распознанному тексту: каждая фраза после VAD идёт в распознавание, «Харви» ищется в тексте. Так работает русское «Харви» и «Харви, иди домой» одной фразой. Отдельная модель KWS (английская gigaspeech, «HARVEY») — позже, для Pi Zero.
- Микрофон и динамик в v1 — ноутбука (вместо головы, пока нет железа). Голос в голову (стрим звука на Pi) — не в этом плане.
- LLM: модель задаётся `--model`; по умолчанию — та из установленных (`qwen3.6:35b` MoE, `dolphin3:8b`), что по замеру (задача 5) отвечает по-русски быстрее 4 с; ответ — JSON по схеме, `think: false`.
- Ничего не пишется на диск и не уходит в сеть, кроме `127.0.0.1` (Ollama) и головы в локальной сети.

## Global Constraints
- Все строки для человека — по-русски. Пакет: `код/мозг/harvey_brain`, тесты `код/мозг/tests`, запуск `python -m pytest -q tests` из `код/мозг`.
- Этап A — только stdlib; тесты гонять интерпретатором `C:\venvs\harvey-head\Scripts\python.exe` (там есть pytest и pytest-asyncio). Этап B — своё окружение `C:\venvs\harvey-brain`.
- Пути к файлам вне `код/мозг` искать и как есть, и с `resolve()` (как `harvey_head/protocol.py`) — иначе mutator даёт ложные 100 %.
- Код — по `.claude/skills/ub-mode/SKILL.md`: сначала падающий тест, потом минимальная правка; CRAP < 10.
- Голову, прошивку и симуляцию не менять. Модели (этап B) — в `код/мозг/models/` и в `.gitignore`.
- EMOTES = `neutral, happy, sad, sleepy, surprised, curious, alarm, tired, love` (из `harvey_head/eyes.py` без `asleep`); GOALS = `look, hand, home, idle` (из `harvey_head/behavior.py`).

## Review Focus
1. LLM вернула не JSON, JSON с лишним текстом или `<think>…</think>` — ответ всё равно разобран, Харви говорит текст, без падения (задача 2).
2. Ollama не запущена или молчит дольше таймаута — Харви говорит «Ой, я задумался и потерял мысль.» за ≤ таймаута, цикл живёт (задача 3).
3. «Харви!», «ХАРВИ,», «харвей», «Wake up, Harvey» — пробуждение; «Харвиус», «архив» — нет (задача 2).
4. Голова подключается и отключается много раз; отправка без головы не блокирует и не падает (задача 4).
5. Длинный ответ LLM — до TTS режется до 2 предложений и ≤ 300 символов (задача 2).

---

### Task 1: Каркас, характер и разбор ответа
**Files:** Create `код/мозг/harvey_brain/__init__.py`, `persona.py`, `reply.py`; `код/мозг/tests/test_reply.py`; `код/мозг/pytest.ini` (как в `код/голова`).

**Interfaces — Produces:**
- `persona.SYSTEM_PROMPT: str`, `persona.EMOTES: tuple[str, ...]`, `persona.GOALS: tuple[str, ...]`, `persona.REPLY_SCHEMA: dict` (JSON Schema: `say` string, `emote` enum EMOTES, `goal` enum GOALS + `"none"`; все обязательны).
- `reply.Reply` (dataclass: `say: str`, `emote: str = "neutral"`, `goal: str | None = None`).
- `reply.parse_reply(raw: str) -> Reply`; `reply.trim_say(text: str, sentences: int = 2, limit: int = 300) -> str`; `reply.to_head(r: Reply, seconds: float = 3.0) -> list[dict]` → `[{"t": "emote", "name": r.emote, "s": seconds}]` + `{"t": "goal", "goal": r.goal}`, если goal.

SYSTEM_PROMPT (смысл, текст — на усмотрение): «Ты Харви — маленький добрый робот-краб на рабочем столе, похож характером на ВАЛЛ-И: любопытный, тёплый, немного застенчивый. Отвечай по-русски, коротко — 1–2 предложения, простыми словами. Не обещай того, чего не умеешь. Умеешь: посмотреть на человека (look), подойти к руке (hand), пойти домой на зарядку (home), отдохнуть (idle). Отвечай JSON: say, emote, goal».

- [ ] Step 1: тесты — `parse_reply('{"say":"Привет!","emote":"happy","goal":"none"}') == Reply("Привет!", "happy", None)`; неизвестная эмоция → `"neutral"`; неизвестная цель → `None`; `'<think>x</think>{"say":"Да","emote":"love","goal":"look"}'` → `Reply("Да","love","look")`; не-JSON `"Просто текст"` → `Reply("Просто текст")`; JSON внутри текста `'Вот: {"say":"Ок","emote":"happy","goal":"home"} всё'` → goal `"home"`; `trim_say` три предложения → два; 500 символов без точки → ≤ 300 и заканчивается «…»; `to_head(Reply("x","sad","home"))` == два сообщения выше; без goal — одно.
- [ ] Step 2: запустить — падают (нет модуля).
- [ ] Step 3: реализовать. `parse_reply` всегда пропускает `say` через `trim_say`.
- [ ] Step 4: тесты зелёные.

### Task 2: Слово пробуждения и быстрые команды
**Files:** Create `harvey_brain/wake.py`, `harvey_brain/commands.py`; tests `tests/test_wake.py`, `tests/test_commands.py`.

**Interfaces — Produces:**
- `wake.normalize(text: str) -> str` — нижний регистр, ё→е, пунктуация → пробел, лишние пробелы убраны.
- `wake.WAKE = ("харви", "харвей", "харвий", "harvey", "wake up harvey", "вейк ап харви")`.
- `wake.split_wake(text: str) -> tuple[bool, str]` — ищет любую фразу WAKE целым словом (словами) в любом месте; возвращает (найдено, остаток без неё, нормализованный).
- `commands.quick_reply(text: str) -> Reply | None` (текст — уже нормализованный остаток).

Быстрые команды (подстрока в нормализованном тексте → Reply):
- «домой», «на зарядку», «заряжаться», «на базу» → `Reply("Иду домой.", "happy", "home")`
- «посмотри на меня», «смотри на меня» → `Reply("Смотрю!", "curious", "look")`
- «иди ко мне», «иди сюда», «к руке» → `Reply("Иду к тебе.", "happy", "hand")`
- «стоп», «стой», «отдыхай», «хватит» → `Reply("Хорошо, отдыхаю.", "neutral", "idle")`

- [ ] Step 1: тесты — `split_wake("Харви, иди домой") == (True, "иди домой")`; `"ХАРВИ!"` → `(True, "")`; `"Wake up, Harvey"` → `(True, "")`; `"привет харвей как дела"` → `(True, "привет как дела")`; `"Харвиус"` → `(False, "харвиус")`; `"открой архив"` → False; `quick_reply("иди домой").goal == "home"`; `quick_reply("посмотри на меня").goal == "look"`; `quick_reply("как дела") is None`.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.

### Task 3: LLM через Ollama
**Files:** Create `harvey_brain/llm.py`; test `tests/test_llm.py`.

**Interfaces — Consumes:** `persona.SYSTEM_PROMPT`, `persona.REPLY_SCHEMA`, `reply.parse_reply`, `reply.Reply`.
**Produces:** `llm.OllamaChat(model: str, url: str = "http://127.0.0.1:11434", history_turns: int = 6, timeout: float = 30.0, post=None)`; `post(url: str, payload: dict, timeout: float) -> dict` — по умолчанию urllib POST JSON; `OllamaChat.ask(text: str) -> Reply`; `OllamaChat.FALLBACK = Reply("Ой, я задумался и потерял мысль.", "sad")`.

Запрос `POST {url}/api/chat`: `{"model", "messages": [system, …история…, user], "format": REPLY_SCHEMA, "stream": false, "think": false, "keep_alive": "30m", "options": {"temperature": 0.7}}`; ответ — `resp["message"]["content"]` → `parse_reply`. История — пары (user text, assistant `say`), не больше `history_turns` пар.

- [ ] Step 1: тесты с поддельным `post`: payload содержит system-сообщение первым, `format == REPLY_SCHEMA`, `think is False`; ответ разобран в Reply; после 8 вопросов в payload ≤ 6 пар истории + system + user; `post` бросает `urllib.error.URLError` / `TimeoutError` / возвращает `{}` → `FALLBACK`, история не пополняется.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.

### Task 4: Сервер для головы
**Files:** Create `harvey_brain/protocol.py` (поиск `код/прошивка/rp2350/link.py` как в `harvey_head/protocol.py`, реэкспорт `encode`, `LineReader`), `harvey_brain/server.py`; test `tests/test_server.py` (asyncio).

**Produces:** `server.HeadServer(host: str = "0.0.0.0", port: int = 8765)`; `async start() -> None`; `async stop() -> None`; `send(msg: dict) -> int` (сколько голов получили; без голов → 0, не блокирует); `inbox: asyncio.Queue` (сообщения от голов); `heads: int`.

- [ ] Step 1: тесты на `127.0.0.1` и свободном порту, клиент — настоящий `harvey_head.links.BrainLink` (импорт из `код/голова`, путь — и как есть, и с resolve()): голова подключилась → `heads == 1`; `send({"t":"emote","name":"happy","s":2})` доходит в `BrainLink.inbox`; `BrainLink.offer({"t":"ev","ev":"lifted"})` доходит в `server.inbox`; 5 подключений-отключений подряд — сервер жив, `heads == 0` после; `send` без голов → 0.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.

### Task 5: Диалог и текстовый режим
**Files:** Create `harvey_brain/dialog.py`, `harvey_brain/__main__.py`; tests `tests/test_dialog.py`, `tests/test_main.py`; Create `код/мозг/README.md`.

**Consumes:** `wake.split_wake`, `commands.quick_reply`, `llm.OllamaChat.ask`, `reply.to_head`, `server.HeadServer`.
**Produces:**
- `dialog.Dialog(llm, follow_s: float = 8.0)`; `on_text(text: str, now: float) -> Reply | None`; `on_head(msg: dict, now: float) -> Reply | None`; `awake(now) -> bool`.
  - Спит: без пробуждения → None. Пробуждение с пустым остатком → `Reply("Да?", "curious")`; с остатком → ответ на остаток. После любого ответа — бодрствует `follow_s` с; в это время фраза без «Харви» тоже получает ответ.
  - Ответ: `quick_reply(остаток)` или `llm.ask(остаток)`.
  - `on_head`: `{"t":"ev","ev":"lifted"}` → `Reply("Ой! Поставь меня, пожалуйста.", "surprised")`; `"docked"` → `Reply("Ммм, зарядка.", "happy")`; `"bat_low"` → `Reply("Я устал, пойду заряжаться.", "tired")`; одно и то же событие — не чаще раза в 20 с; прочее → None.
- `python -m harvey_brain --text [--model M] [--port 8765] [--no-head]`: строка с клавиатуры → `Dialog.on_text` → печать `Харви: <say> [emote, goal]` → `server.send` каждого сообщения `to_head`. События головы из `server.inbox` → `Dialog.on_head`. Выход — пустая строка дважды или Ctrl+C.
- [ ] Step 1: тесты — сон без «Харви» → None (LLM не вызван); «Харви» → «Да?»; «Харви, иди домой» → goal home без вызова LLM; «как дела» через 3 с после ответа → вызван LLM; через 9 с → None; «lifted» дважды за 5 с → второй None; `main` с поддельным вводом `["Харви, посмотри на меня", "", ""]` и поддельным сервером печатает «Харви: Смотрю!» и шлёт `{"t":"goal","goal":"look"}`.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.
- [ ] Step 5: замер на настоящей Ollama (без загрузок): 5 русских фраз («привет», «как дела», «что ты умеешь», «расскажи о себе», «ты устал?») моделями `qwen3.6:35b` и `dolphin3:8b`, время ответа и качество русского — в отчёт; модель по умолчанию — быстрее 4 с с нормальным русским (если обе медленнее — быстрейшая и пометка в README).
- [ ] Step 6: README мозга (запуск, команды, протокол с головой), строка про `код/мозг/` в `CLAUDE.md` (раздел «Структура папки»), запись в `заметки/Журнал решений.md`.

### Task 6 (этап B, после разрешения на загрузки): голос
**Files:** Create `harvey_brain/speech.py`, `get_models.py`, `код/мозг/requirements.txt`, `.gitignore` (`models/`); tests `tests/test_speech.py`.

**Produces:** `speech.Listener` — протокол `utterances() -> Iterator[str]`; `speech.MicListener(models_dir, device=None)` — микрофон 16 кГц моно → Silero VAD → GigaAM v2 CTC → текст; `speech.Speaker` — `say(text: str) -> None`; `speech.PiperSpeaker(models_dir)` — Piper ru_RU → динамик; `speech.PrintSpeaker`, `speech.ListListener(lines)` — для тестов и `--text`. `__main__`: `--mic` (MicListener + PiperSpeaker), `--voice` (в `--text` ещё и говорить). `get_models.py` скачивает в `models/` только перечисленные архивы и проверяет размер.
- [ ] Step 1: тесты — `ListListener` + `PrintSpeaker` через `Dialog` дают ответы; настоящие модели: распознать WAV, синтезированный `PiperSpeaker` из фразы «Харви, иди домой» → `split_wake` True и `quick_reply.goal == "home"` (skip, если `models/` нет).
- [ ] Step 2–4: падают → реализовать → зелёные.
- [ ] Step 5: живая проверка — пользователь сам: «Харви», «Харви, посмотри на меня», посторонний разговор 1 мин (ложных пробуждений 0).
