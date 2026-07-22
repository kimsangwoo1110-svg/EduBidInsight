"""학교360 통합 대시보드와 예정사업 관리 화면."""

import customtkinter as ctk
from tkinter import filedialog, messagebox

from gui.ui_theme import COLORS, FONTS, card, own_child_window, secondary_button
from services.project_import_service import ProjectImportService
from services.project_service import ProjectService
from services.school360_view_model import School360MockProvider, normalize_school_selection


def format_currency(value):
    return f"{int(value or 0):,}원"


def open_school360_window(parent, school, data_provider=School360MockProvider):
    school = normalize_school_selection(school)
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title(f"학교360 · {school['school_name']}")
    window.geometry("1400x860")
    window.minsize(1080, 700)
    build_school360(window, school, data_provider=data_provider)
    return window


def build_school360(parent, school, data_provider=School360MockProvider):
    school = normalize_school_selection(school)
    container = ctk.CTkFrame(parent, fg_color=COLORS["window"], corner_radius=0)
    container.pack(fill="both", expand=True)

    header = ctk.CTkFrame(container, fg_color=COLORS["surface"], corner_radius=0)
    header.pack(fill="x")
    heading = ctk.CTkFrame(header, fg_color="transparent")
    heading.pack(side="left", fill="x", expand=True, padx=24, pady=14)
    ctk.CTkLabel(heading, text=school["school_name"], font=FONTS["display"], anchor="w").pack(fill="x")
    ctk.CTkLabel(
        heading, text=f"학교360  ·  {school['school_code']}  ·  통합 학교 정보",
        font=FONTS["body"], text_color=COLORS["muted"], anchor="w",
    ).pack(fill="x")
    badge = ctk.CTkLabel(
        header, text="외부 데이터: 모의 연동", height=30, corner_radius=15,
        fg_color=COLORS["orange_tint"], text_color=COLORS["orange"],
        font=FONTS["caption"],
    )
    badge.pack(side="right", padx=(8, 14))

    content = ctk.CTkScrollableFrame(container, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=14, pady=(10, 8))
    content.grid_columnconfigure(0, weight=1, uniform="school360")
    content.grid_columnconfigure(1, weight=1, uniform="school360")

    def section(row, column, title, subtitle=""):
        panel = card(content)
        panel.grid(row=row, column=column, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(panel, text=title, font=FONTS["section"], anchor="w").pack(fill="x", padx=16, pady=(13, 1))
        ctk.CTkLabel(panel, text=subtitle, font=FONTS["caption"], text_color=COLORS["muted"], anchor="w").pack(fill="x", padx=16, pady=(0, 7))
        return panel

    basic_panel = section(0, 0, "기본 정보", "학교정보 공개 API 모의 데이터")
    stats_panel = section(0, 1, "학교 통계", "학교 및 사업 현황 요약")
    project_panel = section(1, 0, "예정사업", "등록·수정·삭제 및 Excel 일괄 가져오기")
    procurement_panel = section(1, 1, "조달 현황", "학교장터 및 나라장터 모의 데이터")
    crm_panel = section(2, 0, "고객 관계 관리", "읽기 전용 모의 활동")
    attachment_panel = section(2, 1, "첨부파일", "화면 표시용 모의 파일")

    status = ctk.CTkLabel(container, text="", height=28, font=FONTS["caption"], text_color=COLORS["muted"], anchor="w")
    status.pack(side="bottom", fill="x", padx=22, pady=(0, 4))

    def clear(panel):
        for child in panel.winfo_children()[2:]:
            child.destroy()

    def line(panel, values):
        row = ctk.CTkFrame(panel, fg_color=COLORS["surface_alt"], corner_radius=7)
        row.pack(fill="x", padx=13, pady=4)
        for text, width, anchor, color, font in values:
            ctk.CTkLabel(
                row, text=str(text or "—"), width=width, anchor=anchor,
                text_color=color or COLORS["text"], font=font or FONTS["body"],
                wraplength=250,
            ).pack(side="left", fill="x" if width == 0 else None, expand=width == 0, padx=7, pady=8)
        return row

    def open_project_form(project=None):
        form = ctk.CTkToplevel(parent.winfo_toplevel())
        own_child_window(form, parent.winfo_toplevel())
        form.title("사업 수정" if project else "사업 추가")
        form.geometry("620x670")
        form.minsize(560, 620)
        form.grab_set()
        ctk.CTkLabel(form, text="사업 수정" if project else "사업 추가", font=FONTS["title"], anchor="w").pack(fill="x", padx=24, pady=(18, 6))
        fields = ctk.CTkScrollableFrame(form, fg_color="transparent")
        fields.pack(fill="both", expand=True, padx=18, pady=5)
        fields.grid_columnconfigure(1, weight=1)
        variables = {}
        definitions = (
            ("project_name", "사업명", project.get("project_name", "") if project else ""),
            ("category", "사업 분류", project.get("category", "") if project else ""),
            ("budget", "예산(원)", project.get("budget", "") if project else ""),
            ("start_year", "시작 연도", project.get("start_year", "") if project else ""),
            ("end_year", "종료 연도", project.get("end_year", "") if project else ""),
            ("expected_procurement_date", "예상 조달일", project.get("expected_procurement_date", "") if project else ""),
            ("source", "출처", project.get("source", "수동 등록") if project else "수동 등록"),
        )
        for row_index, (key, label, value) in enumerate(definitions):
            ctk.CTkLabel(fields, text=label, font=FONTS["body_bold"], anchor="w").grid(row=row_index, column=0, padx=8, pady=7, sticky="w")
            variable = ctk.StringVar(value=str(value or "")); variables[key] = variable
            ctk.CTkEntry(fields, textvariable=variable, height=40).grid(row=row_index, column=1, padx=8, pady=7, sticky="ew")
        ctk.CTkLabel(fields, text="상태", font=FONTS["body_bold"], anchor="w").grid(row=7, column=0, padx=8, pady=7, sticky="w")
        status_variable = ctk.StringVar(value=project.get("status", "예정") if project else "예정")
        ctk.CTkOptionMenu(fields, variable=status_variable, values=list(ProjectService.STATUS_OPTIONS), height=40).grid(row=7, column=1, padx=8, pady=7, sticky="ew")
        ctk.CTkLabel(fields, text="메모", font=FONTS["body_bold"], anchor="nw").grid(row=8, column=0, padx=8, pady=7, sticky="nw")
        memo = ctk.CTkTextbox(fields, height=110)
        memo.grid(row=8, column=1, padx=8, pady=7, sticky="ew")
        memo.insert("1.0", project.get("memo", "") if project else "")

        def optional_year(key):
            text = variables[key].get().strip()
            return int(text) if text else None

        def save():
            try:
                values = {
                    "project_name": variables["project_name"].get(), "category": variables["category"].get(),
                    "status": status_variable.get(),
                    "budget": float(variables["budget"].get().replace(",", "").replace("원", "").strip() or 0),
                    "start_year": optional_year("start_year"), "end_year": optional_year("end_year"),
                    "source": variables["source"].get(),
                    "expected_procurement_date": variables["expected_procurement_date"].get(),
                    "memo": memo.get("1.0", "end-1c"),
                }
                if values["start_year"] and values["end_year"] and values["end_year"] < values["start_year"]:
                    raise ValueError("종료 연도는 시작 연도보다 빠를 수 없습니다.")
                if values["budget"] < 0:
                    raise ValueError("예산은 0 이상이어야 합니다.")
                if project:
                    ProjectService.update(project["id"], **values)
                else:
                    ProjectService.create(school["school_code"], **values)
            except (TypeError, ValueError) as error:
                messagebox.showerror("입력 오류", str(error), parent=form)
                return
            form.grab_release(); form.destroy(); render()

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(5, 16))
        secondary_button(buttons, text="취소", width=100, command=form.destroy).pack(side="right")
        ctk.CTkButton(buttons, text="저장", width=120, command=save, font=FONTS["body_bold"]).pack(side="right", padx=8)

    def delete_project(project):
        if messagebox.askyesno("사업 삭제", f"'{project['project_name']}' 사업을 삭제할까요?", parent=parent.winfo_toplevel()):
            ProjectService.delete(project["id"])
            render()

    def import_projects():
        path = filedialog.askopenfilename(parent=parent.winfo_toplevel(), title="예정사업 Excel 파일 선택", filetypes=(("Excel 통합 문서", "*.xlsx"),))
        if not path:
            return
        try:
            summary = ProjectImportService.import_excel(path, school["school_code"])
        except (OSError, ValueError) as error:
            messagebox.showerror("가져오기 오류", str(error), parent=parent.winfo_toplevel())
            return
        errors = "\n".join(summary["errors"][:5])
        messagebox.showinfo(
            "가져오기 완료",
            f"전체 {summary['rows']:,}행\n등록 {summary['inserted']:,}건\n수정 {summary['updated']:,}건\n실패 {summary['failed']:,}건" + (f"\n\n{errors}" if errors else ""),
            parent=parent.winfo_toplevel(),
        )
        render()

    def download_template():
        path = filedialog.asksaveasfilename(parent=parent.winfo_toplevel(), title="예정사업 양식 저장", defaultextension=".xlsx", initialfile="예정사업_가져오기_양식.xlsx", filetypes=(("Excel 통합 문서", "*.xlsx"),))
        if path:
            ProjectImportService.create_template(path)
            messagebox.showinfo("양식 저장 완료", "예정사업 양식을 저장했습니다.", parent=parent.winfo_toplevel())

    def render():
        snapshot = data_provider.dashboard(school)
        current = snapshot["school"]
        projects = ProjectService.list_for_school(school["school_code"])
        stats = dict(snapshot["statistics"])
        stats["planned_projects"] = len(projects)
        stats["planned_budget"] = sum(float(project.get("budget") or 0) for project in projects)
        for panel in (basic_panel, stats_panel, project_panel, procurement_panel, crm_panel, attachment_panel):
            clear(panel)

        for label, value in (
            ("학교코드", current.get("school_code")), ("학교급", current.get("school_type")),
            ("교육청", current.get("office")), ("지역", current.get("region")),
            ("주소", current.get("address")), ("홈페이지", current.get("homepage")),
        ):
            line(basic_panel, ((label, 125, "w", COLORS["muted"], FONTS["caption"]), (value, 0, "w", None, FONTS["body_bold"])))
        ctk.CTkFrame(basic_panel, fg_color="transparent", height=7).pack()

        stat_grid = ctk.CTkFrame(stats_panel, fg_color="transparent")
        stat_grid.pack(fill="both", expand=True, padx=8, pady=(3, 10))
        stat_items = (
            ("학생수", f"{stats['students']:,}"), ("학급수", f"{stats['classes']:,}"),
            ("예정사업", f"{stats['planned_projects']:,}건"), ("사업 예산", format_currency(stats["planned_budget"])),
            ("조달 건수", f"{stats['procurement_count']:,}건"), ("조달 금액", format_currency(stats["procurement_total"])),
            ("고객 활동", f"{stats['crm_activities']:,}건"), ("첨부파일", f"{stats['attachments']:,}개"),
        )
        for index, (label, value) in enumerate(stat_items):
            stat = ctk.CTkFrame(stat_grid, fg_color=COLORS["blue_tint"], corner_radius=8)
            stat.grid(row=index // 2, column=index % 2, padx=5, pady=5, sticky="nsew")
            stat_grid.grid_columnconfigure(index % 2, weight=1, uniform="stat")
            ctk.CTkLabel(stat, text=label, font=FONTS["caption"], text_color=COLORS["muted"], anchor="w").pack(fill="x", padx=12, pady=(9, 1))
            ctk.CTkLabel(stat, text=value, font=FONTS["section"], text_color=COLORS["blue"], anchor="w").pack(fill="x", padx=12, pady=(1, 9))

        tools = ctk.CTkFrame(project_panel, fg_color="transparent")
        tools.pack(fill="x", padx=10, pady=(1, 7))
        ctk.CTkButton(tools, text="사업 추가", width=100, command=open_project_form, font=FONTS["body_bold"]).pack(side="left", padx=3)
        secondary_button(tools, text="예정사업 가져오기", width=150, command=import_projects).pack(side="left", padx=3)
        secondary_button(tools, text="양식 다운로드", width=120, command=download_template).pack(side="left", padx=3)
        if not projects:
            ctk.CTkLabel(project_panel, text="등록된 예정사업이 없습니다.", font=FONTS["body"], text_color=COLORS["muted"], anchor="w").pack(fill="x", padx=17, pady=20)
        for project in projects:
            project_row = line(project_panel, (
                (project["project_name"], 0, "w", None, FONTS["body_bold"]),
                (project["status"], 58, "center", COLORS["orange"], FONTS["caption"]),
                (format_currency(project["budget"]), 112, "e", None, FONTS["body"]),
            ))
            secondary_button(project_row, text="수정", width=52, height=30, command=lambda item=project: open_project_form(item)).pack(side="left", padx=2)
            secondary_button(project_row, text="삭제", width=52, height=30, command=lambda item=project: delete_project(item)).pack(side="left", padx=(0, 6))
            period = f"{project.get('start_year') or '미정'} ~ {project.get('end_year') or '미정'}"
            procurement = project.get("expected_procurement_date") or "미정"
            ctk.CTkLabel(
                project_panel,
                text=f"{project.get('category') or '미분류'}  ·  사업기간 {period}  ·  예상 조달일 {procurement}\n{project.get('memo') or '메모 없음'}",
                font=FONTS["caption"], text_color=COLORS["muted"], anchor="w", justify="left", wraplength=590,
            ).pack(fill="x", padx=21, pady=(0, 6))
        ctk.CTkFrame(project_panel, fg_color="transparent", height=7).pack()

        for item in snapshot["procurement"]:
            line(procurement_panel, ((item["source"], 48, "center", COLORS["blue"], FONTS["caption"]), (item["item"], 0, "w", None, FONTS["body_bold"]), (format_currency(item["amount"]), 115, "e", None, FONTS["body"])))
            ctk.CTkLabel(procurement_panel, text=f"{item['date']}  ·  {item['vendor']}", font=FONTS["caption"], text_color=COLORS["muted"], anchor="w").pack(fill="x", padx=21, pady=(0, 3))
        ctk.CTkFrame(procurement_panel, fg_color="transparent", height=7).pack()

        for activity in snapshot["crm"]:
            line(crm_panel, ((activity["date"], 90, "w", COLORS["muted"], FONTS["caption"]), (activity["type"], 52, "center", COLORS["green"], FONTS["caption"]), (activity["summary"], 0, "w", None, FONTS["body_bold"]), (activity["status"], 75, "e", COLORS["blue"], FONTS["caption"])))
        ctk.CTkFrame(crm_panel, fg_color="transparent", height=7).pack()

        for attachment in snapshot["attachments"]:
            line(attachment_panel, ((attachment["type"], 75, "center", COLORS["blue"], FONTS["caption"]), (attachment["name"], 0, "w", None, FONTS["body_bold"]), (attachment["size"], 62, "e", COLORS["muted"], FONTS["caption"])))
        ctk.CTkFrame(attachment_panel, fg_color="transparent", height=7).pack()
        source_labels = {
            "School Info OpenAPI": "학교정보 공개 API",
            "Education Office": "교육청",
            "School Market (S2B)": "학교장터(S2B)",
            "NaraJangteo (G2B)": "나라장터(G2B)",
            "CRM Mock": "고객 활동 모의 연동",
            "Attachment Mock": "첨부파일 모의 연동",
        }
        status.configure(
            text="외부 데이터는 모의 연동 자료입니다.  ·  "
            + "  |  ".join(source_labels.get(source, source) for source in snapshot["connector_sources"])
        )

    refresh_button = secondary_button(header, text="새로고침", width=105, command=render)
    refresh_button.pack(side="right", padx=8)
    render()
    return container
