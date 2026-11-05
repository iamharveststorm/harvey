"""Формат обмена с головой — тот же файл, что в прошивке (код/прошивка/rp2350/link.py), без копии."""
import sys
from pathlib import Path


def _firmware_dir() -> Path:
    """Путь ищется и как есть, и с раскрытыми ссылками (рабочие папки mutator)."""
    here = Path(__file__)
    for base in (here.absolute(), here.resolve()):
        candidate = base.parents[2] / "прошивка" / "rp2350"
        if (candidate / "link.py").exists():
            return candidate
    raise ImportError("не найден код/прошивка/rp2350/link.py — мозг и прошивка должны лежать рядом, как в репозитории")


_FIRMWARE = str(_firmware_dir())
if _FIRMWARE not in sys.path:
    sys.path.append(_FIRMWARE)

from link import LineReader, encode  # noqa: E402,F401


def _head_dir() -> Path:
    """код/голова рядом с код/мозг: общий формат медиа-кадров (media.py, stdlib) берётся оттуда, без копии."""
    here = Path(__file__)
    for base in (here.absolute(), here.resolve()):
        candidate = base.parents[2] / "голова"
        if (candidate / "harvey_head" / "media.py").exists():
            return candidate
    raise ImportError("не найден код/голова/harvey_head/media.py — мозг и голова должны лежать рядом, как в репозитории")


_HEAD = str(_head_dir())
if _HEAD not in sys.path:
    sys.path.append(_HEAD)

from harvey_head import media  # noqa: E402,F401
