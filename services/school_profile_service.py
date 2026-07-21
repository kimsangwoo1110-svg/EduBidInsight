"""Single read-model aggregation service for the School 360° profile."""

from services.connectors.schoolmarket_import import SchoolMarketService
from services.connectors.g2b_import import G2BService
from services.contract_service import ContractService
from services.project_service import ProjectService
from services.sales_activity_service import SalesActivityService
from services.school_service import SCHOOL_FIELDS, SchoolService
from services.analytics_service import AnalyticsService
from services.action_center import ActionCenterService


class SchoolProfileService:
    """Load each school data source once and build one profile read model."""

    DEFAULT_ACTIVITY_LIMIT = 30

    @staticmethod
    def resolve_school(value):
        """Resolve a school code or exact school name through SchoolService."""
        selected = str(value or "").strip()
        if not selected:
            return None
        school = SchoolService.get_by_code(selected)
        if school:
            return school
        matches = SchoolService.search(keyword=selected)
        exact = next(
            (
                row for row in matches
                if str(row[1] or "").strip().casefold() == selected.casefold()
            ),
            None,
        )
        return dict(zip(SCHOOL_FIELDS, exact)) if exact else None

    @staticmethod
    def recent_activity_from_profiles(profiles, limit=20):
        """Merge already-loaded profile events without issuing new lookups."""
        events = [
            event
            for profile in profiles
            for event in (profile.get("recent_activity") or [])
        ]
        return sorted(
            events,
            key=lambda event: (str(event.get("timestamp") or ""), int(event.get("id") or 0)),
            reverse=True,
        )[: max(0, int(limit))]

    @classmethod
    def get_profile(
        cls,
        school_code,
        activity_limit=DEFAULT_ACTIVITY_LIMIT,
        school=None,
        include_opportunity=True,
    ):
        code = str(school_code or "").strip()
        school = school or SchoolService.get_by_code(code)
        if school is None:
            return cls.empty_profile(code)

        # Exactly one lookup per source. Everything below is derived in memory.
        contracts = ContractService.search_by_school(code)
        projects = ProjectService.list_for_school(code)
        crm_activities = SalesActivityService.list_by_school(code)
        schoolmarket_ids = set(SchoolMarketService.contract_ids_for_school(code))
        g2b_ids = set(G2BService.contract_ids_for_school(code))
        action_summary = ActionCenterService.school_summary(code)

        events = cls._activity_events(
            contracts, projects, crm_activities, schoolmarket_ids, g2b_ids
        )
        selected_limit = max(0, int(activity_limit))
        if selected_limit:
            events = events[:selected_limit]
        else:
            events = []

        g2b_contracts = [contract for contract in contracts if contract["id"] in g2b_ids]
        active_projects = [
            project for project in projects if project.get("status") in {"진행중", "예정", "Active"}
        ]
        completed_projects = [
            project for project in projects if project.get("status") in {"완료", "Completed"}
        ]
        latest_projects = sorted(
            projects,
            key=lambda project: (
                int(project.get("start_year") or 0),
                str(project.get("updated_at") or ""),
                int(project.get("id") or 0),
            ),
            reverse=True,
        )[:5]
        source_contracts = [
            {
                **contract,
                "source_type": (
                    "G2B" if contract["id"] in g2b_ids
                    else "SchoolMarket" if contract["id"] in schoolmarket_ids
                    else "Contract"
                ),
            }
            for contract in contracts
        ]
        profile = {
            "exists": True,
            "school": cls._school_summary(school),
            "school_metadata": {"office": school.get("office", "")},
            "statistics": {
                "schoolmarket_purchases": sum(
                    contract["id"] in schoolmarket_ids for contract in contracts
                ),
                "contracts": len(contracts),
                "projects": len(projects),
                "crm_activities": len(crm_activities),
                "g2b_contracts": len(g2b_contracts),
                "g2b_spending": sum(
                    float(contract.get("amount") or 0) for contract in g2b_contracts
                ),
                "active_projects": len(active_projects),
                "completed_projects": len(completed_projects),
                "project_budget": sum(float(project.get("budget") or 0) for project in projects),
            },
            "latest_g2b_contracts": sorted(
                g2b_contracts,
                key=lambda contract: (
                    str(contract.get("contract_date") or ""),
                    int(contract.get("id") or 0),
                ),
                reverse=True,
            )[:5],
            "latest_projects": latest_projects,
            "recent_activity": events,
            "actions": action_summary,
            "analytics": AnalyticsService.summarize_loaded(projects, contracts),
            "opportunity_context": {
                "projects": projects,
                "contracts": source_contracts,
                "crm_activities": crm_activities,
            },
            "opportunity": None,
            "ai_recommendation": "Coming in Sprint 16",
        }
        if include_opportunity:
            from services.opportunity_engine import OpportunityEngine

            profile["opportunity"] = OpportunityEngine.evaluate_profile(profile)
        return profile

    @staticmethod
    def empty_profile(school_code=""):
        return {
            "exists": False,
            "school": {
                "school_name": "",
                "school_code": str(school_code or "").strip(),
                "region": "",
                "address": "",
                "student_count": 0,
                "class_count": 0,
            },
            "school_metadata": {"office": ""},
            "statistics": {
                "schoolmarket_purchases": 0,
                "contracts": 0,
                "projects": 0,
                "crm_activities": 0,
                "g2b_contracts": 0,
                "g2b_spending": 0.0,
                "active_projects": 0,
                "completed_projects": 0,
                "project_budget": 0.0,
            },
            "latest_g2b_contracts": [],
            "latest_projects": [],
            "recent_activity": [],
            "actions": ActionCenterService.school_summary(school_code),
            "analytics": AnalyticsService.summarize_loaded([], []),
            "opportunity_context": {
                "projects": [], "contracts": [], "crm_activities": [],
            },
            "opportunity": None,
            "ai_recommendation": "Coming in Sprint 16",
        }

    @staticmethod
    def _school_summary(school):
        return {
            "school_name": school.get("school_name", ""),
            "school_code": school.get("school_code", ""),
            "region": school.get("region", ""),
            "address": school.get("address", ""),
            "student_count": int(school.get("student_count") or 0),
            "class_count": int(school.get("class_count") or 0),
        }

    @classmethod
    def _activity_events(
        cls, contracts, projects, crm_activities, schoolmarket_ids, g2b_ids
    ):
        events = []
        for contract in contracts:
            if contract["id"] in g2b_ids:
                events.append(
                    cls._event(
                        "G2B",
                        contract.get("contract_date") or contract.get("imported_at"),
                        f"G2B contract · {contract.get('product', '')}",
                        f"{contract.get('vendor', '')} · {cls._amount(contract.get('amount'))}",
                        contract.get("id"),
                    )
                )
            elif contract["id"] in schoolmarket_ids:
                events.append(
                    cls._event(
                        "SchoolMarket",
                        contract.get("imported_at") or contract.get("contract_date"),
                        f"SchoolMarket purchase · {contract.get('product', '')}",
                        f"{contract.get('vendor', '')} · {cls._amount(contract.get('amount'))}",
                        contract.get("id"),
                    )
                )
            else:
                events.append(
                    cls._event(
                        "Contract",
                        contract.get("contract_date") or contract.get("imported_at"),
                        f"Contract · {contract.get('product', '')}",
                        f"{contract.get('vendor', '')} · {cls._amount(contract.get('amount'))}",
                        contract.get("id"),
                    )
                )
        for project in projects:
            timestamp = project.get("updated_at")
            if not timestamp and project.get("start_year"):
                timestamp = f"{int(project['start_year']):04d}-01-01"
            source = "Education Office" if project.get("source") == "Education Office" else "Project"
            events.append(
                cls._event(
                    source,
                    timestamp,
                    f"Project · {project.get('project_name', '')}",
                    f"{project.get('status', '')} · {project.get('category', '')}",
                    project.get("id"),
                )
            )
        for activity in crm_activities:
            events.append(
                cls._event(
                    "CRM",
                    activity.get("activity_date"),
                    f"CRM · {activity.get('activity_type', '')}",
                    activity.get("memo") or activity.get("contact_person") or "CRM activity",
                    activity.get("id"),
                )
            )
        return sorted(
            events,
            key=lambda event: (
                str(event.get("timestamp") or ""),
                int(event.get("record_id") or 0),
                event.get("source", ""),
            ),
            reverse=True,
        )

    @staticmethod
    def _event(source, timestamp, title, description, record_id):
        return {
            "source": source,
            "timestamp": str(timestamp or ""),
            "title": str(title or "").strip(),
            "description": str(description or "").strip(),
            "record_id": record_id,
        }

    @staticmethod
    def _amount(value):
        return f"{int(float(value or 0)):,}원"
