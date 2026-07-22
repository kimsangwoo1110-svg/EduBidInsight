import webbrowser
from urllib.parse import urlparse

import customtkinter as ctk
from tkinter import Menu, messagebox, ttk

from gui.crm import build_school_crm
from gui.dashboard import build_school_dashboard
from gui.school_profile import build_school_profile, open_school_profile
from gui.ui_theme import create_empty_state, own_child_window, update_empty_state
from services.contract_service import ContractService
from services.excel_service import export_school_excel
from services.project_service import ProjectService
from services.region_data import OFFICES
from services.rule_service import RuleService
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


def sort_treeview_column(tree, column_id, is_numeric, sort_directions):
    """Sort one Treeview column, toggling only that column's direction."""
    reverse = not sort_directions[column_id] if column_id in sort_directions else False
    sort_directions[column_id] = reverse

    def sort_key(item_id):
        value = tree.set(item_id, column_id)
        if is_numeric:
            try:
                return int(str(value).replace(",", ""))
            except ValueError:
                return 0
        return str(value).casefold()

    ordered_items = sorted(tree.get_children(""), key=sort_key, reverse=reverse)
    for index, item_id in enumerate(ordered_items):
        tree.move(item_id, "", index)

    return reverse


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
    own_child_window(detail, parent)
    detail.title(row[SCHOOL_NAME_INDEX])
    detail.geometry("1180x700")

    ctk.CTkLabel(
        detail,
        text=row[SCHOOL_NAME_INDEX],
        font=("맑은 고딕", 26, "bold"),
    ).pack(pady=20)

    tabs = ctk.CTkTabview(detail)
    tabs.pack(fill="both", expand=True, padx=20, pady=10)

    profile_tab = tabs.add("360° 프로필")
    school_tab = tabs.add("학교 정보")
    dashboard_tab = tabs.add("대시보드")
    crm_tab = tabs.add("CRM")
    project_tab = tabs.add("프로젝트")
    contract_tab = tabs.add("계약")
    insight_tab = tabs.add("영업 인사이트")
    market_tab = tabs.add("학교 시장")
    g2b_tab = tabs.add("G2B")
    ai_tab = tabs.add("AI 분석")

    build_school_profile(profile_tab, row[SCHOOL_CODE_INDEX])

    school_frame = ctk.CTkFrame(school_tab)
    school_frame.pack(fill="both", expand=True, padx=10, pady=10)

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
        line = ctk.CTkFrame(school_frame)
        line.pack(fill="x", pady=3)

        ctk.CTkLabel(
            line,
            text=title,
            width=120,
            anchor="w",
            font=("맑은 고딕", 13, "bold"),
        ).pack(side="left", padx=10)

        ctk.CTkLabel(line, text=value or "", anchor="w").pack(side="left")

    school_code = row[SCHOOL_CODE_INDEX]
    project_rows = {}
    build_school_dashboard(
        dashboard_tab,
        school_code,
        row[SCHOOL_NAME_INDEX],
    )
    build_school_crm(crm_tab, school_code)

    filter_frame = ctk.CTkFrame(project_tab)
    filter_frame.pack(fill="x", padx=10, pady=(12, 6))

    project_keyword = ctk.CTkEntry(
        filter_frame, width=180, placeholder_text="프로젝트명 검색"
    )
    project_keyword.grid(row=0, column=0, padx=8, pady=8)
    category_filter = ctk.CTkComboBox(filter_frame, width=130, values=["전체"])
    category_filter.grid(row=0, column=1, padx=4, pady=8)
    status_filter = ctk.CTkComboBox(
        filter_frame,
        width=110,
        values=["전체", *ProjectService.STATUS_OPTIONS],
    )
    status_filter.grid(row=0, column=2, padx=4, pady=8)
    year_filter = ctk.CTkComboBox(filter_frame, width=100, values=["전체"])
    year_filter.grid(row=0, column=3, padx=4, pady=8)
    category_filter.set("전체")
    status_filter.set("전체")
    year_filter.set("전체")

    summary_label = ctk.CTkLabel(project_tab, anchor="w")
    summary_label.pack(fill="x", padx=12, pady=(0, 6))

    project_columns = (
        "project_name",
        "category",
        "status",
        "budget",
        "period",
        "source",
    )
    project_tree = ttk.Treeview(
        project_tab,
        columns=project_columns,
        show="headings",
        height=12,
    )
    project_headings = (
        ("project_name", "프로젝트명", 260),
        ("category", "분류", 110),
        ("status", "상태", 110),
        ("budget", "예산", 180),
        ("period", "기간", 120),
        ("source", "출처", 140),
    )
    for column_id, heading, width in project_headings:
        project_tree.heading(column_id, text=heading)
        project_tree.column(column_id, width=width, anchor="center")

    project_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    status_colors = {
        "진행중": "#1F6AA5",
        "예정": "#D97706",
        "완료": "#2E8B57",
        "보류": "#7C3AED",
    }
    for status, color in status_colors.items():
        project_tree.tag_configure(status, foreground=color)

    def filter_values():
        year = year_filter.get()
        return {
            "project_name": project_keyword.get(),
            "category": category_filter.get(),
            "status": status_filter.get(),
            "year": None if year == "전체" else year,
        }

    def update_filter_options(projects):
        selected_category = category_filter.get()
        selected_year = year_filter.get()
        categories = ["전체"] + sorted(
            {project["category"] for project in projects if project["category"]}
        )
        years = sorted(
            {
                year
                for project in projects
                for year in (project["start_year"], project["end_year"])
                if year
            },
            reverse=True,
        )
        year_values = ["전체", *[str(year) for year in years]]
        category_filter.configure(values=categories)
        year_filter.configure(values=year_values)
        category_filter.set(
            selected_category if selected_category in categories else "전체"
        )
        year_filter.set(selected_year if selected_year in year_values else "전체")

    def refresh_projects():
        saved_projects = ProjectService.list_for_school(school_code)
        source_projects = saved_projects or ProjectService.sample_projects(school_code)
        update_filter_options(source_projects)
        filters = filter_values()
        if saved_projects:
            projects = ProjectService.list_for_school(school_code, **filters)
            message = "등록된 프로젝트"
        else:
            projects = ProjectService.filter_projects(source_projects, **filters)
            message = "등록된 프로젝트가 없어 샘플 데이터를 표시합니다."

        project_tree.delete(*project_tree.get_children())
        project_rows.clear()
        for index, project in enumerate(projects):
            start_year = project["start_year"] or "-"
            end_year = project["end_year"] or "-"
            item_id = f"project-{project['id'] or f'sample-{index}'}"
            project_rows[item_id] = project
            project_tree.insert(
                "",
                "end",
                iid=item_id,
                tags=(project["status"],),
                values=(
                    project["project_name"],
                    project["category"],
                    f"● {project['status'] or '-'}",
                    ProjectService.format_budget(project["budget"]),
                    f"{start_year} ~ {end_year}",
                    project["source"],
                ),
            )

        summary = ProjectService.summarize(projects)
        counts = summary["status_counts"]
        summary_label.configure(
            text=(
                f"{message} | 총 {summary['total_count']}건 | "
                f"총 예산 {ProjectService.format_budget(summary['total_budget'])} | "
                f"진행중 {counts['진행중']} · 예정 {counts['예정']} · "
                f"완료 {counts['완료']} · 보류 {counts['보류']}"
            )
        )

    def selected_project():
        selection = project_tree.selection()
        return project_rows.get(selection[0]) if selection else None

    def to_optional_year(value):
        value = value.strip()
        return int(value) if value else None

    def open_project_form(project=None):
        form = ctk.CTkToplevel(detail)
        own_child_window(form, detail)
        form.title("프로젝트 수정" if project else "프로젝트 등록")
        form.geometry("460x440")
        form.grab_set()

        fields = ctk.CTkFrame(form)
        fields.pack(fill="both", expand=True, padx=20, pady=20)

        def add_entry(label, row_index, value=""):
            ctk.CTkLabel(fields, text=label, anchor="w").grid(
                row=row_index, column=0, padx=8, pady=7, sticky="w"
            )
            entry = ctk.CTkEntry(fields, width=270)
            entry.insert(0, str(value or ""))
            entry.grid(row=row_index, column=1, padx=8, pady=7)
            return entry

        name_entry = add_entry("프로젝트명", 0, project["project_name"] if project else "")
        category_entry = add_entry("분류", 1, project["category"] if project else "")
        budget_entry = add_entry("예산(원)", 2, project["budget"] if project else "")
        start_year_entry = add_entry("시작연도", 3, project["start_year"] if project else "")
        end_year_entry = add_entry("종료연도", 4, project["end_year"] if project else "")
        source_entry = add_entry("출처", 5, project["source"] if project else "")
        ctk.CTkLabel(fields, text="상태", anchor="w").grid(
            row=6, column=0, padx=8, pady=7, sticky="w"
        )
        status_entry = ctk.CTkComboBox(fields, width=270, values=list(ProjectService.STATUS_OPTIONS))
        status_entry.set(project["status"] if project and project["status"] else "예정")
        status_entry.grid(row=6, column=1, padx=8, pady=7)

        def save_project():
            try:
                budget = float(budget_entry.get().replace(",", "").strip() or 0)
                start_year = to_optional_year(start_year_entry.get())
                end_year = to_optional_year(end_year_entry.get())
                if start_year and end_year and end_year < start_year:
                    raise ValueError("종료연도는 시작연도보다 빠를 수 없습니다.")
                values = (
                    name_entry.get(),
                    category_entry.get(),
                    status_entry.get(),
                    budget,
                    start_year,
                    end_year,
                    source_entry.get(),
                )
                if project:
                    ProjectService.update(project["id"], *values)
                else:
                    ProjectService.create(school_code, *values)
            except ValueError as error:
                messagebox.showerror("입력 오류", str(error), parent=form)
                return
            form.grab_release()
            form.destroy()
            refresh_projects()
            refresh_insights()

        ctk.CTkButton(form, text="저장", width=150, command=save_project).pack(
            pady=(0, 20)
        )

    def edit_selected_project():
        project = selected_project()
        if project is None:
            messagebox.showinfo("프로젝트", "수정할 프로젝트를 선택하세요.", parent=detail)
        elif project["id"] is None:
            messagebox.showinfo("프로젝트", "샘플 데이터는 수정할 수 없습니다.", parent=detail)
        else:
            open_project_form(project)

    def delete_selected_project():
        project = selected_project()
        if project is None:
            messagebox.showinfo("프로젝트", "삭제할 프로젝트를 선택하세요.", parent=detail)
        elif project["id"] is None:
            messagebox.showinfo("프로젝트", "샘플 데이터는 삭제할 수 없습니다.", parent=detail)
        elif messagebox.askyesno(
            "프로젝트 삭제",
            f"'{project['project_name']}' 프로젝트를 삭제할까요?",
            parent=detail,
        ):
            ProjectService.delete(project["id"])
            refresh_projects()
            refresh_insights()

    ctk.CTkButton(filter_frame, text="조회", width=70, command=refresh_projects).grid(
        row=0, column=4, padx=8, pady=8
    )
    ctk.CTkButton(
        filter_frame,
        text="초기화",
        width=70,
        command=lambda: (
            project_keyword.delete(0, "end"),
            category_filter.set("전체"),
            status_filter.set("전체"),
            year_filter.set("전체"),
            refresh_projects(),
        ),
    ).grid(row=0, column=5, padx=(0, 8), pady=8)

    project_button_frame = ctk.CTkFrame(project_tab, fg_color="transparent")
    project_button_frame.pack(pady=(0, 10))
    ctk.CTkButton(
        project_button_frame, text="등록", width=110, command=open_project_form
    ).pack(side="left", padx=4)
    ctk.CTkButton(
        project_button_frame, text="수정", width=110, command=edit_selected_project
    ).pack(side="left", padx=4)
    ctk.CTkButton(
        project_button_frame, text="삭제", width=110, command=delete_selected_project
    ).pack(side="left", padx=4)
    project_keyword.bind("<Return>", lambda _event: refresh_projects())

    contract_header = ctk.CTkFrame(contract_tab, fg_color="transparent")
    contract_header.pack(fill="x", padx=10, pady=(12, 6))
    contract_summary = ctk.CTkLabel(contract_header, anchor="w")
    contract_summary.pack(side="left", fill="x", expand=True)

    contract_tree = ttk.Treeview(
        contract_tab,
        columns=("date", "product", "category", "vendor", "quantity", "amount", "source"),
        show="headings",
        height=14,
    )
    for column, heading, width in (
        ("date", "계약일", 100),
        ("product", "품목", 230),
        ("category", "카테고리", 120),
        ("vendor", "업체", 190),
        ("quantity", "수량", 70),
        ("amount", "금액", 140),
        ("source", "원본 파일", 180),
    ):
        contract_tree.heading(column, text=heading)
        contract_tree.column(column, width=width, anchor="center")
    contract_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def refresh_contracts():
        contracts = ContractService.search_by_school(school_code)
        contract_tree.delete(*contract_tree.get_children())
        for contract in contracts:
            contract_tree.insert(
                "",
                "end",
                iid=f"contract-{contract['id']}",
                values=(
                    contract["contract_date"],
                    contract["product"],
                    contract["category"],
                    contract["vendor"],
                    f"{contract['quantity']:,}",
                    ContractService.format_amount(contract["amount"]),
                    contract["source_file"],
                ),
            )
        total_amount = sum(float(contract["amount"] or 0) for contract in contracts)
        contract_summary.configure(
            text=(
                f"계약 {len(contracts):,}건 · "
                f"총액 {ContractService.format_amount(total_amount)}"
            )
        )

    ctk.CTkButton(
        contract_header, text="새로고침", width=100, command=refresh_contracts
    ).pack(side="right")

    insight_header = ctk.CTkFrame(insight_tab, fg_color="transparent")
    insight_header.pack(fill="x", padx=10, pady=(12, 6))
    insight_summary = ctk.CTkLabel(insight_header, anchor="w")
    insight_summary.pack(side="left", fill="x", expand=True)
    ctk.CTkButton(
        insight_header, text="다시 평가", width=100, command=lambda: refresh_insights()
    ).pack(side="right")

    insight_columns = (
        "project_name",
        "recommendation",
        "score",
        "reason",
        "priority",
    )
    insight_tree = ttk.Treeview(
        insight_tab,
        columns=insight_columns,
        show="headings",
        height=14,
    )
    for column_id, heading, width in (
        ("project_name", "대상", 210),
        ("recommendation", "추천", 280),
        ("score", "점수", 70),
        ("reason", "근거", 410),
        ("priority", "우선순위", 90),
    ):
        insight_tree.heading(column_id, text=heading)
        insight_tree.column(column_id, width=width, anchor="center")
    insight_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    insight_tree.tag_configure("높음", foreground="#C2410C")
    insight_tree.tag_configure("보통", foreground="#1F6AA5")
    insight_tree.tag_configure("낮음", foreground="#64748B")

    def refresh_insights():
        saved_projects = ProjectService.list_for_school(school_code)
        projects = saved_projects or ProjectService.sample_projects(school_code)
        sample_notice = "" if saved_projects else " (샘플 프로젝트 기반)"
        contracts = ContractService.search_by_school(school_code)
        insights = (
            RuleService.evaluate_projects(projects)
            + RuleService.evaluate_contracts(contracts)
        )
        insights.sort(
            key=lambda insight: (-insight["score"], insight["project_name"].casefold())
        )
        insight_tree.delete(*insight_tree.get_children())
        for index, insight in enumerate(insights):
            insight_tree.insert(
                "",
                "end",
                iid=f"insight-{index}",
                tags=(insight["priority"],),
                values=(
                    (
                        "계약: " if insight.get("target_type") == "contract" else "프로젝트: "
                    ) + insight["project_name"],
                    insight["recommendation"],
                    insight["score"],
                    insight["reason"],
                    insight["priority"],
                ),
            )

        if insights:
            high_priority_count = sum(
                insight["priority"] == "높음" for insight in insights
            )
            insight_summary.configure(
                text=(
                    f"추천 기회 {len(insights)}건 · "
                    f"높은 우선순위 {high_priority_count}건{sample_notice}"
                )
            )
        else:
            insight_summary.configure(
                text="활성 규칙과 일치하는 프로젝트 또는 계약이 없습니다."
            )

    refresh_projects()
    refresh_contracts()
    refresh_insights()

    for tab, heading, description in (
        (market_tab, "학교 시장", "학교 시장 데이터는 향후 프로젝트 데이터를 기반으로 제공합니다."),
        (g2b_tab, "G2B", "나라장터 연계 데이터는 향후 업데이트에서 제공합니다."),
        (ai_tab, "AI 분석", "AI 분석은 프로젝트 및 입찰 데이터가 축적되면 제공합니다."),
    ):
        ctk.CTkLabel(tab, text=heading, font=("맑은 고딕", 20, "bold")).pack(
            pady=(45, 12)
        )
        ctk.CTkLabel(tab, text=description, text_color="gray").pack(padx=20)

    ctk.CTkButton(
        detail,
        text="닫기",
        width=150,
        command=detail.destroy,
    ).pack(pady=20)


def open_school_window(parent):
    """Open the school search window and its result actions."""
    popup = ctk.CTkToplevel(parent)
    own_child_window(popup, parent)
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
        sort_treeview_column(tree, column_id, is_numeric, sort_reverse)
        update_headings(column_id)

    for column_id, heading, width, is_numeric in TREE_COLUMNS:
        tree.column(column_id, width=width, anchor="center")
        tree.heading(
            column_id,
            text=heading,
            command=lambda col=column_id, numeric=is_numeric: sort_tree(col, numeric),
        )

    tree.pack(fill="both", expand=True, padx=20, pady=10)
    empty_state = create_empty_state(
        popup,
        "⌕  검색 조건에 맞는 학교가 없습니다.\nNo schools match your search.",
    )

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

    def open_selected_profile():
        row = selected_row()
        if row is not None:
            open_school_profile(popup, row[SCHOOL_CODE_INDEX])

    def open_selected_homepage():
        row = selected_row()
        homepage = normalize_homepage(row[HOMEPAGE_INDEX]) if row else None
        if homepage is None:
            messagebox.showinfo("홈페이지", "등록된 유효한 홈페이지 주소가 없습니다.", parent=popup)
            return
        webbrowser.open_new_tab(homepage)

    context_menu = Menu(popup, tearoff=False)
    context_menu.add_command(label="360° 프로필", command=open_selected_profile)
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
        update_empty_state(tree, empty_state)

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
