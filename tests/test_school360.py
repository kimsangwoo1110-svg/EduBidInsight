import unittest

from gui.school360_window import format_currency
from services.school360_view_model import (
    SCHOOL_FIELDS, School360MockProvider, normalize_school_selection,
)


SCHOOL_ROW = (
    "S360", "통합미래학교", "초등학교", "서울교육청", "서울",
    "서울시 미래로 360", "https://school.example", 1, 1, 0, 0, 720, 28,
)


class School360Test(unittest.TestCase):
    def test_search_row_normalizes_to_named_school_record(self):
        school = normalize_school_selection(SCHOOL_ROW)

        self.assertEqual(tuple(school), SCHOOL_FIELDS)
        self.assertEqual(school["school_code"], "S360")
        self.assertEqual(school["school_name"], "통합미래학교")
        self.assertEqual(school["student_count"], 720)

    def test_required_school_identity_is_validated(self):
        with self.assertRaises(ValueError):
            normalize_school_selection({"school_code": "", "school_name": "학교"})
        with self.assertRaises(ValueError):
            normalize_school_selection({"school_code": "S1", "school_name": ""})

    def test_mock_dashboard_contains_every_required_section(self):
        dashboard = School360MockProvider.dashboard(SCHOOL_ROW)

        self.assertEqual(
            set(dashboard),
            {
                "school", "statistics", "planned_projects", "procurement",
                "crm", "attachments", "mock", "connector_sources",
            },
        )
        self.assertTrue(dashboard["mock"])
        self.assertEqual(dashboard["school"]["school_code"], "S360")
        self.assertEqual(len(dashboard["planned_projects"]), 3)
        self.assertEqual(len(dashboard["procurement"]), 3)
        self.assertEqual(len(dashboard["crm"]), 3)
        self.assertEqual(len(dashboard["attachments"]), 3)

    def test_statistics_are_derived_from_mock_connector_records(self):
        dashboard = School360MockProvider.dashboard(SCHOOL_ROW)
        statistics = dashboard["statistics"]

        self.assertEqual(statistics["students"], 720)
        self.assertEqual(statistics["classes"], 28)
        self.assertEqual(statistics["planned_projects"], 3)
        self.assertEqual(statistics["planned_budget"], 269_000_000)
        self.assertEqual(statistics["procurement_total"], 63_300_000)
        self.assertEqual(statistics["crm_activities"], 3)
        self.assertEqual(format_currency(statistics["procurement_total"]), "63,300,000원")

    def test_mock_sources_include_required_connector_families(self):
        sources = School360MockProvider.dashboard(SCHOOL_ROW)["connector_sources"]

        self.assertIn("School Info OpenAPI", sources)
        self.assertIn("Education Office", sources)
        self.assertIn("School Market (S2B)", sources)
        self.assertIn("NaraJangteo (G2B)", sources)


if __name__ == "__main__":
    unittest.main()
