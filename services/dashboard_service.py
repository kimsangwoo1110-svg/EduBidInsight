"""Cached aggregate read model for the EduBid Today Dashboard."""

from datetime import date, datetime
from statistics import mean
from threading import RLock
from time import monotonic

from services.action_center import ActionCenterService
from services.analytics_service import AnalyticsService
from services.opportunity_engine import OpportunityEngine
from services.school_profile_service import SchoolProfileService


class DashboardService:
    """Compose existing service results into one five-minute dashboard snapshot."""

    CACHE_TTL_SECONDS = 300
    PRIORITY_LIMIT = 10
    ACTIVITY_LIMIT = 20
    opportunity_engine = OpportunityEngine
    action_service = ActionCenterService
    profile_service = SchoolProfileService
    analytics_service = AnalyticsService
    _cache = {}
    _lock = RLock()

    @classmethod
    def get_dashboard(cls, today=None, force_refresh=False):
        selected_today = cls._date(today or date.today())
        cache_key = selected_today.isoformat()
        current_clock = monotonic()
        with cls._lock:
            cached = cls._cache.get(cache_key)
            if (
                not force_refresh and cached
                and current_clock - cached["cached_at"] < cls.CACHE_TTL_SECONDS
            ):
                return cached["value"]

        started = monotonic()
        value = cls._aggregate(selected_today)
        value["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        value["elapsed_ms"] = round((monotonic() - started) * 1000, 2)
        with cls._lock:
            cls._cache[cache_key] = {"cached_at": monotonic(), "value": value}
        return value

    @classmethod
    def refresh(cls, today=None):
        """Force a fresh snapshot for manual refresh and post-mutation UI flows."""
        return cls.get_dashboard(today=today, force_refresh=True)

    @classmethod
    def complete_action(cls, action_id, today=None):
        """Complete an action through the workflow service and refresh the snapshot."""
        cls.action_service.update_status(action_id, "Completed")
        return cls.refresh(today=today)

    @classmethod
    def clear_cache(cls):
        with cls._lock:
            cls._cache.clear()

    @classmethod
    def _aggregate(cls, today):
        opportunities = cls.opportunity_engine.dashboard(
            limit=cls.PRIORITY_LIMIT, today=today, persist=False, cached_only=True
        )
        all_opportunities = opportunities.get(
            "all_opportunities", opportunities.get("top_opportunities", [])
        )
        priority_schools = sorted(
            all_opportunities,
            key=lambda item: (-item.score, item.school_name.casefold(), item.school_id),
        )[: cls.PRIORITY_LIMIT]
        actions = cls.action_service.dashboard_summary(today=today)
        action_activity = cls.action_service.recent_activity(limit=cls.ACTIVITY_LIMIT)
        profiles = list((opportunities.get("loaded_profiles") or {}).values())
        profile_activity = cls.profile_service.recent_activity_from_profiles(
            profiles, limit=cls.ACTIVITY_LIMIT
        )
        legacy_crm_activity = [
            {
                "id": event.get("id"),
                "timestamp": event.get("timestamp", ""),
                "activity_type": "CRM",
                "school_id": event.get("school_code", ""),
                "title": event.get("title", "CRM activity"),
                "description": event.get("description", ""),
            }
            for event in profile_activity
            if event.get("source") == "CRM"
        ]
        recent_activity = sorted(
            [*action_activity, *legacy_crm_activity],
            key=lambda item: str(item.get("timestamp") or ""),
            reverse=True,
        )[: cls.ACTIVITY_LIMIT]
        portfolio = cls.analytics_service.education_office_analytics()
        scores = [int(item.score or 0) for item in all_opportunities]
        average_score = round(mean(scores), 1) if scores else 0.0
        school_names = {
            item.school_id: item.school_name for item in all_opportunities
        }
        alerts = cls._alerts(all_opportunities, actions["overdue"], school_names)
        kpis = {
            "opportunity_count": len(all_opportunities),
            "completed_this_week": actions["completed_this_week"],
            "upcoming_visits": actions["upcoming_visits"],
            "average_opportunity_score": average_score,
            "open_actions": actions["open_actions"],
        }
        return {
            "date": today.isoformat(),
            "priority_schools": priority_schools,
            "today_actions": actions["today"],
            "upcoming_visits": actions["visits"],
            "overdue_actions": actions["overdue"],
            "recently_completed": actions["completed"],
            "recent_activity": recent_activity,
            "weekly_kpi": kpis,
            "opportunity_summary": {
                "total": len(all_opportunities),
                "average_score": average_score,
                "high_priority": sum(item.score >= 70 for item in all_opportunities),
                "qualified": sum(50 <= item.score < 70 for item in all_opportunities),
                "monitor": sum(item.score < 50 for item in all_opportunities),
            },
            "alerts": alerts,
            "school_names": school_names,
            "portfolio_analytics": portfolio,
        }

    @staticmethod
    def _alerts(opportunities, overdue_actions, school_names=None):
        names = school_names or {}
        alerts = []
        seen = set()
        evidence_alerts = (
            ("no crm activity", "CRM inactivity", "Warning"),
            ("contract renewal window", "Renewal window", "High"),
            ("large annual project budget", "High-value project", "High"),
        )
        for result in opportunities:
            evidence_text = " ".join(result.evidence).casefold()
            for marker, alert_type, severity in evidence_alerts:
                if marker not in evidence_text:
                    continue
                key = (alert_type, result.school_id)
                if key in seen:
                    continue
                seen.add(key)
                alerts.append({
                    "type": alert_type,
                    "severity": severity,
                    "school_id": result.school_id,
                    "school_name": result.school_name,
                    "message": f"{result.school_name}: {alert_type}",
                })
        for action in overdue_actions:
            key = ("Overdue action", action.action_id)
            if key in seen:
                continue
            seen.add(key)
            school_name = names.get(action.school_id, action.school_id)
            alerts.append({
                "type": "Overdue action",
                "severity": "Critical",
                "school_id": action.school_id,
                "school_name": school_name,
                "action_id": action.action_id,
                "message": f"{school_name}: {action.title} was due {action.due_date}",
            })
        severity_order = {"Critical": 0, "High": 1, "Warning": 2}
        return sorted(
            alerts,
            key=lambda item: (
                severity_order.get(item["severity"], 9),
                item["school_name"].casefold(),
                item["type"],
            ),
        )

    @staticmethod
    def _date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value).strip()[:10])
