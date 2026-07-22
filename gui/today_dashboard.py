"""Default Today Dashboard home screen."""

import customtkinter as ctk
from tkinter import messagebox, ttk

from gui.ui_theme import (
    COLORS,
    FONTS,
    card,
    create_empty_state,
    prepare_treeview,
    primary_button,
    own_child_window,
    secondary_button,
    stripe_treeview,
    update_empty_state,
)
from services.dashboard_service import DashboardService


AUTO_REFRESH_MS = 5 * 60 * 1000


def build_today_dashboard(
    parent,
    dashboard_service=DashboardService,
    refresh_interval_ms=AUTO_REFRESH_MS,
    on_refresh=None,
):
    container = ctk.CTkFrame(parent, fg_color=COLORS["window"], corner_radius=0)
    container.pack(fill="both", expand=True)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(20, 8))
    heading = ctk.CTkFrame(header, fg_color="transparent")
    heading.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        heading, text="오늘의 대시보드", font=FONTS["display"], anchor="w"
    ).pack(fill="x")
    ctk.CTkLabel(
        heading,
        text="학교 기회, 예정 활동, 영업 현황을 한눈에 확인하세요.",
        font=FONTS["body"],
        text_color=COLORS["muted"],
        anchor="w",
    ).pack(fill="x", pady=(2, 0))
    status = ctk.CTkLabel(
        header,
        text="준비됨",
        anchor="e",
        font=FONTS["caption"],
        text_color=COLORS["muted"],
    )
    status.pack(side="right", padx=(12, 0))

    content = ctk.CTkScrollableFrame(container, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=18, pady=(4, 14))
    for column in range(2):
        content.grid_columnconfigure(column, weight=1, uniform="today-column")

    kpi_frame = ctk.CTkFrame(content, fg_color="transparent")
    kpi_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(2, 10))
    kpi_keys = (
        ("opportunity_count", "영업 기회"),
        ("completed_this_week", "이번 주 완료"),
        ("upcoming_visits", "예정된 방문"),
        ("average_opportunity_score", "평균 기회 점수"),
        ("open_actions", "진행 중 액션"),
    )
    kpi_accents = (
        (COLORS["blue"], COLORS["blue_tint"]),
        (COLORS["green"], COLORS["green_tint"]),
        (COLORS["orange"], COLORS["orange_tint"]),
        (COLORS["blue"], COLORS["blue_tint"]),
        (COLORS["red"], COLORS["red_tint"]),
    )
    kpi_labels = {}
    for grid_column in range(6):
        kpi_frame.grid_columnconfigure(grid_column, weight=1, uniform="today-kpi")
    for column, (key, title) in enumerate(kpi_keys):
        accent, tint = kpi_accents[column]
        kpi_card = card(kpi_frame, height=112)
        if column < 3:
            grid_row, grid_column, column_span = 0, column * 2, 2
        else:
            grid_row, grid_column, column_span = 1, (column - 3) * 3, 3
        kpi_card.grid(
            row=grid_row,
            column=grid_column,
            columnspan=column_span,
            padx=5,
            pady=5,
            sticky="nsew",
        )
        kpi_card.grid_propagate(False)
        ctk.CTkFrame(
            kpi_card, width=4, corner_radius=3, fg_color=accent
        ).pack(side="left", fill="y", padx=(0, 0), pady=12)
        body = ctk.CTkFrame(kpi_card, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(body, text=title, text_color=COLORS["muted"], anchor="w", font=FONTS["caption"]).pack(
            fill="x", padx=15, pady=(17, 4)
        )
        label = ctk.CTkLabel(body, text="0", font=FONTS["kpi"], anchor="w", text_color=accent)
        label.pack(fill="x", padx=15, pady=(0, 14))
        kpi_labels[key] = label

    empty_states = {}

    def table_panel(row, column, title, columns, empty_message, height=7):
        panel = card(content)
        panel.grid(row=row, column=column, padx=5, pady=6, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            panel, text=title, font=FONTS["section"], anchor="w"
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        tree = ttk.Treeview(
            panel, columns=[item[0] for item in columns], show="headings", height=height
        )
        for key, heading, width in columns:
            # Keep the two-column dashboard inside the viewport at Windows DPI
            # scaling; stretch uses extra room and the scrollbar preserves access.
            responsive_width = max(int(width * 0.68), 70)
            tree.heading(key, text=heading)
            tree.column(
                key,
                width=responsive_width,
                minwidth=min(responsive_width, 90),
                stretch=False,
                anchor="w",
            )
        prepare_treeview(tree)
        scrollbar = ttk.Scrollbar(panel, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=scrollbar.set)
        tree.grid(row=1, column=0, padx=12, pady=(0, 0), sticky="nsew")
        scrollbar.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")
        empty_states[tree] = create_empty_state(panel, empty_message)
        return panel, tree

    _, priority_tree = table_panel(1, 0, "우선 관리 학교 상위 10개", (
        ("school", "학교", 150), ("score", "점수", 55),
        ("priority", "우선순위", 85), ("recommendation", "추천", 250),
    ), "◎  우선 관리 학교가 아직 없습니다.")
    today_panel, today_tree = table_panel(1, 1, "오늘의 액션", (
        ("school", "학교", 115), ("action", "액션", 230),
        ("due", "예정 시간", 90), ("status", "상태", 90),
    ), "✓  오늘 예정된 액션이 없습니다.")
    _, visits_tree = table_panel(2, 0, "예정된 방문", (
        ("school", "학교", 130), ("visit", "방문", 250), ("due", "예정일", 95),
    ), "◷  예정된 방문이 없습니다.", height=5)
    _, overdue_tree = table_panel(2, 1, "지연된 액션", (
        ("school", "학교", 130), ("action", "액션", 245), ("due", "예정일", 95),
    ), "✓  지연된 액션이 없습니다.", height=5)
    _, completed_tree = table_panel(3, 0, "최근 완료", (
        ("school", "학교", 130), ("action", "액션", 235),
        ("completed", "완료일", 105),
    ), "○  최근 완료된 액션이 없습니다.", height=5)
    _, activity_tree = table_panel(3, 1, "최근 활동", (
        ("time", "시간", 130), ("type", "유형", 100),
        ("school", "학교", 90), ("detail", "내용", 190),
    ), "◇  최근 활동이 없습니다.", height=5)
    _, alert_tree = table_panel(4, 0, "알림", (
        ("severity", "중요도", 75), ("type", "유형", 120),
        ("school", "학교", 120), ("message", "메시지", 220),
    ), "✓  확인할 알림이 없습니다.", height=6)
    opportunity_panel, opportunity_tree = table_panel(4, 1, "영업 기회 요약", (
        ("band", "구간", 160), ("count", "학교 수", 90),
    ), "◎  영업 기회 요약 데이터가 없습니다.", height=6)

    ctk.CTkLabel(
        kpi_frame, text="주간 핵심 지표", font=FONTS["section"], anchor="w"
    ).grid(row=2, column=0, columnspan=6, padx=5, pady=(9, 0), sticky="w")

    def school_name(snapshot, school_id):
        return snapshot.get("school_names", {}).get(school_id, school_id)

    def reset_tree(tree):
        tree.delete(*tree.get_children())

    def populate(snapshot):
        for key, label in kpi_labels.items():
            value = snapshot["weekly_kpi"][key]
            label.configure(text=f"{value:.1f}" if isinstance(value, float) else f"{value:,}")

        for tree in (
            priority_tree, today_tree, visits_tree, overdue_tree, completed_tree,
            activity_tree, alert_tree, opportunity_tree,
        ):
            reset_tree(tree)
        for item in snapshot["priority_schools"]:
            priority_tree.insert("", "end", values=(
                item.school_name, item.score, item.priority, item.recommendation,
            ))
        for action in snapshot["today_actions"]:
            today_tree.insert("", "end", iid=f"action-{action.action_id}", values=(
                school_name(snapshot, action.school_id), action.title,
                action.due_date or "종일", action.status,
            ))
        for action in snapshot["upcoming_visits"]:
            visits_tree.insert("", "end", values=(
                school_name(snapshot, action.school_id), action.title, action.due_date or "-",
            ))
        for action in snapshot["overdue_actions"]:
            overdue_tree.insert("", "end", values=(
                school_name(snapshot, action.school_id), action.title, action.due_date or "-",
            ))
        for action in snapshot["recently_completed"]:
            completed_tree.insert("", "end", values=(
                school_name(snapshot, action.school_id), action.title,
                action.completed_date or "-",
            ))
        for event in snapshot["recent_activity"]:
            activity_tree.insert("", "end", values=(
                str(event.get("timestamp") or "")[:16], event.get("activity_type", ""),
                school_name(snapshot, event.get("school_id", "")),
                event.get("description") or event.get("title", ""),
            ))
        for alert in snapshot["alerts"]:
            alert_tree.insert("", "end", values=(
                alert["severity"], alert["type"], alert["school_name"], alert["message"],
            ))
        summary = snapshot["opportunity_summary"]
        for label, key in (
            ("높은 우선순위 (70점 이상)", "high_priority"),
            ("유효 기회 (50~69점)", "qualified"),
            ("관찰 대상 (50점 미만)", "monitor"),
            ("평균 점수", "average_score"),
            ("전체 영업 기회", "total"),
        ):
            opportunity_tree.insert("", "end", values=(label, summary[key]))
        status.configure(
        text=f"업데이트 {snapshot['generated_at'][11:19]}  ·  {snapshot['elapsed_ms']:.0f}밀리초"
        )
        for tree in (
            priority_tree, today_tree, visits_tree, overdue_tree, completed_tree,
            activity_tree, alert_tree, opportunity_tree,
        ):
            stripe_treeview(tree)
            update_empty_state(tree, empty_states[tree])
        if on_refresh:
            on_refresh(snapshot)

    def refresh(force=False):
        status.configure(text="새로고침 중…")
        container.update_idletasks()
        try:
            snapshot = (
                dashboard_service.refresh() if force
                else dashboard_service.get_dashboard()
            )
            populate(snapshot)
        except Exception as error:
            status.configure(text="새로고침 실패")
            messagebox.showerror("오늘의 대시보드", str(error), parent=container.winfo_toplevel())

    def complete_selected():
        selection = today_tree.selection()
        if not selection:
            messagebox.showinfo(
                "액션 완료", "먼저 오늘의 액션을 선택하세요.",
                parent=container.winfo_toplevel(),
            )
            return
        action_id = int(selection[0].split("-", 1)[1])
        snapshot = dashboard_service.complete_action(action_id)
        populate(snapshot)

    secondary_button(
        today_panel, text="✓  선택 항목 완료", width=164, command=complete_selected
    ).grid(row=3, column=0, padx=12, pady=(0, 12), sticky="e")
    primary_button(
        header, text="↻  새로고침", width=112, command=lambda: refresh(True)
    ).pack(side="right", padx=(14, 0), pady=4)

    def auto_refresh():
        if container.winfo_exists():
            refresh(False)
            container.after(refresh_interval_ms, auto_refresh)

    refresh(False)
    container.after(refresh_interval_ms, auto_refresh)
    return container


def open_today_dashboard(parent):
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("오늘의 대시보드")
    window.geometry("1400x900")
    window.minsize(1050, 700)
    build_today_dashboard(window)
    return window
