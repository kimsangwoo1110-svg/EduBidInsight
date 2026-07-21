"""Data-source import launcher and history viewer."""

import customtkinter as ctk
from tkinter import ttk

from gui.import_wizard import open_contract_import_wizard
from services.import_history_service import ImportHistoryService


IMPORT_HISTORY_COLUMNS = (
    ("imported_at", "가져온 시각", 200),
    ("source_type", "소스 유형", 180),
    ("filename", "파일명", 260),
    ("result", "결과", 110),
    ("imported_rows", "가져온 행", 100),
)


def import_history_values(history):
    """Map one import-history record to display values."""
    return (
        history.get("imported_at", ""),
        history.get("source_type", ""),
        history.get("filename", ""),
        history.get("result", ""),
        int(history.get("imported_rows") or 0),
    )


def open_data_source_manager(parent):
    """Open the Data Source Manager without blocking the main GUI."""
    manager = ctk.CTkToplevel(parent)
    manager.title("데이터 소스 관리")
    manager.geometry("950x620")
    manager.transient(parent)

    ctk.CTkLabel(
        manager,
        text="Data Source Manager",
        font=("맑은 고딕", 25, "bold"),
    ).pack(pady=(18, 10))

    controls = ctk.CTkFrame(manager)
    controls.pack(fill="x", padx=18, pady=6)
    ctk.CTkLabel(controls, text="파일 기반 데이터 소스").pack(
        side="left", padx=12, pady=12
    )

    history_tree = ttk.Treeview(
        manager,
        columns=tuple(column[0] for column in IMPORT_HISTORY_COLUMNS),
        show="headings",
        height=20,
    )
    for column, heading, width in IMPORT_HISTORY_COLUMNS:
        history_tree.heading(column, text=heading)
        history_tree.column(column, width=width, anchor="center")
    history_tree.tag_configure("SUCCESS", foreground="#2E8B57")
    history_tree.tag_configure("PARTIAL", foreground="#D97706")
    history_tree.tag_configure("FAILED", foreground="#C2410C")
    history_tree.pack(fill="both", expand=True, padx=18, pady=8)

    def refresh_history():
        history_tree.delete(*history_tree.get_children())
        for history in ImportHistoryService.history():
            history_tree.insert(
                "",
                "end",
                iid=f"import-history-{history['id']}",
                tags=(history["result"],),
                values=import_history_values(history),
            )

    ctk.CTkButton(
        controls,
        text="계약 파일 가져오기",
        width=155,
        command=lambda: open_contract_import_wizard(manager, refresh_history),
    ).pack(side="left", padx=5, pady=10)
    ctk.CTkButton(
        controls,
        text="이력 새로고침",
        width=130,
        command=refresh_history,
    ).pack(side="left", padx=5, pady=10)

    refresh_history()
    return manager
