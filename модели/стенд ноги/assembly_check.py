"""Старая проверка сборки ноги заменена полной — leg_check.py.
Старая не проверяла пару «привод бедра ↔ привод колена» и пропустила, что при бедре 45 мм они упираются.
    python assembly_check.py   (то же, что python leg_check.py)"""
import runpy, os
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "leg_check.py"), run_name="__main__")
