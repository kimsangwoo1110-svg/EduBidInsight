"""Official workbook template download center."""

import shutil

import customtkinter as ctk
from tkinter import filedialog, messagebox

from gui.ui_theme import COLORS, FONTS, card, own_child_window, primary_button, secondary_button
from services.import_center import PROFILES, template_path


def open_template_center(parent):
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("템플릿 센터")
    window.geometry("760x610")
    window.minsize(680, 520)

    ctk.CTkLabel(window, text="템플릿 센터", font=FONTS["title"], anchor="w").pack(
        fill="x", padx=24, pady=(22, 2)
    )
    ctk.CTkLabel(
        window,
        text="공식 양식을 내려받아 데이터 오류를 줄이세요.",
        font=FONTS["body"], text_color=COLORS["muted"], anchor="w",
    ).pack(fill="x", padx=24, pady=(0, 16))

    content = ctk.CTkScrollableFrame(window, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=18, pady=(0, 12))

    def download(profile):
        source = template_path(profile.key)
        if not source.is_file():
            messagebox.showerror("템플릿 오류", f"번들 템플릿을 찾을 수 없습니다.\n{source}", parent=window)
            return
        destination = filedialog.asksaveasfilename(
            parent=window, title="템플릿 저장",
            defaultextension=".xlsx", initialfile=profile.template_name,
            filetypes=(("Excel Workbook", "*.xlsx"),),
        )
        if not destination:
            return
        try:
            shutil.copyfile(source, destination)
        except OSError as error:
            messagebox.showerror("저장 오류", str(error), parent=window)
            return
        messagebox.showinfo("저장 완료", f"공식 템플릿을 저장했습니다.\n{destination}", parent=window)

    for profile in PROFILES.values():
        row = card(content)
        row.pack(fill="x", padx=6, pady=6)
        icon = ctk.CTkLabel(
            row, text="▦", width=44, height=44, corner_radius=8,
            fg_color=COLORS["blue_tint"], text_color=COLORS["blue"],
            font=("Segoe UI Symbol", 20),
        )
        icon.pack(side="left", padx=(14, 12), pady=12)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(text, text=profile.title, font=FONTS["body_bold"], anchor="w").pack(fill="x")
        ctk.CTkLabel(text, text="공식 Excel 양식", font=FONTS["caption"], text_color=COLORS["muted"], anchor="w").pack(fill="x")
        primary_button(row, text="다운로드", width=125, command=lambda selected=profile: download(selected)).pack(side="right", padx=14)

    secondary_button(window, text="닫기", width=110, command=window.destroy).pack(
        anchor="e", padx=24, pady=(0, 18)
    )
    return window
