"""NEIS school-information connector."""

import requests

from config.settings import NEIS_API_KEY
from services.connectors.base import BaseConnector
from services.database import add_school, get_connection, school_exists
from services.region_data import normalize_office, normalize_region


URL = "https://open.neis.go.kr/hub/schoolInfo"
PAGE_SIZE = 1000


class NeisSchoolConnector(BaseConnector):
    source = "NEIS 학교정보"

    def __init__(self, api_key=NEIS_API_KEY, session=None):
        self.api_key = api_key
        self.session = session or requests
        self.connection = None
        super().__init__()

    def open(self):
        self.connection = get_connection()

    def close(self, success):
        if self.connection is None:
            return
        if success:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.connection.close()
        self.connection = None

    def fetch(self):
        page = 1
        downloaded = 0
        expected_total = 0
        while True:
            self.notify(
                stage="requesting",
                page=page,
                downloaded=downloaded,
                total=expected_total,
            )
            response = self.session.get(
                URL,
                params={
                    "KEY": self.api_key,
                    "Type": "json",
                    "pIndex": page,
                    "pSize": PAGE_SIZE,
                },
                timeout=30,
            )
            response.raise_for_status()
            response_data = response.json()
            school_info, rows, page_total = self.extract_school_info(response_data)
            if school_info is None:
                if downloaded:
                    break
                raise RuntimeError(self.api_error_message(response_data))

            expected_total = page_total or expected_total
            if not rows:
                break
            for school in rows:
                downloaded += 1
                yield school

            self.notify(
                stage="downloading",
                page=page,
                downloaded=downloaded,
                total=expected_total,
            )
            if len(rows) < PAGE_SIZE:
                break
            page += 1

        self.notify(
            stage="complete",
            page=page,
            downloaded=downloaded,
            total=expected_total,
        )

    def transform(self, school):
        school_code = str(school.get("SD_SCHUL_CODE", "") or "").strip()
        school_name = str(school.get("SCHUL_NM", "") or "").strip()
        if not school_code or not school_name:
            return None
        return {
            "school_code": school_code,
            "name": school_name,
            "office": normalize_office(school.get("ATPT_OFCDC_SC_NM", "")),
            "region": normalize_region(school.get("LCTN_SC_NM", "")),
            "school_type": school.get("SCHUL_KND_SC_NM", ""),
            "address": school.get("ORG_RDNMA", ""),
            "homepage": school.get("HMPG_ADRES", ""),
        }

    def load(self, school):
        is_update = school_exists(school["school_code"], self.connection)
        add_school(**school, connection=self.connection, commit=False)
        return "updated" if is_update else "inserted"

    @staticmethod
    def api_error_message(data):
        result = data.get("RESULT", {})
        code = result.get("CODE", "Unknown API response")
        message = result.get("MESSAGE", "schoolInfo data was not returned")
        return f"NEIS API error: {code} - {message}"

    @staticmethod
    def extract_school_info(data):
        school_info = data.get("schoolInfo")
        if not school_info:
            return None, [], 0

        total_count = 0
        rows = []
        for section in school_info:
            for header in section.get("head", []):
                total_count = int(header.get("list_total_count", total_count) or 0)
            rows.extend(section.get("row", []))
        return school_info, rows, total_count
