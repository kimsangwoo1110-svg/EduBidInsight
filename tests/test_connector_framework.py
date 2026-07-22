import os
import tempfile
import unittest

from openpyxl import Workbook

from connectors import (
    EducationConnector, ExcelConnector, G2BConnector, S2BConnector,
    SchoolInfoConnector, connector_catalog, connector_for_profile,
)
from connectors.base_connector import BaseConnector, ConnectorMetadata


class LifecycleConnector(BaseConnector):
    metadata = ConnectorMetadata("test", "Test", "school", "Test connector", False)

    def __init__(self, valid=True):
        super().__init__()
        self.valid = valid
        self.events = []

    def connect(self):
        self.events.append("connect"); self.connected = True

    def disconnect(self):
        self.events.append("disconnect"); self.connected = False

    def validate(self):
        self.events.append("validate"); return self.valid

    def fetch(self):
        self.events.append("fetch"); return [{"id": 1}]

    def import_data(self, records):
        self.events.append("import_data"); return {"imported": len(records)}


class ConnectorFrameworkTest(unittest.TestCase):
    def test_sync_runs_complete_lifecycle_and_disconnects(self):
        connector = LifecycleConnector()

        result = connector.sync()

        self.assertEqual(
            connector.events,
            ["connect", "validate", "fetch", "import_data", "disconnect"],
        )
        self.assertFalse(connector.connected)
        self.assertEqual(result["fetched"], 1)
        self.assertEqual(result["imported"], 1)

    def test_sync_disconnects_when_validation_fails(self):
        connector = LifecycleConnector(valid=False)

        with self.assertRaises(ValueError):
            connector.sync()

        self.assertEqual(connector.events, ["connect", "validate", "disconnect"])
        self.assertFalse(connector.connected)

    def test_future_connectors_are_safe_no_write_mocks(self):
        for connector_type in (
            SchoolInfoConnector, S2BConnector, G2BConnector, EducationConnector,
        ):
            with self.subTest(connector=connector_type.__name__):
                result = connector_type([{"external_id": "1"}]).sync()
                self.assertEqual(result["status"], "MOCK")
                self.assertEqual(result["imported"], 0)
                self.assertEqual(result["skipped"], 1)

    def test_catalog_drives_all_import_center_profiles(self):
        catalog = connector_catalog()

        self.assertEqual(
            [item.metadata.profile_key for item in catalog],
            ["school", "education_office", "schoolmarket", "g2b", "crm"],
        )
        self.assertIsInstance(connector_for_profile("g2b"), G2BConnector)
        self.assertIsInstance(connector_for_profile("crm"), ExcelConnector)

    def test_excel_connector_reads_rows_and_uses_injected_importer(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = os.path.join(temporary, "source.xlsx")
            workbook = Workbook(); sheet = workbook.active
            sheet.append(["학교명", "지역"]); sheet.append(["미래학교", "서울"])
            workbook.save(source); workbook.close()
            received = []

            def import_handler(records):
                received.extend(records)
                return {"status": "SUCCESS", "imported": len(records), "failed": 0}

            result = ExcelConnector(source, import_handler=import_handler).sync()

        self.assertEqual(received, [{"학교명": "미래학교", "지역": "서울"}])
        self.assertEqual(result["fetched"], 1)
        self.assertEqual(result["imported"], 1)


if __name__ == "__main__":
    unittest.main()
