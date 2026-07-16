from openpyxl import Workbook
from tkinter import filedialog


def export_school_excel(rows):

    if not rows:
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel", "*.xlsx")],
        initialfile="학교검색결과.xlsx"
    )

    if not file_path:
        return

    wb = Workbook()
    ws = wb.active

    ws.title = "학교목록"

    ws.append([
        "학교명",
        "학교급",
        "교육청",
        "지역",
        "주소"
    ])

    for row in rows:
        ws.append(row)

    wb.save(file_path)