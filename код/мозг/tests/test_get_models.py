from pathlib import Path

from get_models import ASSETS, plan


def test_plan_lists_all_three_when_empty(tmp_path):
    todo = plan(tmp_path)
    assert [a.name for a in todo] == [a.name for a in ASSETS] and len(todo) == 3
    assert {a.url.split("/")[-1] for a in todo} == {
        "silero_vad.onnx",
        "sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19.tar.bz2",
        "vits-piper-ru_RU-dmitri-medium.tar.bz2",
    }


def test_plan_skips_existing(tmp_path):
    (tmp_path / "silero_vad.onnx").write_bytes(b"x")
    (tmp_path / "vits-piper-ru_RU-dmitri-medium").mkdir()
    assert [a.name for a in plan(tmp_path)] == ["sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19"]


def test_destinations_are_inside_models_dir(tmp_path):
    for a in plan(tmp_path):
        assert a.dest(tmp_path).parent == tmp_path
