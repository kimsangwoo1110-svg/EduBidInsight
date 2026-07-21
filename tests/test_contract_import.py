import csv
import os
import tempfile
import unittest
from contextlib import closing

from openpyxl import Workbook

from gui.import_wizard import mapping_status, preview_table_values
from services import database
from services.connectors.contract_import import ContractImportConnector
from services.contract_service import ContractService
from services.rule_service import RuleService
from services.sync_service import SyncService


HEADERS = [
    "학교 코드",
    "학교명",
    "계약일자",
    "제품명",
    "분류",
    "공급업체",
    "수량",
    "계약금액",
]
ROW = ["S001", "미래초", "2026.07.01", "전자칠판", "교육기자재", "에듀테크", "2", "1,500,000원"]


class ContractImportTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "contracts.db")
        database.create_database()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def create_excel(self):
        path = os.path.join(self.temp_directory.name, "contracts.xlsx")
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "계약"
        worksheet.append(HEADERS)
        worksheet.append(ROW)
        workbook.create_sheet("참고")
        workbook.save(path)
        workbook.close()
        return path

    def create_csv(self):
        path = os.path.join(self.temp_directory.name, "contracts.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(HEADERS)
            writer.writerow(ROW)
        return path

    def test_alias_mapping_maps_required_and_optional_columns(self):
        mapping = ContractImportConnector.auto_map(HEADERS)

        self.assertEqual(mapping["school_code"], "학교 코드")
        self.assertEqual(mapping["contract_date"], "계약일자")
        self.assertEqual(mapping["vendor"], "공급업체")
        self.assertEqual(mapping["amount"], "계약금액")
        self.assertIn("필수 컬럼 완료", mapping_status(mapping))

    def test_excel_import_selects_sheet_and_normalizes_values(self):
        path = self.create_excel()
        self.assertEqual(ContractImportConnector.sheet_names(path), ["계약", "참고"])
        connector = ContractImportConnector(path, sheet_name="계약")

        preview = connector.preview()
        result = SyncService.synchronize_connector(connector)
        contract = ContractService.search_by_school("S001")[0]

        self.assertEqual(preview[0]["error"], "")
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(contract["contract_date"], "2026-07-01")
        self.assertEqual(contract["quantity"], 2)
        self.assertEqual(contract["amount"], 1_500_000)
        self.assertEqual(contract["source_file"], "contracts.xlsx")

    def test_csv_import_and_duplicate_detection(self):
        path = self.create_csv()

        first = SyncService.synchronize_connector(ContractImportConnector(path))
        second = SyncService.synchronize_connector(ContractImportConnector(path))

        self.assertEqual(first["inserted"], 1)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(len(ContractService.search()), 1)

    def test_contract_service_search_update_and_duplicate_check(self):
        contract_id = ContractService.save(
            school_code="S002",
            school_name="새빛중",
            contract_date="2026/06/15",
            product="노트북",
            category="디지털",
            vendor="좋은업체",
            quantity="10",
            amount="20,000,000",
            source_file="manual.csv",
        )
        self.assertTrue(
            ContractService.duplicate_check(
                school_code="S002",
                school_name="새빛중",
                contract_date="2026-06-15",
                product="노트북",
                category="디지털",
                vendor="좋은업체",
                quantity=10,
                amount=20_000_000,
                source_file="another.csv",
            )
        )
        self.assertEqual(ContractService.search_by_vendor("좋은")[0]["id"], contract_id)
        self.assertEqual(ContractService.search_by_product("노트")[0]["id"], contract_id)
        self.assertEqual(ContractService.recent_contracts(1)[0]["id"], contract_id)

        self.assertTrue(
            ContractService.update(
                contract_id,
                school_code="S002",
                school_name="새빛중",
                contract_date="2026-06-15",
                product="태블릿",
                category="디지털",
                vendor="좋은업체",
                quantity=12,
                amount=21_000_000,
                source_file="manual.csv",
            )
        )
        self.assertEqual(ContractService.search_by_product("태블릿")[0]["quantity"], 12)

    def test_invalid_rows_are_counted_as_errors(self):
        path = os.path.join(self.temp_directory.name, "invalid.csv")
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(HEADERS)
            writer.writerow(["S003", "오류고", "not-a-date", "서버", "IT", "업체", "1.5", "금액"])

        connector = ContractImportConnector(path)
        preview = connector.preview()
        result = SyncService.synchronize_connector(connector)

        self.assertTrue(preview[0]["error"])
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(ContractService.search(), [])

    def test_contracts_are_evaluated_by_rule_engine(self):
        ContractService.save(
            school_code="S004",
            school_name="인사이트고",
            contract_date="2026-05-10",
            product="AI 학습 플랫폼",
            category="소프트웨어",
            vendor="AI 공급사",
            quantity=1,
            amount=50_000_000,
        )
        RuleService.create(
            "계약 업체",
            {"field": "vendor", "operator": "contains", "value": "AI"},
            "재계약 제안",
            45,
            "AI 공급 계약 발견",
        )

        insights = RuleService.evaluate_contracts(
            ContractService.search_by_school("S004")
        )

        self.assertEqual(insights[0]["target_type"], "contract")
        self.assertEqual(insights[0]["project_name"], "AI 학습 플랫폼")
        self.assertIn("재계약 제안", insights[0]["recommendation"])

    def test_gui_preview_values_show_validation_state(self):
        values = preview_table_values(
            {
                "row_number": 2,
                "contract": {
                    "school_code": "S1",
                    "school_name": "학교",
                    "contract_date": "2026-01-01",
                    "product": "제품",
                    "vendor": "업체",
                    "amount": 1000,
                },
                "error": "",
            }
        )
        self.assertEqual(values[-2:], ("1,000원", "정상"))

    def test_contract_table_migration_columns(self):
        with closing(database.get_connection()) as connection:
            columns = [row[1] for row in connection.execute("PRAGMA table_info(contracts)")]
        self.assertEqual(
            columns,
            [
                "id",
                "school_code",
                "school_name",
                "contract_date",
                "product",
                "category",
                "vendor",
                "quantity",
                "amount",
                "source_file",
                "imported_at",
                "updated_at",
            ],
        )


if __name__ == "__main__":
    unittest.main()
