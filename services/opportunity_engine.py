"""Explainable rule-based school sales Opportunity Engine v1."""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime

from services.database import (
    add_opportunity_history,
    find_latest_opportunity_history,
    find_opportunity_history,
)
from services.school_profile_service import SchoolProfileService
from services.school_service import SchoolService


DEFAULT_WEIGHTS = {
    "ai_education_project": 20,
    "space_innovation": 15,
    "smart_classroom": 15,
    "recent_ict_purchase": 10,
    "recent_g2b_contract": 10,
    "crm_inactive": 20,
    "contract_renewal": 15,
    "large_annual_budget": 10,
    "recent_project_completion": 10,
}


@dataclass(frozen=True)
class OpportunityResult:
    school_id: str
    school_name: str
    score: int
    priority: str
    recommendation: str
    next_action: str
    confidence: str
    evidence: list
    generated_at: str

    def to_dict(self):
        return asdict(self)


class OpportunityEngine:
    """Apply configurable weighted rules to one aggregated school profile."""

    RECENT_DAYS = 365
    CRM_INACTIVE_DAYS = 180
    RENEWAL_MIN_DAYS = 300
    RENEWAL_MAX_DAYS = 425
    LARGE_ANNUAL_BUDGET = 100_000_000

    @classmethod
    def evaluate(cls, school_id, weights=None, today=None, persist=False):
        profile = SchoolProfileService.get_profile(
            school_id, include_opportunity=False
        )
        result = cls.evaluate_profile(profile, weights=weights, today=today)
        if persist and result.school_id:
            cls.save(result)
        return result

    @classmethod
    def evaluate_profile(cls, profile, weights=None, today=None):
        selected_weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        selected_today = cls._date(today or date.today())
        school = profile.get("school") or {}
        context = profile.get("opportunity_context") or {}
        projects = context.get("projects") or []
        contracts = context.get("contracts") or []
        crm_activities = context.get("crm_activities") or []
        analytics = profile.get("analytics") or {}
        evidence = []
        score = 0

        def award(rule, reason):
            nonlocal score
            score += max(0, int(selected_weights.get(rule, 0) or 0))
            evidence.append(f"✓ {reason}")

        project_texts = [
            f"{project.get('project_name', '')} {project.get('category', '')}".casefold()
            for project in projects
        ]
        if any(cls._contains(text, ("ai education", "ai교육", "ai 교육", "인공지능")) for text in project_texts):
            award("ai_education_project", "AI Education Project")
        if any(cls._contains(text, ("space innovation", "공간혁신", "공간 혁신")) for text in project_texts):
            award("space_innovation", "Space Innovation Project")
        if any(cls._contains(text, ("smart classroom", "스마트교실", "스마트 교실")) for text in project_texts):
            award("smart_classroom", "Smart Classroom Project")

        schoolmarket_contracts = [
            contract for contract in contracts if contract.get("source_type") == "SchoolMarket"
        ]
        recent_ict = next(
            (
                contract for contract in schoolmarket_contracts
                if cls._is_recent(contract.get("contract_date") or contract.get("imported_at"), selected_today)
                and cls._contains(
                    f"{contract.get('category', '')} {contract.get('product', '')}".casefold(),
                    ("ict", "tablet", "notebook", "display", "태블릿", "노트북", "전자칠판", "컴퓨터"),
                )
            ),
            None,
        )
        if recent_ict:
            award("recent_ict_purchase", "Recent ICT Purchase")

        recent_g2b = next(
            (
                contract for contract in contracts
                if contract.get("source_type") == "G2B"
                and cls._is_recent(contract.get("contract_date") or contract.get("imported_at"), selected_today)
            ),
            None,
        )
        if recent_g2b:
            award("recent_g2b_contract", "Recent G2B Contract")

        crm_dates = [
            selected
            for selected in (
                cls._optional_date(activity.get("activity_date"))
                for activity in crm_activities
            )
            if selected is not None
        ]
        latest_crm = max(crm_dates, default=None)
        if latest_crm is None:
            award("crm_inactive", "No CRM activity recorded")
        elif (selected_today - latest_crm).days > cls.CRM_INACTIVE_DAYS:
            months = max(6, round((selected_today - latest_crm).days / 30))
            award("crm_inactive", f"No CRM activity in {months} months")

        renewal = next(
            (
                contract for contract in contracts
                if cls._in_renewal_window(contract.get("contract_date"), selected_today)
            ),
            None,
        )
        if renewal:
            award("contract_renewal", "Contract Renewal Window")

        budget_trends = (
            analytics.get("project_analytics", {}).get("budget_trends", [])
        )
        if any(float(row.get("budget") or 0) >= cls.LARGE_ANNUAL_BUDGET for row in budget_trends):
            award("large_annual_budget", "Large Annual Project Budget")

        recent_completion = next(
            (
                project for project in projects
                if project.get("status") in {"완료", "Completed"}
                and cls._is_recent(project.get("updated_at") or f"{project.get('end_year') or ''}-12-31", selected_today)
            ),
            None,
        )
        if recent_completion:
            award("recent_project_completion", "Recent Project Completion")

        capped_score = min(100, score)
        recommendation = cls.recommendation(evidence)
        return OpportunityResult(
            school_id=str(school.get("school_code") or "").strip(),
            school_name=str(school.get("school_name") or "").strip(),
            score=capped_score,
            priority=cls.priority(capped_score),
            recommendation=recommendation,
            next_action=cls.next_action(evidence),
            confidence=cls.confidence(len(evidence)),
            evidence=evidence,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )

    @staticmethod
    def priority(score):
        value = max(0, min(100, int(score or 0)))
        if value >= 90:
            return "★★★★★"
        if value >= 70:
            return "★★★★☆"
        if value >= 50:
            return "★★★☆☆"
        return "★★☆☆☆"

    @staticmethod
    def confidence(evidence_count):
        count = max(0, int(evidence_count or 0))
        if count >= 5:
            return "High"
        if count >= 3:
            return "Medium"
        return "Low"

    @staticmethod
    def recommendation(evidence):
        text = " ".join(evidence).casefold()
        if "ai education" in text:
            return "Recommend AI Classroom proposal."
        if any(term in text for term in ("smart classroom", "space innovation", "ict purchase")):
            return "Recommend Interactive Display."
        if "no crm activity" in text:
            return "Recommend Follow-up Visit."
        if "contract renewal" in text or "g2b" in text:
            return "Recommend contract renewal proposal."
        return "Monitor school opportunity."

    @staticmethod
    def next_action(evidence):
        text = " ".join(evidence).casefold()
        if "no crm activity" in text:
            return "Visit this week"
        if "contract renewal" in text or "g2b" in text:
            return "Prepare quotation"
        if any(term in text for term in ("ai education", "smart classroom", "space innovation")):
            return "Call next Monday"
        return "Monitor project"

    @classmethod
    def save(cls, result):
        return add_opportunity_history(
            result.school_id,
            result.school_name,
            result.score,
            result.generated_at,
            json.dumps(result.to_dict(), ensure_ascii=False),
        )

    @staticmethod
    def generate_actions(result, persist=True, today=None):
        """Convert a scored opportunity into Action Center suggestions."""
        from services.action_center import ActionCenterService

        return ActionCenterService.generate_from_opportunity(
            result, persist=persist, today=today
        )

    @classmethod
    def dashboard(
        cls, limit=20, weights=None, today=None, persist=True, cached_only=False
    ):
        if cached_only:
            return cls.cached_dashboard(limit=limit)
        results = []
        profiles = {}
        for school in SchoolService.all():
            profile = SchoolProfileService.get_profile(
                school["school_code"], school=school, include_opportunity=False
            )
            profiles[school["school_code"]] = profile
            result = cls.evaluate_profile(profile, weights=weights, today=today)
            results.append(result)
            if persist:
                cls.save(result)
        all_ranked = sorted(
            results, key=lambda item: (-item.score, item.school_name.casefold(), item.school_id)
        )
        ranked = all_ranked[: max(1, int(limit))]
        return {
            "top_opportunities": ranked,
            "highest_scores": ranked[:5],
            "recently_increased_scores": cls.recently_increased(limit=limit),
            "all_opportunities": all_ranked,
            "loaded_profiles": profiles,
        }

    @classmethod
    def cached_dashboard(cls, limit=20):
        """Build a fast ranking from the latest persisted score per school."""
        latest = {}
        for _row_id, school_id, school_name, score, generated_at, result_json in find_latest_opportunity_history():
            if school_id in latest:
                continue
            try:
                payload = json.loads(result_json)
                latest[school_id] = OpportunityResult(**payload)
            except (TypeError, ValueError, json.JSONDecodeError):
                latest[school_id] = OpportunityResult(
                    school_id=school_id,
                    school_name=school_name,
                    score=int(score),
                    priority=cls.priority(score),
                    recommendation="Monitor school opportunity.",
                    next_action="Monitor project",
                    confidence="Low",
                    evidence=[],
                    generated_at=generated_at,
                )
        ranked = sorted(
            latest.values(),
            key=lambda item: (-item.score, item.school_name.casefold(), item.school_id),
        )
        selected_limit = max(1, int(limit))
        return {
            "top_opportunities": ranked[:selected_limit],
            "highest_scores": ranked[:5],
            "recently_increased_scores": cls.recently_increased(limit=limit),
            "all_opportunities": ranked,
            "loaded_profiles": {},
        }

    @staticmethod
    def recently_increased(limit=20):
        scores = {}
        names = {}
        for _row_id, school_id, school_name, score, _generated_at, _json in find_opportunity_history():
            names[school_id] = school_name
            scores.setdefault(school_id, []).append(int(score))
        increases = [
            {
                "school_id": school_id,
                "school_name": names[school_id],
                "score": values[0],
                "increase": values[0] - values[1],
            }
            for school_id, values in scores.items()
            if len(values) >= 2 and values[0] > values[1]
        ]
        return sorted(
            increases,
            key=lambda item: (-item["increase"], -item["score"], item["school_name"].casefold()),
        )[: max(1, int(limit))]

    @staticmethod
    def _contains(text, terms):
        return any(term in text for term in terms)

    @classmethod
    def _is_recent(cls, value, today):
        selected = cls._optional_date(value)
        return selected is not None and 0 <= (today - selected).days <= cls.RECENT_DAYS

    @classmethod
    def _in_renewal_window(cls, value, today):
        selected = cls._optional_date(value)
        if selected is None:
            return False
        age = (today - selected).days
        return cls.RENEWAL_MIN_DAYS <= age <= cls.RENEWAL_MAX_DAYS

    @staticmethod
    def _optional_date(value):
        text = str(value or "").strip()[:10]
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])
