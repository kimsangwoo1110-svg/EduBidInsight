"""CRM activity, follow-up, pipeline, and sales KPI service."""

from datetime import date, datetime, timedelta

from services.database import (
    add_sales_activity,
    delete_sales_activity,
    find_sales_activities,
    update_sales_activity,
)


ACTIVITY_FIELDS = (
    "id",
    "school_code",
    "activity_date",
    "activity_type",
    "contact_person",
    "memo",
    "next_action_date",
    "status",
)
PIPELINE_STAGES = ("Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost")
ACTIVITY_TYPES = ("방문", "전화", "견적", "이메일", "미팅", "기타")
CLOSED_STAGES = {"Won", "Lost"}


class SalesActivityService:
    """Service boundary for daily school sales workflow management."""

    PIPELINE_STAGES = PIPELINE_STAGES
    ACTIVITY_TYPES = ACTIVITY_TYPES

    @classmethod
    def add_activity(
        cls,
        school_code,
        activity_date,
        activity_type,
        contact_person="",
        memo="",
        next_action_date=None,
        status="Lead",
    ):
        activity = cls._validate(
            school_code,
            activity_date,
            activity_type,
            contact_person,
            memo,
            next_action_date,
            status,
        )
        return add_sales_activity(activity)

    @classmethod
    def update_activity(
        cls,
        activity_id,
        school_code,
        activity_date,
        activity_type,
        contact_person="",
        memo="",
        next_action_date=None,
        status="Lead",
    ):
        activity = cls._validate(
            school_code,
            activity_date,
            activity_type,
            contact_person,
            memo,
            next_action_date,
            status,
        )
        return update_sales_activity(activity_id, activity)

    @staticmethod
    def delete_activity(activity_id):
        return delete_sales_activity(activity_id)

    @staticmethod
    def list_by_school(school_code, limit=None):
        return SalesActivityService._rows(
            find_sales_activities(school_code=school_code, limit=limit)
        )

    @classmethod
    def upcoming_actions(cls, school_code=None, days=30, today=None):
        selected_today = cls._as_date(today or date.today())
        deadline = selected_today + timedelta(days=max(0, int(days)))
        activities = cls._rows(find_sales_activities(school_code=school_code or ""))
        upcoming = [
            activity
            for activity in activities
            if activity["status"] not in CLOSED_STAGES
            and activity["next_action_date"]
            and selected_today
            <= date.fromisoformat(activity["next_action_date"])
            <= deadline
        ]
        return sorted(
            upcoming,
            key=lambda activity: (activity["next_action_date"], activity["id"]),
        )

    @classmethod
    def overdue_actions(cls, school_code=None, today=None):
        selected_today = cls._as_date(today or date.today())
        activities = cls._rows(find_sales_activities(school_code=school_code or ""))
        overdue = [
            activity
            for activity in activities
            if activity["status"] not in CLOSED_STAGES
            and activity["next_action_date"]
            and date.fromisoformat(activity["next_action_date"]) < selected_today
        ]
        return sorted(
            overdue,
            key=lambda activity: (activity["next_action_date"], activity["id"]),
        )

    @classmethod
    def recent_activities(cls, school_code, limit=5):
        return cls.list_by_school(school_code, limit=limit)

    @classmethod
    def pipeline_summary(cls, school_code):
        activities = cls.list_by_school(school_code)
        counts = {stage: 0 for stage in PIPELINE_STAGES}
        for activity in activities:
            counts[activity["status"]] += 1
        return {
            "current_stage": activities[0]["status"] if activities else "Lead",
            "counts": counts,
            "total": len(activities),
        }

    @classmethod
    def kpi_summary(cls, school_code):
        activities = cls.list_by_school(school_code)
        normalized_types = [activity["activity_type"].strip().casefold() for activity in activities]
        visits = sum(value in {"방문", "visit", "visits"} for value in normalized_types)
        calls = sum(value in {"전화", "call", "calls"} for value in normalized_types)
        quotations = sum(
            value in {"견적", "quotation", "quote", "quotations"}
            for value in normalized_types
        )
        wins = sum(activity["status"] == "Won" for activity in activities)
        losses = sum(activity["status"] == "Lost" for activity in activities)
        decisions = wins + losses
        return {
            "visits": visits,
            "calls": calls,
            "quotations": quotations,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / decisions * 100) if decisions else 0,
        }

    @classmethod
    def school_crm_summary(cls, school_code, today=None):
        return {
            "recent_activities": cls.recent_activities(school_code),
            "upcoming_actions": cls.upcoming_actions(
                school_code, today=today
            ),
            "overdue_actions": cls.overdue_actions(school_code, today=today),
            "pipeline": cls.pipeline_summary(school_code),
            "kpis": cls.kpi_summary(school_code),
        }

    @classmethod
    def _validate(
        cls,
        school_code,
        activity_date,
        activity_type,
        contact_person,
        memo,
        next_action_date,
        status,
    ):
        code = str(school_code or "").strip()
        selected_type = str(activity_type or "").strip()
        selected_status = str(status or "").strip()
        if not code:
            raise ValueError("school_code is required")
        if not selected_type:
            raise ValueError("activity_type is required")
        if selected_status not in PIPELINE_STAGES:
            raise ValueError(f"unsupported pipeline stage: {selected_status}")
        activity_day = cls._as_date(activity_date).isoformat()
        next_day = (
            cls._as_date(next_action_date).isoformat()
            if str(next_action_date or "").strip()
            else None
        )
        return {
            "school_code": code,
            "activity_date": activity_day,
            "activity_type": selected_type,
            "contact_person": str(contact_person or "").strip(),
            "memo": str(memo or "").strip(),
            "next_action_date": next_day,
            "status": selected_status,
        }

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value or "").strip()
        for pattern in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(text, pattern).date()
            except ValueError:
                continue
        raise ValueError(f"invalid date: {value}")

    @staticmethod
    def _rows(rows):
        return [dict(zip(ACTIVITY_FIELDS, row)) for row in rows]
