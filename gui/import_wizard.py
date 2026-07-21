"""Five-step smart Excel/CSV contract import wizard."""

import os
import queue
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from core.app_settings import get_app_settings
from core.logger import get_logger

from services.connectors.contract_import import (
    CONTRACT_COLUMNS,
    FIELD_LABELS,
    ContractImportConnector,
)
from services.contract_service import ContractService, REQUIRED_FIELDS
from services.connectors.schoolmarket_import import (
    SCHOOLMARKET_COLUMNS,
    SCHOOLMARKET_FIELD_LABELS,
    SCHOOLMARKET_REQUIRED_FIELDS,
    SchoolMarketImport,
)
from services.connectors.g2b_import import (
    G2B_COLUMNS,
    G2B_FIELD_LABELS,
    G2B_REQUIRED_FIELDS,
    G2BImport,
)
from services.connectors.education_office_import import (
    EDUCATION_OFFICE_COLUMNS,
    EDUCATION_OFFICE_FIELD_LABELS,
    EDUCATION_OFFICE_REQUIRED_FIELDS,
    EducationOfficeImport,
)
from services.smart_import import MappingStore, SmartContractImport, format_import_summary


UNMAPPED = "선택 안 함"
STEP_TITLES = ("파일 선택", "미리보기", "컬럼 매핑", "가져오기 진행", "요약")


def mapping_status(
    mapping, fields=CONTRACT_COLUMNS, labels=FIELD_LABELS, required=REQUIRED_FIELDS
):
    """Return a concise mapping-completeness message for the wizard."""
    mapped = sum(bool(mapping.get(field)) for field in fields)
    missing = [labels[field] for field in required if not mapping.get(field)]
    if missing:
        return f"자동 매핑 {mapped}/{len(fields)} · 필수 누락: {', '.join(missing)}"
    return f"자동 매핑 {mapped}/{len(fields)} · 필수 컬럼 완료"


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


def progress_text(progress):
    """Format worker progress consistently for the dialog and tests."""
    percentage = max(0, min(100, int(progress.get("percentage", 0) or 0)))
    processed = max(0, int(progress.get("processed", 0) or 0))
    total = max(0, int(progress.get("total", 0) or 0))
    return (
        f"{progress.get('stage', 'Reading file...')}\n"
        f"{percentage}% · current row {processed:,} / {total:,}"
    )


def open_contract_import_wizard(parent, on_complete=None):
    """Open the existing contract profile in the Smart Import Wizard."""
    return _open_import_wizard(parent, on_complete, source_kind="contract")


def open_schoolmarket_import_wizard(parent, on_complete=None):
    """Open the SchoolMarket profile in the Smart Import Wizard."""
    return _open_import_wizard(parent, on_complete, source_kind="schoolmarket")


def open_g2b_import_wizard(parent, on_complete=None):
    """Open the G2B profile in the Smart Import Wizard."""
    return _open_import_wizard(parent, on_complete, source_kind="g2b")


def open_education_office_import_wizard(parent, on_complete=None):
    """Open the Education Office profile in the Smart Import Wizard."""
    return _open_import_wizard(parent, on_complete, source_kind="education_office")


def _open_import_wizard(parent, on_complete=None, source_kind="contract"):
    """Open a modal-style, five-step import wizard for one source profile."""
    if source_kind == "education_office":
        fields = EDUCATION_OFFICE_COLUMNS
        labels = EDUCATION_OFFICE_FIELD_LABELS
        required_fields = EDUCATION_OFFICE_REQUIRED_FIELDS
        adapter = EducationOfficeImport
        importer_factory = EducationOfficeImport
        mapping_name = "education_office"
        source_title = "Education Office Project Import"
    elif source_kind == "g2b":
        fields = G2B_COLUMNS
        labels = G2B_FIELD_LABELS
        required_fields = G2B_REQUIRED_FIELDS
        adapter = G2BImport
        importer_factory = G2BImport
        mapping_name = "g2b"
        source_title = "G2B (나라장터) Import"
    elif source_kind == "schoolmarket":
        fields = SCHOOLMARKET_COLUMNS
        labels = SCHOOLMARKET_FIELD_LABELS
        required_fields = SCHOOLMARKET_REQUIRED_FIELDS
        adapter = SchoolMarketImport
        importer_factory = SchoolMarketImport
        mapping_name = "schoolmarket"
        source_title = "SchoolMarket Import"
    else:
        fields = CONTRACT_COLUMNS
        labels = FIELD_LABELS
        required_fields = REQUIRED_FIELDS
        adapter = ContractImportConnector
        importer_factory = SmartContractImport
        mapping_name = "contract"
        source_title = "Contract Import"
    wizard = ctk.CTkToplevel(parent)
    wizard.title("스마트 가져오기 마법사")
    wizard.geometry("1220x760")
    wizard.minsize(980, 650)
    wizard.transient(parent)

    state = {
        "step": 0,
        "file_path": "",
        "headers": [],
        "preview": [],
        "running": False,
        "importer": None,
    }
    event_queue = queue.Queue()
    mapping_store = MappingStore()
    mapping_selectors = {}

    header = ctk.CTkFrame(wizard)
    header.pack(fill="x", padx=18, pady=(16, 8))
    ctk.CTkLabel(
        header, text=f"Smart Import Wizard · {source_title}", font=("맑은 고딕", 24, "bold")
    ).pack(anchor="w", padx=16, pady=(12, 4))
    step_label = ctk.CTkLabel(header, text="", anchor="w")
    step_label.pack(fill="x", padx=16, pady=(0, 12))

    body = ctk.CTkFrame(wizard)
    body.pack(fill="both", expand=True, padx=18, pady=8)
    pages = [ctk.CTkFrame(body, fg_color="transparent") for _ in STEP_TITLES]

    # Step 1: file selection.
    file_label = ctk.CTkLabel(pages[0], text="선택한 파일 없음", anchor="w")
    file_label.pack(fill="x", padx=24, pady=(50, 12))
    sheet_selector = ctk.CTkComboBox(pages[0], values=["-"], width=320)
    sheet_selector.set("-")
    sheet_selector.pack(anchor="w", padx=24, pady=8)

    # Step 2: scrollable 100-row preview.
    ctk.CTkLabel(
        pages[1], text="첫 100행 (필수 값 누락 행은 강조됩니다)", anchor="w"
    ).pack(fill="x", padx=12, pady=(10, 4))
    preview_container = ctk.CTkFrame(pages[1], fg_color="transparent")
    preview_container.pack(fill="both", expand=True, padx=10, pady=8)
    preview_tree = ttk.Treeview(
        preview_container,
        columns=("row", "code", "school", "date", "product", "vendor", "amount", "validation"),
        show="headings",
    )
    for column, heading, width in (
        ("row", "행", 55), ("code", "학교코드", 100), ("school", "학교명", 160),
        ("date", "계약일", 100), ("product", "품목", 170), ("vendor", "업체", 140),
        ("amount", "금액", 120), ("validation", "검증", 260),
    ):
        preview_tree.heading(column, text=heading)
        preview_tree.column(column, width=width, anchor="center")
    preview_tree.tag_configure("missing", background="#FEE2E2", foreground="#991B1B")
    preview_tree.tag_configure("warning", background="#FFF7ED", foreground="#9A3412")
    vertical_scroll = ttk.Scrollbar(preview_container, orient="vertical", command=preview_tree.yview)
    horizontal_scroll = ttk.Scrollbar(preview_container, orient="horizontal", command=preview_tree.xview)
    preview_tree.configure(yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set)
    preview_tree.grid(row=0, column=0, sticky="nsew")
    vertical_scroll.grid(row=0, column=1, sticky="ns")
    horizontal_scroll.grid(row=1, column=0, sticky="ew")
    preview_container.grid_rowconfigure(0, weight=1)
    preview_container.grid_columnconfigure(0, weight=1)

    # Step 3: editable mappings.
    mapping_message = ctk.CTkLabel(pages[2], text="", anchor="w")
    mapping_message.grid(row=0, column=0, columnspan=4, padx=16, pady=(18, 10), sticky="w")
    for index, field in enumerate(fields):
        row = 1 + index // 2
        column = (index % 2) * 2
        required_mark = " *" if field in required_fields else ""
        ctk.CTkLabel(pages[2], text=f"{labels[field]}{required_mark}", anchor="w").grid(
            row=row, column=column, padx=(16, 5), pady=10, sticky="w"
        )
        selector = ctk.CTkComboBox(pages[2], values=[UNMAPPED], width=280)
        selector.set(UNMAPPED)
        selector.grid(row=row, column=column + 1, padx=(5, 20), pady=10, sticky="ew")
        mapping_selectors[field] = selector
    save_mapping = ctk.CTkCheckBox(pages[2], text="이 매핑을 다음 가져오기에 재사용")
    save_mapping.select()
    save_mapping.grid(
        row=2 + (len(fields) - 1) // 2,
        column=0,
        columnspan=4,
        padx=16,
        pady=16,
        sticky="w",
    )
    pages[2].grid_columnconfigure(1, weight=1)
    pages[2].grid_columnconfigure(3, weight=1)

    # Step 4: progress and cancellation.
    progress_status = ctk.CTkLabel(
        pages[3], text=progress_text({}), font=("맑은 고딕", 18, "bold")
    )
    progress_status.pack(pady=(120, 20))
    progress_bar = ctk.CTkProgressBar(pages[3], width=600)
    progress_bar.set(0)
    progress_bar.pack(pady=10)
    cancel_button = ctk.CTkButton(pages[3], text="가져오기 취소", fg_color="#B91C1C")
    cancel_button.pack(pady=25)

    # Step 5: clipboard-ready summary.
    summary_box = ctk.CTkTextbox(pages[4], wrap="word")
    summary_box.pack(fill="both", expand=True, padx=18, pady=18)

    footer = ctk.CTkFrame(wizard)
    footer.pack(fill="x", padx=18, pady=(4, 16))
    back_button = ctk.CTkButton(footer, text="이전", width=100)
    back_button.pack(side="left", padx=8, pady=10)
    next_button = ctk.CTkButton(footer, text="다음", width=120)
    next_button.pack(side="right", padx=8, pady=10)

    def current_mapping():
        return {
            field: "" if selector.get() == UNMAPPED else selector.get()
            for field, selector in mapping_selectors.items()
        }

    def display_step(index):
        pages[state["step"]].pack_forget()
        state["step"] = index
        pages[index].pack(fill="both", expand=True)
        step_label.configure(
            text="  →  ".join(
                f"{'●' if item == index else '○'} {number + 1}. {title}"
                for number, (item, title) in enumerate(zip(range(5), STEP_TITLES))
            )
        )
        back_button.configure(state="disabled" if index in (0, 3, 4) else "normal")
        next_button.configure(
            text="가져오기 시작" if index == 2 else ("닫기" if index == 4 else "다음"),
            state="disabled" if index == 3 else "normal",
        )

    def apply_mapping():
        automatic = adapter.auto_map(state["headers"])
        stored = mapping_store.load(mapping_name)
        values = [UNMAPPED, *state["headers"]]
        used = set()
        for field, selector in mapping_selectors.items():
            candidate = stored.get(field, "")
            if candidate not in state["headers"] or candidate in used:
                candidate = automatic.get(field, "")
            if candidate:
                used.add(candidate)
            selector.configure(values=values)
            selector.set(candidate or UNMAPPED)
        mapping_message.configure(
            text=mapping_status(current_mapping(), fields, labels, required_fields)
        )

    def refresh_preview():
        connector = adapter(
            state["file_path"], sheet_name=sheet_selector.get(), mapping=current_mapping()
        )
        state["preview"] = connector.preview(limit=100)
        preview_tree.delete(*preview_tree.get_children())
        for preview_row in state["preview"]:
            tag = "missing" if preview_row.get("missing_fields") else (
                "warning" if preview_row.get("error") else ""
            )
            preview_tree.insert(
                "", "end", tags=((tag,) if tag else ()), values=preview_table_values(preview_row)
            )

    def select_file():
        file_path = filedialog.askopenfilename(
            parent=wizard,
            title="가져올 파일 선택",
            filetypes=(("Excel/CSV", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")),
        )
        if not file_path:
            return
        try:
            sheets = adapter.sheet_names(file_path)
            state["headers"] = adapter.headers(file_path, sheets[0])
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror("파일 읽기 오류", str(error), parent=wizard)
            return
        state["file_path"] = file_path
        try:
            get_app_settings().add_recent_file(file_path).save()
        except (OSError, ValueError):
            get_logger("settings").exception("failed to update recent import files")
        file_label.configure(text=os.path.basename(file_path))
        sheet_selector.configure(values=sheets)
        sheet_selector.set(sheets[0])
        apply_mapping()

    def change_sheet(_choice=None):
        if not state["file_path"]:
            return
        state["headers"] = adapter.headers(
            state["file_path"], sheet_selector.get()
        )
        apply_mapping()

    def worker(importer):
        try:
            summary = importer.run(lambda **value: event_queue.put(("progress", value)))
            event_queue.put(("complete", summary))
        except BaseException as error:
            event_queue.put(("error", error))

    def process_events():
        while True:
            try:
                event_type, payload = event_queue.get_nowait()
            except queue.Empty:
                break
            if event_type == "progress":
                progress_status.configure(text=progress_text(payload))
                progress_bar.set(max(0, min(1, payload.get("percentage", 0) / 100)))
            elif event_type == "complete":
                state["running"] = False
                cancel_button.configure(state="disabled")
                summary_box.delete("1.0", "end")
                summary_box.insert("1.0", format_import_summary(payload))
                display_step(4)
                if on_complete:
                    on_complete()
            elif event_type == "error":
                state["running"] = False
                cancel_button.configure(state="disabled")
                messagebox.showerror("가져오기 오류", str(payload), parent=wizard)
                display_step(2)
        if state["running"] and wizard.winfo_exists():
            wizard.after(80, process_events)

    def start_import():
        mapping = current_mapping()
        try:
            adapter.validate_mapping(mapping, state["headers"])
            if save_mapping.get():
                mapping_store.save(mapping, mapping_name)
            importer = importer_factory(
                state["file_path"], sheet_name=sheet_selector.get(), mapping=mapping
            )
        except (OSError, TypeError, ValueError, KeyError) as error:
            messagebox.showerror("가져오기 설정 오류", str(error), parent=wizard)
            return
        state["importer"] = importer
        state["running"] = True
        progress_bar.set(0)
        cancel_button.configure(state="normal", text="가져오기 취소")
        display_step(3)
        threading.Thread(target=worker, args=(importer,), daemon=True).start()
        wizard.after(80, process_events)

    def next_step():
        if state["step"] == 0:
            if not state["file_path"]:
                messagebox.showwarning("파일 선택", "Excel 또는 CSV 파일을 선택하세요.", parent=wizard)
                return
            try:
                refresh_preview()
            except (OSError, TypeError, ValueError, KeyError) as error:
                messagebox.showerror("미리보기 오류", str(error), parent=wizard)
                return
            display_step(1)
        elif state["step"] == 1:
            display_step(2)
        elif state["step"] == 2:
            start_import()
        elif state["step"] == 4:
            wizard.destroy()

    def cancel_import():
        if state["running"] and state["importer"]:
            state["importer"].cancel()
            cancel_button.configure(state="disabled", text="취소 요청됨...")

    def copy_summary():
        wizard.clipboard_clear()
        wizard.clipboard_append(summary_box.get("1.0", "end-1c"))

    def close_wizard():
        if state["running"]:
            cancel_import()
            messagebox.showinfo(
                "취소 요청됨", "안전한 롤백이 끝나면 요약 화면이 표시됩니다.", parent=wizard
            )
            return
        wizard.destroy()

    ctk.CTkButton(pages[0], text="파일 선택", command=select_file, width=140).pack(
        anchor="w", padx=24, pady=12
    )
    sheet_selector.configure(command=change_sheet)
    ctk.CTkButton(pages[4], text="요약 복사", command=copy_summary, width=120).pack(
        anchor="e", padx=18, pady=(0, 14)
    )
    back_button.configure(command=lambda: display_step(max(0, state["step"] - 1)))
    next_button.configure(command=next_step)
    cancel_button.configure(command=cancel_import)
    wizard.protocol("WM_DELETE_WINDOW", close_wizard)
    pages[0].pack(fill="both", expand=True)
    display_step(0)
    return wizard
