import webbrowser
from urllib.parse import urlparse

import customtkinter as ctk
from tkinter import Menu, messagebox, ttk

from services.excel_service import export_school_excel
from services.region_data import OFFICES
from services.school_service import SchoolService


SCHOOL_CODE_INDEX = 0
SCHOOL_NAME_INDEX = 1
SCHOOL_TYPE_INDEX = 2
OFFICE_INDEX = 3
REGION_INDEX = 4
ADDRESS_INDEX = 5
HOMEPAGE_INDEX = 6
AI_SCHOOL_INDEX = 7
DIGITAL_SCHOOL_INDEX = 8
SPACE_INNOVATION_INDEX = 9
GREEN_SMART_INDEX = 10
STUDENT_COUNT_INDEX = 11
CLASS_COUNT_INDEX = 12


TREE_COLUMNS = (
    ("school_name", "학교명", 340, False),
    ("school_type", "학교급", 120, False),
    ("office", "교육청", 240, False),
    ("region", "지역", 150, False),
    ("student_count", "학생수", 120, True),
    ("class_count", "학급수", 120, True),
)


def format_number(value):
    """Return a display-safe, thousands-separated number."""
    return f"{int(value or 0):,}"


def normalize_homepage(homepage):
    """Return a safe HTTP(S) URL for a stored homepage value."""
    value = str(homepage or "").strip()
    if not value:
        return None

    if not urlparse(value).scheme:
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return value


def open_school_detail(parent, row):
    """Open the detail dialog for a single school record."""
    detail = ctk.CTkToplevel(parent)
    detail.title(row[SCHOOL_NAME_INDEX])
    detail.geometry("700x620")

    ctk.CTkLabel(
        detail,
        text=row[SCHOOL_NAME_INDEX],
        font=("맑은 고딕", 26, "bold"),
    ).pack(pady=20)

    frame = ctk.CTkFrame(detail)
    frame.pack(fill="both", expand=True, padx=20, pady=10)

    infos = [
        ("학교코드", row[SCHOOL_CODE_INDEX]),
        ("학교명", row[SCHOOL_NAME_INDEX]),
        ("학교급", row[SCHOOL_TYPE_INDEX]),
        ("교육청", row[OFFICE_INDEX]),
        ("지역", row[REGION_INDEX]),
        ("주소", row[ADDRESS_INDEX]),
        ("홈페이지", row[HOMEPAGE_INDEX]),
        ("학생수", format_number(row[STUDENT_COUNT_INDEX])),
        ("학급수", format_number(row[CLASS_COUNT_INDEX])),
    ]

    for title, value in infos:
        line = ctk.CTkFrame(frame)
        line.pack(fill="x", pady=3)

        ctk.CTkLabel(
            line,
            text=title,
            width=120,
            anchor="w",
            font=("맑은 고딕", 13, "bold"),
        ).pack(side="left", padx=10)

        ctk.CTkLabel(line, text=value or "", anchor="w").pack(side="left")

    ctk.CTkButton(
        detail,
        text="닫기",
        width=150,
        command=detail.destroy,
    ).pack(pady=20)


def open_school_window(parent):
    """Open the school search window and its result actions."""
    popup = ctk.CTkToplevel(parent)
    popup.title("학교 검색")
    popup.geometry("1400x850")

    rows_by_school_code = {}
    item_school_codes = {}
    sort_reverse = {}

    title = ctk.CTkLabel(
        popup,
        text="학교 검색",
        font=("맑은 고딕", 32, "bold"),
    )
    title.pack(pady=20)

    search_frame = ctk.CTkFrame(popup)
    search_frame.pack(fill="x", padx=20)

    ctk.CTkLabel(search_frame, text="학교명").grid(row=0, column=0, padx=10)
    keyword = ctk.CTkEntry(
        search_frame,
        width=220,
        placeholder_text="학교명을 입력하세요",
    )
    keyword.grid(row=1, column=0, padx=10, pady=(0, 15))

    ctk.CTkLabel(search_frame, text="지역").grid(row=0, column=1)
    region = ctk.CTkComboBox(
        search_frame,
        width=180,
        values=list(OFFICES.keys()),
    )
    region.set("전체")
    region.grid(row=1, column=1, padx=10)

    ctk.CTkLabel(search_frame, text="학교급").grid(row=0, column=2)
    school_type = ctk.CTkComboBox(
        search_frame,
        width=180,
        values=["전체", "유치원", "초등학교", "중학교", "고등학교", "특수학교"],
    )
    school_type.set("전체")
    school_type.grid(row=1, column=2, padx=10)

    ctk.CTkLabel(search_frame, text="교육청").grid(row=0, column=3)
    office = ctk.CTkComboBox(
        search_frame,
        width=220,
        values=OFFICES["전체"],
    )
    office.set("전체")
    office.grid(row=1, column=3, padx=10)

    def change_region(choice):
        office.configure(values=OFFICES[choice])
        office.set(OFFICES[choice][0])

    region.configure(command=change_region)

    option_frame = ctk.CTkFrame(popup)
    option_frame.pack(fill="x", padx=20, pady=10)

    ai_var = ctk.BooleanVar()
    digital_var = ctk.BooleanVar()
    space_var = ctk.BooleanVar()
    green_var = ctk.BooleanVar()

    ctk.CTkCheckBox(option_frame, text="AI중점학교", variable=ai_var).pack(
        side="left", padx=15
    )
    ctk.CTkCheckBox(option_frame, text="디지털선도학교", variable=digital_var).pack(
        side="left", padx=15
    )
    ctk.CTkCheckBox(option_frame, text="공간혁신학교", variable=space_var).pack(
        side="left", padx=15
    )
    ctk.CTkCheckBox(option_frame, text="그린스마트학교", variable=green_var).pack(
        side="left", padx=15
    )

    result_count = ctk.CTkLabel(
        popup,
        text="검색 결과 : 0건",
        font=("맑은 고딕", 14, "bold"),
    )
    result_count.pack(anchor="w", padx=20)

    column_ids = tuple(column[0] for column in TREE_COLUMNS)
    tree = ttk.Treeview(popup, columns=column_ids, show="headings", height=20)

    def selected_item():
        selection = tree.selection()
        return selection[0] if selection else None

    def selected_row():
        item_id = selected_item()
        if not item_id:
            return None
        school_code = item_school_codes.get(item_id)
        return rows_by_school_code.get(school_code)

    def displayed_rows():
        rows = []
        for item_id in tree.get_children(""):
            school_code = item_school_codes.get(item_id)
            row = rows_by_school_code.get(school_code)
            if row is not None:
                rows.append(row)
        return rows

    def update_headings(active_column=None):
        for column_id, heading, _, is_numeric in TREE_COLUMNS:
            indicator = ""
            if column_id == active_column:
                indicator = " ▼" if sort_reverse[column_id] else " ▲"
            tree.heading(
                column_id,
                text=f"{heading}{indicator}",
                command=lambda col=column_id, numeric=is_numeric: sort_tree(col, numeric),
            )

    def sort_tree(column_id, is_numeric):
        reverse = sort_reverse.get(column_id, True)
        sort_reverse[column_id] = reverse

        def sort_key(item_id):
            value = tree.set(item_id, column_id)
            if is_numeric:
                try:
                    return int(value.replace(",", ""))
                except (AttributeError, ValueError):
                    return 0
            return value.casefold()

        ordered_items = sorted(tree.get_children(""), key=sort_key, reverse=reverse)
        for index, item_id in enumerate(ordered_items):
            tree.move(item_id, "", index)

        update_headings(column_id)

    for column_id, heading, width, is_numeric in TREE_COLUMNS:
        tree.column(column_id, width=width, anchor="center")
        tree.heading(
            column_id,
            text=heading,
            command=lambda col=column_id, numeric=is_numeric: sort_tree(col, numeric),
        )

    tree.pack(fill="both", expand=True, padx=20, pady=10)

    def copy_text(value):
        popup.clipboard_clear()
        popup.clipboard_append(str(value or ""))
        popup.update_idletasks()

    def copy_selected_row(_event=None):
        row = selected_row()
        if row is None:
            return "break"

        values = [
            row[SCHOOL_NAME_INDEX],
            row[SCHOOL_TYPE_INDEX],
            row[OFFICE_INDEX],
            row[REGION_INDEX],
            format_number(row[STUDENT_COUNT_INDEX]),
            format_number(row[CLASS_COUNT_INDEX]),
        ]
        copy_text("\t".join(str(value or "") for value in values))
        return "break"

    def copy_selected_field(index):
        row = selected_row()
        if row is not None:
            copy_text(row[index])

    def open_selected_detail(_event=None):
        row = selected_row()
        if row is not None:
            open_school_detail(popup, row)
        return "break"

    def open_selected_homepage():
        row = selected_row()
        homepage = normalize_homepage(row[HOMEPAGE_INDEX]) if row else None
        if homepage is None:
            messagebox.showinfo("홈페이지", "등록된 유효한 홈페이지 주소가 없습니다.", parent=popup)
            return
        webbrowser.open_new_tab(homepage)

    context_menu = Menu(popup, tearoff=False)
    context_menu.add_command(label="상세 보기", command=open_selected_detail)
    context_menu.add_command(label="홈페이지 열기", command=open_selected_homepage)
    context_menu.add_separator()
    context_menu.add_command(
        label="학교명 복사",
        command=lambda: copy_selected_field(SCHOOL_NAME_INDEX),
    )
    context_menu.add_command(
        label="학교코드 복사",
        command=lambda: copy_selected_field(SCHOOL_CODE_INDEX),
    )
    context_menu.add_command(
        label="주소 복사",
        command=lambda: copy_selected_field(ADDRESS_INDEX),
    )

    def show_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return

        tree.selection_set(item_id)
        tree.focus(item_id)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def matches_project_filters(row):
        return not (
            (ai_var.get() and not row[AI_SCHOOL_INDEX])
            or (digital_var.get() and not row[DIGITAL_SCHOOL_INDEX])
            or (space_var.get() and not row[SPACE_INNOVATION_INDEX])
            or (green_var.get() and not row[GREEN_SMART_INDEX])
        )

    def insert_row(row):
        school_code = str(row[SCHOOL_CODE_INDEX] or "")
        item_id = school_code or "__missing_school_code__"
        item_school_codes[item_id] = school_code
        tree.insert(
            "",
            "end",
            iid=item_id,
            values=(
                row[SCHOOL_NAME_INDEX],
                row[SCHOOL_TYPE_INDEX],
                row[OFFICE_INDEX],
                row[REGION_INDEX],
                format_number(row[STUDENT_COUNT_INDEX]),
                format_number(row[CLASS_COUNT_INDEX]),
            ),
        )

    def search():
        tree.delete(*tree.get_children())
        rows_by_school_code.clear()
        item_school_codes.clear()
        sort_reverse.clear()

        rows = SchoolService.search(
            keyword=keyword.get(),
            region=region.get(),
            school_type=school_type.get(),
            office=office.get(),
        )

        for row in rows:
            if not matches_project_filters(row):
                continue

            school_code = str(row[SCHOOL_CODE_INDEX] or "")
            rows_by_school_code[school_code] = row
            insert_row(row)

        result_count.configure(text=f"검색 결과 : {len(rows_by_school_code):,}건")
        update_headings()

    def reset():
        keyword.delete(0, "end")
        region.set("전체")
        school_type.set("전체")
        office.configure(values=OFFICES["전체"])
        office.set("전체")
        ai_var.set(False)
        digital_var.set(False)
        space_var.set(False)
        green_var.set(False)
        search()

    tree.bind("<Double-1>", open_selected_detail)
    tree.bind("<Control-c>", copy_selected_row)
    tree.bind("<Control-C>", copy_selected_row)
    tree.bind("<Button-3>", show_context_menu)

    button_frame = ctk.CTkFrame(popup, fg_color="transparent")
    button_frame.pack(pady=10)

    ctk.CTkButton(button_frame, text="검색", width=150, command=search).pack(
        side="left", padx=5
    )
    ctk.CTkButton(button_frame, text="초기화", width=150, command=reset).pack(
        side="left", padx=5
    )
    ctk.CTkButton(
        button_frame,
        text="Excel 다운로드",
        width=180,
        command=lambda: export_school_excel(displayed_rows()),
    ).pack(side="left", padx=5)

    search()
