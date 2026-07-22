"""Excel Import Center launcher, template access, and audit history."""

import customtkinter as ctk
from tkinter import ttk

from gui.import_wizard import (
    open_crm_import_wizard, open_education_office_import_wizard,
    open_g2b_import_wizard, open_school_import_wizard,
    open_schoolmarket_import_wizard,
)
from gui.template_center import open_template_center
from gui.ui_theme import COLORS, FONTS, card, create_empty_state, own_child_window, primary_button, secondary_button, stripe_treeview, update_empty_state
from services.import_center import ImportRunStore, PROFILES


IMPORT_HISTORY_COLUMNS = (
    ("date", "날짜\nDate", 185), ("source", "소스\nSource", 145),
    ("filename", "파일\nFile", 220), ("rows", "행\nRows", 80),
    ("success", "성공\nSuccess", 85), ("failed", "실패\nFailed", 80),
    ("duration", "소요 시간\nDuration", 100), ("status", "상태\nStatus", 100),
)


def import_history_values(history):
    """Retain the legacy display mapper used by integrations and tests."""
    return (
        history.get("imported_at", ""), history.get("source_type", ""),
        history.get("filename", ""), history.get("result", ""),
        int(history.get("imported_rows") or 0),
    )


def import_run_values(history):
    return (
        str(history.get("date", "")).replace("T", " ")[:19], history.get("source", ""),
        history.get("filename", ""), int(history.get("rows", 0) or 0),
        int(history.get("success", 0) or 0), int(history.get("failed", 0) or 0),
        f"{float(history.get('duration', 0) or 0):.2f}s", history.get("status", ""),
    )


def open_data_source_manager(parent):
    manager = ctk.CTkToplevel(parent)
    own_child_window(manager, parent)
    manager.title("Excel 가져오기 센터 · Excel Import Center")
    manager.geometry("1180x760")
    manager.minsize(1020, 680)
    history_store = ImportRunStore()

    title_row = ctk.CTkFrame(manager, fg_color="transparent")
    title_row.pack(fill="x", padx=24, pady=(20, 10))
    title_text = ctk.CTkFrame(title_row, fg_color="transparent")
    title_text.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(title_text, text="Excel 가져오기 센터", font=FONTS["title"], anchor="w").pack(fill="x")
    ctk.CTkLabel(title_text, text="Excel Import Center  ·  공식 템플릿과 검증된 가져오기 흐름", font=FONTS["body"], text_color=COLORS["muted"], anchor="w").pack(fill="x")
    secondary_button(title_row, text="템플릿 센터  Template Center", width=220, command=lambda: open_template_center(manager)).pack(side="right", padx=(12, 0))

    launch_panel = card(manager)
    launch_panel.pack(fill="x", padx=24, pady=8)
    ctk.CTkLabel(launch_panel, text="가져오기 시작 · Start Import", font=FONTS["section"], anchor="w").pack(fill="x", padx=16, pady=(14, 8))
    button_row = ctk.CTkFrame(launch_panel, fg_color="transparent")
    button_row.pack(fill="x", padx=10, pady=(0, 14))
    launchers = (
        ("school", open_school_import_wizard),
        ("education_office", open_education_office_import_wizard),
        ("schoolmarket", open_schoolmarket_import_wizard),
        ("g2b", open_g2b_import_wizard),
        ("crm", open_crm_import_wizard),
    )

    def refresh_history():
        history_tree.delete(*history_tree.get_children())
        for index, history in enumerate(history_store.combined_history()):
            history_tree.insert("", "end", iid=f"import-run-{index}", tags=(history.get("status", ""),), values=import_run_values(history))
        stripe_treeview(history_tree); update_empty_state(history_tree, history_empty)

    for index, (key, launcher) in enumerate(launchers):
        profile = PROFILES[key]
        button = primary_button(button_row, text=profile.title, height=58, command=lambda selected=launcher: selected(manager, refresh_history))
        button.grid(row=0, column=index, padx=5, sticky="ew")
        button_row.grid_columnconfigure(index, weight=1, uniform="import-profile")

    history_header = ctk.CTkFrame(manager, fg_color="transparent")
    history_header.pack(fill="x", padx=24, pady=(14, 4))
    ctk.CTkLabel(history_header, text="가져오기 이력 · Import History", font=FONTS["section"], anchor="w").pack(side="left")
    secondary_button(history_header, text="새로고침  Refresh", width=145, command=refresh_history).pack(side="right")

    table_panel = ctk.CTkFrame(manager, fg_color="transparent")
    table_panel.pack(fill="both", expand=True, padx=24, pady=(4, 20))
    history_tree = ttk.Treeview(
        table_panel,
        columns=tuple(column[0] for column in IMPORT_HISTORY_COLUMNS),
        show="headings",
        height=15,
    )
    history_empty = create_empty_state(
        table_panel, "▦\n가져오기 이력이 없습니다.\nNo import history yet."
    )
    ybar = ttk.Scrollbar(table_panel, orient="vertical", command=history_tree.yview)
    history_tree.configure(yscrollcommand=ybar.set)
    for column, heading, width in IMPORT_HISTORY_COLUMNS:
        history_tree.heading(column, text=heading); history_tree.column(column, width=width, anchor="center")
    history_tree.tag_configure("SUCCESS", foreground="#47765F")
    history_tree.tag_configure("PARTIAL", foreground="#9A6E3E")
    history_tree.tag_configure("FAILED", foreground="#8B4545")
    history_tree.grid(row=0, column=0, sticky="nsew")
    ybar.grid(row=0, column=1, sticky="ns")
    table_panel.grid_rowconfigure(0, weight=1); table_panel.grid_columnconfigure(0, weight=1)

    refresh_history()
    return manager
