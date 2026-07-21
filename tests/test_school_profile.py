import csv
import os
import tempfile
import unittest
from unittest.mock import patch

from services import database
from services.connectors.schoolmarket_import import SchoolMarketImport, SchoolMarketService
from services.connectors.g2b_import import G2BService
from services.contract_service import ContractService
from services.project_service import ProjectService
from services.sales_activity_service import SalesActivityService
from services.school_profile_service import SchoolProfileService
from services.school_service import SchoolService


class SchoolProfileServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "profile.db")
        database.create_database()
        SchoolService.save(
            "S360",
            "통합미래학교",
            "서울교육청",
            "서울",
            "초등학교",
            "서울시 미래로 360",
            student_count=720,
            class_count=28,
        )

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def create_schoolmarket_file(self):
        path = os.path.join(self.temp_directory.name, "schoolmarket.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["계약번호", "학교명", "구매일", "제품명", "업체", "수량", "금액"])
            writer.writerow(["SM-360", "통합미래학교", "2026-07-18", "Tablet", "스마트상사", 20, 10000000])
        return path

    def populate_profile(self):
        SchoolMarketImport(self.create_schoolmarket_file()).run()
        ContractService.save(
            school_code="S360",
            school_name="통합미래학교",
            contract_date="2026-07-19",
            product="네트워크 장비",
            category="ICT",
            vendor="네트워크상사",
            quantity=1,
            amount=5_000_000,
            source_file="manual.csv",
        )
        ProjectService.create(
            "S360", "AI 교실 구축", "AI", "진행중", 80_000_000, 2026, 2026, "교육청"
        )
        SalesActivityService.add_activity(
            "S360", "2026-07-20", "미팅", "담당교사", "태블릿 활용 협의", status="Qualified"
        )

    def test_aggregation_contains_school_summary_and_all_sources(self):
        self.populate_profile()

        profile = SchoolProfileService.get_profile("S360")

        self.assertTrue(profile["exists"])
        self.assertEqual(
            profile["school"],
            {
                "school_name": "통합미래학교",
                "school_code": "S360",
                "region": "서울",
                "address": "서울시 미래로 360",
                "student_count": 720,
                "class_count": 28,
            },
        )
        self.assertEqual(
            {event["source"] for event in profile["recent_activity"]},
            {"SchoolMarket", "Contract", "Project", "CRM"},
        )

    def test_statistics_cards_use_aggregated_rows(self):
        self.populate_profile()

        statistics = SchoolProfileService.get_profile("S360")["statistics"]

        self.assertEqual(
            statistics,
            {
                "schoolmarket_purchases": 1,
                "contracts": 2,
                "projects": 1,
                "crm_activities": 1,
                "g2b_contracts": 0,
                "g2b_spending": 0,
                "active_projects": 1,
                "completed_projects": 0,
                "project_budget": 80_000_000,
            },
        )

    def test_recent_activity_is_latest_first_and_can_be_limited(self):
        self.populate_profile()

        events = SchoolProfileService.get_profile("S360", activity_limit=3)["recent_activity"]

        self.assertEqual(len(events), 3)
        self.assertEqual(
            [event["timestamp"] for event in events],
            sorted((event["timestamp"] for event in events), reverse=True),
        )
        self.assertTrue(all(event["title"] and event["source"] for event in events))

    def test_empty_or_unknown_school_returns_safe_empty_profile(self):
        profile = SchoolProfileService.get_profile("UNKNOWN")

        self.assertFalse(profile["exists"])
        self.assertEqual(profile["school"]["school_code"], "UNKNOWN")
        self.assertEqual(profile["statistics"]["contracts"], 0)
        self.assertEqual(profile["recent_activity"], [])
        self.assertEqual(profile["ai_recommendation"], "Coming in Sprint 16")

    def test_existing_school_without_related_data_has_zero_statistics(self):
        profile = SchoolProfileService.get_profile("S360")

        self.assertTrue(profile["exists"])
        self.assertEqual(profile["school"]["school_name"], "통합미래학교")
        self.assertTrue(all(value == 0 for value in profile["statistics"].values()))
        self.assertEqual(profile["recent_activity"], [])

    def test_performance_loads_each_source_exactly_once(self):
        school = {
            "school_code": "S360", "school_name": "통합미래학교", "region": "서울",
            "address": "주소", "student_count": 1, "class_count": 1,
        }
        contract = {
            "id": 1, "contract_date": "2026-01-01", "imported_at": "2026-01-02",
            "product": "Tablet", "vendor": "업체", "amount": 10,
        }
        project = {
            "id": 2, "project_name": "사업", "category": "ICT", "status": "진행중",
            "updated_at": "2026-01-03", "start_year": 2026,
        }
        activity = {
            "id": 3, "activity_date": "2026-01-04", "activity_type": "전화",
            "memo": "메모", "contact_person": "", 
        }
        with (
            patch.object(SchoolService, "get_by_code", return_value=school) as school_get,
            patch.object(ContractService, "search_by_school", return_value=[contract]) as contracts_get,
            patch.object(ProjectService, "list_for_school", return_value=[project]) as projects_get,
            patch.object(SalesActivityService, "list_by_school", return_value=[activity]) as crm_get,
            patch.object(SchoolMarketService, "contract_ids_for_school", return_value=[1]) as market_get,
            patch.object(G2BService, "contract_ids_for_school", return_value=[]) as g2b_get,
        ):
            profile = SchoolProfileService.get_profile("S360")

        self.assertEqual(profile["statistics"]["schoolmarket_purchases"], 1)
        for lookup in (school_get, contracts_get, projects_get, crm_get, market_get, g2b_get):
            lookup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
