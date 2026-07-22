"""School analytics dashboard presentation components."""

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from services.contract_service import ContractService
from services.dashboard_export_service import DashboardExportService
from services.insight_service import InsightService
from services.project_service import ProjectService
from services.sales_activity_service import SalesActivityService


def dashboard_kpi_values(summary):
    kpis = summary["kpis"]
    return (
        ("프로젝트", f"{kpis['projects']:,}건"),
        ("프로젝트 예산", ProjectService.format_budget(kpis["project_budget"])),
        ("계약", f"{kpis['contracts']:,}건"),
        ("계약 총액", ContractService.format_amount(kpis["contract_amount"])),
        ("거래 업체", f"{kpis['vendors']:,}개"),
        ("Opportunity Score", f"{kpis['opportunity_score']}/100"),
    )


def g2b_kpi_values(summary):
    """Return G2B-specific cards without changing the established KPI set."""
    g2b = summary.get("g2b_summary") or {}
    return (
        ("G2B contracts", f"{int(g2b.get('total_count', 0) or 0):,}건"),
        ("G2B spending", ContractService.format_amount(g2b.get("total_spending", 0))),
    )


def project_portfolio_values(summary):
    """Return the Education Office project portfolio KPI values."""
    projects = summary.get("project_analytics") or {}
    return (
        ("Total projects", f"{int(projects.get('total_projects', 0) or 0):,}건"),
        ("Active projects", f"{int(projects.get('active_projects', 0) or 0):,}건"),
        ("Total project budget", ProjectService.format_budget(projects.get("total_budget", 0))),
    )


def purchase_cycle_text(cycle):
    if cycle["status"] != "분석 완료":
        return f"{cycle['status']} · 최근 구매일 {cycle['last_purchase_date'] or '-'}"
    return (
        f"평균 {cycle['average_days']:.1f}일 · 중앙값 {cycle['median_days']:.1f}일 · "
        f"최근 {cycle['last_purchase_date']} · 다음 예상 {cycle['next_expected_date']}"
    )


def business_insight_values(insight):
    """Return headline values used by the BI dashboard sections."""
    return {
        "summary": insight["summary"],
        "explanation": insight["explanation"]["text"],
        "recommendations": len(insight["recommended_products"]),
        "risks": len(insight["risks"]),
        "actions": len(insight["next_actions"]),
    }


def sales_kpi_values(kpis):
    return (
        ("Visits", f"{kpis['visits']:,}"),
        ("Calls", f"{kpis['calls']:,}"),
        ("Quotations", f"{kpis['quotations']:,}"),
        ("Wins", f"{kpis['wins']:,}"),
        ("Win rate", f"{kpis['win_rate']:.1f}%"),
    )


def build_school_dashboard(parent, school_code, school_name):
    """Build a refreshable dashboard inside an existing tab frame."""
    dashboard = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    dashboard.pack(fill="both", expand=True, padx=6, pady=6)

    toolbar = ctk.CTkFrame(dashboard, fg_color="transparent")
    toolbar.pack(fill="x", padx=4, pady=(2, 8))
    dashboard_status = ctk.CTkLabel(toolbar, text="분석 준비 중", anchor="w")
    dashboard_status.pack(side="left", fill="x", expand=True)

    kpi_frame = ctk.CTkFrame(dashboard)
    kpi_frame.pack(fill="x", pady=5)
    kpi_labels = []
    for index in range(6):
        card = ctk.CTkFrame(kpi_frame)
        card.grid(row=0, column=index, padx=4, pady=7, sticky="nsew")
        kpi_frame.grid_columnconfigure(index, weight=1)
        title = ctk.CTkLabel(card, text="-", text_color="gray")
        title.pack(padx=8, pady=(8, 2))
        value = ctk.CTkLabel(card, text="-", font=("맑은 고딕", 15, "bold"))
        value.pack(padx=8, pady=(2, 8))
        kpi_labels.append((title, value))

    g2b_frame = ctk.CTkFrame(dashboard)
    g2b_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        g2b_frame, text="G2B (나라장터)", font=("맑은 고딕", 16, "bold")
    ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 3), sticky="w")
    g2b_kpi_labels = []
    for index in range(2):
        card = ctk.CTkFrame(g2b_frame)
        card.grid(row=1, column=index, padx=5, pady=(3, 8), sticky="nsew")
        g2b_frame.grid_columnconfigure(index, weight=1)
        title = ctk.CTkLabel(card, text="-", text_color="gray")
        title.pack(padx=8, pady=(7, 2))
        value = ctk.CTkLabel(card, text="-", font=("맑은 고딕", 15, "bold"))
        value.pack(padx=8, pady=(2, 8))
        g2b_kpi_labels.append((title, value))
    g2b_latest_tree = ttk.Treeview(
        g2b_frame,
        columns=("date", "product", "vendor", "amount"),
        show="headings",
        height=3,
    )
    for column, heading, width in (
        ("date", "계약일", 110),
        ("product", "품명", 260),
        ("vendor", "공급업체", 220),
        ("amount", "계약금액", 150),
    ):
        g2b_latest_tree.heading(column, text=heading)
        g2b_latest_tree.column(column, width=width, anchor="center")
    g2b_latest_tree.grid(row=2, column=0, columnspan=2, padx=8, pady=(2, 9), sticky="ew")

    office_project_frame = ctk.CTkFrame(dashboard)
    office_project_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        office_project_frame,
        text="교육청 예정사업",
        font=("맑은 고딕", 16, "bold"),
    ).grid(row=0, column=0, columnspan=3, padx=10, pady=(8, 3), sticky="w")
    office_project_kpis = []
    for index in range(3):
        card = ctk.CTkFrame(office_project_frame)
        card.grid(row=1, column=index, padx=5, pady=(3, 8), sticky="nsew")
        office_project_frame.grid_columnconfigure(index, weight=1)
        title = ctk.CTkLabel(card, text="-", text_color="gray")
        title.pack(padx=8, pady=(7, 2))
        value = ctk.CTkLabel(card, text="-", font=("맑은 고딕", 15, "bold"))
        value.pack(padx=8, pady=(2, 8))
        office_project_kpis.append((title, value))
    project_category_tree = ttk.Treeview(
        office_project_frame,
        columns=("category", "projects", "budget"),
        show="headings",
        height=4,
    )
    for column, heading, width in (
        ("category", "분류", 240),
        ("projects", "사업 수", 100),
        ("budget", "예산", 190),
    ):
        project_category_tree.heading(column, text=heading)
        project_category_tree.column(column, width=width, anchor="center")
    project_category_tree.grid(
        row=2, column=0, columnspan=3, padx=8, pady=(2, 9), sticky="ew"
    )

    sales_kpi_frame = ctk.CTkFrame(dashboard)
    sales_kpi_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        sales_kpi_frame, text="영업 핵심 지표", font=("맑은 고딕", 18, "bold")
    ).grid(row=0, column=0, columnspan=5, padx=10, pady=(8, 3), sticky="w")
    sales_kpi_labels = []
    for index in range(5):
        card = ctk.CTkFrame(sales_kpi_frame)
        card.grid(row=1, column=index, padx=4, pady=(3, 8), sticky="nsew")
        sales_kpi_frame.grid_columnconfigure(index, weight=1)
        title = ctk.CTkLabel(card, text="-", text_color="gray")
        title.pack(padx=8, pady=(7, 2))
        value = ctk.CTkLabel(card, text="-", font=("맑은 고딕", 15, "bold"))
        value.pack(padx=8, pady=(2, 7))
        sales_kpi_labels.append((title, value))

    crm_frame = ctk.CTkFrame(dashboard)
    crm_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        crm_frame, text="영업 단계 및 후속 활동", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 2))
    pipeline_label = ctk.CTkLabel(crm_frame, text="영업 단계: 잠재 고객", anchor="w")
    pipeline_label.pack(fill="x", padx=10, pady=(2, 6))
    crm_tables = ctk.CTkFrame(crm_frame, fg_color="transparent")
    crm_tables.pack(fill="x", padx=5, pady=(0, 8))

    def crm_table(title):
        panel = ctk.CTkFrame(crm_tables)
        panel.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(panel, text=title, font=("맑은 고딕", 13, "bold")).pack(
            anchor="w", padx=7, pady=(6, 2)
        )
        tree = ttk.Treeview(
            panel,
            columns=("date", "type", "memo", "status"),
            show="headings",
            height=4,
        )
        for column, heading, width in (
            ("date", "일자", 85),
            ("type", "유형", 65),
            ("memo", "내용", 180),
            ("status", "단계", 75),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="center")
        tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        return tree

    recent_activity_tree = crm_table("최근 활동")
    upcoming_action_tree = crm_table("예정된 액션")
    overdue_action_tree = crm_table("지연된 액션")

    summaries = ctk.CTkFrame(dashboard, fg_color="transparent")
    summaries.pack(fill="x", pady=5)
    project_frame = ctk.CTkFrame(summaries)
    project_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
    contract_frame = ctk.CTkFrame(summaries)
    contract_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))
    ctk.CTkLabel(
        project_frame, text="사업 요약", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=12, pady=(10, 4))
    project_summary_label = ctk.CTkLabel(
        project_frame, text="-", anchor="w", justify="left"
    )
    project_summary_label.pack(fill="x", padx=12, pady=(2, 12))
    ctk.CTkLabel(
        contract_frame, text="계약 요약", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=12, pady=(10, 4))
    contract_summary_label = ctk.CTkLabel(
        contract_frame, text="-", anchor="w", justify="left"
    )
    contract_summary_label.pack(fill="x", padx=12, pady=(2, 12))

    statistics_frame = ctk.CTkFrame(dashboard, fg_color="transparent")
    statistics_frame.pack(fill="x", pady=5)

    def statistics_panel(title, key_name, first_heading):
        panel = ctk.CTkFrame(statistics_frame)
        panel.pack(side="left", fill="both", expand=True, padx=4)
        ctk.CTkLabel(
            panel, text=title, font=("맑은 고딕", 16, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 4))
        tree = ttk.Treeview(
            panel,
            columns=(key_name, "count", "quantity", "amount", "share"),
            show="headings",
            height=6,
        )
        for column, heading, width in (
            (key_name, first_heading, 150),
            ("count", "계약", 55),
            ("quantity", "수량", 60),
            ("amount", "금액", 115),
            ("share", "비중", 60),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        return tree

    product_tree = statistics_panel("Product Statistics", "product", "품목")
    vendor_tree = statistics_panel("Vendor Statistics", "vendor", "업체")

    trend_frame = ctk.CTkFrame(dashboard)
    trend_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        trend_frame, text="연도별 추이", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 4))
    trend_tree = ttk.Treeview(
        trend_frame,
        columns=("year", "projects", "budget", "contracts", "amount"),
        show="headings",
        height=4,
    )
    for column, heading, width in (
        ("year", "연도", 70),
        ("projects", "프로젝트", 90),
        ("budget", "프로젝트 예산", 180),
        ("contracts", "계약", 70),
        ("amount", "계약 금액", 160),
    ):
        trend_tree.heading(column, text=heading)
        trend_tree.column(column, width=width, anchor="center")
    trend_tree.pack(fill="x", padx=8, pady=(0, 8))

    cycle_frame = ctk.CTkFrame(dashboard)
    cycle_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        cycle_frame, text="구매 주기", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 2))
    cycle_label = ctk.CTkLabel(cycle_frame, text="-", anchor="w")
    cycle_label.pack(fill="x", padx=10, pady=(2, 9))

    opportunity_frame = ctk.CTkFrame(dashboard)
    opportunity_frame.pack(fill="x", pady=5)
    opportunity_header = ctk.CTkFrame(opportunity_frame, fg_color="transparent")
    opportunity_header.pack(fill="x", padx=10, pady=(8, 3))
    ctk.CTkLabel(
        opportunity_header,
        text="영업 기회 점수",
        font=("맑은 고딕", 16, "bold"),
    ).pack(side="left")
    opportunity_label = ctk.CTkLabel(opportunity_header, text="0/100")
    opportunity_label.pack(side="right")
    opportunity_bar = ctk.CTkProgressBar(opportunity_frame)
    opportunity_bar.set(0)
    opportunity_bar.pack(fill="x", padx=10, pady=4)
    opportunity_tree = ttk.Treeview(
        opportunity_frame,
        columns=("target", "recommendation", "score", "priority"),
        show="headings",
        height=5,
    )
    for column, heading, width in (
        ("target", "대상", 260),
        ("recommendation", "추천", 430),
        ("score", "점수", 70),
        ("priority", "우선순위", 90),
    ):
        opportunity_tree.heading(column, text=heading)
        opportunity_tree.column(column, width=width, anchor="center")
    opportunity_tree.pack(fill="x", padx=8, pady=(4, 8))

    insight_frame = ctk.CTkFrame(dashboard)
    insight_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        insight_frame, text="영업 인사이트", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 2))
    business_summary_label = ctk.CTkLabel(
        insight_frame, text="-", anchor="w", justify="left", wraplength=1080
    )
    business_summary_label.pack(fill="x", padx=10, pady=(2, 8))

    explanation_frame = ctk.CTkFrame(dashboard)
    explanation_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        explanation_frame, text="설명", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 2))
    explanation_label = ctk.CTkLabel(
        explanation_frame, text="-", anchor="w", justify="left", wraplength=1080
    )
    explanation_label.pack(fill="x", padx=10, pady=(2, 8))

    recommendation_frame = ctk.CTkFrame(dashboard)
    recommendation_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        recommendation_frame, text="추천", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 3))
    recommendation_tree = ttk.Treeview(
        recommendation_frame,
        columns=("product", "confidence", "priority", "reason"),
        show="headings",
        height=5,
    )
    for column, heading, width in (
        ("product", "추천 제품", 230),
        ("confidence", "신뢰도", 75),
        ("priority", "우선순위", 85),
        ("reason", "추천 근거", 650),
    ):
        recommendation_tree.heading(column, text=heading)
        recommendation_tree.column(column, width=width, anchor="center")
    recommendation_tree.pack(fill="x", padx=8, pady=(2, 8))

    risk_frame = ctk.CTkFrame(dashboard)
    risk_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        risk_frame, text="위험 요소", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 3))
    risk_tree = ttk.Treeview(
        risk_frame,
        columns=("level", "risk", "mitigation"),
        show="headings",
        height=4,
    )
    for column, heading, width in (
        ("level", "수준", 80),
        ("risk", "위험", 480),
        ("mitigation", "대응", 510),
    ):
        risk_tree.heading(column, text=heading)
        risk_tree.column(column, width=width, anchor="center")
    risk_tree.pack(fill="x", padx=8, pady=(2, 8))

    action_frame = ctk.CTkFrame(dashboard)
    action_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        action_frame, text="다음 활동", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 3))
    action_tree = ttk.Treeview(
        action_frame,
        columns=("order", "timing", "action", "reason"),
        show="headings",
        height=4,
    )
    for column, heading, width in (
        ("order", "순서", 50),
        ("timing", "시점", 100),
        ("action", "행동", 500),
        ("reason", "근거", 490),
    ):
        action_tree.heading(column, text=heading)
        action_tree.column(column, width=width, anchor="center")
    action_tree.pack(fill="x", padx=8, pady=(2, 8))

    timeline_frame = ctk.CTkFrame(dashboard)
    timeline_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        timeline_frame, text="영업 기회 일정", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 3))
    timeline_tree = ttk.Treeview(
        timeline_frame,
        columns=("date", "type", "title", "detail"),
        show="headings",
        height=6,
    )
    for column, heading, width in (
        ("date", "날짜", 110),
        ("type", "유형", 80),
        ("title", "기회", 370),
        ("detail", "상세", 570),
    ):
        timeline_tree.heading(column, text=heading)
        timeline_tree.column(column, width=width, anchor="center")
    timeline_tree.pack(fill="x", padx=8, pady=(2, 8))

    matrix_frame = ctk.CTkFrame(dashboard)
    matrix_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(
        matrix_frame, text="우선순위 매트릭스", font=("맑은 고딕", 18, "bold")
    ).pack(anchor="w", padx=10, pady=(8, 3))
    matrix_tree = ttk.Treeview(
        matrix_frame,
        columns=("item", "impact", "urgency", "quadrant", "reason"),
        show="headings",
        height=5,
    )
    for column, heading, width in (
        ("item", "항목", 230),
        ("impact", "영향도", 75),
        ("urgency", "긴급도", 75),
        ("quadrant", "영역", 100),
        ("reason", "근거", 630),
    ):
        matrix_tree.heading(column, text=heading)
        matrix_tree.column(column, width=width, anchor="center")
    matrix_tree.pack(fill="x", padx=8, pady=(2, 8))

    def refresh_dashboard():
        insight = InsightService.summarize_school(school_code)
        summary = insight["analytics"]
        crm_summary = SalesActivityService.school_crm_summary(school_code)
        display_labels = {
            "Opportunity Score": "영업 기회 점수",
            "G2B contracts": "나라장터 계약",
            "G2B spending": "나라장터 계약 금액",
            "Total projects": "전체 사업",
            "Active projects": "진행 사업",
            "Total project budget": "전체 사업 예산",
            "Visits": "방문", "Calls": "전화", "Quotations": "견적",
            "Wins": "수주", "Win rate": "수주율",
        }
        for (title_label, value_label), (title, value) in zip(
            kpi_labels, dashboard_kpi_values(summary)
        ):
            title_label.configure(text=display_labels.get(title, title))
            value_label.configure(text=value)
        for (title_label, value_label), (title, value) in zip(
            g2b_kpi_labels, g2b_kpi_values(summary)
        ):
            title_label.configure(text=display_labels.get(title, title))
            value_label.configure(text=value)
        g2b_latest_tree.delete(*g2b_latest_tree.get_children())
        for contract in summary.get("g2b_summary", {}).get("latest_contracts", []):
            g2b_latest_tree.insert(
                "",
                "end",
                values=(
                    contract.get("contract_date", ""),
                    contract.get("product", ""),
                    contract.get("vendor", ""),
                    ContractService.format_amount(contract.get("amount")),
                ),
            )
        for (title_label, value_label), (title, value) in zip(
            office_project_kpis, project_portfolio_values(summary)
        ):
            title_label.configure(text=display_labels.get(title, title))
            value_label.configure(text=value)
        project_category_tree.delete(*project_category_tree.get_children())
        for category in summary.get("project_analytics", {}).get(
            "category_distribution", []
        ):
            project_category_tree.insert(
                "",
                "end",
                values=(
                    category["category"],
                    category["project_count"],
                    ProjectService.format_budget(category["budget"]),
                ),
            )
        for (title_label, value_label), (title, value) in zip(
            sales_kpi_labels, sales_kpi_values(crm_summary["kpis"])
        ):
            title_label.configure(text=display_labels.get(title, title))
            value_label.configure(text=value)

        pipeline = crm_summary["pipeline"]
        stage_counts = " · ".join(
            f"{stage} {pipeline['counts'][stage]}"
            for stage in SalesActivityService.PIPELINE_STAGES
        )
        pipeline_label.configure(
            text=f"현재 단계: {pipeline['current_stage']} | {stage_counts}"
        )
        for tree, activities, date_field, prefix in (
            (
                recent_activity_tree,
                crm_summary["recent_activities"],
                "activity_date",
                "recent",
            ),
            (
                upcoming_action_tree,
                crm_summary["upcoming_actions"],
                "next_action_date",
                "upcoming",
            ),
            (
                overdue_action_tree,
                crm_summary["overdue_actions"],
                "next_action_date",
                "overdue",
            ),
        ):
            tree.delete(*tree.get_children())
            for index, activity in enumerate(activities[:5]):
                tree.insert(
                    "",
                    "end",
                    iid=f"{prefix}-{index}",
                    values=(
                        activity[date_field] or "-",
                        activity["activity_type"],
                        activity["memo"],
                        activity["status"],
                    ),
                )

        projects = summary["project_summary"]
        statuses = projects["status_counts"]
        project_summary_label.configure(
            text=(
                f"총 {projects['total_count']:,}건 · 예산 {ProjectService.format_budget(projects['total_budget'])}\n"
                f"진행중 {statuses['진행중']} · 예정 {statuses['예정']} · "
                f"완료 {statuses['완료']} · 보류 {statuses['보류']}"
            )
        )
        contracts = summary["contract_summary"]
        contract_summary_label.configure(
            text=(
                f"총 {contracts['total_count']:,}건 · 금액 {ContractService.format_amount(contracts['total_amount'])}\n"
                f"평균 {ContractService.format_amount(contracts['average_amount'])} · "
                f"품목 {contracts['product_count']:,}개 · 업체 {contracts['vendor_count']:,}개"
            )
        )

        for tree, rows, key in (
            (product_tree, summary["product_statistics"], "product"),
            (vendor_tree, summary["vendor_statistics"], "vendor"),
        ):
            tree.delete(*tree.get_children())
            for index, row in enumerate(rows[:10]):
                tree.insert(
                    "",
                    "end",
                    iid=f"{key}-{index}",
                    values=(
                        row[key],
                        row["count"],
                        row["quantity"],
                        ContractService.format_amount(row["amount"]),
                        f"{row['share']:.1f}%",
                    ),
                )

        trend_tree.delete(*trend_tree.get_children())
        for row in summary["yearly_trend"]:
            trend_tree.insert(
                "",
                "end",
                iid=f"trend-{row['year']}",
                values=(
                    row["year"],
                    row["project_count"],
                    ProjectService.format_budget(row["project_budget"]),
                    row["contract_count"],
                    ContractService.format_amount(row["contract_amount"]),
                ),
            )

        cycle_label.configure(text=purchase_cycle_text(summary["purchase_cycle"]))
        opportunity = summary["opportunity"]
        opportunity_label.configure(
            text=(
                f"{opportunity['score']}/100 · {opportunity['priority']} · "
                f"기회 {opportunity['opportunity_count']}건"
            )
        )
        opportunity_bar.set(opportunity["score"] / 100)
        opportunity_tree.delete(*opportunity_tree.get_children())
        for index, opportunity_item in enumerate(opportunity["insights"][:10]):
            prefix = (
                "계약"
                if opportunity_item.get("target_type") == "contract"
                else "프로젝트"
            )
            opportunity_tree.insert(
                "",
                "end",
                iid=f"opportunity-{index}",
                values=(
                    f"{prefix}: {opportunity_item['project_name']}",
                    opportunity_item["recommendation"],
                    opportunity_item["score"],
                    opportunity_item["priority"],
                ),
            )

        insight_values = business_insight_values(insight)
        business_summary_label.configure(text=insight_values["summary"])
        explanation_label.configure(text=insight_values["explanation"])
        recommendation_tree.delete(*recommendation_tree.get_children())
        for index, recommendation in enumerate(insight["recommended_products"]):
            recommendation_tree.insert(
                "",
                "end",
                iid=f"recommendation-{index}",
                values=(
                    recommendation["product"],
                    f"{recommendation['confidence']}%",
                    recommendation["priority"],
                    recommendation["reason"],
                ),
            )
        risk_tree.delete(*risk_tree.get_children())
        for index, risk in enumerate(insight["risks"]):
            risk_tree.insert(
                "",
                "end",
                iid=f"risk-{index}",
                values=(risk["level"], risk["risk"], risk["mitigation"]),
            )
        action_tree.delete(*action_tree.get_children())
        for action in insight["next_actions"]:
            action_tree.insert(
                "",
                "end",
                iid=f"action-{action['order']}",
                values=(
                    action["order"],
                    action["timing"],
                    action["action"],
                    action["reason"],
                ),
            )
        timeline_tree.delete(*timeline_tree.get_children())
        for index, event in enumerate(insight["opportunity_timeline"]):
            timeline_tree.insert(
                "",
                "end",
                iid=f"timeline-{index}",
                values=(event["date"], event["type"], event["title"], event["detail"]),
            )
        matrix_tree.delete(*matrix_tree.get_children())
        for index, item in enumerate(insight["priority_matrix"]):
            matrix_tree.insert(
                "",
                "end",
                iid=f"matrix-{index}",
                values=(
                    item["item"],
                    item["impact"],
                    item["urgency"],
                    item["quadrant"],
                    item["reason"],
                ),
            )
        dashboard_status.configure(
            text=f"BI 이력 #{insight['history_id']} · 저장된 프로젝트·계약·활성 규칙 기준"
        )

    def export_excel():
        file_path = filedialog.asksaveasfilename(
            parent=parent,
            defaultextension=".xlsx",
            filetypes=(("Excel", "*.xlsx"),),
            initialfile=f"{school_name}_분석대시보드.xlsx",
        )
        if file_path:
            try:
                summary = InsightService.summarize_school(
                    school_code, persist=False
                )["analytics"]
                DashboardExportService.export_excel(file_path, school_name, summary)
                messagebox.showinfo("내보내기", "Excel 저장이 완료되었습니다.", parent=parent)
            except (OSError, ValueError) as error:
                messagebox.showerror("내보내기 오류", str(error), parent=parent)

    def export_pdf():
        file_path = filedialog.asksaveasfilename(
            parent=parent,
            defaultextension=".pdf",
            filetypes=(("PDF", "*.pdf"),),
            initialfile=f"{school_name}_분석요약.pdf",
        )
        if file_path:
            try:
                summary = InsightService.summarize_school(
                    school_code, persist=False
                )["analytics"]
                DashboardExportService.export_pdf(file_path, school_name, summary)
                messagebox.showinfo("내보내기", "PDF 저장이 완료되었습니다.", parent=parent)
            except (OSError, ValueError) as error:
                messagebox.showerror("내보내기 오류", str(error), parent=parent)

    ctk.CTkButton(toolbar, text="새로고침", width=95, command=refresh_dashboard).pack(
        side="right", padx=3
    )
    ctk.CTkButton(toolbar, text="Excel", width=85, command=export_excel).pack(
        side="right", padx=3
    )
    ctk.CTkButton(toolbar, text="PDF 요약", width=95, command=export_pdf).pack(
        side="right", padx=3
    )
    refresh_dashboard()
    return dashboard
