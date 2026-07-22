"""Configurable rule-management windows for the opportunity engine."""

import json

import customtkinter as ctk
from tkinter import messagebox, ttk

from gui.ui_theme import own_child_window
from services.contract_service import ContractService
from services.project_service import ProjectService
from services.rule_service import RuleService
from services.school_service import SchoolService


RULE_TABLE_COLUMNS = (
    ("enabled", "활성", 70),
    ("category", "카테고리", 140),
    ("recommendation", "추천", 260),
    ("score", "점수", 70),
    ("description", "설명", 430),
)


def sort_rule_records(rules, column, reverse=False):
    """Return a sorted copy of rule rows for the management table."""
    if column == "score":
        key = lambda rule: int(rule.get(column) or 0)
    elif column == "enabled":
        key = lambda rule: bool(rule.get(column))
    else:
        key = lambda rule: str(rule.get(column) or "").casefold()
    return sorted(rules, key=key, reverse=reverse)


def rule_table_values(rule):
    """Map a rule to its localized table representation."""
    return (
        "사용" if rule.get("enabled") else "중지",
        rule.get("category", ""),
        rule.get("recommendation", ""),
        int(rule.get("score") or 0),
        rule.get("description", ""),
    )


def rule_test_display_values(result):
    """Map a service test result to the three values shown by the UI."""
    return (
        "일치" if result["match"] else "불일치",
        str(result["score"]),
        result["reason"],
    )


def open_rule_manager(parent):
    """Open the rule list with CRUD and test actions."""
    manager = ctk.CTkToplevel(parent)
    own_child_window(manager, parent)
    manager.title("규칙 관리")
    manager.geometry("1150x720")

    ctk.CTkLabel(
        manager,
        text="영업 기회 규칙 관리",
        font=("맑은 고딕", 25, "bold"),
    ).pack(pady=(18, 4))
    ctk.CTkLabel(
        manager,
        text="영업 추천 규칙을 코드 수정 없이 관리합니다.",
        text_color="gray",
    ).pack(pady=(0, 12))

    table = ttk.Treeview(
        manager,
        columns=tuple(column[0] for column in RULE_TABLE_COLUMNS),
        show="headings",
        height=19,
    )
    table.pack(fill="both", expand=True, padx=18, pady=8)
    table.tag_configure("disabled", foreground="#8A8A8A")

    rules_by_item = {}
    sort_directions = {}

    def selected_rule():
        selection = table.selection()
        return rules_by_item.get(selection[0]) if selection else None

    def require_selected_rule():
        rule = selected_rule()
        if rule is None:
            messagebox.showinfo("규칙 관리", "규칙을 선택하세요.", parent=manager)
        return rule

    def render_rules(rules, selected_id=None):
        table.delete(*table.get_children())
        rules_by_item.clear()
        selected_item = None
        for rule in rules:
            item_id = f"rule-{rule['id']}"
            rules_by_item[item_id] = rule
            table.insert(
                "",
                "end",
                iid=item_id,
                tags=(() if rule["enabled"] else ("disabled",)),
                values=rule_table_values(rule),
            )
            if rule["id"] == selected_id:
                selected_item = item_id
        if selected_item:
            table.selection_set(selected_item)
            table.focus(selected_item)

    def refresh_rules(selected_id=None):
        render_rules(RuleService.list(), selected_id)

    def sort_table(column):
        reverse = not sort_directions.get(column, True)
        sort_directions[column] = reverse
        selected = selected_rule()
        render_rules(
            sort_rule_records(list(rules_by_item.values()), column, reverse),
            selected["id"] if selected else None,
        )
        for column_id, heading, _width in RULE_TABLE_COLUMNS:
            indicator = ""
            if column_id == column:
                indicator = " ▼" if reverse else " ▲"
            table.heading(column_id, text=f"{heading}{indicator}")

    for column_id, heading, width in RULE_TABLE_COLUMNS:
        table.heading(
            column_id,
            text=heading,
            command=lambda selected_column=column_id: sort_table(selected_column),
        )
        table.column(column_id, width=width, anchor="center")

    def open_rule_form(rule=None):
        form = ctk.CTkToplevel(manager)
        own_child_window(form, manager)
        form.title("규칙 수정" if rule else "규칙 생성")
        form.geometry("760x690")
        form.grab_set()

        content = ctk.CTkFrame(form)
        content.pack(fill="both", expand=True, padx=18, pady=18)
        content.grid_columnconfigure(1, weight=1)

        def add_entry(label, row, value=""):
            ctk.CTkLabel(content, text=label, anchor="w").grid(
                row=row, column=0, padx=10, pady=7, sticky="nw"
            )
            entry = ctk.CTkEntry(content)
            entry.insert(0, str(value or ""))
            entry.grid(row=row, column=1, padx=10, pady=7, sticky="ew")
            return entry

        category_entry = add_entry("카테고리", 0, rule["category"] if rule else "")
        recommendation_entry = add_entry(
            "추천", 1, rule["recommendation"] if rule else ""
        )
        score_entry = add_entry("점수", 2, rule["score"] if rule else 0)
        description_entry = add_entry("설명", 3, rule["description"] if rule else "")

        ctk.CTkLabel(content, text="JSON 조건", anchor="w").grid(
            row=4, column=0, padx=10, pady=7, sticky="nw"
        )
        condition_editor = ctk.CTkTextbox(content, height=270, wrap="none")
        condition_editor.grid(row=4, column=1, padx=10, pady=7, sticky="nsew")
        content.grid_rowconfigure(4, weight=1)
        if rule:
            try:
                initial_condition = RuleService.format_condition(rule["condition"])
            except (ValueError, TypeError, json.JSONDecodeError):
                initial_condition = str(rule["condition"] or "")
        else:
            initial_condition = json.dumps(
                {"field": "category", "operator": "contains", "value": ""},
                ensure_ascii=False,
                indent=2,
            )
        condition_editor.insert("1.0", initial_condition)

        help_text = (
            "필드: project_name, category, status, budget, start_year, end_year, source\n"
            "계약 필드: contract_date, product, vendor, quantity, amount, source_file\n"
            "연산자: equals, not_equals, contains, in, gt, gte, lt, lte · "
            "복합 조건: all, any"
        )
        ctk.CTkLabel(
            content,
            text=help_text,
            justify="left",
            anchor="w",
            text_color="gray",
        ).grid(row=5, column=1, padx=10, pady=(0, 6), sticky="w")

        enabled_var = ctk.BooleanVar(value=bool(rule["enabled"]) if rule else True)
        ctk.CTkCheckBox(content, text="활성화", variable=enabled_var).grid(
            row=6, column=1, padx=10, pady=8, sticky="w"
        )

        def condition_text():
            return condition_editor.get("1.0", "end").strip()

        def validate_condition(show_success=True):
            try:
                RuleService.validate_condition(condition_text())
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                messagebox.showerror(
                    "JSON 조건 오류", str(error), parent=form
                )
                return False
            if show_success:
                messagebox.showinfo(
                    "JSON 조건", "유효한 규칙 조건입니다.", parent=form
                )
            return True

        def save_rule():
            if not validate_condition(show_success=False):
                return
            try:
                values = (
                    category_entry.get(),
                    condition_text(),
                    recommendation_entry.get(),
                    score_entry.get(),
                    description_entry.get(),
                    enabled_var.get(),
                )
                if rule:
                    RuleService.update(rule["id"], *values)
                    selected_id = rule["id"]
                else:
                    selected_id = RuleService.create(*values)
            except ValueError as error:
                messagebox.showerror("규칙 입력 오류", str(error), parent=form)
                return
            form.grab_release()
            form.destroy()
            refresh_rules(selected_id)

        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=2, pady=(10, 2))
        ctk.CTkButton(
            buttons, text="JSON 검증", width=120, command=validate_condition
        ).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text="저장", width=120, command=save_rule).pack(
            side="left", padx=5
        )
        ctk.CTkButton(buttons, text="취소", width=120, command=form.destroy).pack(
            side="left", padx=5
        )

    def edit_selected():
        rule = require_selected_rule()
        if rule:
            open_rule_form(rule)

    def delete_selected():
        rule = require_selected_rule()
        if rule and messagebox.askyesno(
            "규칙 삭제",
            f"'{rule['recommendation']}' 규칙을 삭제할까요?",
            parent=manager,
        ):
            RuleService.delete(rule["id"])
            refresh_rules()

    def duplicate_selected():
        rule = require_selected_rule()
        if rule:
            new_rule_id = RuleService.duplicate(rule["id"])
            refresh_rules(new_rule_id)

    def toggle_selected():
        rule = require_selected_rule()
        if rule:
            RuleService.set_enabled(rule["id"], not rule["enabled"])
            refresh_rules(rule["id"])

    def test_selected():
        rule = require_selected_rule()
        if rule:
            open_rule_test_window(manager, rule)

    actions = ctk.CTkFrame(manager, fg_color="transparent")
    actions.pack(pady=(5, 15))
    for text, command in (
        ("생성", open_rule_form),
        ("수정", edit_selected),
        ("삭제", delete_selected),
        ("복제", duplicate_selected),
        ("활성/비활성", toggle_selected),
        ("규칙 테스트", test_selected),
        ("닫기", manager.destroy),
    ):
        ctk.CTkButton(actions, text=text, width=125, command=command).pack(
            side="left", padx=4
        )

    table.bind("<Double-1>", lambda _event: edit_selected())
    refresh_rules()
    return manager


def open_rule_test_window(parent, rule):
    """Open a school selector and evaluate exactly one rule."""
    test_window = ctk.CTkToplevel(parent)
    own_child_window(test_window, parent)
    test_window.title("규칙 테스트")
    test_window.geometry("850x620")

    ctk.CTkLabel(
        test_window,
        text=f"테스트 규칙: {rule['recommendation']}",
        font=("맑은 고딕", 20, "bold"),
    ).pack(pady=(18, 10))

    search_frame = ctk.CTkFrame(test_window)
    search_frame.pack(fill="x", padx=18, pady=6)
    school_keyword = ctk.CTkEntry(
        search_frame, width=300, placeholder_text="학교명 검색"
    )
    school_keyword.pack(side="left", padx=10, pady=10)

    school_tree = ttk.Treeview(
        test_window,
        columns=("school_name", "school_code", "region"),
        show="headings",
        height=11,
    )
    for column, heading, width in (
        ("school_name", "학교명", 330),
        ("school_code", "학교코드", 170),
        ("region", "지역", 260),
    ):
        school_tree.heading(column, text=heading)
        school_tree.column(column, width=width, anchor="center")
    school_tree.pack(fill="both", expand=True, padx=18, pady=8)
    schools_by_item = {}

    result_frame = ctk.CTkFrame(test_window)
    result_frame.pack(fill="x", padx=18, pady=8)
    match_result = ctk.CTkLabel(result_frame, text="일치: -", anchor="w")
    match_result.pack(fill="x", padx=12, pady=(10, 3))
    score_result = ctk.CTkLabel(result_frame, text="점수: -", anchor="w")
    score_result.pack(fill="x", padx=12, pady=3)
    reason_result = ctk.CTkLabel(
        result_frame, text="근거: -", anchor="w", justify="left", wraplength=770
    )
    reason_result.pack(fill="x", padx=12, pady=(3, 10))

    def search_schools():
        schools = SchoolService.search(keyword=school_keyword.get())
        school_tree.delete(*school_tree.get_children())
        schools_by_item.clear()
        for index, school in enumerate(schools):
            item_id = f"school-{index}"
            schools_by_item[item_id] = school
            school_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(school[1], school[0], school[4]),
            )

    def run_test():
        selection = school_tree.selection()
        school = schools_by_item.get(selection[0]) if selection else None
        if school is None:
            messagebox.showinfo(
                "규칙 테스트", "학교를 선택하세요.", parent=test_window
            )
            return
        records = (
            ProjectService.list_for_school(school[0])
            + ContractService.search_by_school(school[0])
        )
        try:
            result = RuleService.test_rule(rule, records)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            messagebox.showerror("규칙 테스트 오류", str(error), parent=test_window)
            return
        match, score, reason = rule_test_display_values(result)
        match_result.configure(text=f"일치 여부: {match}")
        score_result.configure(text=f"점수: {score}")
        reason_result.configure(text=f"사유: {reason}")

    ctk.CTkButton(
        search_frame, text="학교 검색", width=110, command=search_schools
    ).pack(side="left", padx=5, pady=10)
    ctk.CTkButton(
        search_frame, text="선택 학교 평가", width=140, command=run_test
    ).pack(side="left", padx=5, pady=10)
    school_keyword.bind("<Return>", lambda _event: search_schools())
    return test_window
