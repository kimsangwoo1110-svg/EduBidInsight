"""Responsive School 360° profile dashboard."""

import customtkinter as ctk
from datetime import date, timedelta

from services.action_center import ActionCenterService
from services.school_profile_service import SchoolProfileService
from gui.ui_theme import own_child_window


STAT_CARDS = (
    ("schoolmarket_purchases", "학교장터 구매", "count"),
    ("g2b_contracts", "나라장터 계약", "count"),
    ("g2b_spending", "나라장터 구매액", "currency"),
    ("contracts", "전체 계약", "count"),
    ("projects", "사업", "count"),
    ("crm_activities", "고객 활동", "count"),
    ("active_projects", "진행 사업", "count"),
    ("completed_projects", "완료 사업", "count"),
    ("project_budget", "전체 사업 예산", "currency"),
)
SOURCE_COLORS = {
    "SchoolMarket": "#2563EB",
    "Contract": "#059669",
    "Project": "#7C3AED",
    "CRM": "#D97706",
    "G2B": "#DC2626",
    "Education Office": "#0891B2",
}


def build_school_profile(parent, school_code, profile_service=SchoolProfileService):
    """Build a refreshable profile inside an existing parent widget."""
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.pack(fill="both", expand=True)

    toolbar = ctk.CTkFrame(container)
    toolbar.pack(fill="x", padx=12, pady=(10, 4))
    status_label = ctk.CTkLabel(toolbar, text="학교 360° 프로필", anchor="w")
    status_label.pack(side="left", fill="x", expand=True, padx=12, pady=10)

    content = ctk.CTkScrollableFrame(container, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=8, pady=6)
    content.grid_columnconfigure(0, weight=1)

    def clear_content():
        for child in content.winfo_children():
            child.destroy()

    def label_pair(parent_frame, row, title, value):
        ctk.CTkLabel(
            parent_frame,
            text=title,
            width=120,
            anchor="w",
            font=("맑은 고딕", 12, "bold"),
        ).grid(row=row, column=0, padx=(16, 8), pady=5, sticky="w")
        ctk.CTkLabel(
            parent_frame, text=str(value or "-"), anchor="w", wraplength=850
        ).grid(row=row, column=1, padx=(8, 16), pady=5, sticky="ew")

    def render():
        clear_content()
        profile = profile_service.get_profile(school_code)
        school = profile["school"]
        statistics = profile["statistics"]

        summary = ctk.CTkFrame(content)
        summary.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 10))
        summary.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            summary,
            text=school["school_name"] or "학교를 찾을 수 없습니다.",
            font=("맑은 고딕", 24, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")
        label_pair(summary, 1, "학교코드", school["school_code"])
        label_pair(summary, 2, "지역", school["region"])
        label_pair(summary, 3, "주소", school["address"])
        label_pair(summary, 4, "학생수", f"{school['student_count']:,}")
        label_pair(summary, 5, "학급수", f"{school['class_count']:,}")

        cards = ctk.CTkFrame(content, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=0, pady=4)
        for column in range(3):
            cards.grid_columnconfigure(column, weight=1, uniform="profile-card")
        for index, (key, title, value_type) in enumerate(STAT_CARDS):
            card = ctk.CTkFrame(cards)
            card.grid(row=index // 3, column=index % 3, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(card, text=title, anchor="w").pack(
                fill="x", padx=14, pady=(14, 4)
            )
            ctk.CTkLabel(
                card,
                text=(
                    f"{int(float(statistics.get(key, 0) or 0)):,}원"
                    if value_type == "currency"
                    else f"{int(statistics.get(key, 0) or 0):,}"
                ),
                font=("맑은 고딕", 26, "bold"),
                anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 14))

        activity = ctk.CTkFrame(content)
        activity.grid(row=2, column=0, sticky="ew", padx=6, pady=10)
        activity.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            activity, text="최근 활동", font=("맑은 고딕", 20, "bold"), anchor="w"
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        events = profile["recent_activity"]
        if not events:
            ctk.CTkLabel(activity, text="최근 활동이 없습니다.", anchor="w").grid(
                row=1, column=0, padx=16, pady=(4, 16), sticky="ew"
            )
        for row, event in enumerate(events, start=1):
            line = ctk.CTkFrame(activity, fg_color=("#F3F4F6", "#242424"))
            line.grid(row=row, column=0, padx=12, pady=4, sticky="ew")
            line.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                line,
                text=event["source"],
                width=110,
                text_color=SOURCE_COLORS.get(event["source"], "#6B7280"),
                font=("맑은 고딕", 12, "bold"),
            ).grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="w")
            ctk.CTkLabel(
                line, text=event["title"], anchor="w", font=("맑은 고딕", 13, "bold")
            ).grid(row=0, column=1, padx=8, pady=(8, 1), sticky="ew")
            ctk.CTkLabel(
                line, text=event["description"], anchor="w", wraplength=750
            ).grid(row=1, column=1, padx=8, pady=(1, 8), sticky="ew")
            ctk.CTkLabel(line, text=event["timestamp"], width=170, anchor="e").grid(
                row=0, column=2, rowspan=2, padx=12, pady=8, sticky="e"
            )

        latest = ctk.CTkFrame(content)
        latest.grid(row=3, column=0, sticky="ew", padx=6, pady=10)
        latest.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            latest, text="최근 나라장터 계약", font=("맑은 고딕", 20, "bold"), anchor="w"
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        latest_contracts = profile.get("latest_g2b_contracts") or []
        if not latest_contracts:
            ctk.CTkLabel(latest, text="나라장터 계약이 없습니다.", anchor="w").grid(
                row=1, column=0, padx=16, pady=(4, 16), sticky="ew"
            )
        for row, contract in enumerate(latest_contracts, start=1):
            ctk.CTkLabel(
                latest,
                text=(
                    f"{contract.get('contract_date', '-')}  ·  {contract.get('product', '')}  ·  "
                    f"{contract.get('vendor', '')}  ·  {int(float(contract.get('amount') or 0)):,}원"
                ),
                anchor="w",
            ).grid(row=row, column=0, padx=16, pady=5, sticky="ew")

        latest_projects = ctk.CTkFrame(content)
        latest_projects.grid(row=4, column=0, sticky="ew", padx=6, pady=10)
        latest_projects.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            latest_projects, text="최근 사업", font=("맑은 고딕", 20, "bold"), anchor="w"
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        project_rows = profile.get("latest_projects") or []
        if not project_rows:
            ctk.CTkLabel(latest_projects, text="등록된 사업이 없습니다.", anchor="w").grid(
                row=1, column=0, padx=16, pady=(4, 16), sticky="ew"
            )
        for row, project in enumerate(project_rows, start=1):
            ctk.CTkLabel(
                latest_projects,
                text=(
                    f"{project.get('start_year') or '-'}  ·  {project.get('project_name', '')}  ·  "
                    f"{project.get('status', '')}  ·  {int(float(project.get('budget') or 0)):,}원"
                ),
                anchor="w",
            ).grid(row=row, column=0, padx=16, pady=5, sticky="ew")

        actions_panel = ctk.CTkFrame(content, border_width=1, border_color="#0F766E")
        actions_panel.grid(row=5, column=0, sticky="ew", padx=6, pady=10)
        ctk.CTkLabel(
            actions_panel, text="고객 활동", font=("맑은 고딕", 20, "bold"), anchor="w"
        ).pack(fill="x", padx=16, pady=(14, 5))

        def quick_action(action_type, title, days):
            ActionCenterService.create(
                school_code, action_type, title,
                due_date=(date.today() + timedelta(days=days)).isoformat(),
            )
            render()

        quick = ctk.CTkFrame(actions_panel, fg_color="transparent")
        quick.pack(fill="x", padx=12, pady=5)
        for text, action_type, title, days in (
            ("+ 방문", "Visit", "학교 방문", 7),
            ("+ 전화", "Phone Call", "학교 전화", 1),
            ("+ 견적", "Quotation", "견적 준비", 3),
            ("+ 메모", "Other", "고객 메모", 0),
        ):
            ctk.CTkButton(
                quick, text=text, width=100,
                command=lambda kind=action_type, heading=title, offset=days: quick_action(kind, heading, offset),
            ).pack(side="left", padx=4)

        action_data = profile.get("actions") or {}
        for heading, key in (
            ("현재 활동", "current_actions"),
            ("예정 활동", "upcoming_actions"),
            ("완료 활동", "completed_actions"),
            ("활동 일정", "action_timeline"),
        ):
            rows = action_data.get(key) or []
            ctk.CTkLabel(
                actions_panel, text=f"{heading} ({len(rows)})",
                font=("맑은 고딕", 13, "bold"), anchor="w",
            ).pack(fill="x", padx=16, pady=(9, 2))
            text = "활동이 없습니다." if not rows else "\n".join(
                f"{item.due_date or item.updated_at[:10]}  •  {item.action_type}  •  {item.title}  •  {item.status}"
                for item in rows[:5]
            )
            ctk.CTkLabel(
                actions_panel, text=text, anchor="w", justify="left", wraplength=950,
            ).pack(fill="x", padx=16, pady=(0, 4))

        ai_panel = ctk.CTkFrame(content, border_width=1, border_color="#6366F1")
        ai_panel.grid(row=6, column=0, sticky="ew", padx=6, pady=(10, 18))
        ctk.CTkLabel(
            ai_panel, text="AI 추천", font=("맑은 고딕", 20, "bold"), anchor="w"
        ).pack(fill="x", padx=16, pady=(14, 5))
        opportunity = profile.get("opportunity")
        if opportunity is None:
            ctk.CTkLabel(ai_panel, text="영업 기회 데이터가 없습니다.", anchor="w").pack(
                fill="x", padx=16, pady=(0, 16)
            )
        else:
            def create_suggested_actions():
                from services.opportunity_engine import OpportunityEngine

                OpportunityEngine.generate_actions(opportunity, persist=True)
                render()

            score_line = ctk.CTkFrame(ai_panel, fg_color="transparent")
            score_line.pack(fill="x", padx=16, pady=5)
            ctk.CTkLabel(
                score_line,
                text=f"{opportunity.score}/100",
                font=("맑은 고딕", 28, "bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                score_line,
                text=f"{opportunity.priority}  ·  신뢰도 {opportunity.confidence}",
                font=("맑은 고딕", 16, "bold"),
            ).pack(side="left", padx=18)
            score_bar = ctk.CTkProgressBar(ai_panel)
            score_bar.set(opportunity.score / 100)
            score_bar.pack(fill="x", padx=16, pady=(2, 10))
            ctk.CTkLabel(
                ai_panel,
                text=f"추천: {opportunity.recommendation}",
                anchor="w",
                wraplength=950,
            ).pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(
                ai_panel,
                text=f"다음 활동: {opportunity.next_action}",
                anchor="w",
            ).pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(
                ai_panel,
                text="근거",
                anchor="w",
                font=("맑은 고딕", 13, "bold"),
            ).pack(fill="x", padx=16, pady=(10, 3))
            ctk.CTkLabel(
                ai_panel,
                text="\n".join(opportunity.evidence) or "아직 점수 산정 근거가 없습니다.",
                anchor="w",
                justify="left",
                wraplength=950,
            ).pack(fill="x", padx=16, pady=(0, 16))
            ctk.CTkButton(
                ai_panel,
                text="추천 활동 생성",
                width=190,
                command=create_suggested_actions,
            ).pack(anchor="e", padx=16, pady=(0, 16))

        status_label.configure(
            text=f"학교 360° · 새로고침 완료 · 최근 활동 {len(events):,}건"
        )
        return profile

    ctk.CTkButton(toolbar, text="새로고침", width=105, command=render).pack(
        side="right", padx=10, pady=8
    )
    render()
    return container


def open_school_profile(parent, school_code):
    """Open the School 360° profile as a standalone resizable screen."""
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("학교 360° 프로필")
    window.geometry("1280x820")
    window.minsize(900, 620)
    build_school_profile(window, school_code)
    return window
