"""CRM Action Center domain service and Opportunity action suggestions."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from core.logger import get_logger
from services import database


ACTION_TYPES = (
    "Visit", "Phone Call", "Quotation", "Follow-up", "Meeting", "Proposal", "Other",
)
ACTION_STATUSES = ("Planned", "In Progress", "Waiting", "Completed", "Cancelled")
ACTION_PRIORITIES = ("Low", "Medium", "High", "Critical")
OPEN_STATUSES = frozenset(("Planned", "In Progress", "Waiting"))


@dataclass(frozen=True)
class Action:
    action_id: int
    school_id: str
    action_type: str
    title: str
    status: str
    priority: str
    due_date: str | None
    completed_date: str | None
    note: str
    created_at: str
    updated_at: str

    def to_dict(self):
        return asdict(self)


class ActionCenterService:
    """Create, search, transition, and aggregate CRM actions."""

    logger = get_logger("action_center")

    @classmethod
    def create(
        cls, school_id, action_type, title, status="Planned", priority="Medium",
        due_date=None, note="", created_at=None,
    ):
        school = str(school_id or "").strip()
        selected_type = cls._choice(action_type, ACTION_TYPES, "action type")
        selected_status = cls._choice(status, ACTION_STATUSES, "status")
        selected_priority = cls._choice(priority, ACTION_PRIORITIES, "priority")
        selected_title = str(title or "").strip()
        if not school:
            raise ValueError("school_id is required")
        if not selected_title:
            raise ValueError("title is required")
        now = cls._timestamp(created_at)
        completed = now[:10] if selected_status == "Completed" else None
        values = {
            "school_id": school,
            "action_type": selected_type,
            "title": selected_title,
            "status": selected_status,
            "priority": selected_priority,
            "due_date": cls._optional_date(due_date),
            "completed_date": completed,
            "note": str(note or "").strip(),
            "created_at": now,
            "updated_at": now,
        }
        action_id = database.add_crm_action(values)
        cls.logger.info(
            "action created | id=%s | school=%s | type=%s | status=%s | due=%s",
            action_id, school, selected_type, selected_status, values["due_date"],
        )
        return cls.get(action_id)

    @staticmethod
    def get(action_id):
        row = database.get_crm_action(action_id)
        return Action(*row) if row else None

    @classmethod
    def update_status(cls, action_id, status, completed_date=None, note="", updated_at=None):
        selected_status = cls._choice(status, ACTION_STATUSES, "status")
        current = cls.get(action_id)
        if current is None:
            raise ValueError(f"Action {action_id} was not found")
        now = cls._timestamp(updated_at)
        if selected_status == "Completed":
            completed = cls._optional_date(completed_date) or now[:10]
        else:
            completed = None
        database.transition_crm_action(
            action_id, selected_status, completed, now, str(note or "").strip()
        )
        cls.logger.info(
            "action status | id=%s | %s -> %s | completion=%s",
            action_id, current.status, selected_status, completed or "",
        )
        return cls.get(action_id)

    @staticmethod
    def search(
        status="", priority="", school="", action_type="", due_date=None,
        due_from=None, due_to=None, exact_school=False,
    ):
        if due_date is not None:
            selected = ActionCenterService._optional_date(due_date)
            due_from = selected
            due_to = selected
        rows = database.find_crm_actions(
            status=status, priority=priority, school=school, action_type=action_type,
            due_from=ActionCenterService._optional_date(due_from),
            due_to=ActionCenterService._optional_date(due_to),
            exact_school=exact_school,
        )
        return [Action(*row) for row in rows]

    @staticmethod
    def history(action_id):
        keys = (
            "id", "action_id", "changed_at", "event_type", "old_status",
            "new_status", "note", "completed_at",
        )
        return [dict(zip(keys, row)) for row in database.find_crm_action_history(action_id)]

    @classmethod
    def school_summary(cls, school_id, today=None):
        selected_today = cls._date(today or date.today())
        actions = cls.search(school=school_id, exact_school=True)
        current = [item for item in actions if item.status in OPEN_STATUSES]
        completed = [item for item in actions if item.status == "Completed"]
        upcoming = [
            item for item in current
            if item.due_date and cls._date(item.due_date) >= selected_today
        ]
        timeline = sorted(actions, key=lambda item: item.updated_at, reverse=True)
        return {
            "current_actions": current,
            "completed_actions": completed,
            "upcoming_actions": upcoming,
            "action_timeline": timeline,
            "counts": {
                "current": len(current), "completed": len(completed),
                "upcoming": len(upcoming),
            },
        }

    @classmethod
    def dashboard_summary(cls, today=None):
        selected_today = cls._date(today or date.today())
        week_start = selected_today - timedelta(days=selected_today.weekday())
        visit_horizon = selected_today + timedelta(days=7)
        actions = cls.search()
        today_actions = [
            item for item in actions
            if item.status in OPEN_STATUSES and item.due_date == selected_today.isoformat()
        ]
        overdue = [
            item for item in actions
            if item.status in OPEN_STATUSES and item.due_date
            and cls._date(item.due_date) < selected_today
        ]
        completed_week = [
            item for item in actions
            if item.status == "Completed" and item.completed_date
            and week_start <= cls._date(item.completed_date) <= selected_today
        ]
        visits = [
            item for item in actions
            if item.action_type == "Visit" and item.status in OPEN_STATUSES
            and item.due_date
            and selected_today <= cls._date(item.due_date) <= visit_horizon
        ]
        open_actions = [item for item in actions if item.status in OPEN_STATUSES]
        return {
            "today_actions": len(today_actions),
            "overdue_actions": len(overdue),
            "completed_this_week": len(completed_week),
            "upcoming_visits": len(visits),
            "open_actions": len(open_actions),
            "today": today_actions,
            "overdue": overdue,
            "completed": completed_week,
            "visits": visits,
            "open": open_actions,
        }

    @staticmethod
    def recent_activity(limit=20):
        """Return normalized Visit/Call/Quote and status-change events."""
        rows = database.find_recent_crm_action_history(max(1, int(limit)) * 3)
        activities = []
        visible_types = {"Visit", "Phone Call", "Quotation"}
        for row in rows:
            (
                history_id, action_id, changed_at, event_type, old_status,
                new_status, note, completed_at, school_id, action_type, title,
                priority, due_date,
            ) = row
            if event_type == "Created" and action_type not in visible_types:
                continue
            kind = "Status Change" if event_type != "Created" else action_type
            activities.append({
                "id": history_id,
                "action_id": action_id,
                "timestamp": changed_at,
                "activity_type": kind,
                "school_id": school_id,
                "title": title,
                "description": (
                    f"{old_status or '-'} → {new_status}"
                    if event_type != "Created" else f"{action_type} planned"
                ),
                "priority": priority,
                "due_date": due_date,
                "completed_at": completed_at,
                "note": note or "",
            })
            if len(activities) >= max(1, int(limit)):
                break
        return activities

    @classmethod
    def generate_from_opportunity(cls, result, persist=True, today=None):
        """Turn explainable Opportunity evidence into deduplicated suggestions."""
        selected_today = cls._date(today or date.today())
        evidence = " ".join(result.evidence).casefold()
        suggestions = []
        if "ai education project" in evidence:
            suggestions.append(("Visit", "Visit for AI Education opportunity", "High", 7))
        if int(result.score or 0) >= 70:
            suggestions.append(("Proposal", "Prepare opportunity proposal", "Critical", 10))
        if "no crm activity" in evidence:
            suggestions.append(("Follow-up", "Re-engage inactive school", "High", 3))

        existing = cls.search(school=result.school_id, exact_school=True) if persist else []
        open_keys = {
            (item.action_type, item.title) for item in existing if item.status in OPEN_STATUSES
        }
        generated = []
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for action_type, title, priority, due_days in suggestions:
            if (action_type, title) in open_keys:
                continue
            due = (selected_today + timedelta(days=due_days)).isoformat()
            note = f"Generated from Opportunity score {result.score}: {result.recommendation}"
            if persist:
                action = cls.create(
                    result.school_id, action_type, title, priority=priority,
                    due_date=due, note=note,
                )
            else:
                action = Action(
                    0, result.school_id, action_type, title, "Planned", priority,
                    due, None, note, now, now,
                )
            generated.append(action)
            open_keys.add((action_type, title))
        return generated

    @staticmethod
    def _choice(value, choices, label):
        selected = str(value or "").strip()
        if selected not in choices:
            raise ValueError(f"Unsupported {label}: {selected}")
        return selected

    @staticmethod
    def _timestamp(value=None):
        if value is None:
            return datetime.now().astimezone().isoformat(timespec="seconds")
        if isinstance(value, datetime):
            return value.astimezone().isoformat(timespec="seconds")
        text = str(value).strip()
        datetime.fromisoformat(text)
        return text

    @staticmethod
    def _optional_date(value):
        if value in (None, ""):
            return None
        return ActionCenterService._date(value).isoformat()

    @staticmethod
    def _date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value).strip()[:10])


ActionCenter = ActionCenterService
