"""Тесты головы: поиск файлов проекта вне код/голова (документы/). Путь ищется и как есть, и с раскрытыми ссылками:
в рабочих папках mutator тесты — ссылки, а папок проекта рядом нет."""
from pathlib import Path


def project_file(rel: str) -> Path:
    here = Path(__file__)
    for base in (here.absolute(), here.resolve()):
        for parent in base.parents:
            if (parent / rel).exists():
                return parent / rel
    raise FileNotFoundError(rel)
