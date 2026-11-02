"""Формат обмена с «спинным мозгом» — тот же файл, что в прошивке (код/прошивка/rp2350/link.py), без копии.
Им же голова говорит с ПК: одна строка — одно сообщение JSON."""
import sys
from pathlib import Path


def _firmware_dir() -> Path:
    """код/прошивка/rp2350 рядом с код/голова. Путь ищется и как есть, и с раскрытыми ссылками: в рабочих
    папках mutator файлы головы — ссылки, а прошивки рядом нет."""
    here = Path(__file__)
    for base in (here.absolute(), here.resolve()):
        candidate = base.parents[2] / "прошивка" / "rp2350"
        if (candidate / "link.py").exists():
            return candidate
    raise ImportError("не найден код/прошивка/rp2350/link.py — голова и прошивка должны лежать рядом, как в репозитории")


_FIRMWARE = str(_firmware_dir())
if _FIRMWARE not in sys.path:
    sys.path.append(_FIRMWARE)

from link import VERSION, LineReader, decode, encode, joints  # noqa: E402,F401
