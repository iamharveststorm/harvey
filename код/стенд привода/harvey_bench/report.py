"""Отчёт стенда в Excel: лист «Результаты» с нормами и итогом, лист «Нагрев» с записью по времени."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

F = "Arial"
THIN = Side(style="thin", color="C9D2D7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HDR = PatternFill("solid", fgColor="1F2A31")
OK = PatternFill("solid", fgColor="E2EFDA")
BAD = PatternFill("solid", fgColor="F8D7DA")


def _header(ws, row: int, cols: list[str]) -> None:
    for c, h in enumerate(cols, 1):
        cell = ws.cell(row, c, h)
        cell.font = Font(name=F, bold=True, color="FFFFFF")
        cell.fill = HDR
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def verdict_fill(verdict: str) -> PatternFill | None:
    """Цвет ячейки «Итог»: зелёный — ОК, красный — НЕ ОК, без цвета — не измерено («—»)."""
    return {"ОК": OK, "НЕ ОК": BAD}.get(verdict)


def write(path: Path, results: list[dict], heat_log: list[list], title: str = "Харви — стенд привода STS3215-C018",
          log_header: list[str] | None = None) -> None:
    wb = Workbook()
    _results_sheet(wb.active, title, results)
    _log_sheet(wb.create_sheet("Нагрев"), log_header or ["Время, с", "Температура, °C", "Ток, А", "Напряжение, В", "Позиция"],
               heat_log)
    wb.save(path)


def _results_sheet(ws, title: str, results: list[dict]) -> None:
    """Лист «Результаты»: заголовок, строка на каждый замер, цвет итога."""
    ws.title = "Результаты"
    ws["A1"] = title
    ws["A1"].font = Font(name=F, bold=True, size=14)
    _header(ws, 3, ["№", "Замер", "Измерено", "Норма", "Итог", "Примечание"])
    for i, r in enumerate(results, 4):
        for c, v in enumerate([r["n"], r["test"], r["measured"], r["norm"], r["verdict"], r["note"]], 1):
            cell = ws.cell(i, c, v)
            cell.font = Font(name=F, size=10, bold=(c == 5))
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        fill = verdict_fill(r["verdict"])
        if fill:
            ws.cell(i, 5).fill = fill
    for col, w in zip("ABCDEF", (6, 34, 34, 30, 9, 50)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A4"


def _log_sheet(lg, header: list[str], log: list[list]) -> None:
    """Лист «Нагрев»: журнал по времени (у ноги — 11 колонок шага, у привода — 5 колонок нагрева)."""
    _header(lg, 1, header)
    for i, row in enumerate(log, 2):
        for c, v in enumerate(row, 1):
            lg.cell(i, c, v).font = Font(name=F, size=10)
    for c in range(1, len(header) + 1):
        lg.column_dimensions[lg.cell(1, c).column_letter].width = 16
    lg.freeze_panes = "A2"
