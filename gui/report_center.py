"""Unified Report Center with filterable print preview and export."""

import os

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.app_settings import get_app_settings
from core.logger import get_logger
from services.report_service import EXPORT_FORMATS, REPORT_TYPES, ReportService


def open_report_center(parent, report_service=ReportService):
    window = ctk.CTkToplevel(parent)
    window.title("EduBid Insight — Report Center")
    window.geometry("1180x760")
    window.minsize(900, 620)
    window.transient(parent)

    shell = ctk.CTkFrame(window, fg_color="transparent")
    shell.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(
        shell, text="Report Center", font=("맑은 고딕", 28, "bold"), anchor="w"
    ).pack(fill="x", pady=(0, 10))

    controls = ctk.CTkFrame(shell)
    controls.pack(fill="x", pady=5)
    for column in range(6):
        controls.grid_columnconfigure(column, weight=1)

    report_type = ctk.StringVar(value=REPORT_TYPES[0])
    export_format = ctk.StringVar(value=EXPORT_FORMATS[0])
    variables = {
        "school": ctk.StringVar(),
        "region": ctk.StringVar(),
        "office": ctk.StringVar(),
        "date_from": ctk.StringVar(),
        "date_to": ctk.StringVar(),
        "category": ctk.StringVar(),
    }

    def field(row, column, title, widget):
        ctk.CTkLabel(controls, text=title, anchor="w").grid(
            row=row * 2, column=column, padx=8, pady=(9, 2), sticky="ew"
        )
        widget.grid(row=row * 2 + 1, column=column, padx=8, pady=(0, 9), sticky="ew")

    field(0, 0, "Report Type", ctk.CTkOptionMenu(controls, variable=report_type, values=list(REPORT_TYPES)))
    field(0, 1, "School (code or name)", ctk.CTkEntry(controls, textvariable=variables["school"]))
    field(0, 2, "Region", ctk.CTkEntry(controls, textvariable=variables["region"]))
    field(0, 3, "Office", ctk.CTkEntry(controls, textvariable=variables["office"]))
    field(0, 4, "Date From", ctk.CTkEntry(controls, textvariable=variables["date_from"], placeholder_text="YYYY-MM-DD"))
    field(0, 5, "Date To", ctk.CTkEntry(controls, textvariable=variables["date_to"], placeholder_text="YYYY-MM-DD"))
    field(1, 0, "Category", ctk.CTkEntry(controls, textvariable=variables["category"]))
    field(1, 1, "Export Format", ctk.CTkOptionMenu(controls, variable=export_format, values=list(EXPORT_FORMATS)))

    preview_frame = ctk.CTkFrame(shell)
    preview_frame.pack(fill="both", expand=True, pady=10)
    preview_header = ctk.CTkLabel(
        preview_frame, text="Print Preview", font=("맑은 고딕", 17, "bold"), anchor="w"
    )
    preview_header.pack(fill="x", padx=12, pady=(10, 4))
    preview_text = ctk.CTkTextbox(preview_frame, wrap="none", font=("Consolas", 12))
    preview_text.pack(fill="both", expand=True, padx=10, pady=(2, 10))
    preview_text.insert("1.0", "Choose a report and select Print Preview before exporting.")
    preview_text.configure(state="disabled")

    status = ctk.CTkLabel(shell, text="Ready", anchor="w")
    status.pack(fill="x", pady=4)
    current_document = {"value": None}

    def selected_filters():
        return {key: variable.get().strip() for key, variable in variables.items()}

    def show_preview(force=True):
        status.configure(text="Preparing report…")
        window.update_idletasks()
        try:
            document = report_service.aggregate(
                report_type.get(), selected_filters(), force_refresh=force
            )
            text = report_service.preview(document)
        except Exception as error:
            current_document["value"] = None
            export_button.configure(state="disabled")
            status.configure(text="Preview failed")
            messagebox.showerror("Report Center", str(error), parent=window)
            return
        current_document["value"] = document
        preview_text.configure(state="normal")
        preview_text.delete("1.0", "end")
        preview_text.insert("1.0", text)
        preview_text.configure(state="disabled")
        preview_header.configure(text=f"Print Preview — {document.report_type}")
        export_button.configure(state="normal")
        status.configure(text=f"Preview ready • {len(document.sections)} sections")

    def export_report():
        document = current_document["value"]
        if document is None:
            messagebox.showinfo("Report Center", "Preview the report before export.", parent=window)
            return
        selected_format = export_format.get()
        extension = {"PDF": ".pdf", "Excel": ".xlsx", "CSV": ".csv"}[selected_format]
        file_path = filedialog.asksaveasfilename(
            parent=window,
            title=f"Export {document.report_type}",
            defaultextension=extension,
            initialfile=document.report_type.lower().replace(" ", "_") + extension,
            filetypes=[(selected_format, f"*{extension}"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            report_service.export(document, file_path, selected_format)
        except Exception as error:
            get_logger("report").exception("report export failed")
            messagebox.showerror("Export failed", str(error), parent=window)
            return
        try:
            get_app_settings().add_recent_file(file_path).save()
        except (OSError, ValueError):
            get_logger("settings").exception("failed to update recent report files")
        status.configure(text=f"Exported • {os.path.basename(file_path)}")
        messagebox.showinfo("Report Center", "Report exported successfully.", parent=window)

    buttons = ctk.CTkFrame(controls, fg_color="transparent")
    buttons.grid(row=3, column=2, columnspan=4, padx=8, pady=(0, 9), sticky="e")
    ctk.CTkButton(
        buttons, text="Print Preview", width=130, command=lambda: show_preview(True)
    ).pack(side="left", padx=5)
    export_button = ctk.CTkButton(
        buttons, text="Export", width=110, state="disabled", command=export_report
    )
    export_button.pack(side="left", padx=5)
    return window
