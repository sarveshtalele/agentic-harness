"""One plain CSV per sheet, from the recalculated workbook's values. python export_csv.py <xlsx> <dir>"""
import csv, sys
from pathlib import Path
from openpyxl import load_workbook
wb, out = load_workbook(sys.argv[1], data_only=True), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for i, ws in enumerate(wb.worksheets, 1):
    path = out / f"{i:02d}_{ws.title.lower().replace(' ', '_')}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel shows the rupee sign correctly
        w = csv.writer(f)
        for row in ws.iter_rows(values_only=True):
            vals = ["" if v is None else (round(v, 4) if isinstance(v, float) else v) for v in row]
            while vals and vals[-1] == "":
                vals.pop()
            w.writerow(vals)
    print(path)
