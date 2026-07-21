import time
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.action_center import Action
from services.dashboard_service import DashboardService
from services.opportunity_engine import OpportunityResult


def opportunity(school_id, score, evidence=None):
    return OpportunityResult(
        school_id=school_id,
        school_name=f"School {school_id}",
        score=score,
        priority="★★★★☆",
        recommendation=f"Recommendation {school_id}",
        next_action="Visit this week",
        confidence="Medium",
        evidence=evidence or [],
        generated_at="2026-07-21T09:00:00+09:00",
    )


def action(action_id, school_id="S1", action_type="Visit", title="Visit", due="2026-07-21", status="Planned", completed=None):
    return Action(
        action_id, school_id, action_type, title, status, "High", due,
        completed, "", "2026-07-20T09:00:00+09:00", "2026-07-21T09:00:00+09:00",
    )


class DashboardServiceTest(unittest.TestCase):
    def setUp(self):
        DashboardService.clear_cache()
        self.results = [
            opportunity("S2", 55),
            opportunity("S1", 92, [
                "✓ No CRM activity in 8 months",
                "✓ Contract Renewal Window",
                "✓ Large Annual Project Budget",
            ]),
            opportunity("S3", 75),
        ]
        self.overdue = action(2, "S2", "Phone Call", "Late call", "2026-07-19")
        self.completed = action(
            3, "S3", "Quotation", "Quote", "2026-07-20", "Completed", "2026-07-21"
        )
        self.opportunity_engine = SimpleNamespace(
            dashboard=Mock(return_value={
                "top_opportunities": self.results,
                "all_opportunities": self.results,
                "loaded_profiles": {"S1": {"recent_activity": []}},
            })
        )
        self.action_service = SimpleNamespace(
            dashboard_summary=Mock(return_value={
                "today_actions": 1,
                "overdue_actions": 1,
                "completed_this_week": 1,
                "upcoming_visits": 1,
                "open_actions": 3,
                "today": [action(1)],
                "overdue": [self.overdue],
                "completed": [self.completed],
                "visits": [action(4, "S1", due="2026-07-25")],
                "open": [action(1), self.overdue, action(4)],
            }),
            recent_activity=Mock(return_value=[{
                "id": 1,
                "timestamp": "2026-07-21T09:00:00+09:00",
                "activity_type": "Visit",
                "school_id": "S1",
                "title": "Visit",
                "description": "Visit planned",
            }]),
            update_status=Mock(),
        )
        self.profile_service = SimpleNamespace(
            recent_activity_from_profiles=Mock(return_value=[])
        )
        self.analytics_service = SimpleNamespace(
            education_office_analytics=Mock(return_value={
                "total_projects": 2, "total_budget": 100_000_000,
            })
        )
        self.dependencies = (
            patch.object(DashboardService, "opportunity_engine", self.opportunity_engine),
            patch.object(DashboardService, "action_service", self.action_service),
            patch.object(DashboardService, "profile_service", self.profile_service),
            patch.object(DashboardService, "analytics_service", self.analytics_service),
        )
        for dependency in self.dependencies:
            dependency.start()

    def tearDown(self):
        for dependency in reversed(self.dependencies):
            dependency.stop()
        DashboardService.clear_cache()

    def test_dashboard_aggregation_and_weekly_kpis(self):
        dashboard = DashboardService.get_dashboard(today=date(2026, 7, 21))

        self.assertEqual(dashboard["weekly_kpi"], {
            "opportunity_count": 3,
            "completed_this_week": 1,
            "upcoming_visits": 1,
            "average_opportunity_score": 74.0,
            "open_actions": 3,
        })
        self.assertEqual(len(dashboard["today_actions"]), 1)
        self.assertEqual(len(dashboard["recently_completed"]), 1)
        self.assertEqual(dashboard["recent_activity"][0]["activity_type"], "Visit")
        self.analytics_service.education_office_analytics.assert_called_once_with()
        self.profile_service.recent_activity_from_profiles.assert_called_once()

    def test_priority_schools_are_score_ordered_and_limited_to_ten(self):
        extra = [opportunity(f"E{index}", index) for index in range(20)]
        self.opportunity_engine.dashboard.return_value["all_opportunities"] = [
            *self.results, *extra,
        ]

        dashboard = DashboardService.get_dashboard(today="2026-07-21")

        scores = [item.score for item in dashboard["priority_schools"]]
        self.assertEqual(len(scores), 10)
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(dashboard["priority_schools"][0].school_id, "S1")

    def test_alert_generation_covers_all_required_alert_families(self):
        dashboard = DashboardService.get_dashboard(today="2026-07-21")

        alert_types = {item["type"] for item in dashboard["alerts"]}
        self.assertEqual(alert_types, {
            "CRM inactivity", "Renewal window", "High-value project", "Overdue action",
        })
        self.assertEqual(dashboard["alerts"][0]["severity"], "Critical")

    def test_cached_dashboard_loads_under_two_seconds(self):
        started = time.perf_counter()
        first = DashboardService.get_dashboard(today="2026-07-21")
        cold_elapsed = time.perf_counter() - started
        started = time.perf_counter()
        second = DashboardService.get_dashboard(today="2026-07-21")
        cached_elapsed = time.perf_counter() - started

        self.assertLess(cold_elapsed, 2.0)
        self.assertLess(cached_elapsed, 2.0)
        self.assertIs(first, second)
        self.opportunity_engine.dashboard.assert_called_once()
        self.action_service.dashboard_summary.assert_called_once()

    def test_manual_refresh_bypasses_cache_and_quick_completion_refreshes(self):
        first = DashboardService.get_dashboard(today="2026-07-21")
        cached = DashboardService.get_dashboard(today="2026-07-21")
        refreshed = DashboardService.refresh(today="2026-07-21")
        completed = DashboardService.complete_action(1, today="2026-07-21")

        self.assertIs(first, cached)
        self.assertIsNot(refreshed, first)
        self.assertIsNot(completed, refreshed)
        self.assertEqual(self.opportunity_engine.dashboard.call_count, 3)
        self.action_service.update_status.assert_called_once_with(1, "Completed")


if __name__ == "__main__":
    unittest.main()
