"""School-level analytics across projects, contracts, and opportunities."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import median

from services.contract_service import ContractService
from services.connectors.g2b_import import G2BService
from services.connectors.education_office_import import EducationOfficeService
from services.project_service import ProjectService
from services.rule_service import RuleService


class AnalyticsService:
    """Build consistent dashboard metrics from existing domain services."""

    @classmethod
    def school_summary(cls, school_code):
        projects = ProjectService.list_for_school(school_code)
        contracts = ContractService.search_by_school(school_code)
        project_summary = ProjectService.summarize(projects)
        project_analytics = cls._project_analytics(projects)
        contract_summary = cls._contract_statistics(contracts)
        g2b_ids = set(G2BService.contract_ids_for_school(school_code))
        g2b_contracts = [contract for contract in contracts if contract["id"] in g2b_ids]
        g2b_summary = {
            "total_count": len(g2b_contracts),
            "total_spending": sum(
                float(contract.get("amount") or 0) for contract in g2b_contracts
            ),
            "latest_contracts": sorted(
                g2b_contracts,
                key=lambda contract: (
                    str(contract.get("contract_date") or ""),
                    int(contract.get("id") or 0),
                ),
                reverse=True,
            )[:5],
        }
        opportunity = cls._opportunity_score(projects, contracts)
        return {
            "school_code": str(school_code or "").strip(),
            "project_summary": project_summary,
            "project_analytics": project_analytics,
            "contract_summary": contract_summary,
            "g2b_summary": g2b_summary,
            "product_statistics": cls._group_statistics(contracts, "product"),
            "vendor_statistics": cls._group_statistics(contracts, "vendor"),
            "yearly_trend": cls._yearly_trend(projects, contracts),
            "purchase_cycle": cls._purchase_cycle(contracts),
            "opportunity": opportunity,
            "kpis": {
                "projects": project_summary["total_count"],
                "project_budget": project_summary["total_budget"],
                "active_projects": project_analytics["active_projects"],
                "contracts": contract_summary["total_count"],
                "contract_amount": contract_summary["total_amount"],
                "vendors": contract_summary["vendor_count"],
                "opportunity_score": opportunity["score"],
                "g2b_contracts": g2b_summary["total_count"],
                "g2b_spending": g2b_summary["total_spending"],
            },
        }

    @classmethod
    def contract_statistics(cls, school_code):
        return cls._contract_statistics(ContractService.search_by_school(school_code))

    @classmethod
    def vendor_statistics(cls, school_code):
        return cls._group_statistics(
            ContractService.search_by_school(school_code), "vendor"
        )

    @classmethod
    def product_statistics(cls, school_code):
        return cls._group_statistics(
            ContractService.search_by_school(school_code), "product"
        )

    @classmethod
    def yearly_trend(cls, school_code):
        return cls._yearly_trend(
            ProjectService.list_for_school(school_code),
            ContractService.search_by_school(school_code),
        )

    @classmethod
    def purchase_cycle(cls, school_code):
        return cls._purchase_cycle(ContractService.search_by_school(school_code))

    @classmethod
    def opportunity_score(cls, school_code):
        return cls._opportunity_score(
            ProjectService.list_for_school(school_code),
            ContractService.search_by_school(school_code),
        )

    @classmethod
    def summarize_loaded(cls, projects, contracts):
        """Reuse analytics calculations for an already-loaded profile context."""
        return {
            "project_analytics": cls._project_analytics(projects),
            "contract_summary": cls._contract_statistics(contracts),
            "yearly_trend": cls._yearly_trend(projects, contracts),
        }

    @classmethod
    def education_office_analytics(cls):
        """Aggregate imported office projects for trends and office comparison."""
        projects = EducationOfficeService.projects()
        analytics = cls._project_analytics(projects)
        offices = defaultdict(lambda: {"project_count": 0, "budget": 0.0})
        for project in projects:
            office = str(project.get("office") or "Unknown").strip() or "Unknown"
            offices[office]["project_count"] += 1
            offices[office]["budget"] += float(project.get("budget") or 0)
        analytics["office_comparison"] = [
            {"office": office, **values}
            for office, values in sorted(
                offices.items(), key=lambda item: (-item[1]["budget"], item[0].casefold())
            )
        ]
        return analytics

    @staticmethod
    def _project_analytics(projects):
        trends = defaultdict(lambda: {"project_count": 0, "budget": 0.0})
        categories = defaultdict(lambda: {"project_count": 0, "budget": 0.0})
        for project in projects:
            year = project.get("fiscal_year") or project.get("start_year")
            if year:
                trends[int(year)]["project_count"] += 1
                trends[int(year)]["budget"] += float(project.get("budget") or 0)
            category = str(project.get("category") or "Other").strip() or "Other"
            categories[category]["project_count"] += 1
            categories[category]["budget"] += float(project.get("budget") or 0)
        return {
            "total_projects": len(projects),
            "active_projects": sum(
                project.get("status") in {"진행중", "예정", "Active"} for project in projects
            ),
            "completed_projects": sum(
                project.get("status") in {"완료", "Completed"} for project in projects
            ),
            "total_budget": sum(float(project.get("budget") or 0) for project in projects),
            "budget_trends": [
                {"year": year, **trends[year]} for year in sorted(trends)
            ],
            "category_distribution": [
                {"category": category, **values}
                for category, values in sorted(
                    categories.items(), key=lambda item: (-item[1]["budget"], item[0].casefold())
                )
            ],
        }

    @staticmethod
    def _contract_statistics(contracts):
        amounts = [float(contract.get("amount") or 0) for contract in contracts]
        return {
            "total_count": len(contracts),
            "total_amount": sum(amounts),
            "average_amount": sum(amounts) / len(amounts) if amounts else 0,
            "maximum_amount": max(amounts, default=0),
            "total_quantity": sum(int(contract.get("quantity") or 0) for contract in contracts),
            "vendor_count": len(
                {contract.get("vendor") for contract in contracts if contract.get("vendor")}
            ),
            "product_count": len(
                {contract.get("product") for contract in contracts if contract.get("product")}
            ),
        }

    @staticmethod
    def _group_statistics(contracts, field):
        grouped = defaultdict(lambda: {"count": 0, "quantity": 0, "amount": 0.0})
        total_amount = sum(float(contract.get("amount") or 0) for contract in contracts)
        for contract in contracts:
            name = str(contract.get(field) or "미분류").strip() or "미분류"
            grouped[name]["count"] += 1
            grouped[name]["quantity"] += int(contract.get("quantity") or 0)
            grouped[name]["amount"] += float(contract.get("amount") or 0)
        rows = []
        for name, values in grouped.items():
            rows.append(
                {
                    field: name,
                    **values,
                    "share": (values["amount"] / total_amount * 100) if total_amount else 0,
                }
            )
        return sorted(rows, key=lambda row: (-row["amount"], row[field].casefold()))

    @staticmethod
    def _yearly_trend(projects, contracts):
        yearly = defaultdict(
            lambda: {
                "project_count": 0,
                "project_budget": 0.0,
                "contract_count": 0,
                "contract_amount": 0.0,
            }
        )
        for project in projects:
            year = project.get("start_year")
            if year:
                yearly[int(year)]["project_count"] += 1
                yearly[int(year)]["project_budget"] += float(project.get("budget") or 0)
        for contract in contracts:
            contract_date = str(contract.get("contract_date") or "")
            if len(contract_date) >= 4 and contract_date[:4].isdigit():
                year = int(contract_date[:4])
                yearly[year]["contract_count"] += 1
                yearly[year]["contract_amount"] += float(contract.get("amount") or 0)
        return [{"year": year, **yearly[year]} for year in sorted(yearly)]

    @staticmethod
    def _purchase_cycle(contracts):
        purchase_dates = sorted(
            {
                date.fromisoformat(contract["contract_date"])
                for contract in contracts
                if contract.get("contract_date")
            }
        )
        if not purchase_dates:
            return {
                "purchase_dates": 0,
                "average_days": None,
                "median_days": None,
                "last_purchase_date": None,
                "next_expected_date": None,
                "status": "데이터 없음",
            }
        intervals = [
            (current - previous).days
            for previous, current in zip(purchase_dates, purchase_dates[1:])
        ]
        average_days = sum(intervals) / len(intervals) if intervals else None
        next_expected = (
            purchase_dates[-1] + timedelta(days=round(average_days))
            if average_days is not None
            else None
        )
        return {
            "purchase_dates": len(purchase_dates),
            "average_days": round(average_days, 1) if average_days is not None else None,
            "median_days": float(median(intervals)) if intervals else None,
            "last_purchase_date": purchase_dates[-1].isoformat(),
            "next_expected_date": next_expected.isoformat() if next_expected else None,
            "status": "분석 완료" if intervals else "데이터 부족",
        }

    @staticmethod
    def _opportunity_score(projects, contracts):
        insights = (
            RuleService.evaluate_projects(projects)
            + RuleService.evaluate_contracts(contracts)
        )
        scores = [int(insight["score"] or 0) for insight in insights]
        score = min(100, max(scores, default=0))
        return {
            "score": score,
            "raw_total": sum(scores),
            "opportunity_count": len(insights),
            "high_priority_count": sum(
                insight.get("priority") == "높음" for insight in insights
            ),
            "priority": RuleService.priority_for_score(score) if score else "없음",
            "insights": sorted(
                insights,
                key=lambda insight: (-insight["score"], insight["project_name"].casefold()),
            ),
        }
