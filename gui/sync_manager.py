"""Synchronization source launcher and history viewer."""

import queue
import threading

import customtkinter as ctk
from tkinter import messagebox, ttk

from gui.import_wizard import (
    open_contract_import_wizard,
    open_education_office_import_wizard,
    open_g2b_import_wizard,
    open_schoolmarket_import_wizard,
)
from services.sync_service import SyncService
from gui.ui_theme import own_child_window


SYNC_HISTORY_COLUMNS = (
    ("source", "소스", 150),
    ("started_at", "시작", 185),
    ("finished_at", "종료", 185),
    ("inserted", "추가", 65),
    ("updated", "수정", 65),
    ("skipped", "건너뜀", 70),
    ("errors", "오류", 60),
    ("duration", "소요(초)", 75),
    ("status", "상태", 85),
)


def sync_history_values(history):
    """Map one synchronization history record to display values."""
    return (
        history.get("source", ""),
        history.get("started_at", ""),
        history.get("finished_at") or "-",
        int(history.get("inserted") or 0),
        int(history.get("updated") or 0),
        int(history.get("skipped") or 0),
        int(history.get("errors") or 0),
        f"{float(history.get('duration') or 0):.2f}",
        history.get("status", ""),
    )


def open_sync_manager(parent):
    """Open the synchronization manager without blocking the main GUI."""
    manager = ctk.CTkToplevel(parent)
    own_child_window(manager, parent)
    manager.title("데이터 동기화 관리")
    manager.geometry("1100x680")

    ctk.CTkLabel(
        manager,
        text="Data Sync Manager",
        font=("맑은 고딕", 25, "bold"),
    ).pack(pady=(18, 10))

    controls = ctk.CTkFrame(manager)
    controls.pack(fill="x", padx=18, pady=6)
    sources = SyncService.available_sources()
    source_selector = ctk.CTkComboBox(controls, width=260, values=sources or ["-"])
    source_selector.set(sources[0] if sources else "-")
    source_selector.pack(side="left", padx=10, pady=10)
    sync_button = ctk.CTkButton(controls, text="동기화 실행", width=130)
    sync_button.pack(side="left", padx=5, pady=10)
    refresh_button = ctk.CTkButton(controls, text="이력 새로고침", width=130)
    refresh_button.pack(side="left", padx=5, pady=10)
    import_button = ctk.CTkButton(
        controls,
        text="계약 파일 가져오기",
        width=150,
        command=lambda: open_contract_import_wizard(manager, refresh_history),
    )
    import_button.pack(side="left", padx=5, pady=10)
    ctk.CTkButton(
        controls,
        text="SchoolMarket 가져오기",
        width=165,
        command=lambda: open_schoolmarket_import_wizard(manager, refresh_history),
    ).pack(side="left", padx=5, pady=10)
    ctk.CTkButton(
        controls,
        text="G2B 가져오기",
        width=130,
        command=lambda: open_g2b_import_wizard(manager, refresh_history),
    ).pack(side="left", padx=5, pady=10)
    ctk.CTkButton(
        controls,
        text="교육청 사업",
        width=125,
        command=lambda: open_education_office_import_wizard(manager, refresh_history),
    ).pack(side="left", padx=5, pady=10)

    progress_bar = ctk.CTkProgressBar(controls, width=220)
    progress_bar.set(0)
    progress_bar.pack(side="right", padx=10, pady=10)
    progress_label = ctk.CTkLabel(manager, text="동기화 소스를 선택하세요.", anchor="w")
    progress_label.pack(fill="x", padx=22, pady=(2, 5))

    history_tree = ttk.Treeview(
        manager,
        columns=tuple(column[0] for column in SYNC_HISTORY_COLUMNS),
        show="headings",
        height=19,
    )
    for column, heading, width in SYNC_HISTORY_COLUMNS:
        history_tree.heading(column, text=heading)
        history_tree.column(column, width=width, anchor="center")
    history_tree.tag_configure("SUCCESS", foreground="#2E8B57")
    history_tree.tag_configure("PARTIAL", foreground="#D97706")
    history_tree.tag_configure("FAILED", foreground="#C2410C")
    history_tree.tag_configure("RUNNING", foreground="#1F6AA5")
    history_tree.pack(fill="both", expand=True, padx=18, pady=8)

    event_queue = queue.Queue()
    running = {"value": False}

    def refresh_history():
        history_tree.delete(*history_tree.get_children())
        for history in SyncService.history():
            history_tree.insert(
                "",
                "end",
                iid=f"history-{history['id']}",
                tags=(history["status"],),
                values=sync_history_values(history),
            )

    def report_progress(progress):
        event_queue.put(("progress", progress))

    def worker(source):
        try:
            event_queue.put(("complete", SyncService.synchronize(source, report_progress)))
        except Exception as error:
            event_queue.put(("error", error))

    def finish_run():
        running["value"] = False
        sync_button.configure(state="normal")
        source_selector.configure(state="normal")
        refresh_history()

    def process_events():
        finished = False
        while True:
            try:
                event_type, payload = event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "progress":
                processed = payload.get("processed", payload.get("downloaded", 0))
                total = payload.get("total", 0)
                if total:
                    progress_bar.set(min(processed / total, 1))
                    progress_label.configure(text=f"{processed:,} / {total:,}건 처리")
                else:
                    progress_label.configure(text=f"{processed:,}건 처리")
            elif event_type == "complete":
                finished = True
                finish_run()
                progress_bar.set(1)
                progress_label.configure(
                    text=(
                        f"완료 · 추가 {payload['inserted']:,} · 수정 {payload['updated']:,} · "
                        f"건너뜀 {payload['skipped']:,} · 오류 {payload['errors']:,}"
                    )
                )
            elif event_type == "error":
                finished = True
                finish_run()
                progress_label.configure(text="동기화 실패")
                messagebox.showerror("동기화 오류", str(payload), parent=manager)

        if running["value"] and not finished and manager.winfo_exists():
            manager.after(100, process_events)

    def start_sync():
        source = source_selector.get()
        if source not in SyncService.available_sources():
            messagebox.showinfo("동기화", "유효한 소스를 선택하세요.", parent=manager)
            return
        running["value"] = True
        sync_button.configure(state="disabled")
        source_selector.configure(state="disabled")
        progress_bar.set(0)
        progress_label.configure(text=f"{source} 동기화를 시작합니다...")
        refresh_history()
        threading.Thread(target=worker, args=(source,), daemon=True).start()
        manager.after(100, process_events)

    def close_manager():
        if running["value"]:
            messagebox.showinfo(
                "동기화 진행 중", "동기화가 끝난 후 창을 닫아주세요.", parent=manager
            )
            return
        manager.destroy()

    sync_button.configure(command=start_sync)
    refresh_button.configure(command=refresh_history)
    manager.protocol("WM_DELETE_WINDOW", close_manager)
    refresh_history()
    return manager
