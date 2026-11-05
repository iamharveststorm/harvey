# Звук и картинка между головой и ПК — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** На настоящем роботе Харви слушает своими микрофонами и говорит своим динамиком, а распознавание, LLM и голос остаются на ПК; ПК получает кадры камеры головы (для зрения). Проверяется на ПК без железа: имитации arecord / aplay / камеры.

**Architecture:** Второе TCP-соединение «медиа» (порт 8766), двоичные кадры; связь команд (8765, JSON-строки) не меняется. Общий формат — `код/голова/harvey_head/media.py` (stdlib), мозг подключает его по пути (как `harvey_brain/protocol.py` — `link.py`). Голова — клиент `MediaLink` (переподключение как у `BrainLink`), ПК — сервер `MediaServer`. В мозге — `RemoteMicListener` и `RemoteSpeaker` с теми же интерфейсами, что `MicListener` / `PiperSpeaker`, режим `--head-audio`.

**Tech Stack:** Python stdlib (asyncio, struct, subprocess), numpy (мозг; на голове уже есть `python3-numpy`), arecord / aplay (alsa-utils), picamera2 + OpenCV на голове (уже в установке).

**Spec:** этот документ; решения — ведущего.

## Формат кадра (media.py)
`MAGIC = b"HV"`, заголовок `struct "<2sBII"`: magic, kind (u8), seq (u32), length (u32), затем `length` байт.
- `AUDIO_UP = 1` — голова → ПК: PCM int16 LE моно 16 кГц, 20 мс = 320 отсчётов = 640 байт.
- `VIDEO_UP = 2` — голова → ПК: JPEG кадра камеры.
- `SPEECH_DOWN = 3` — ПК → голова: начало фразы: payload = `struct "<I"` частота (напр. 22050) + PCM int16 LE моно; одна фраза может идти несколькими кадрами `SPEECH_MORE = 4` (только PCM) и закрываться `SPEECH_END = 5` (пусто).
- `CONTROL = 6` — JSON (UTF-8) в обе стороны: `{"video": true, "fps": 5}` (ПК → голова), `{"speaking": true|false}` (голова → ПК).
- Максимум payload — 512 КиБ; больше — разрыв соединения (защита от мусора).

## Global Constraints
- Голова: всё железное — через подменяемый запуск процессов (`run`/`Popen`) и камеру; в тестах ни arecord, ни aplay, ни камеры. INMP441: `arecord -c 2 -r 16000 -f S32_LE` (как `audio.record_cmd`) — моно = левый канал, `>> 16` → int16 (**предварительно, какой канал живой и уровень — проверить на стенде**). aplay: `aplay -q -D <dev> -t raw -f S16_LE -c 1 -r <rate> -`.
- Полудуплекс на голове: пока играет речь и 0,3 с после — звук с микрофонов не отправляется, голова шлёт `{"speaking": ...}`.
- Пути вне своей папки — и как есть, и через `resolve()`. TDD по `.claude/skills/ub-mode/SKILL.md`. CRAP < 10.
- Тесты: голова — `C:\venvs\harvey-head\Scripts\python.exe -m pytest -q tests` (`код/голова`), мозг — `C:\venvs\harvey-brain\Scripts\python.exe -m pytest -q tests` (`код/мозг`); прежние зелёные.

## Review Focus
1. Мусор/обрыв посреди кадра — читатель не падает и не зависает, соединение закрывается и переподключается (задача 1, 2).
2. Wi-Fi медленный — очередь отправки голос/видео ограничена (аудио ≤ 50 кадров = 1 с, видео ≤ 2 кадра), старое выбрасывается, а не копится (задача 2).
3. ПК шлёт речь, пока голова ещё играет прошлую — фразы встают в очередь, не смешиваются (задача 2).
4. Мозг без головы в `--head-audio` — ждёт подключения головы, печатает «Жду голову…» один раз (задача 3).
5. Видео выключено по умолчанию — без `{"video": true}` голова кадры не шлёт (задача 2).

---

### Task 1: Формат кадров
**Files:** Create `код/голова/harvey_head/media.py`; Test `код/голова/tests/test_media.py`.
**Produces:** константы выше; `pack(kind: int, seq: int, payload: bytes) -> bytes`; `class FrameReader` — `feed(data: bytes) -> list[tuple[int, int, bytes]]` (kind, seq, payload), `MediaError` на неверный magic / длину > максимума; `speech_frames(samples_int16: bytes, rate: int, chunk: int = 32000) -> list[tuple[int, bytes]]` (SPEECH_DOWN, MORE…, END); `stereo32_to_mono16(raw: bytes) -> bytes` (левый канал, `>> 16`).
- [ ] Step 1: тесты — pack→feed туда-обратно; кадр, разрезанный на куски по 1 байту; два кадра в одном куске; неверный magic → MediaError; длина > 512 КиБ → MediaError; speech_frames для 70 000 байт → SPEECH_DOWN с частотой, 2 × MORE, END, склейка = исходные байты; stereo32_to_mono16 на известных отсчётах.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.

### Task 2: Голова — MediaLink, микрофон, динамик, камера
**Files:** Create `код/голова/harvey_head/media_link.py`; Modify `harvey_head/main.py` (запуск медиа, кроме `--sim`), `harvey_head/config.py` (`MEDIA_PORT = 8766`, из `HARVEY_MEDIA_PORT`), `harvey_head/camera.py` (только: отдать последний кадр BGR, если его ещё нет в API — минимально); Test `код/голова/tests/test_media_link.py`.
**Produces:** `MediaLink(host, port)` — asyncio-клиент с переподключением (как `BrainLink`); `offer_audio(pcm16: bytes)` (очередь ≤ 50, старое выбрасывается), `offer_video(jpeg: bytes)` (≤ 2), `video_wanted -> bool`, `video_fps -> float`; входящую речь отдаёт `Speaker`. `MicStream(run=subprocess.Popen, device)` — читает stdout arecord кусками 20 мс стерео-32 → `stereo32_to_mono16` → `offer_audio`, если не `muted`. `SpeakerStream(popen=subprocess.Popen, device)` — фразы в очереди, каждая — свой `aplay` с stdin; на время фразы + 0,3 с `mic.muted = True`, шлёт `{"speaking": …}`. Камера: если `video_wanted`, не чаще `video_fps` — `cv2.imencode(".jpg", frame, [IMWRITE_JPEG_QUALITY, 70])` → `offer_video` (кодировщик подменяется).
- [ ] Step 1: тесты с настоящим asyncio-сервером на localhost (поддельный ПК): аудио доходит кадрами по 640 байт; без `{"video": true}` видео нет, после — не чаще fps; речь из двух фраз → два запуска поддельного aplay по очереди, байты совпадают; во время речи `offer_audio` не шлёт; обрыв посреди кадра → переподключение; переполнение очереди → не больше 50 / 2.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные; все тесты головы зелёные.

### Task 3: Мозг — MediaServer, звук головы
**Files:** Create `код/мозг/harvey_brain/media_server.py`; Modify `harvey_brain/protocol.py` (реэкспорт `media` из головы), `harvey_brain/speech.py` (`RemoteMicListener`, `RemoteSpeaker`), `harvey_brain/__main__.py` (`--head-audio`, `--media-port 8766`), `код/мозг/README.md`, `код/голова/README.md`, `CLAUDE.md` (строки голова/мозг), `заметки/Журнал решений.md` (2026-11-05); Tests `код/мозг/tests/test_media_server.py`, дополнить `test_speech.py`, `test_main.py`.
**Produces:** `MediaServer(host="0.0.0.0", port=8766)`: `start()/stop()`, `audio: queue.Queue[bytes]` (pcm16 16 кГц), `latest_frame() -> tuple[float, bytes] | None` (время приёма, JPEG), `request_video(on: bool, fps: float = 5)`, `send_speech(pcm16: bytes, rate: int) -> bool`, `head_speaking -> bool`, `connected -> bool`. `RemoteMicListener(server, models_dir)` — те же VAD + распознавание, что `MicListener`, но блоки из `server.audio` (переиспользовать `segments` и `Transcriber`); `RemoteSpeaker(server, piper)` — `synth` → int16 → `send_speech`. `--head-audio`: слушает и говорит голова; без головы — «Жду голову…».
- [ ] Step 1: тесты — настоящий `MediaLink` головы (импорт по пути) ↔ `MediaServer`: аудио приходит в `server.audio`; `request_video(True, 5)` → голова начинает слать, `latest_frame()` отдаёт JPEG; `send_speech` → поддельный aplay головы получает те же байты; `RemoteMicListener` на синтезированной фразе «Харви, иди домой» (модели есть — не пропускать), поданной кадрами 20 мс через настоящий `MediaLink` → `split_wake` True и цель home.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные; все тесты мозга и головы зелёные.
