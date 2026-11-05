from pathlib import Path

import io

import pytest

import get_models
from get_models import ASSETS, fetch, plan


def test_plan_lists_all_when_empty(tmp_path):
    todo = plan(tmp_path)
    assert [a.name for a in todo] == [a.name for a in ASSETS] and len(todo) == 4
    assert {a.url.split("/")[-1] for a in todo} == {
        "silero_vad.onnx",
        "sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19.tar.bz2",
        "vits-piper-ru_RU-dmitri-medium.tar.bz2",
        "face_detection_yunet_2023mar.onnx",
    }


def test_plan_skips_existing(tmp_path):
    (tmp_path / "silero_vad.onnx").write_bytes(b"x")
    (tmp_path / "vits-piper-ru_RU-dmitri-medium").mkdir()
    assert [a.name for a in plan(tmp_path)] == ["sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19", YUNET]


def test_destinations_are_inside_models_dir(tmp_path):
    for a in plan(tmp_path):
        assert tmp_path in a.dest(tmp_path).parents


YUNET = "vision/face_detection_yunet_2023mar.onnx"


def yunet():
    return next(a for a in ASSETS if a.name == YUNET)


def test_yunet_comes_from_opencv_zoo_and_is_skipped_when_present(tmp_path):
    assert yunet().url == ("https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
                           "face_detection_yunet/face_detection_yunet_2023mar.onnx")
    (tmp_path / "vision").mkdir()
    (tmp_path / YUNET).write_bytes(b"x")
    assert YUNET not in [a.name for a in plan(tmp_path)]


class Resp(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_fetch_saves_yunet_into_the_vision_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(get_models.urllib.request, "urlopen", lambda url: Resp(b"m" * 200_000))
    fetch(yunet(), tmp_path)
    assert (tmp_path / YUNET).stat().st_size == 200_000


def test_fetch_rejects_a_tiny_file_as_an_lfs_pointer(tmp_path, monkeypatch):
    monkeypatch.setattr(get_models.urllib.request, "urlopen", lambda url: Resp(b"version https://git-lfs.github.com/spec/v1"))
    with pytest.raises(OSError, match="указатель Git LFS"):
        fetch(yunet(), tmp_path)
    assert not (tmp_path / YUNET).exists()
