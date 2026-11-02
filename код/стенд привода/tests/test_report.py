"""Отчёт Excel: что видит человек, открыв файл, — листы, заголовки, строки замеров, цвет итога, журнал."""
from pathlib import Path

import pytest
from openpyxl import load_workbook

from harvey_bench import report

RESULTS = [
    dict(n="1", test="Связь", measured="1", norm="все", verdict="ОК", note="номера: 1"),
    dict(n="2а", test="Ток покоя", measured="0.120 А", norm="≤ 0,1 А", verdict="НЕ ОК", note=""),
    dict(n="5", test="Люфт", measured="не измерен", norm="≤ 1°", verdict="—", note=""),
]


def written(results=RESULTS, log=None, **kw):
    path = Path("r.xlsx")
    report.write(path, results, log or [], **kw)
    return load_workbook(path)


def test_results_sheet_has_title_header_and_rows():
    ws = written(title="Харви — стенд STS3032")["Результаты"]
    assert ws["A1"].value == "Харви — стенд STS3032" and ws["A1"].font.bold and ws["A1"].font.size == 14
    assert [c.value for c in ws[3]] == ["№", "Замер", "Измерено", "Норма", "Итог", "Примечание"]
    assert [c.value for c in ws[4]] == ["1", "Связь", "1", "все", "ОК", "номера: 1"]
    assert [c.value for c in ws[5]][:5] == ["2а", "Ток покоя", "0.120 А", "≤ 0,1 А", "НЕ ОК"]
    assert ws.max_row == 6 and ws.freeze_panes == "A4"


def test_default_title_is_the_sts3215_bench():
    assert written()["Результаты"]["A1"].value == "Харви — стенд привода STS3215-C018"


def test_verdict_is_bold_and_coloured():
    ws = written()["Результаты"]
    assert ws.cell(4, 5).fill.fgColor.rgb.endswith(report.OK.fgColor.rgb[-6:])
    assert ws.cell(5, 5).fill.fgColor.rgb.endswith(report.BAD.fgColor.rgb[-6:])
    assert ws.cell(6, 5).fill.fill_type is None                     # «—» — без цвета
    assert ws.cell(4, 5).font.bold and not ws.cell(4, 2).font.bold
    assert ws.cell(4, 2).alignment.wrap_text and ws.cell(4, 2).border.left.style == "thin"


def test_header_cells_are_white_on_dark():
    ws = written()["Результаты"]
    cell = ws.cell(3, 2)
    assert cell.font.bold and cell.font.color.rgb.endswith("FFFFFF") and cell.fill.fgColor.rgb.endswith("1F2A31")
    assert cell.alignment.horizontal == "center" and cell.alignment.wrap_text            # длинные заголовки — в две строки


def test_column_widths():
    ws = written()["Результаты"]
    assert [ws.column_dimensions[c].width for c in "ABCDEF"] == [6, 34, 34, 30, 9, 50]


def test_log_sheet_with_default_header():
    lg = written(log=[[0.0, 26, 0.06, 12.0, 2048], [2.0, 27, 0.9, 11.9, 2050]])["Нагрев"]
    assert [c.value for c in lg[1]] == ["Время, с", "Температура, °C", "Ток, А", "Напряжение, В", "Позиция"]
    assert [c.value for c in lg[3]] == [2.0, 27, 0.9, 11.9, 2050]
    assert lg.freeze_panes == "A2" and lg.column_dimensions["E"].width == 16


def test_log_sheet_with_leg_header():
    header = [f"к{i}" for i in range(11)]
    lg = written(log=[list(range(11))], log_header=header)["Нагрев"]
    assert [c.value for c in lg[1]] == header and lg.cell(2, 11).value == 10
    assert lg.column_dimensions["K"].width == 16


def test_empty_report_still_opens():
    wb = written(results=[], log=[])
    assert wb.sheetnames == ["Результаты", "Нагрев"] and wb["Результаты"].max_row == 3


@pytest.mark.parametrize("verdict, fill", [("ОК", report.OK), ("НЕ ОК", report.BAD), ("—", None)])
def test_verdict_fill(verdict, fill):
    assert report.verdict_fill(verdict) is fill
