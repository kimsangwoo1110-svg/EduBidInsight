"""Application settings, backup operations, diagnostics, and About dialog."""

import platform
import sys
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.version import BUILD_DATE, __version__
from services.backup_service import BackupService
from services.diagnostics_service import DiagnosticsService
from services.migration_service import MigrationService
from services.release_validator import ReleaseValidator


def open_about_dialog(parent, settings):
    """Open a compact standalone About dialog for menu integrations."""
    window = ctk.CTkToplevel(parent)
    window.title("About EduBid Insight Personal")
    window.geometry("480x330")
    window.resizable(False, False)
    window.transient(parent)
    version = MigrationService(settings.database_path).current_version()
    ctk.CTkLabel(
        window,
        text=(
            f"EduBid Insight Personal\n\nVersion: {__version__}\n"
            f"Python: {platform.python_version()}\nDatabase schema: {version}\n"
            f"Build date: {BUILD_DATE}\n"
            f"Mode: {'Portable' if settings.portable_mode else 'Installed'}"
        ),
        font=("맑은 고딕", 15),
        justify="left",
    ).pack(fill="both", expand=True, padx=28, pady=24)
    ctk.CTkButton(window, text="Close", width=100, command=window.destroy).pack(pady=(0, 20))
    return window


def open_settings_dialog(parent, settings):
    window = ctk.CTkToplevel(parent)
    window.title("Settings — EduBid Insight Personal")
    window.geometry("820x650")
    window.minsize(720, 560)
    window.transient(parent)
    window.grab_set()

    tabs = ctk.CTkTabview(window)
    tabs.pack(fill="both", expand=True, padx=14, pady=(14, 8))
    for name in ("General", "Backup", "Performance", "Appearance", "About"):
        tabs.add(name)

    variables = {
        "data_directory": ctk.StringVar(value=settings.get("data_directory")),
        "backup_directory": ctk.StringVar(value=settings.get("backup_directory")),
        "window_size": ctk.StringVar(value=settings.get("window_size")),
        "auto_refresh_interval": ctk.StringVar(value=str(settings.get("auto_refresh_interval"))),
        "theme": ctk.StringVar(value=settings.get("theme")),
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

        ctk.CTkButton(tab, text="Browse", width=80, command=browse).grid(
            row=row, column=2, padx=12, pady=10
        )

    general = tabs.tab("General")
    general.grid_columnconfigure(1, weight=1)
    directory_row(general, 0, "Data directory", variables["data_directory"])
    ctk.CTkLabel(general, text="Window size", anchor="w").grid(
        row=1, column=0, padx=12, pady=10, sticky="w"
    )
    ctk.CTkEntry(general, textvariable=variables["window_size"]).grid(
        row=1, column=1, padx=8, pady=10, sticky="ew"
    )
    ctk.CTkLabel(
        general,
        text=("Portable mode" if settings.portable_mode else "Installed mode")
        + f"\nSettings: {settings.settings_path}",
        anchor="w",
        justify="left",
    ).grid(row=2, column=0, columnspan=3, padx=12, pady=10, sticky="ew")
    ctk.CTkLabel(general, text="Recent files", anchor="w").grid(
        row=3, column=0, padx=12, pady=8, sticky="nw"
    )
    recent_text = ctk.CTkTextbox(general, height=170)
    recent_text.grid(row=3, column=1, columnspan=2, padx=8, pady=8, sticky="nsew")
    recent_text.insert("1.0", "\n".join(settings.get("recent_files", [])) or "No recent files")
    recent_text.configure(state="disabled")

    backup_tab = tabs.tab("Backup")
    backup_tab.grid_columnconfigure(1, weight=1)
    directory_row(backup_tab, 0, "Backup directory", variables["backup_directory"])
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
        backup_list.insert("1.0", "\n".join(rows) or "No backups")
        backup_list.configure(state="disabled")

    def manual_backup():
        try:
            path = backup_service().create_backup()
            refresh_backups()
            backup_status.configure(text=f"Created: {path}")
        except Exception as error:
            messagebox.showerror("Backup", str(error), parent=window)

    def restore_backup():
        path = filedialog.askopenfilename(
            parent=window, title="Restore EduBid backup", filetypes=[("SQLite backup", "*.db")]
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Restore backup", "Replace the current database with this verified backup?",
            parent=window,
        ):
            return
        try:
            backup_service().restore_backup(path)
            backup_status.configure(text="Restore complete. Restart the application.")
        except Exception as error:
            messagebox.showerror("Restore", str(error), parent=window)

    backup_buttons = ctk.CTkFrame(backup_tab, fg_color="transparent")
    backup_buttons.grid(row=1, column=0, columnspan=3, padx=8, pady=5, sticky="w")
    ctk.CTkButton(backup_buttons, text="Create Backup", command=manual_backup).pack(side="left", padx=4)
    ctk.CTkButton(backup_buttons, text="Restore Backup", command=restore_backup).pack(side="left", padx=4)
    ctk.CTkButton(backup_buttons, text="Refresh List", command=refresh_backups).pack(side="left", padx=4)
    refresh_backups()

    performance = tabs.tab("Performance")
    ctk.CTkLabel(performance, text="Dashboard auto refresh interval (seconds)", anchor="w").pack(
        fill="x", padx=14, pady=(20, 5)
    )
    ctk.CTkEntry(performance, textvariable=variables["auto_refresh_interval"]).pack(
        fill="x", padx=14, pady=5
    )
    ctk.CTkLabel(
        performance, text="Allowed range: 30–86400 seconds. Changes apply after restart.",
        text_color="gray", anchor="w",
    ).pack(fill="x", padx=14, pady=5)

    appearance = tabs.tab("Appearance")
    ctk.CTkLabel(appearance, text="Theme", anchor="w").pack(fill="x", padx=14, pady=(20, 5))
    ctk.CTkOptionMenu(
        appearance, variable=variables["theme"], values=["Light", "Dark", "System"]
    ).pack(anchor="w", padx=14, pady=5)

    about = tabs.tab("About")
    database_version = MigrationService(settings.database_path).current_version()
    about_text = (
        f"EduBid Insight Personal\n\n"
        f"Version: {__version__}\n"
        f"Python: {platform.python_version()} ({sys.platform})\n"
        f"Database schema: {database_version}\n"
        f"Build date: {BUILD_DATE}\n"
        f"Mode: {'Portable' if settings.portable_mode else 'Installed'}"
    )
    ctk.CTkLabel(
        about, text=about_text, font=("맑은 고딕", 15), anchor="w", justify="left"
    ).pack(fill="x", padx=18, pady=18)
    health_text = ctk.CTkTextbox(about, height=240)
    health_text.pack(fill="both", expand=True, padx=14, pady=8)
    health_text.insert("1.0", "Run diagnostics or release validation.")
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
        lines = [f"Release ready: {'YES' if report.ready else 'NO'}"]
        lines.extend(
            f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}"
            for check in report.checks
        )
        show_health("\n".join(lines))

    about_buttons = ctk.CTkFrame(about, fg_color="transparent")
    about_buttons.pack(fill="x", padx=10, pady=5)
    ctk.CTkButton(about_buttons, text="Run Diagnostics", command=run_diagnostics).pack(side="left", padx=4)
    ctk.CTkButton(about_buttons, text="Validate Release", command=validate_release).pack(side="left", padx=4)

    def save_settings():
        try:
            settings.update({
                "data_directory": variables["data_directory"].get(),
                "backup_directory": variables["backup_directory"].get(),
                "window_size": variables["window_size"].get(),
                "auto_refresh_interval": variables["auto_refresh_interval"].get(),
                "theme": variables["theme"].get(),
            })
            settings.ensure_directories()
            settings.save()
            ctk.set_appearance_mode(settings.get("theme"))
        except Exception as error:
            messagebox.showerror("Settings", str(error), parent=window)
            return
        messagebox.showinfo("Settings", "Settings saved. Path changes apply after restart.", parent=window)
        window.grab_release()
        window.destroy()

    footer = ctk.CTkFrame(window, fg_color="transparent")
    footer.pack(fill="x", padx=14, pady=(0, 12))
    ctk.CTkButton(footer, text="Save", width=100, command=save_settings).pack(side="right", padx=5)
    ctk.CTkButton(footer, text="Cancel", width=100, command=window.destroy).pack(side="right", padx=5)
    return window
