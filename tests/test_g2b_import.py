import csv
import os
import tempfile
import unittest

from services import database
from services.connectors.g2b_import import G2BImport, classify_g2b_product
from services.contract_service import ContractService
from services.analytics_service import AnalyticsService
from services.import_history_service import ImportHistoryService
from services.school_profile_service import SchoolProfileService
from services.school_service import SchoolService


HEADERS = [
    "계약번호", "입찰공고번호", "수요기관명", "낙찰업체", "품명",
    "계약금액", "계약일자", "품목분류",
]


class G2BImportTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "g2b.db")
        database.create_database()
        SchoolService.save(
            "G-S1", "나라초등학교", "서울교육청", "서울", "초등학교", "서울시"
        )

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def create_csv(self, rows):
        path = os.path.join(self.temp_directory.name, "g2b.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        return path

    @staticmethod
    def row(
        contract="C-1",
        notice="N-1",
        school="나라초등학교",
        product="네트워크 스위치",
        amount="12000000",
        category="통신장비",
    ):
        return [
            contract, notice, school, "조달공급사", product,
            amount, "2026-07-20", category,
        ]

    def test_import_auto_mapping_school_match_category_and_history(self):
        path = self.create_csv([self.row()])
        importer = G2BImport(path)

        summary = importer.run()
        contract = ContractService.search_by_school("G-S1")[0]

        self.assertEqual(importer.mapping["notice_number"], "입찰공고번호")
        self.assertEqual(importer.mapping["procuring_organization"], "수요기관명")
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["imported"], 1)
        self.assertEqual(summary["school_match_rate"], 100.0)
        self.assertEqual(summary["category_summary"], {"Network": 1})
        self.assertEqual(contract["school_code"], "G-S1")
        self.assertEqual(contract["category"], "Network")
        self.assertEqual(ImportHistoryService.history()[0]["source_type"], "G2B")

    def test_duplicate_priority_contract_then_notice_then_composite(self):
        contract_path = self.create_csv(
            [
                self.row(contract="C-10", notice="N-10", product="Tablet"),
                self.row(contract="C-10", notice="N-11", product="Display"),
            ]
        )
        contract_summary = G2BImport(contract_path).run()
        self.assertEqual(contract_summary["imported"], 1)
        self.assertEqual(contract_summary["duplicates"], 1)

        notice_path = self.create_csv(
            [
                self.row(contract="", notice="N-20", product="Notebook"),
                self.row(contract="", notice="N-20", product="Software License"),
            ]
        )
        notice_summary = G2BImport(notice_path).run()
        self.assertEqual(notice_summary["imported"], 1)
        self.assertEqual(notice_summary["duplicates"], 1)

        composite_path = self.create_csv([self.row(contract="", notice="", product="Desk")])
        first = G2BImport(composite_path).run()
        second = G2BImport(composite_path).run()
        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["duplicates"], 1)

    def test_unmatched_school_warns_without_aborting(self):
        path = self.create_csv([self.row(school="미등록학교")])

        summary = G2BImport(path).run()
        contract = ContractService.search()[0]

        self.assertEqual(summary["imported"], 1)
        self.assertEqual(summary["school_match_rate"], 0.0)
        self.assertTrue(summary["warnings"])
        self.assertTrue(contract["school_code"].startswith("UNMATCHED-"))

    def test_extensible_categories(self):
        cases = {
            "Tablet computer": "ICT",
            "Interactive Display": "Display",
            "Student Chair": "Furniture",
            "Network Firewall": "Network",
            "Learning Software License": "Software",
            "복사용지": "Other",
        }
        for product, expected in cases.items():
            with self.subTest(product=product):
                self.assertEqual(classify_g2b_product(product), expected)

    def test_school_profile_timeline_and_dashboard_aggregation(self):
        path = self.create_csv(
            [
                self.row(contract="C-30", notice="N-30", product="Tablet", amount="10000000"),
                self.row(contract="C-31", notice="N-31", product="Software License", amount="5000000"),
            ]
        )
        G2BImport(path).run()

        profile = SchoolProfileService.get_profile("G-S1")
        dashboard = AnalyticsService.school_summary("G-S1")

        self.assertEqual(profile["statistics"]["g2b_contracts"], 2)
        self.assertEqual(profile["statistics"]["g2b_spending"], 15_000_000)
        self.assertEqual(len(profile["latest_g2b_contracts"]), 2)
        self.assertEqual(dashboard["g2b_summary"]["total_count"], 2)
        self.assertEqual(dashboard["g2b_summary"]["total_spending"], 15_000_000)
        self.assertEqual(len(dashboard["g2b_summary"]["latest_contracts"]), 2)
        self.assertEqual(
            sum(event["source"] == "G2B" for event in profile["recent_activity"]), 2
        )
        self.assertNotIn(
            "Contract",
            {event["source"] for event in profile["recent_activity"]},
        )


if __name__ == "__main__":
    unittest.main()
