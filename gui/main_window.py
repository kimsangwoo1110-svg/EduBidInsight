import queue
import threading

import customtkinter as ctk
from tkinter import messagebox

from core.version import __version__
from core.app_settings import get_app_settings
from core.logger import get_logger
from gui.data_source_manager import open_data_source_manager
from gui.rule_manager import open_rule_manager
from gui.school_window import open_school_window
from gui.opportunity_dashboard import open_opportunity_dashboard
from gui.action_center import open_action_center
from gui.today_dashboard import build_today_dashboard
from gui.report_center import open_report_center
from gui.settings_dialog import open_settings_dialog
from gui.sync_manager import open_sync_manager
from services.sync_service import SyncService
from services.backup_service import BackupService


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def run(settings=None):
    settings = settings or get_app_settings()
    ctk.set_appearance_mode(settings.get("theme"))
    app = ctk.CTk()
    app.title(f"EduBid Insight v{__version__}")
    app.geometry(settings.get("window_size"))
    app.minsize(1180, 720)

    shell = ctk.CTkFrame(app, fg_color="transparent")
    shell.pack(fill="both", expand=True)
    sidebar = ctk.CTkScrollableFrame(shell, width=330, corner_radius=0)
    sidebar.pack(side="left", fill="y")
    home = ctk.CTkFrame(shell, fg_color="transparent")
    home.pack(side="right", fill="both", expand=True)

    title = ctk.CTkLabel(
        sidebar,
        text="EduBid Insight",
        font=("맑은 고딕", 32, "bold"),
    )
    title.pack(pady=(40, 10))

    subtitle = ctk.CTkLabel(
        sidebar,
        text="학교 교육사업 통합 검색 플랫폼",
        font=("맑은 고딕", 15),
    )
    subtitle.pack(pady=(0, 30))

    status = ctk.CTkLabel(sidebar, text="학교 데이터를 업데이트하세요")
    status.pack(pady=10)

    action_buttons = []

    def set_action_buttons_state(state):
        for button in action_buttons:
            button.configure(state=state)

    def update_school_data():
        set_action_buttons_state("disabled")
        status.configure(text="학교 데이터를 업데이트하는 중입니다...")

        progress_dialog = ctk.CTkToplevel(app)
        progress_dialog.title("학교 데이터 업데이트")
        progress_dialog.geometry("420x170")
        progress_dialog.transient(app)
        progress_dialog.grab_set()
        progress_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        progress_label = ctk.CTkLabel(
            progress_dialog,
            text="NEIS 데이터 다운로드를 시작하는 중입니다...",
        )
        progress_label.pack(padx=20, pady=(30, 12))

        progress_bar = ctk.CTkProgressBar(progress_dialog, width=340)
        progress_bar.set(0)
        progress_bar.pack(padx=20, pady=8)

        event_queue = queue.Queue()

        def report_progress(progress):
            event_queue.put(("progress", progress))

        def download_worker():
            try:
                result = SyncService.synchronize(
                    SyncService.DEFAULT_SCHOOL_SOURCE,
                    progress_callback=report_progress,
                )
                count = result["inserted"] + result["updated"]
                event_queue.put(("complete", count))
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
                        progress_label.configure(
                            text=f"페이지 {page} | {downloaded:,}개 학교 처리"
                        )
                elif event_type == "complete":
                    completed = True
                    close_progress_dialog()
                    set_action_buttons_state("normal")
                    status.configure(text=f"업데이트 완료 : {payload:,}개 학교")
                    messagebox.showinfo(
                        "완료",
                        f"{payload:,}개 학교 데이터를 업데이트했습니다.",
                        parent=app,
                    )
                elif event_type == "error":
                    completed = True
                    close_progress_dialog()
                    set_action_buttons_state("normal")
                    status.configure(text="업데이트 실패")
                    messagebox.showerror("오류", str(payload), parent=app)

            if not completed:
                app.after(100, process_download_events)

        threading.Thread(target=download_worker, daemon=True).start()
        app.after(100, process_download_events)

    update_btn = ctk.CTkButton(
        sidebar,
        text="학교 데이터 업데이트",
        width=320,
        height=45,
        command=update_school_data,
    )
    update_btn.pack(pady=10)
    action_buttons.append(update_btn)

    school_btn = ctk.CTkButton(
        sidebar,
        text="학교 검색",
        width=320,
        height=45,
        command=lambda: open_school_window(app),
    )
    school_btn.pack(pady=10)
    action_buttons.append(school_btn)

    rule_btn = ctk.CTkButton(
        sidebar,
        text="규칙 관리",
        width=320,
        height=45,
        command=lambda: open_rule_manager(app),
    )
    rule_btn.pack(pady=10)
    action_buttons.append(rule_btn)

    sync_btn = ctk.CTkButton(
        sidebar,
        text="데이터 동기화 관리",
        width=320,
        height=45,
        command=lambda: open_sync_manager(app),
    )
    sync_btn.pack(pady=10)
    action_buttons.append(sync_btn)

    source_manager_btn = ctk.CTkButton(
        sidebar,
        text="데이터 소스 관리",
        width=320,
        height=45,
        command=lambda: open_data_source_manager(app),
    )
    source_manager_btn.pack(pady=10)
    action_buttons.append(source_manager_btn)

    office_btn = ctk.CTkButton(
        sidebar,
        text="교육청 검색",
        width=320,
        height=45,
        command=lambda: print("교육청 검색"),
    )
    office_btn.pack(pady=10)
    action_buttons.append(office_btn)

    g2b_btn = ctk.CTkButton(
        sidebar,
        text="나라장터 검색",
        width=320,
        height=45,
        command=lambda: print("나라장터 검색"),
    )
    g2b_btn.pack(pady=10)
    action_buttons.append(g2b_btn)

    ai_btn = ctk.CTkButton(
        sidebar,
        text="AI 검색",
        width=320,
        height=45,
        command=lambda: open_opportunity_dashboard(app),
    )
    ai_btn.pack(pady=10)
    action_buttons.append(ai_btn)

    action_center_btn = ctk.CTkButton(
        sidebar,
        text="CRM Action Center",
        width=320,
        height=45,
        command=lambda: open_action_center(app),
    )
    action_center_btn.pack(pady=10)
    action_buttons.append(action_center_btn)

    report_center_btn = ctk.CTkButton(
        sidebar,
        text="Report Center",
        width=320,
        height=45,
        command=lambda: open_report_center(app),
    )
    report_center_btn.pack(pady=10)
    action_buttons.append(report_center_btn)

    settings_btn = ctk.CTkButton(
        sidebar,
        text="Settings",
        width=320,
        height=45,
        command=lambda: open_settings_dialog(app, settings),
    )
    settings_btn.pack(pady=10)
    action_buttons.append(settings_btn)

    footer = ctk.CTkLabel(
        sidebar,
        text=f"EduBid Insight v{__version__} | Developer : 김상우",
        font=("맑은 고딕", 11),
        text_color="gray",
    )
    footer.pack(side="bottom", pady=10)

    build_today_dashboard(
        home,
        refresh_interval_ms=int(settings.get("auto_refresh_interval")) * 1000,
    )

    def close_application():
        logger = get_logger("shutdown")
        try:
            geometry = app.geometry().split("+", 1)[0]
            settings.set("window_size", geometry).save()
        except Exception:
            logger.exception("failed to save settings on exit")
        try:
            BackupService(
                settings.database_path, settings.backup_directory
            ).automatic_backup()
        except Exception:
            logger.exception("automatic exit backup failed")
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", close_application)
    app.mainloop()
