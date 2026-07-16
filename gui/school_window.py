import customtkinter as ctk
from tkinter import ttk
from services.database import find_school
from services.excel_service import export_school_excel
from services.region_data import OFFICES


def open_school_detail(parent, row):

    detail = ctk.CTkToplevel(parent)
    detail.title(row[1])
    detail.geometry("700x600")

    ctk.CTkLabel(
        detail,
        text=row[1],
        font=("맑은 고딕", 26, "bold")
    ).pack(pady=20)

    info = ctk.CTkFrame(detail)
    info.pack(fill="both", expand=True, padx=20, pady=20)

    labels = [

        ("학교코드", row[0]),
        ("학교명", row[1]),
        ("학교급", row[2]),
        ("교육청", row[3]),
        ("지역", row[4]),
        ("주소", row[5]),
        ("홈페이지", row[6]),
        ("학생수", f"{row[11]:,}"),
        ("학급수", f"{row[12]:,}")

    ]

    for title, value in labels:

        frame = ctk.CTkFrame(info)

        frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            frame,
            text=title,
            width=120,
            anchor="w",
            font=("맑은 고딕", 13, "bold")
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            frame,
            text=value,
            anchor="w"
        ).pack(side="left", padx=10)

    ctk.CTkButton(
        detail,
        text="닫기",
        width=150,
        command=detail.destroy
    ).pack(pady=20)