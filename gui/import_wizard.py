"""Guided Excel/CSV contract import interface."""

import os
import queue
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from services.connectors.contract_import import (
    CONTRACT_COLUMNS,
    FIELD_LABELS,
    ContractImportConnector,
)
from services.contract_service import ContractService, REQUIRED_FIELDS
from services.import_history_service import ImportHistoryService
from services.sync_service import SyncService


UNMAPPED = "선택 안 함"


def mapping_status(mapping):
    """Return a concise mapping-completeness message for the wizard."""
    mapped = sum(bool(mapping.get(field)) for field in CONTRACT_COLUMNS)
    missing = [FIELD_LABELS[field] for field in REQUIRED_FIELDS if not mapping.get(field)]
    if missing:
        return f"자동 매핑 {mapped}/{len(CONTRACT_COLUMNS)} · 필수 누락: {', '.join(missing)}"
    return f"자동 매핑 {mapped}/{len(CONTRACT_COLUMNS)} · 필수 컬럼 완료"


def preview_table_values(preview_row):
    contract = preview_row["contract"]
    amount = contract.get("amount", "")
    try:
        amount = ContractService.format_amount(amount) if amount not in (None, "") else ""
    except (TypeError, ValueError):
        amount = str(amount or "")
    return (
        preview_row["row_number"],
        contract.get("school_code", ""),
        contract.get("school_name", ""),
        contract.get("contract_date", ""),
        contract.get("product", ""),
        contract.get("vendor", ""),
        amount,
        preview_row.get("error") or "정상",
    )


def open_contract_import_wizard(parent, on_complete=None):
    """Open the five-step contract import wizard."""
    wizard = ctk.CTkToplevel(parent)
    wizard.title("계약 가져오기 마법사")
    wizard.geometry("1250x820")
    wizard.transient(parent)

    ctk.CTkLabel(
        wizard,
        text="Contract Import Wizard",
        font=("맑은 고딕", 25, "bold"),
    ).pack(pady=(15, 8))

    state = {"file_path": "", "headers": [], "running": False}
    mapping_selectors = {}

    file_frame = ctk.CTkFrame(wizard)
    file_frame.pack(fill="x", padx=16, pady=4)
    ctk.CTkLabel(file_frame, text="1. 파일 선택", width=120, anchor="w").pack(
        side="left", padx=10, pady=9
    )
    file_label = ctk.CTkLabel(file_frame, text="선택된 파일 없음", anchor="w")
    file_label.pack(side="left", fill="x", expand=True, padx=5)

    sheet_frame = ctk.CTkFrame(wizard)
    sheet_frame.pack(fill="x", padx=16, pady=4)
    ctk.CTkLabel(sheet_frame, text="2. 시트 선택", width=120, anchor="w").pack(
        side="left", padx=10, pady=9
    )
    sheet_selector = ctk.CTkComboBox(sheet_frame, width=280, values=["-"])
    sheet_selector.set("-")
    sheet_selector.pack(side="left", padx=5)

    mapping_frame = ctk.CTkFrame(wizard)
    mapping_frame.pack(fill="x", padx=16, pady=4)
    ctk.CTkLabel(mapping_frame, text="3. 자동 컬럼 매핑", anchor="w").grid(
        row=0, column=0, columnspan=8, padx=10, pady=(8, 3), sticky="w"
    )
    for index, field in enumerate(CONTRACT_COLUMNS):
        row = 1 + index // 4
        column = (index % 4) * 2
        required_mark = " *" if field in REQUIRED_FIELDS else ""
        ctk.CTkLabel(
            mapping_frame, text=f"{FIELD_LABELS[field]}{required_mark}", anchor="w"
        ).grid(row=row, column=column, padx=(10, 3), pady=5, sticky="w")
        selector = ctk.CTkComboBox(mapping_frame, width=175, values=[UNMAPPED])
        selector.set(UNMAPPED)
        selector.grid(row=row, column=column + 1, padx=(3, 8), pady=5)
        mapping_selectors[field] = selector
    mapping_message = ctk.CTkLabel(mapping_frame, text="파일을 선택하세요.", anchor="w")
    mapping_message.grid(row=3, column=0, columnspan=7, padx=10, pady=8, sticky="w")

    preview_frame = ctk.CTkFrame(wizard)
    preview_frame.pack(fill="both", expand=True, padx=16, pady=4)
    ctk.CTkLabel(preview_frame, text="4. 미리보기", anchor="w").pack(
        fill="x", padx=10, pady=(7, 3)
    )
    preview_tree = ttk.Treeview(
        preview_frame,
        columns=("row", "code", "school", "date", "product", "vendor", "amount", "validation"),
        show="headings",
        height=12,
    )
    for column, heading, width in (
        ("row", "행", 45),
        ("code", "학교코드", 100),
        ("school", "학교명", 180),
        ("date", "계약일", 100),
        ("product", "품목", 180),
        ("vendor", "업체", 150),
        ("amount", "금액", 120),
        ("validation", "검증", 280),
    ):
        preview_tree.heading(column, text=heading)
        preview_tree.column(column, width=width, anchor="center")
    preview_tree.tag_configure("error", foreground="#C2410C")
    preview_tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    action_frame = ctk.CTkFrame(wizard)
    action_frame.pack(fill="x", padx=16, pady=(4, 12))
    import_status = ctk.CTkLabel(action_frame, text="5. 가져오기 대기", anchor="w")
    import_status.pack(side="left", fill="x", expand=True, padx=10)
    progress_bar = ctk.CTkProgressBar(action_frame, width=180)
    progress_bar.set(0)
    progress_bar.pack(side="left", padx=8, pady=10)

    event_queue = queue.Queue()

    def current_mapping():
        return {
            field: "" if selector.get() == UNMAPPED else selector.get()
            for field, selector in mapping_selectors.items()
        }

    def apply_automatic_mapping():
        if not state["headers"]:
            return
        automatic = ContractImportConnector.auto_map(state["headers"])
        values = [UNMAPPED, *state["headers"]]
        for field, selector in mapping_selectors.items():
            selector.configure(values=values)
            selector.set(automatic.get(field) or UNMAPPED)
        mapping_message.configure(text=mapping_status(current_mapping()))

    def load_selected_sheet(_choice=None):
        if not state["file_path"]:
            return
        try:
            state["headers"] = ContractImportConnector.headers(
                state["file_path"], sheet_selector.get()
            )
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror("파일 읽기 오류", str(error), parent=wizard)
            return
        apply_automatic_mapping()
        preview_tree.delete(*preview_tree.get_children())

    def select_file():
        file_path = filedialog.askopenfilename(
            parent=wizard,
            title="계약 파일 선택",
            filetypes=(
                ("계약 파일", "*.xlsx *.csv"),
                ("Excel", "*.xlsx"),
                ("CSV", "*.csv"),
            ),
        )
        if not file_path:
            return
        try:
            sheets = ContractImportConnector.sheet_names(file_path)
        except (OSError, ValueError) as error:
            messagebox.showerror("파일 선택 오류", str(error), parent=wizard)
            return
        state["file_path"] = file_path
        file_label.configure(text=os.path.basename(file_path))
        sheet_selector.configure(values=sheets)
        sheet_selector.set(sheets[0])
        load_selected_sheet()

    def build_connector():
        if not state["file_path"]:
            raise ValueError("먼저 계약 파일을 선택하세요.")
        mapping = current_mapping()
        ContractImportConnector.validate_mapping(mapping, state["headers"])
        return ContractImportConnector(
            state["file_path"],
            sheet_name=sheet_selector.get(),
            mapping=mapping,
        )

    def show_preview():
        try:
            preview_rows = build_connector().preview(limit=20)
        except (OSError, TypeError, ValueError, KeyError) as error:
            messagebox.showerror("미리보기 오류", str(error), parent=wizard)
            return
        preview_tree.delete(*preview_tree.get_children())
        for preview_row in preview_rows:
            preview_tree.insert(
                "",
                "end",
                tags=(("error",) if preview_row["error"] else ()),
                values=preview_table_values(preview_row),
            )
        mapping_message.configure(text=mapping_status(current_mapping()))
        import_status.configure(text=f"5. 가져오기 대기 · 미리보기 {len(preview_rows)}건")

    def report_progress(progress):
        event_queue.put(("progress", progress))

    def import_worker(connector):
        try:
            result = SyncService.synchronize_connector(connector, report_progress)
            ImportHistoryService.record(
                source_type=connector.source,
                filename=connector.file_path,
                result=result["status"],
                imported_rows=result["inserted"],
            )
            event_queue.put(("complete", result))
        except Exception as error:
            ImportHistoryService.record(
                source_type=connector.source,
                filename=connector.file_path,
                result="FAILED",
                imported_rows=0,
            )
            event_queue.put(("error", error))

    def process_events():
        finished = False
        while True:
            try:
                event_type, payload = event_queue.get_nowait()
            except queue.Empty:
                break
            if event_type == "progress":
                processed = payload.get("processed", 0)
                import_status.configure(text=f"5. 가져오는 중 · {processed:,}건 처리")
            elif event_type == "complete":
                finished = True
                state["running"] = False
                progress_bar.set(1)
                import_button.configure(state="normal")
                import_status.configure(
                    text=(
                        f"5. 완료 · 추가 {payload['inserted']:,} · "
                        f"중복/건너뜀 {payload['skipped']:,} · 오류 {payload['errors']:,}"
                    )
                )
                if on_complete:
                    on_complete()
            elif event_type == "error":
                finished = True
                state["running"] = False
                import_button.configure(state="normal")
                import_status.configure(text="5. 가져오기 실패")
                messagebox.showerror("계약 가져오기 오류", str(payload), parent=wizard)
        if state["running"] and not finished and wizard.winfo_exists():
            wizard.after(100, process_events)

    def start_import():
        try:
            connector = build_connector()
        except (OSError, TypeError, ValueError, KeyError) as error:
            messagebox.showerror("가져오기 설정 오류", str(error), parent=wizard)
            return
        state["running"] = True
        import_button.configure(state="disabled")
        progress_bar.set(0)
        import_status.configure(text="5. 계약 가져오기를 시작합니다...")
        threading.Thread(target=import_worker, args=(connector,), daemon=True).start()
        wizard.after(100, process_events)

    def close_wizard():
        if state["running"]:
            messagebox.showinfo(
                "가져오기 진행 중",
                "계약 가져오기가 끝난 후 창을 닫아주세요.",
                parent=wizard,
            )
            return
        wizard.destroy()

    ctk.CTkButton(file_frame, text="파일 선택", width=110, command=select_file).pack(
        side="right", padx=10, pady=8
    )
    sheet_selector.configure(command=load_selected_sheet)
    ctk.CTkButton(
        sheet_frame, text="자동 매핑", width=110, command=apply_automatic_mapping
    ).pack(side="left", padx=10)
    ctk.CTkButton(action_frame, text="미리보기", width=110, command=show_preview).pack(
        side="left", padx=5
    )
    import_button = ctk.CTkButton(
        action_frame, text="가져오기", width=110, command=start_import
    )
    import_button.pack(side="left", padx=5)
    ctk.CTkButton(action_frame, text="닫기", width=100, command=close_wizard).pack(
        side="left", padx=(5, 10)
    )
    wizard.protocol("WM_DELETE_WINDOW", close_wizard)
    return wizard
