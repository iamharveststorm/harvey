"""Скачивает модели речи в папку моделей (по умолчанию ~/.harvey/models): python get_models.py [--models PATH]"""
import argparse
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from harvey_brain.speech import ModelsPathError, resolve_models_dir

BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download"


@dataclass(frozen=True)
class Asset:
    name: str  # имя файла или папки в папке моделей
    url: str

    def dest(self, models_dir) -> Path:
        return Path(models_dir) / self.name

    @property
    def is_archive(self) -> bool:
        return self.url.endswith(".tar.bz2")


ASSETS = (
    Asset("silero_vad.onnx", f"{BASE}/asr-models/silero_vad.onnx"),
    Asset("sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19",
          f"{BASE}/asr-models/sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19.tar.bz2"),
    Asset("vits-piper-ru_RU-dmitri-medium", f"{BASE}/tts-models/vits-piper-ru_RU-dmitri-medium.tar.bz2"),
)


def plan(models_dir) -> list[Asset]:
    return [a for a in ASSETS if not a.dest(models_dir).exists()]


def fetch(asset: Asset, models_dir) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        part = Path(tmp) / "download"
        with urllib.request.urlopen(asset.url) as resp, open(part, "wb") as f:
            expected = int(resp.headers.get("Content-Length") or 0)
            shutil.copyfileobj(resp, f)
        if expected and part.stat().st_size != expected:
            raise OSError(f"{asset.name}: скачано {part.stat().st_size} байт из {expected}")
        if asset.is_archive:
            with tarfile.open(part) as tar:
                tar.extractall(models_dir, filter="data")
        else:
            shutil.move(part, asset.dest(models_dir))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Скачать модели речи Харви")
    ap.add_argument("--models", help="папка моделей (иначе HARVEY_MODELS, иначе ~/.harvey/models)")
    args = ap.parse_args(argv)
    try:
        models_dir = resolve_models_dir(args.models, os.environ, Path.home())
    except ModelsPathError as e:
        print(e)
        return 2
    models_dir.mkdir(parents=True, exist_ok=True)
    todo = plan(models_dir)
    for asset in todo:
        print(f"Скачиваю {asset.name} …")
        fetch(asset, models_dir)
    print("Всё скачано." if todo else "Все модели уже на месте.", models_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
