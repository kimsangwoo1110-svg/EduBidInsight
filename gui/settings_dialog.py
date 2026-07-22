"""Application settings, backup operations, diagnostics, and About dialog."""

import platform
import subprocess

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.version import BUILD_DATE, __version__
from gui.ui_theme import COLORS, FONTS, card, own_child_window, primary_button, secondary_button
from services.backup_service import BackupService
from services.diagnostics_service import DiagnosticsService
from services.migration_service import MigrationService
from services.release_validator import ReleaseValidator


DEVELOPER = "김상우"
LICENSE = "EduBid Insight 개인용 라이선스"


def _git_version():
    """Return Git's display version when installed, without surfacing errors."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return "사용할 수 없음"
    return result.stdout.strip().removeprefix("git version ") or "사용할 수 없음"


def _about_details(settings):
    return (
        ("버전", __version__),
        ("빌드 날짜", BUILD_DATE),
        ("Python 버전", platform.python_version()),
        ("데이터베이스 버전", str(MigrationService(settings.database_path).current_version())),
        ("Git 버전", _git_version()),
        ("개발자", DEVELOPER),
        ("라이선스", LICENSE),
    )


def _about_content(parent, settings, compact=False):
    """Render the shared professional product identity and version panel."""
    hero = ctk.CTkFrame(parent, fg_color="transparent")
    hero.pack(fill="x", padx=24, pady=(24, 16))
    ctk.CTkLabel(
        hero,
        text="EB",
        width=64,
        height=64,
        corner_radius=14,
        fg_color=COLORS["blue"],
        text_color="white",
        font=("Segoe UI", 22, "bold"),
    ).pack(side="left")
    identity = ctk.CTkFrame(hero, fg_color="transparent")
    identity.pack(side="left", fill="x", expand=True, padx=(16, 0))
    ctk.CTkLabel(
        identity, text="EduBid Insight", font=FONTS["title"], anchor="w"
    ).pack(fill="x")
    ctk.CTkLabel(
        identity,
        text="Windows용 교육 영업 인텔리전스 플랫폼",
        font=FONTS["body"],
        text_color=COLORS["muted"],
        anchor="w",
    ).pack(fill="x", pady=(3, 0))

    details = card(parent)
    details.pack(fill="both", expand=True, padx=24, pady=(0, 16))
    for row, (label, value) in enumerate(_about_details(settings)):
        ctk.CTkLabel(
            details,
            text=label,
            font=FONTS["caption"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=row, column=0, padx=(18, 24), pady=6 if compact else 8, sticky="w")
        ctk.CTkLabel(
            details, text=value, font=FONTS["body_bold"], anchor="w"
        ).grid(row=row, column=1, padx=(0, 18), pady=6 if compact else 8, sticky="w")
    details.grid_columnconfigure(1, weight=1)
    return details


def open_about_dialog(parent, settings):
    """Open the standalone product About dialog."""
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("EduBid Insight 정보")
    window.geometry("620x570")
    window.resizable(False, False)
    window.configure(fg_color=COLORS["window"])
    _about_content(window, settings)
    primary_button(window, text="닫기", width=110, command=window.destroy).pack(
        anchor="e", padx=24, pady=(0, 22)
    )
    return window


def open_settings_dialog(parent, settings):
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("설정 — EduBid Insight")
    window.geometry("900x700")
    window.minsize(800, 620)
    window.grab_set()
    window.configure(fg_color=COLORS["window"])

    heading = ctk.CTkFrame(window, fg_color="transparent")
    heading.pack(fill="x", padx=24, pady=(20, 8))
    ctk.CTkLabel(heading, text="설정", font=FONTS["title"], anchor="w").pack(fill="x")
    ctk.CTkLabel(
        heading,
        text="일반 설정, 성능, 백업, 화면 모양을 관리합니다.",
        font=FONTS["body"],
        text_color=COLORS["muted"],
        anchor="w",
    ).pack(fill="x", pady=(3, 0))

    tabs = ctk.CTkTabview(
        window,
        fg_color=COLORS["surface"],
        border_color=COLORS["border"],
        border_width=1,
        corner_radius=10,
        segmented_button_selected_color=COLORS["blue"],
        segmented_button_selected_hover_color=COLORS["blue_hover"],
    )
    tabs.pack(fill="both", expand=True, padx=24, pady=(8, 12))
    for name in ("일반", "성능", "백업", "화면", "정보"):
        tabs.add(name)

    variables = {
        "data_directory": ctk.StringVar(value=settings.get("data_directory")),
        "backup_directory": ctk.StringVar(value=settings.get("backup_directory")),
        "window_size": ctk.StringVar(value=settings.get("window_size")),
        "auto_refresh_interval": ctk.StringVar(value=str(settings.get("auto_refresh_interval"))),
        "theme": ctk.StringVar(value={"Light": "밝게", "Dark": "어둡게", "System": "시스템"}.get(settings.get("theme"), "밝게")),
    }

    def directory_row(tab, row, title, variable):
        ctk.CTkLabel(tab, text=title, anchor="w").grid(
            row=row, column=0, padx=12, pady=10, sticky="w"
        )
        ctk.CTkEntry(tab, textvariable=variable).grid(
            row=row, column=1, padx=8, pady=10, sticky="ew"
        )

        def browse():
            selected = filedialog.askdirectory(parent=window, initialdir=variable.get())
            if selected:
                variable.set(selected)

        secondary_button(tab, text="찾아보기…", width=105, command=browse).grid(
            row=row, column=2, padx=12, pady=10
        )

    general = tabs.tab("일반")
    general.grid_columnconfigure(1, weight=1)
    directory_row(general, 0, "데이터 폴더", variables["data_directory"])
    ctk.CTkLabel(general, text="창 크기", anchor="w").grid(
        row=1, column=0, padx=12, pady=10, sticky="w"
    )
    ctk.CTkEntry(general, textvariable=variables["window_size"]).grid(
        row=1, column=1, padx=8, pady=10, sticky="ew"
    )
    ctk.CTkLabel(
        general,
        text=("이동식 모드" if settings.portable_mode else "설치 모드")
        + f"\n설정 파일: {settings.settings_path}",
        anchor="w",
        justify="left",
    ).grid(row=2, column=0, columnspan=3, padx=12, pady=10, sticky="ew")
    ctk.CTkLabel(general, text="최근 파일", anchor="w").grid(
        row=3, column=0, padx=12, pady=8, sticky="nw"
    )
    recent_text = ctk.CTkTextbox(general, height=170)
    recent_text.grid(row=3, column=1, columnspan=2, padx=8, pady=8, sticky="nsew")
    recent_text.insert("1.0", "\n".join(settings.get("recent_files", [])) or "최근 파일이 없습니다.")
    recent_text.configure(state="disabled")

    backup_tab = tabs.tab("백업")
    backup_tab.grid_columnconfigure(1, weight=1)
    directory_row(backup_tab, 0, "백업 폴더", variables["backup_directory"])
    backup_status = ctk.CTkLabel(backup_tab, text="", anchor="w")
    backup_status.grid(row=2, column=0, columnspan=3, padx=12, pady=8, sticky="ew")
    backup_list = ctk.CTkTextbox(backup_tab, height=280)
    backup_list.grid(row=3, column=0, columnspan=3, padx=12, pady=8, sticky="nsew")

    def backup_service():
        return BackupService(settings.database_path, variables["backup_directory"].get())

    def refresh_backups():
        rows = backup_service().list_backups()
        backup_list.configure(state="normal")
        backup_list.delete("1.0", "end")
        backup_list.insert("1.0", "\n".join(rows) or "백업이 없습니다.")
        backup_list.configure(state="disabled")

    def manual_backup():
        try:
            path = backup_service().create_backup()
            refresh_backups()
            backup_status.configure(text=f"생성됨: {path}")
        except Exception as error:
            messagebox.showerror("백업", str(error), parent=window)

    def restore_backup():
        path = filedialog.askopenfilename(
            parent=window, title="EduBid 백업 복원", filetypes=[("SQLite 백업", "*.db")]
        )
        if not path:
            return
        if not messagebox.askyesno(
            "백업 복원", "검증된 백업으로 현재 데이터베이스를 교체할까요?",
            parent=window,
        ):
            return
        try:
            backup_service().restore_backup(path)
            backup_status.configure(text="복원이 완료되었습니다. 프로그램을 다시 시작하세요.")
        except Exception as error:
            messagebox.showerror("복원", str(error), parent=window)

    backup_buttons = ctk.CTkFrame(backup_tab, fg_color="transparent")
    backup_buttons.grid(row=1, column=0, columnspan=3, padx=8, pady=5, sticky="w")
    primary_button(backup_buttons, text="＋  백업 생성", command=manual_backup).pack(side="left", padx=4)
    secondary_button(backup_buttons, text="백업 복원", command=restore_backup).pack(side="left", padx=4)
    secondary_button(backup_buttons, text="↻  목록 새로고침", command=refresh_backups).pack(side="left", padx=4)
    refresh_backups()

    performance = tabs.tab("성능")
    ctk.CTkLabel(performance, text="대시보드 자동 새로고침 간격(초)", anchor="w").pack(
        fill="x", padx=14, pady=(20, 5)
    )
    ctk.CTkEntry(performance, textvariable=variables["auto_refresh_interval"]).pack(
        fill="x", padx=14, pady=5
    )
    ctk.CTkLabel(
        performance, text="허용 범위: 30~86400초. 다시 시작한 뒤 적용됩니다.",
        text_color=COLORS["muted"], anchor="w",
    ).pack(fill="x", padx=14, pady=5)

    appearance = tabs.tab("화면")
    ctk.CTkLabel(appearance, text="화면 테마", anchor="w").pack(fill="x", padx=14, pady=(20, 5))
    ctk.CTkOptionMenu(
        appearance,
        variable=variables["theme"],
        values=["밝게", "어둡게", "시스템"],
        width=220,
        height=36,
        fg_color=COLORS["blue"],
        button_color=COLORS["blue_hover"],
    ).pack(anchor="w", padx=14, pady=5)
    ctk.CTkLabel(
        appearance,
        text="편안한 화면 테마를 선택하세요. 저장하면 적용됩니다.",
        font=FONTS["caption"],
        text_color=COLORS["muted"],
        anchor="w",
    ).pack(fill="x", padx=14, pady=8)

    about = tabs.tab("정보")
    _about_content(about, settings, compact=True)
    health_text = ctk.CTkTextbox(
        about,
        height=105,
        corner_radius=8,
        border_width=1,
        border_color=COLORS["border"],
        font=("Consolas", 11),
    )
    health_text.pack(fill="both", expand=True, padx=24, pady=(0, 8))
    health_text.insert("1.0", "진단 또는 배포 검증을 실행하세요.")
    health_text.configure(state="disabled")

    def show_health(text):
        health_text.configure(state="normal")
        health_text.delete("1.0", "end")
        health_text.insert("1.0", text)
        health_text.configure(state="disabled")

    def run_diagnostics():
        show_health(DiagnosticsService(settings).run().to_text())

    def validate_release():
        report = ReleaseValidator(settings).validate()
        lines = [f"배포 준비: {'예' if report.ready else '아니요'}"]
        lines.extend(
            f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}"
            for check in report.checks
        )
        show_health("\n".join(lines))

    about_buttons = ctk.CTkFrame(about, fg_color="transparent")
    about_buttons.pack(fill="x", padx=20, pady=(0, 8))
    secondary_button(about_buttons, text="진단 실행", command=run_diagnostics).pack(side="left", padx=4)
    secondary_button(about_buttons, text="배포 검증", command=validate_release).pack(side="left", padx=4)

    def save_settings():
        try:
            settings.update({
                "data_directory": variables["data_directory"].get(),
                "backup_directory": variables["backup_directory"].get(),
                "window_size": variables["window_size"].get(),
                "auto_refresh_interval": variables["auto_refresh_interval"].get(),
                "theme": {"밝게": "Light", "어둡게": "Dark", "시스템": "System"}[variables["theme"].get()],
            })
            settings.ensure_directories()
            settings.save()
            ctk.set_appearance_mode(settings.get("theme"))
        except Exception as error:
            messagebox.showerror("설정", str(error), parent=window)
            return
        messagebox.showinfo("설정", "설정을 저장했습니다. 폴더 변경은 다시 시작한 뒤 적용됩니다.", parent=window)
        window.grab_release()
        window.destroy()

    footer = ctk.CTkFrame(window, fg_color="transparent")
    footer.pack(fill="x", padx=24, pady=(0, 18))
    primary_button(footer, text="변경 저장", width=130, command=save_settings).pack(side="right", padx=(8, 0))
    secondary_button(footer, text="취소", width=100, command=window.destroy).pack(side="right")
    return window
