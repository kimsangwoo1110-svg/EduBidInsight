import os
import tempfile
import unittest
from datetime import date

from services import database
from services.action_center import ActionCenterService
from services.opportunity_engine import OpportunityEngine, OpportunityResult
from services.school_profile_service import SchoolProfileService
from services.school_service import SchoolService


class ActionCenterServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "actions.db")
        database.create_database()
        SchoolService.save(
            "S17", "Action School", "Office", "Seoul", "Elementary",
            "17 Workflow Road", student_count=500, class_count=20,
        )

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def test_action_creation_and_search_filters(self):
        action = ActionCenterService.create(
            "S17", "Visit", "Visit principal", priority="High",
            due_date="2026-07-21", note="Discuss AI classroom",
            created_at="2026-07-20T09:00:00+09:00",
        )

        self.assertGreater(action.action_id, 0)
        self.assertEqual(action.status, "Planned")
        self.assertEqual(action.note, "Discuss AI classroom")
        self.assertEqual(
            [item.action_id for item in ActionCenterService.search(
                status="Planned", priority="High", school="S17",
                action_type="Visit", due_date="2026-07-21",
            )],
            [action.action_id],
        )

    def test_status_update_logs_history_and_completion_time(self):
        action = ActionCenterService.create("S17", "Phone Call", "Call school")
        progressed = ActionCenterService.update_status(
            action.action_id, "In Progress", updated_at="2026-07-20T10:00:00+09:00"
        )
        completed = ActionCenterService.update_status(
            action.action_id, "Completed", completed_date="2026-07-21",
            note="Call completed", updated_at="2026-07-21T11:30:00+09:00",
        )

        self.assertEqual(progressed.status, "In Progress")
        self.assertEqual(completed.completed_date, "2026-07-21")
        history = ActionCenterService.history(action.action_id)
        self.assertEqual([event["event_type"] for event in history], ["Completed", "Status Changed", "Created"])
        self.assertEqual(history[0]["completed_at"], "2026-07-21")
        self.assertEqual(history[0]["note"], "Call completed")

        activity = ActionCenterService.recent_activity()
        self.assertEqual(activity[0]["activity_type"], "Status Change")
        self.assertEqual(activity[0]["completed_at"], "2026-07-21")

    def test_dashboard_aggregation(self):
        ActionCenterService.create("S17", "Phone Call", "Today", due_date="2026-07-21")
        ActionCenterService.create("S17", "Quotation", "Overdue", due_date="2026-07-20")
        ActionCenterService.create("S17", "Visit", "Upcoming visit", due_date="2026-07-25")
        completed = ActionCenterService.create("S17", "Meeting", "Done")
        ActionCenterService.update_status(
            completed.action_id, "Completed", completed_date="2026-07-21",
            updated_at="2026-07-21T12:00:00+09:00",
        )

        summary = ActionCenterService.dashboard_summary(today=date(2026, 7, 21))

        self.assertEqual(summary["today_actions"], 1)
        self.assertEqual(summary["overdue_actions"], 1)
        self.assertEqual(summary["completed_this_week"], 1)
        self.assertEqual(summary["upcoming_visits"], 1)

    def test_school360_action_integration(self):
        current = ActionCenterService.create("S17", "Visit", "Current", due_date="2026-07-30")
        completed = ActionCenterService.create("S17", "Meeting", "Completed")
        ActionCenterService.update_status(completed.action_id, "Completed")

        profile = SchoolProfileService.get_profile("S17")

        self.assertEqual(profile["actions"]["counts"]["current"], 1)
        self.assertEqual(profile["actions"]["counts"]["completed"], 1)
        self.assertEqual(profile["actions"]["current_actions"][0].action_id, current.action_id)
        self.assertEqual(len(profile["actions"]["action_timeline"]), 2)

    def test_opportunity_integration_generates_unique_actions(self):
        result = OpportunityResult(
            school_id="S17", school_name="Action School", score=80,
            priority="★★★★☆", recommendation="Recommend AI Classroom proposal.",
            next_action="Visit this week", confidence="Medium",
            evidence=["✓ AI Education Project", "✓ No CRM activity in 8 months"],
            generated_at="2026-07-21T09:00:00+09:00",
        )

        generated = OpportunityEngine.generate_actions(
            result, persist=True, today=date(2026, 7, 21)
        )
        repeated = OpportunityEngine.generate_actions(
            result, persist=True, today=date(2026, 7, 21)
        )

        self.assertEqual(
            {action.action_type for action in generated},
            {"Visit", "Proposal", "Follow-up"},
        )
        self.assertEqual(repeated, [])
        self.assertEqual(len(ActionCenterService.search(school="S17")), 3)

    def test_validation_rejects_unsupported_workflow_values(self):
        with self.assertRaises(ValueError):
            ActionCenterService.create("S17", "Email", "Unsupported")
        with self.assertRaises(ValueError):
            ActionCenterService.create("S17", "Visit", "Bad", status="Done")


if __name__ == "__main__":
    unittest.main()
