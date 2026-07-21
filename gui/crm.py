"""School CRM activity timeline and editing interface."""

from datetime import date

import customtkinter as ctk
from tkinter import messagebox, ttk

from services.sales_activity_service import SalesActivityService


def activity_table_values(activity):
    return (
        activity["activity_date"],
        activity["activity_type"],
        activity["contact_person"],
        activity["memo"],
        activity["next_action_date"] or "-",
        activity["status"],
    )


def pipeline_status_text(summary):
    pipeline = summary["pipeline"]
    return (
        f"현재 단계: {pipeline['current_stage']} · "
        f"예정 {len(summary['upcoming_actions'])}건 · "
        f"기한 초과 {len(summary['overdue_actions'])}건"
    )


def build_school_crm(parent, school_code):
    """Build a refreshable CRM tab for one school."""
    owner = parent.winfo_toplevel()
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.pack(fill="x", padx=10, pady=(12, 6))
    status_label = ctk.CTkLabel(header, text="CRM 준비 중", anchor="w")
    status_label.pack(side="left", fill="x", expand=True)

    activity_tree = ttk.Treeview(
        parent,
        columns=("date", "type", "contact", "memo", "next", "status"),
        show="headings",
        height=14,
    )
    for column, heading, width in (
        ("date", "활동일", 100),
        ("type", "활동 유형", 95),
        ("contact", "담당자", 120),
        ("memo", "메모", 420),
        ("next", "다음 후속일", 110),
        ("status", "파이프라인", 100),
    ):
        activity_tree.heading(column, text=heading)
        activity_tree.column(column, width=width, anchor="center")
    for stage, color in (
        ("Lead", "#64748B"),
        ("Qualified", "#1F6AA5"),
        ("Proposal", "#7C3AED"),
        ("Negotiation", "#D97706"),
        ("Won", "#2E8B57"),
        ("Lost", "#C2410C"),
    ):
        activity_tree.tag_configure(stage, foreground=color)
    activity_tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    activities_by_item = {}

    def selected_activity():
        selection = activity_tree.selection()
        return activities_by_item.get(selection[0]) if selection else None

    def refresh_crm():
        activities = SalesActivityService.list_by_school(school_code)
        summary = SalesActivityService.school_crm_summary(school_code)
        activity_tree.delete(*activity_tree.get_children())
        activities_by_item.clear()
        for activity in activities:
            item_id = f"activity-{activity['id']}"
            activities_by_item[item_id] = activity
            activity_tree.insert(
                "",
                "end",
                iid=item_id,
                tags=(activity["status"],),
                values=activity_table_values(activity),
            )
        status_label.configure(text=pipeline_status_text(summary))

    def open_activity_form(activity=None):
        form = ctk.CTkToplevel(owner)
        form.title("영업 활동 수정" if activity else "영업 활동 추가")
        form.geometry("560x560")
        form.transient(owner)
        form.grab_set()

        content = ctk.CTkFrame(form)
        content.pack(fill="both", expand=True, padx=18, pady=18)
        content.grid_columnconfigure(1, weight=1)

        def add_entry(label, row, value=""):
            ctk.CTkLabel(content, text=label, anchor="w").grid(
                row=row, column=0, padx=8, pady=7, sticky="nw"
            )
            entry = ctk.CTkEntry(content)
            entry.insert(0, str(value or ""))
            entry.grid(row=row, column=1, padx=8, pady=7, sticky="ew")
            return entry

        activity_date_entry = add_entry(
            "활동일",
            0,
            activity["activity_date"] if activity else date.today().isoformat(),
        )
        ctk.CTkLabel(content, text="활동 유형", anchor="w").grid(
            row=1, column=0, padx=8, pady=7, sticky="w"
        )
        activity_type_entry = ctk.CTkComboBox(
            content, values=list(SalesActivityService.ACTIVITY_TYPES)
        )
        activity_type_entry.set(activity["activity_type"] if activity else "전화")
        activity_type_entry.grid(row=1, column=1, padx=8, pady=7, sticky="ew")
        contact_entry = add_entry(
            "담당자", 2, activity["contact_person"] if activity else ""
        )
        next_action_entry = add_entry(
            "다음 후속일", 3, activity["next_action_date"] if activity else ""
        )
        ctk.CTkLabel(content, text="상태", anchor="w").grid(
            row=4, column=0, padx=8, pady=7, sticky="w"
        )
        status_entry = ctk.CTkComboBox(
            content, values=list(SalesActivityService.PIPELINE_STAGES)
        )
        status_entry.set(activity["status"] if activity else "Lead")
        status_entry.grid(row=4, column=1, padx=8, pady=7, sticky="ew")
        ctk.CTkLabel(content, text="메모", anchor="w").grid(
            row=5, column=0, padx=8, pady=7, sticky="nw"
        )
        memo_entry = ctk.CTkTextbox(content, height=160)
        memo_entry.insert("1.0", activity["memo"] if activity else "")
        memo_entry.grid(row=5, column=1, padx=8, pady=7, sticky="nsew")
        content.grid_rowconfigure(5, weight=1)

        def save_activity():
            values = (
                school_code,
                activity_date_entry.get(),
                activity_type_entry.get(),
                contact_entry.get(),
                memo_entry.get("1.0", "end").strip(),
                next_action_entry.get(),
                status_entry.get(),
            )
            try:
                if activity:
                    SalesActivityService.update_activity(activity["id"], *values)
                else:
                    SalesActivityService.add_activity(*values)
            except ValueError as error:
                messagebox.showerror("활동 입력 오류", str(error), parent=form)
                return
            form.grab_release()
            form.destroy()
            refresh_crm()

        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=2, pady=10)
        ctk.CTkButton(buttons, text="저장", width=110, command=save_activity).pack(
            side="left", padx=5
        )
        ctk.CTkButton(buttons, text="취소", width=110, command=form.destroy).pack(
            side="left", padx=5
        )

    def edit_selected():
        activity = selected_activity()
        if activity is None:
            messagebox.showinfo("CRM", "수정할 활동을 선택하세요.", parent=parent)
        else:
            open_activity_form(activity)

    def delete_selected():
        activity = selected_activity()
        if activity is None:
            messagebox.showinfo("CRM", "삭제할 활동을 선택하세요.", parent=parent)
        elif messagebox.askyesno(
            "활동 삭제",
            f"{activity['activity_date']} {activity['activity_type']} 활동을 삭제할까요?",
            parent=parent,
        ):
            SalesActivityService.delete_activity(activity["id"])
            refresh_crm()

    ctk.CTkButton(
        header, text="활동 추가", width=100, command=open_activity_form
    ).pack(side="right", padx=3)
    ctk.CTkButton(header, text="수정", width=80, command=edit_selected).pack(
        side="right", padx=3
    )
    ctk.CTkButton(header, text="삭제", width=80, command=delete_selected).pack(
        side="right", padx=3
    )
    ctk.CTkButton(header, text="새로고침", width=90, command=refresh_crm).pack(
        side="right", padx=3
    )
    activity_tree.bind("<Double-1>", lambda _event: edit_selected())
    refresh_crm()
    return parent
