"""Primary application shell and presentation-only navigation."""

import queue
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from core.app_settings import get_app_settings
from core.logger import get_logger
from core.resources import apply_window_icon
from core.version import __version__
from gui.action_center import open_action_center
from gui.data_source_manager import open_data_source_manager
from gui.opportunity_dashboard import open_opportunity_dashboard
from gui.report_center import open_report_center
from gui.rule_manager import open_rule_manager
from gui.school_window import open_school_window
from gui.settings_dialog import open_settings_dialog
from gui.sync_manager import open_sync_manager
from gui.today_dashboard import build_today_dashboard
from gui.ui_theme import COLORS, FONTS, configure_ttk_styles, own_child_window
from services.backup_service import BackupService
from services.sync_service import SyncService


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def run(settings=None):
    settings = settings or get_app_settings()
    ctk.set_appearance_mode(settings.get("theme"))
    app = ctk.CTk(fg_color=COLORS["window"])
    app.title(f"EduBid Insight v{__version__}")
    apply_window_icon(app)
    app.geometry(settings.get("window_size"))
    app.minsize(1180, 720)
    configure_ttk_styles(app)

    # The bottom status bar is packed first so it remains visible at every size.
    status_bar = ctk.CTkFrame(
        app,
        height=30,
        corner_radius=0,
        fg_color=COLORS["surface"],
        border_color=COLORS["border"],
        border_width=1,
    )
    status_bar.pack(side="bottom", fill="x")
    status_bar.pack_propagate(False)

    shell = ctk.CTkFrame(app, fg_color="transparent", corner_radius=0)
    shell.pack(fill="both", expand=True)
    sidebar = ctk.CTkScrollableFrame(
        shell,
        width=250,
        corner_radius=0,
        fg_color=COLORS["sidebar"],
        scrollbar_button_color=COLORS["border"],
        scrollbar_button_hover_color=COLORS["muted"],
    )
    sidebar.pack(side="left", fill="y")
    home = ctk.CTkFrame(shell, fg_color="transparent", corner_radius=0)
    home.pack(side="right", fill="both", expand=True)
    # Keep wide dashboard children inside the remaining shell viewport.
    home.pack_propagate(False)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.pack(fill="x", padx=18, pady=(22, 14))
    logo = ctk.CTkLabel(
        brand,
        text="EB",
        width=42,
        height=42,
        corner_radius=9,
        fg_color=COLORS["blue"],
        text_color="white",
        font=("Segoe UI", 16, "bold"),
    )
    logo.pack(side="left")
    brand_text = ctk.CTkFrame(brand, fg_color="transparent")
    brand_text.pack(side="left", fill="x", expand=True, padx=(11, 0))
    ctk.CTkLabel(
        brand_text, text="EduBid Insight", font=FONTS["section"], anchor="w"
    ).pack(fill="x")
    ctk.CTkLabel(
        brand_text,
        text="Education Sales Intelligence",
        font=FONTS["caption"],
        text_color=COLORS["muted"],
        anchor="w",
    ).pack(fill="x")

    operation_status = ctk.CTkLabel(
        sidebar,
        text="Ready",
        font=FONTS["caption"],
        text_color=COLORS["muted"],
        anchor="w",
    )
    operation_status.pack(fill="x", padx=22, pady=(0, 8))
    action_buttons = []

    def set_action_buttons_state(state):
        for button in action_buttons:
            button.configure(state=state)

    def update_school_data():
        set_action_buttons_state("disabled")
        operation_status.configure(text="Updating school data…")

        progress_dialog = ctk.CTkToplevel(app)
        own_child_window(progress_dialog, app)
        progress_dialog.title("학교 데이터 업데이트")
        progress_dialog.geometry("440x190")
        progress_dialog.grab_set()
        progress_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        progress_label = ctk.CTkLabel(
            progress_dialog,
            text="NEIS 데이터 다운로드를 시작하는 중입니다...",
            font=FONTS["body"],
        )
        progress_label.pack(padx=24, pady=(36, 14))
        progress_bar = ctk.CTkProgressBar(
            progress_dialog,
            width=360,
            height=9,
            progress_color=COLORS["blue"],
        )
        progress_bar.set(0)
        progress_bar.pack(padx=24, pady=8)
        event_queue = queue.Queue()

        def report_progress(progress):
            event_queue.put(("progress", progress))

        def download_worker():
            try:
                result = SyncService.synchronize(
                    SyncService.DEFAULT_SCHOOL_SOURCE,
                    progress_callback=report_progress,
                )
                event_queue.put(("complete", result["inserted"] + result["updated"]))
            except Exception as error:
                event_queue.put(("error", error))

        def close_progress_dialog():
            if progress_dialog.winfo_exists():
                progress_dialog.grab_release()
                progress_dialog.destroy()

        def process_download_events():
            completed = False
            while True:
                try:
                    event_type, payload = event_queue.get_nowait()
                except queue.Empty:
                    break
                if event_type == "progress":
                    downloaded = payload.get("downloaded", payload.get("processed", 0))
                    total = payload.get("total", 0)
                    page = payload.get("page", 1)
                    if total:
                        progress_bar.set(min(downloaded / total, 1))
                        progress_label.configure(
                            text=f"페이지 {page} | {downloaded:,} / {total:,}개 학교 처리"
                        )
                    else:
                        progress_label.configure(text=f"페이지 {page} | {downloaded:,}개 학교 처리")
                elif event_type == "complete":
                    completed = True
                    close_progress_dialog()
                    set_action_buttons_state("normal")
                    operation_status.configure(text=f"Updated · {payload:,} schools")
                    messagebox.showinfo(
                        "완료", f"{payload:,}개 학교 데이터를 업데이트했습니다.", parent=app
                    )
                elif event_type == "error":
                    completed = True
                    close_progress_dialog()
                    set_action_buttons_state("normal")
                    operation_status.configure(text="Update failed")
                    messagebox.showerror("오류", str(payload), parent=app)
            if not completed:
                app.after(100, process_download_events)

        threading.Thread(target=download_worker, daemon=True).start()
        app.after(100, process_download_events)

    def section_label(text):
        ctk.CTkLabel(
            sidebar,
            text=text,
            font=("Segoe UI", 10, "bold"),
            text_color=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", padx=22, pady=(12, 4))

    def nav_button(text, command, icon="", selected=False):
        button = ctk.CTkButton(
            sidebar,
            text=f"{icon}  {text}" if icon else text,
            command=command,
            height=44,
            corner_radius=7,
            anchor="w",
            font=FONTS["body"],
            fg_color=COLORS["blue_tint"] if selected else "transparent",
            hover_color=COLORS["blue_tint"],
            text_color=COLORS["blue"] if selected else COLORS["text"],
            border_width=0,
        )
        button.pack(fill="x", padx=12, pady=1)
        action_buttons.append(button)
        return button

    section_label("대시보드\nDASHBOARD")
    nav_button("대시보드\nDashboard", lambda: home.tkraise(), "▦", selected=True)

    section_label("학교 관리\nSCHOOL")
    nav_button("학교 검색\nSchool Search", lambda: open_school_window(app), "⌕")
    # School 360 opens the existing school workspace; no new behavior is introduced.
    nav_button("학교 360\nSchool 360", lambda: open_school_window(app), "◎")

    section_label("데이터 관리\nDATA")
    nav_button("학교 업데이트\nSchool Update", update_school_data, "↻")
    nav_button("교육청\nEducation Office", lambda: print("교육청 검색"), "▤")
    nav_button("나라장터\nG2B", lambda: print("나라장터 검색"), "▥")
    nav_button("AI 검색\nAI Search", lambda: open_opportunity_dashboard(app), "✦")
    nav_button("데이터 소스\nData Sources", lambda: open_data_source_manager(app), "◫")
    nav_button("동기화 관리\nSync Manager", lambda: open_sync_manager(app), "⇄")

    section_label("영업 관리\nSALES")
    nav_button("CRM 액션 센터\nCRM Action Center", lambda: open_action_center(app), "✓")
    nav_button("보고서\nReports", lambda: open_report_center(app), "▧")

    section_label("시스템 관리\nSYSTEM")
    nav_button("규칙 관리\nRule Management", lambda: open_rule_manager(app), "◇")
    nav_button("설정\nSettings", lambda: open_settings_dialog(app, settings), "⚙")

    ctk.CTkLabel(
        sidebar,
        text=f"Personal Edition  ·  v{__version__}",
        font=FONTS["caption"],
        text_color=COLORS["muted"],
    ).pack(pady=(18, 14))

    status_items = (
        f"Version  {__version__}",
        f"Database  {Path(settings.database_path).name} · Connected",
        "Current User  Local",
    )
    for item in status_items:
        ctk.CTkLabel(
            status_bar,
            text=item,
            font=FONTS["caption"],
            text_color=COLORS["muted"],
        ).pack(side="left", padx=(14, 6))
        ctk.CTkLabel(status_bar, text="│", text_color=COLORS["border"]).pack(side="left")
    last_refresh = ctk.CTkLabel(
        status_bar,
        text="Last Refresh  —",
        font=FONTS["caption"],
        text_color=COLORS["muted"],
    )
    last_refresh.pack(side="right", padx=14)

    def dashboard_refreshed(snapshot):
        generated = str(snapshot.get("generated_at") or "")
        last_refresh.configure(text=f"Last Refresh  {generated[11:19] or '—'}")

    build_today_dashboard(
        home,
        refresh_interval_ms=int(settings.get("auto_refresh_interval")) * 1000,
        on_refresh=dashboard_refreshed,
    )

    def close_application():
        logger = get_logger("shutdown")
        try:
            geometry = app.geometry().split("+", 1)[0]
            settings.set("window_size", geometry).save()
        except Exception:
            logger.exception("failed to save settings on exit")
        try:
            BackupService(settings.database_path, settings.backup_directory).automatic_backup()
        except Exception:
            logger.exception("automatic exit backup failed")
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", close_application)
    app.mainloop()
