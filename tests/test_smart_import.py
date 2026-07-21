import csv
import os
import tempfile
import unittest
from unittest.mock import patch

from gui.import_wizard import progress_text
from services import database
from services.connectors.contract_import import (
    ContractImportConnector,
    auto_map_common_columns,
)
from services.contract_service import ContractService
from services.import_history_service import ImportHistoryService
from services.smart_import import MappingStore, SmartContractImport, format_import_summary


HEADERS = ["학교코드", "학교명", "계약일", "품목", "업체", "금액"]


class SmartImportTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "smart-import.db")
        database.create_database()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def create_csv(self, rows, headers=HEADERS):
        path = os.path.join(self.temp_directory.name, "contracts.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
            writer.writerows(rows)
        return path

    @staticmethod
    def row(code="S1", school="미래초", product="노트북"):
        return [code, school, "2026-07-01", product, "좋은업체", "1000000"]

    def test_preview_is_limited_to_100_and_does_not_write_database(self):
        path = self.create_csv([self.row(f"S{index}") for index in range(120)])

        preview = SmartContractImport(path).preview()

        self.assertEqual(len(preview), 100)
        self.assertEqual(ContractService.search(), [])

    def test_preview_marks_missing_required_fields(self):
        path = self.create_csv([self.row(school="")])

        preview = SmartContractImport(path).preview()

        self.assertIn("school_name", preview[0]["missing_fields"])
        self.assertTrue(preview[0]["error"])

    def test_common_aliases_and_mapping_store_round_trip(self):
        headers = ["학교코드", "기관명", "계약일", "사업명", "업체", "예산"]
        mapping = ContractImportConnector.auto_map(headers)
        common_mapping = auto_map_common_columns(headers)
        path = os.path.join(self.temp_directory.name, "mappings.json")
        store = MappingStore(path)

        store.save(mapping)

        self.assertEqual(mapping["school_name"], "기관명")
        self.assertEqual(mapping["product"], "사업명")
        self.assertEqual(mapping["amount"], "예산")
        self.assertEqual(
            common_mapping,
            {
                "school_name": "기관명",
                "project_name": "사업명",
                "budget": "예산",
                "amount": "",
                "vendor": "업체",
            },
        )
        self.assertEqual(store.load(), mapping)

    def test_progress_reports_all_phases_percentage_and_row_count(self):
        path = self.create_csv([self.row("S1"), self.row("S2")])
        progress = []

        result = SmartContractImport(path).run(lambda **value: progress.append(value))

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(
            [item["stage"] for item in progress],
            ["Reading file...", "Validating...", "Importing...", "Importing...", "Saving..."],
        )
        self.assertEqual(progress[-1]["percentage"], 100)
        self.assertIn("current row 2 / 2", progress_text(progress[-1]))

    def test_cancel_during_import_rolls_back_and_records_cancelled(self):
        path = self.create_csv([self.row("S1"), self.row("S2"), self.row("S3")])
        importer = SmartContractImport(path)

        def cancel_after_first_row(**progress):
            if progress["stage"] == "Importing..." and progress["processed"] == 1:
                importer.cancel()

        result = importer.run(cancel_after_first_row)

        self.assertTrue(result["cancelled"])
        self.assertEqual(result["status"], "Cancelled")
        self.assertEqual(result["imported"], 0)
        self.assertEqual(ContractService.search(), [])
        self.assertEqual(ImportHistoryService.history()[0]["result"], "Cancelled")

    def test_unexpected_failure_rolls_back_and_is_summarized(self):
        path = self.create_csv([self.row("S1"), self.row("S2")])
        real_save = ContractService.save
        calls = {"count": 0}

        def fail_second(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("database unavailable")
            return real_save(*args, **kwargs)

        with patch.object(ContractService, "save", side_effect=fail_second):
            result = SmartContractImport(path).run()

        self.assertEqual(result["status"], "FAILED")
        self.assertIn("database unavailable", result["exception"])
        self.assertEqual(ContractService.search(), [])
        self.assertEqual(ImportHistoryService.history()[0]["result"], "FAILED")

    def test_summary_contains_required_counts_elapsed_and_warnings(self):
        text = format_import_summary(
            {
                "status": "PARTIAL",
                "imported": 5,
                "skipped": 2,
                "failed": 1,
                "elapsed": 1.25,
                "warnings": ["Row 3 was invalid"],
            }
        )

        self.assertIn("Imported rows: 5", text)
        self.assertIn("Skipped rows: 2", text)
        self.assertIn("Failed rows: 1", text)
        self.assertIn("Elapsed time: 1.25s", text)
        self.assertIn("Row 3 was invalid", text)


if __name__ == "__main__":
    unittest.main()
