import os
import tempfile
import unittest
from contextlib import closing
from datetime import date

from gui.crm import activity_table_values, pipeline_status_text
from gui.dashboard import sales_kpi_values
from services import database
from services.sales_activity_service import SalesActivityService


class SalesActivityServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "crm.db")
        database.create_database()
        self.school_code = "S-CRM"

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def add(
        self,
        activity_date,
        activity_type,
        next_action_date=None,
        status="Lead",
        memo="테스트 활동",
    ):
        return SalesActivityService.add_activity(
            self.school_code,
            activity_date,
            activity_type,
            "김담당",
            memo,
            next_action_date,
            status,
        )

    def test_sales_activity_table_schema(self):
        with closing(database.get_connection()) as connection:
            columns = [
                row[1] for row in connection.execute("PRAGMA table_info(sales_activity)")
            ]
        self.assertEqual(
            columns,
            [
                "id",
                "school_code",
                "activity_date",
                "activity_type",
                "contact_person",
                "memo",
                "next_action_date",
                "status",
            ],
        )

    def test_activity_crud(self):
        activity_id = self.add("2026.07.01", "전화", "2026/07/10", "Lead")
        activity = SalesActivityService.list_by_school(self.school_code)[0]

        self.assertEqual(activity["id"], activity_id)
        self.assertEqual(activity["activity_date"], "2026-07-01")
        self.assertEqual(activity["next_action_date"], "2026-07-10")
        self.assertTrue(
            SalesActivityService.update_activity(
                activity_id,
                self.school_code,
                "2026-07-02",
                "방문",
                "이담당",
                "제안 미팅",
                "2026-07-15",
                "Qualified",
            )
        )
        updated = SalesActivityService.list_by_school(self.school_code)[0]
        self.assertEqual(updated["activity_type"], "방문")
        self.assertEqual(updated["status"], "Qualified")
        self.assertTrue(SalesActivityService.delete_activity(activity_id))
        self.assertEqual(SalesActivityService.list_by_school(self.school_code), [])

    def test_upcoming_and_overdue_actions_exclude_closed_pipeline(self):
        overdue_id = self.add("2026-07-01", "전화", "2026-07-20", "Lead")
        upcoming_id = self.add("2026-07-02", "방문", "2026-07-25", "Qualified")
        self.add("2026-07-03", "견적", "2026-07-19", "Won")
        self.add("2026-07-04", "이메일", "2026-09-01", "Proposal")

        upcoming = SalesActivityService.upcoming_actions(
            self.school_code, days=30, today=date(2026, 7, 21)
        )
        overdue = SalesActivityService.overdue_actions(
            self.school_code, today=date(2026, 7, 21)
        )

        self.assertEqual([activity["id"] for activity in upcoming], [upcoming_id])
        self.assertEqual([activity["id"] for activity in overdue], [overdue_id])

    def test_pipeline_and_kpi_summary(self):
        self.add("2026-07-01", "방문", status="Qualified")
        self.add("2026-07-02", "전화", status="Proposal")
        self.add("2026-07-03", "견적", status="Won")
        self.add("2026-07-04", "이메일", status="Lost")
        self.add("2026-07-05", "전화", status="Negotiation")

        pipeline = SalesActivityService.pipeline_summary(self.school_code)
        kpis = SalesActivityService.kpi_summary(self.school_code)

        self.assertEqual(pipeline["current_stage"], "Negotiation")
        self.assertEqual(pipeline["counts"]["Won"], 1)
        self.assertEqual(pipeline["counts"]["Lost"], 1)
        self.assertEqual(kpis["visits"], 1)
        self.assertEqual(kpis["calls"], 2)
        self.assertEqual(kpis["quotations"], 1)
        self.assertEqual(kpis["wins"], 1)
        self.assertEqual(kpis["win_rate"], 50)

    def test_dashboard_and_crm_ui_helpers(self):
        self.add("2026-07-01", "방문", "2026-07-25", "Qualified")
        summary = SalesActivityService.school_crm_summary(
            self.school_code, today=date(2026, 7, 21)
        )
        activity = summary["recent_activities"][0]

        self.assertEqual(activity_table_values(activity)[-1], "Qualified")
        self.assertIn("현재 단계: Qualified", pipeline_status_text(summary))
        self.assertEqual(
            sales_kpi_values(summary["kpis"]),
            (
                ("Visits", "1"),
                ("Calls", "0"),
                ("Quotations", "0"),
                ("Wins", "0"),
                ("Win rate", "0.0%"),
            ),
        )

    def test_validation_rejects_bad_dates_and_pipeline(self):
        with self.assertRaises(ValueError):
            self.add("not-a-date", "전화")
        with self.assertRaises(ValueError):
            self.add("2026-07-01", "전화", status="Unknown")


if __name__ == "__main__":
    unittest.main()
