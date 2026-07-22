"""Six-stage production Excel Import Center wizard."""

import os
import queue
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import TclError, filedialog, messagebox, ttk

from core.app_settings import get_app_settings
from core.logger import get_logger
from gui.template_center import open_template_center
from gui.ui_theme import (
    COLORS, FONTS, card, own_child_window, primary_button, secondary_button,
    stripe_treeview,
)
from services.connectors.contract_import import CONTRACT_COLUMNS, FIELD_LABELS, ContractImportConnector
from services.contract_service import ContractService, REQUIRED_FIELDS
from services.import_center import (
    ImportProfile, ImportRunStore, PROFILES, export_failed_rows, failed_rows,
)
from services.smart_import import MappingStore, SmartContractImport, format_import_summary


UNMAPPED = "선택 안 함 · Unmapped"
STEP_TITLES = (
    "파일 선택\nSelect File", "통합문서 분석\nAnalyze Workbook", "데이터 미리보기\nPreview Data",
    "검증\nValidate", "가져오기\nImport", "결과 요약\nSummary",
)


def mapping_status(mapping, fields=CONTRACT_COLUMNS, labels=FIELD_LABELS, required=REQUIRED_FIELDS):
    mapped = sum(bool(mapping.get(field)) for field in fields)
    missing = [labels[field] for field in required if not mapping.get(field)]
    if missing:
        return f"자동 매핑 {mapped}/{len(fields)} · 필수 열 누락: {', '.join(missing)}"
    return f"자동 매핑 {mapped}/{len(fields)} · 필수 컬럼 완료"


def preview_table_values(preview_row):
    contract = preview_row.get("contract") or {}
    amount = contract.get("amount", "")
    try:
        amount = ContractService.format_amount(amount) if amount not in (None, "") else ""
    except (TypeError, ValueError):
        amount = str(amount or "")
    return (
        preview_row.get("row_number", ""), contract.get("school_code", ""),
        contract.get("school_name", ""), contract.get("contract_date", ""),
        contract.get("product", ""), contract.get("vendor", ""),
        amount, preview_row.get("error") or "정상",
    )


def progress_text(progress):
    percentage = max(0, min(100, int(progress.get("percentage", 0) or 0)))
    processed = max(0, int(progress.get("processed", 0) or 0))
    total = max(0, int(progress.get("total", 0) or 0))
    return f"{progress.get('stage', 'Reading file...')}\n{percentage}% · current row {processed:,} / {total:,}"


def open_school_import_wizard(parent, on_complete=None):
    return _open_import_wizard(parent, on_complete, "school")


def open_education_office_import_wizard(parent, on_complete=None):
    return _open_import_wizard(parent, on_complete, "education_office")


def open_schoolmarket_import_wizard(parent, on_complete=None):
    return _open_import_wizard(parent, on_complete, "schoolmarket")


def open_g2b_import_wizard(parent, on_complete=None):
    return _open_import_wizard(parent, on_complete, "g2b")


def open_crm_import_wizard(parent, on_complete=None):
    return _open_import_wizard(parent, on_complete, "crm")


def open_contract_import_wizard(parent, on_complete=None):
    legacy = ImportProfile(
        "contract", "계약 가져오기\nContract Import", "Contract", "Contract_Template.xlsx",
        CONTRACT_COLUMNS, FIELD_LABELS, REQUIRED_FIELDS, ContractImportConnector,
    )
    return _open_import_wizard(parent, on_complete, "contract", profile_override=legacy)


def _open_import_wizard(parent, on_complete=None, source_kind="school", profile_override=None):
    profile = profile_override or PROFILES[source_kind]
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("Excel 가져오기 센터 · Excel Import Center")
    window.geometry("1260x800")
    window.minsize(1040, 700)

    state = {"step": 0, "file_path": "", "headers": [], "sheets": [], "rows": [], "invalid": [], "running": False, "importer": None}
    events = queue.Queue()
    selectors = {}
    mapping_store = MappingStore()
    run_store = ImportRunStore()

    header = ctk.CTkFrame(window, fg_color=COLORS["surface"], corner_radius=0)
    header.pack(fill="x")
    ctk.CTkLabel(header, text="Excel 가져오기 센터", font=FONTS["title"], anchor="w").pack(fill="x", padx=24, pady=(16, 1))
    ctk.CTkLabel(header, text=f"Excel Import Center  ·  {profile.title.replace(chr(10), ' / ')}", font=FONTS["body"], text_color=COLORS["muted"], anchor="w").pack(fill="x", padx=24, pady=(0, 12))

    step_bar = ctk.CTkFrame(window, fg_color="transparent")
    step_bar.pack(fill="x", padx=20, pady=(12, 4))
    step_labels = []
    for index, title in enumerate(STEP_TITLES):
        label = ctk.CTkLabel(step_bar, text=f"{index + 1}\n{title}", height=55, corner_radius=7, font=FONTS["caption"])
        label.pack(side="left", fill="x", expand=True, padx=3)
        step_labels.append(label)

    body = ctk.CTkFrame(window, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=20, pady=8)
    pages = [ctk.CTkFrame(body, fg_color="transparent") for _ in STEP_TITLES]

    # 1. File selection and drag/drop.
    drop_card = card(pages[0])
    drop_card.pack(fill="both", expand=True, padx=55, pady=42)
    drop_icon = ctk.CTkLabel(drop_card, text="⇩", font=("Segoe UI Symbol", 42), text_color=COLORS["blue"])
    drop_icon.pack(pady=(70, 10))
    file_label = ctk.CTkLabel(drop_card, text="Excel 파일을 여기에 놓으세요.\nDrop an Excel file here.", font=FONTS["section"], justify="center")
    file_label.pack(pady=8)
    file_detail = ctk.CTkLabel(drop_card, text=".xlsx 또는 .csv · 최대 파일 크기는 시스템 메모리에 따릅니다.", font=FONTS["caption"], text_color=COLORS["muted"])
    file_detail.pack(pady=(0, 22))
    select_button = primary_button(drop_card, text="파일 선택  Select File", width=180)
    select_button.pack(pady=6)
    secondary_button(drop_card, text="템플릿 센터  Template Center", width=210, command=lambda: open_template_center(window)).pack(pady=(6, 50))

    # 2. Workbook analysis and editable automatic mapping.
    analysis_top = card(pages[1])
    analysis_top.pack(fill="x", padx=6, pady=(4, 8))
    analysis_label = ctk.CTkLabel(analysis_top, text="파일을 분석하지 않았습니다.", font=FONTS["body_bold"], anchor="w")
    analysis_label.pack(side="left", fill="x", expand=True, padx=16, pady=14)
    sheet_selector = ctk.CTkComboBox(analysis_top, values=["-"], width=220)
    sheet_selector.pack(side="right", padx=16, pady=10)
    mapping_frame = ctk.CTkScrollableFrame(pages[1], label_text="자동 열 매핑 · Automatic Column Mapping", label_font=FONTS["section"])
    mapping_frame.pack(fill="both", expand=True, padx=6, pady=8)
    mapping_message = ctk.CTkLabel(mapping_frame, text="", text_color=COLORS["muted"], anchor="w")
    mapping_message.grid(row=0, column=0, columnspan=4, padx=12, pady=(6, 12), sticky="ew")
    for index, field in enumerate(profile.fields):
        row, column = 1 + index // 2, (index % 2) * 2
        required_mark = "  *" if field in profile.required else ""
        ctk.CTkLabel(mapping_frame, text=f"{profile.labels[field]}{required_mark}", anchor="w").grid(row=row, column=column, padx=(12, 5), pady=7, sticky="w")
        selector = ctk.CTkComboBox(mapping_frame, values=[UNMAPPED], width=260)
        selector.set(UNMAPPED); selector.grid(row=row, column=column + 1, padx=(5, 18), pady=7, sticky="ew")
        selectors[field] = selector
    mapping_frame.grid_columnconfigure(1, weight=1); mapping_frame.grid_columnconfigure(3, weight=1)

    # 3/4. Preview and validation share a table layout.
    def make_table(page):
        panel = card(page); panel.pack(fill="both", expand=True, padx=6, pady=4)
        status = ctk.CTkLabel(panel, text="", font=FONTS["body_bold"], anchor="w")
        status.pack(fill="x", padx=14, pady=(12, 6))
        frame = ctk.CTkFrame(panel, fg_color="transparent"); frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        tree = ttk.Treeview(frame, show="headings")
        ybar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); xbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky="nsew"); ybar.grid(row=0, column=1, sticky="ns"); xbar.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1); frame.grid_columnconfigure(0, weight=1)
        tree.tag_configure("invalid", background="#F8EEEE", foreground="#8B4545")
        return tree, status, panel

    preview_tree, preview_status, _ = make_table(pages[2])
    validation_tree, validation_status, validation_panel = make_table(pages[3])
    export_failed_button = secondary_button(validation_panel, text="실패 행 내보내기  Export Failed Rows", width=240)
    export_failed_button.pack(anchor="e", padx=14, pady=(0, 12))

    # 5. Import progress.
    progress_card = card(pages[4]); progress_card.pack(fill="both", expand=True, padx=60, pady=50)
    progress_status = ctk.CTkLabel(progress_card, text=progress_text({}), font=FONTS["section"], justify="center")
    progress_status.pack(pady=(110, 22))
    progress_bar = ctk.CTkProgressBar(progress_card, width=620, height=10, progress_color=COLORS["blue"])
    progress_bar.set(0); progress_bar.pack(pady=8)
    cancel_button = secondary_button(progress_card, text="가져오기 취소  Cancel Import", width=190)
    cancel_button.pack(pady=26)

    # 6. Summary.
    summary_card = card(pages[5]); summary_card.pack(fill="both", expand=True, padx=24, pady=14)
    summary_box = ctk.CTkTextbox(summary_card, wrap="word", font=FONTS["body"])
    summary_box.pack(fill="both", expand=True, padx=16, pady=16)
    secondary_button(summary_card, text="요약 복사  Copy Summary", width=170, command=lambda: _copy_summary(window, summary_box)).pack(anchor="e", padx=16, pady=(0, 14))

    footer = ctk.CTkFrame(window, fg_color=COLORS["surface"], corner_radius=0)
    footer.pack(fill="x")
    back_button = secondary_button(footer, text="이전  Back", width=115)
    back_button.pack(side="left", padx=20, pady=12)
    next_button = primary_button(footer, text="다음  Next", width=135)
    next_button.pack(side="right", padx=20, pady=12)

    def current_mapping():
        return {field: "" if selector.get() == UNMAPPED else selector.get() for field, selector in selectors.items()}

    def display_step(index):
        pages[state["step"]].pack_forget(); state["step"] = index; pages[index].pack(fill="both", expand=True)
        for number, label in enumerate(step_labels):
            active, complete = number == index, number < index
            label.configure(fg_color=COLORS["blue"] if active else (COLORS["green_tint"] if complete else COLORS["gray_tint"]), text_color="white" if active else (COLORS["green"] if complete else COLORS["muted"]))
        back_button.configure(state="disabled" if index in (0, 4, 5) else "normal")
        next_button.configure(text="닫기  Close" if index == 5 else ("가져오기  Import" if index == 3 else "다음  Next"), state="disabled" if index == 4 else "normal")

    def apply_mapping():
        automatic = profile.adapter.auto_map(state["headers"])
        stored = mapping_store.load(profile.key)
        values = [UNMAPPED, *state["headers"]]; used = set()
        for field, selector in selectors.items():
            candidate = stored.get(field, "")
            if candidate not in state["headers"] or candidate in used: candidate = automatic.get(field, "")
            if candidate: used.add(candidate)
            selector.configure(values=values); selector.set(candidate or UNMAPPED)
        mapping_message.configure(text=mapping_status(current_mapping(), profile.fields, profile.labels, profile.required))

    def analyze_file(file_path):
        file_path = os.path.abspath(file_path)
        if os.path.splitext(file_path)[1].lower() not in {".xlsx", ".csv"}:
            messagebox.showwarning("지원하지 않는 파일", "Excel(.xlsx) 또는 CSV(.csv) 파일을 선택하세요.", parent=window); return
        try:
            sheets = profile.adapter.sheet_names(file_path); headers = profile.adapter.headers(file_path, sheets[0])
            if not headers: raise ValueError("첫 번째 행에서 열 이름을 찾을 수 없습니다.")
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror("분석 오류 · Analysis Error", str(error), parent=window); return
        state.update(file_path=file_path, sheets=sheets, headers=headers, rows=[], invalid=[])
        file_label.configure(text=os.path.basename(file_path)); file_detail.configure(text=file_path)
        sheet_selector.configure(values=sheets); sheet_selector.set(sheets[0]); apply_mapping()
        analysis_label.configure(text=f"{os.path.basename(file_path)}  ·  {len(headers)} columns  ·  {len(sheets)} sheet(s)")
        try: get_app_settings().add_recent_file(file_path).save()
        except (OSError, ValueError): get_logger("settings").exception("failed to update recent import files")
        display_step(1)

    def choose_file():
        selected = filedialog.askopenfilename(parent=window, title="Excel 파일 선택 · Select File", filetypes=(("Excel / CSV", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")))
        if selected: analyze_file(selected)

    def change_sheet(_choice=None):
        if not state["file_path"]: return
        try:
            state["headers"] = profile.adapter.headers(state["file_path"], sheet_selector.get()); apply_mapping()
        except (OSError, ValueError, KeyError) as error: messagebox.showerror("시트 오류 · Sheet Error", str(error), parent=window)

    def create_importer():
        mapping = current_mapping(); profile.adapter.validate_mapping(mapping, state["headers"])
        mapping_store.save(mapping, profile.key)
        factory = SmartContractImport if profile.key == "contract" else profile.adapter
        return factory(state["file_path"], sheet_name=sheet_selector.get(), mapping=mapping)

    def collect_rows(importer):
        raw = list(importer.load())
        validated = importer.validate() if hasattr(importer, "validate") else importer.preview(limit=len(raw))
        result = []
        mapping = current_mapping()
        for index, item in enumerate(validated):
            source = raw[index] if index < len(raw) else {}
            values = {field: source.get(mapping.get(field, ""), "") for field in profile.fields}
            result.append({"row_number": item.get("row_number", index + 2), "values": values, "error": item.get("error", ""), "source": source})
        return result

    def fill_table(tree, rows):
        visible_fields = profile.fields[:7]; columns = ("row", *visible_fields, "validation")
        tree.configure(columns=columns)
        tree.heading("row", text="행\nRow"); tree.column("row", width=58, minwidth=48, anchor="center")
        for field in visible_fields:
            tree.heading(field, text=profile.labels[field]); tree.column(field, width=145, minwidth=90, anchor="center")
        tree.heading("validation", text="검증 결과\nValidation"); tree.column("validation", width=260, minwidth=180, anchor="w")
        tree.delete(*tree.get_children())
        for item in rows[:500]:
            error = item["error"] or "정상 · Valid"
            tree.insert("", "end", values=(item["row_number"], *(item["values"].get(field, "") for field in visible_fields), error), tags=(("invalid",) if item["error"] else ()))
        stripe_treeview(tree)

    def prepare_preview():
        try:
            importer = create_importer(); rows = collect_rows(importer)
        except (OSError, TypeError, ValueError, KeyError) as error:
            messagebox.showerror("검증 오류 · Validation Error", str(error), parent=window); return False
        state["importer"] = importer; state["rows"] = rows; state["invalid"] = [row for row in rows if row["error"]]
        fill_table(preview_tree, rows)
        preview_status.configure(text=f"분석된 행 {len(rows):,}개 · 최대 500행 미리보기 · Analyzed {len(rows):,} rows")
        fill_table(validation_tree, rows)
        valid = len(rows) - len(state["invalid"])
        validation_status.configure(text=f"정상 {valid:,}  ·  실패 {len(state['invalid']):,}  ·  필수 필드는 빨간색 행을 확인하세요.")
        export_failed_button.configure(state="normal" if state["invalid"] else "disabled")
        return True

    def export_invalid():
        try: rows = failed_rows(state["importer"])
        except Exception as error: messagebox.showerror("내보내기 오류", str(error), parent=window); return
        destination = filedialog.asksaveasfilename(parent=window, title="실패 행 저장", defaultextension=".xlsx", initialfile=f"{Path(state['file_path']).stem}_failed.xlsx", filetypes=(("Excel", "*.xlsx"),))
        if not destination: return
        try: export_failed_rows(rows, destination)
        except (OSError, ValueError) as error: messagebox.showerror("내보내기 오류", str(error), parent=window); return
        messagebox.showinfo("내보내기 완료", f"실패 행을 저장했습니다.\n{destination}", parent=window)

    def worker(importer):
        try: events.put(("complete", importer.run(lambda **value: events.put(("progress", value)))))
        except BaseException as error: events.put(("error", error))

    def process_events():
        while True:
            try: event_type, payload = events.get_nowait()
            except queue.Empty: break
            if event_type == "progress":
                progress_status.configure(text=progress_text(payload)); progress_bar.set(max(0, min(1, payload.get("percentage", 0) / 100)))
            elif event_type == "complete":
                state["running"] = False; cancel_button.configure(state="disabled")
                run_store.record(profile, state["file_path"], len(state["rows"]), payload)
                summary_box.delete("1.0", "end"); summary_box.insert("1.0", _bilingual_summary(payload, profile, len(state["rows"])))
                display_step(5)
                if on_complete: on_complete()
            elif event_type == "error":
                state["running"] = False; messagebox.showerror("가져오기 오류 · Import Error", str(payload), parent=window); display_step(3)
        if state["running"] and window.winfo_exists(): window.after(80, process_events)

    def start_import():
        state["running"] = True; progress_bar.set(0); cancel_button.configure(state="normal")
        display_step(4); threading.Thread(target=worker, args=(state["importer"],), daemon=True).start(); window.after(80, process_events)

    def next_step():
        step = state["step"]
        if step == 0: choose_file()
        elif step == 1:
            if prepare_preview(): display_step(2)
        elif step == 2: display_step(3)
        elif step == 3: start_import()
        elif step == 5: window.destroy()

    def cancel_import():
        if state["running"] and state["importer"]:
            state["importer"].cancel(); cancel_button.configure(state="disabled", text="취소 요청 중…")

    def close_window():
        if state["running"]:
            cancel_import(); messagebox.showinfo("취소 요청", "현재 행 처리가 끝나면 안전하게 중단됩니다.", parent=window); return
        window.destroy()

    select_button.configure(command=choose_file); sheet_selector.configure(command=change_sheet)
    export_failed_button.configure(command=export_invalid); cancel_button.configure(command=cancel_import)
    back_button.configure(command=lambda: display_step(max(0, state["step"] - 1))); next_button.configure(command=next_step)
    window.protocol("WM_DELETE_WINDOW", close_window)

    # tkinterdnd2 loads the native tkdnd package and exposes drop methods on Tk widgets.
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        TkinterDnD._require(window)
        drop_card.drop_target_register(DND_FILES)
        drop_card.dnd_bind("<<Drop>>", lambda event: analyze_file(window.tk.splitlist(event.data)[0]))
    except (ImportError, RuntimeError, TclError):
        file_detail.configure(text="드래그 앤 드롭을 사용할 수 없습니다. 파일 선택 버튼을 이용하세요.")

    pages[0].pack(fill="both", expand=True); display_step(0)
    return window


def _copy_summary(window, textbox):
    window.clipboard_clear(); window.clipboard_append(textbox.get("1.0", "end-1c"))


def _bilingual_summary(summary, profile, total):
    return (
        f"가져오기 결과 · Import Summary\n\n"
        f"Source: {profile.source}\nStatus: {summary.get('status', '')}\n"
        f"Analyzed rows: {total:,}\nImported rows: {int(summary.get('imported', 0) or 0):,}\n"
        f"Skipped rows: {int(summary.get('skipped', 0) or 0):,}\nFailed rows: {int(summary.get('failed', 0) or 0):,}\n"
        f"Duration: {float(summary.get('elapsed', 0) or 0):.2f}s\n\n"
        + format_import_summary(summary)
    )
