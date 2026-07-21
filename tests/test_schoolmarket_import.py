import csv
import os
import tempfile
import unittest

from services import database
from services.analytics_service import AnalyticsService
from services.connectors.schoolmarket_import import (
    SchoolMarketImport,
    classify_product,
)
from services.contract_service import ContractService
from services.import_history_service import ImportHistoryService
from services.school_service import SchoolService
from services.smart_import import format_import_summary


HEADERS = ["계약번호", "기관명", "구매일자", "상품명", "판매업체", "구매수량", "구매금액"]


class SchoolMarketImportTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "schoolmarket.db")
        database.create_database()
        SchoolService.save(
            "S001", "미래 초등학교", "서울교육청", "서울", "초등학교", "서울"
        )

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def create_csv(self, rows):
        path = os.path.join(self.temp_directory.name, "schoolmarket.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        return path

    @staticmethod
    def row(number="C-1", school="미래초등학교", product="Interactive Display", amount="3000000"):
        return [number, school, "2026-07-20", product, "에듀상사", "2", amount]

    def test_auto_mapping_school_match_and_unmatched_warning(self):
        path = self.create_csv(
            [self.row("C-1"), self.row("C-2", school="없는학교", product="Desk")]
        )
        importer = SchoolMarketImport(path)

        summary = importer.run()
        contracts = ContractService.search()

        self.assertEqual(importer.mapping["school_name"], "기관명")
        self.assertEqual(summary["imported"], 2)
        self.assertEqual(summary["school_matches"], 1)
        self.assertEqual(summary["school_match_rate"], 50.0)
        self.assertTrue(any("school not matched" in item for item in summary["warnings"]))
        self.assertEqual(
            next(item for item in contracts if item["school_name"] == "미래 초등학교")["school_code"],
            "S001",
        )
        self.assertTrue(
            next(item for item in contracts if item["school_name"] == "없는학교")["school_code"].startswith("UNMATCHED-")
        )

    def test_contract_number_is_preferred_for_duplicate_detection(self):
        path = self.create_csv(
            [self.row("C-100", product="Notebook"), self.row("C-100", product="Tablet")]
        )

        first = SchoolMarketImport(path).run()
        second = SchoolMarketImport(path).run()

        self.assertEqual(first["imported"], 1)
        self.assertEqual(first["duplicates"], 1)
        self.assertEqual(second["imported"], 0)
        self.assertEqual(second["duplicates"], 2)
        self.assertEqual(len(ContractService.search()), 1)

    def test_composite_duplicate_detection_without_contract_number(self):
        path = self.create_csv([self.row(number="")])

        first = SchoolMarketImport(path).run()
        second = SchoolMarketImport(path).run()

        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["duplicates"], 1)
        self.assertEqual(len(ContractService.search()), 1)

    def test_initial_product_categories(self):
        cases = {
            "Interactive Display 75 inch": "ICT",
            "Electronic Whiteboard": "ICT",
            "Notebook computer": "ICT",
            "Tablet": "ICT",
            "Desktop PC": "ICT",
            "Laser Projector": "AV",
            "Commercial Display": "AV",
            "Audio speaker": "AV",
            "Teacher Desk": "Furniture",
            "Student Chair": "Furniture",
            "Storage Cabinet": "Furniture",
            "Paper": "Other",
        }
        for product, expected in cases.items():
            with self.subTest(product=product):
                self.assertEqual(classify_product(product), expected)

    def test_dashboard_statistics_update_after_successful_import(self):
        before = AnalyticsService.school_summary("S001")["kpis"]
        path = self.create_csv([self.row(amount="3500000")])

        summary = SchoolMarketImport(path).run()
        after = AnalyticsService.school_summary("S001")["kpis"]

        self.assertEqual(before["contracts"], 0)
        self.assertEqual(summary["imported"], 1)
        self.assertEqual(after["contracts"], 1)
        self.assertEqual(after["contract_amount"], 3_500_000)

    def test_summary_includes_duplicates_match_rate_categories_and_history(self):
        path = self.create_csv(
            [self.row("C-1", product="Notebook"), self.row("C-1", product="Tablet")]
        )

        summary = SchoolMarketImport(path).run()
        text = format_import_summary(summary)

        self.assertIn("Duplicates: 1", text)
        self.assertIn("School match rate: 100.0%", text)
        self.assertIn("Category summary: ICT: 1", text)
        self.assertEqual(ImportHistoryService.history()[0]["source_type"], "SchoolMarket")
        self.assertEqual(ImportHistoryService.history()[0]["imported_rows"], 1)


if __name__ == "__main__":
    unittest.main()
