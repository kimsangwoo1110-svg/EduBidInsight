import csv
import os
import tempfile
import unittest

from services import database
from services.analytics_service import AnalyticsService
from services.connectors.education_office_import import (
    EducationOfficeImport,
    classify_project,
)
from services.import_history_service import ImportHistoryService
from services.project_service import ProjectService
from services.school_profile_service import SchoolProfileService
from services.school_service import SchoolService
from gui.dashboard import project_portfolio_values


HEADERS = [
    "교육청", "지역", "학교명", "학교코드", "사업명", "사업유형",
    "사업비", "회계연도", "진행상태", "사업시작일", "사업종료일",
]


class EducationOfficeImportTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "office-projects.db")
        database.create_database()
        SchoolService.save(
            "OFF-S1", "교육미래학교", "서울교육청", "서울", "중학교", "서울시"
        )
        SchoolService.save(
            "OFF-S2", "지역혁신학교", "부산교육청", "부산", "고등학교", "부산시"
        )

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def create_csv(self, rows):
        path = os.path.join(self.temp_directory.name, "office-projects.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        return path

    @staticmethod
    def row(
        office="서울교육청",
        region="서울",
        school="교육미래학교",
        code="OFF-S1",
        name="AI 교육환경 구축",
        project_type="AI 교육",
        budget="100000000",
        year="2026",
        status="Active",
    ):
        return [
            office, region, school, code, name, project_type, budget, year,
            status, "2026-03-01", "2026-12-31",
        ]

    def test_import_auto_mapping_normalization_category_and_history(self):
        path = self.create_csv([self.row()])
        importer = EducationOfficeImport(path)

        summary = importer.run()
        project = ProjectService.list_for_school("OFF-S1")[0]

        self.assertEqual(importer.mapping["project_name"], "사업명")
        self.assertEqual(importer.mapping["fiscal_year"], "회계연도")
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["imported"], 1)
        self.assertEqual(summary["school_match_rate"], 100.0)
        self.assertEqual(summary["category_summary"], {"AI Education": 1})
        self.assertEqual(project["category"], "AI Education")
        self.assertEqual(project["status"], "진행중")
        self.assertEqual(project["start_year"], 2026)
        self.assertEqual(ImportHistoryService.history()[0]["source_type"], "Education Office")

    def test_duplicate_priority_and_composite_fallback(self):
        primary = self.create_csv(
            [self.row(budget="100000000"), self.row(budget="120000000")]
        )
        primary_summary = EducationOfficeImport(primary).run()
        self.assertEqual(primary_summary["imported"], 1)
        self.assertEqual(primary_summary["duplicates"], 1)

        fallback = self.create_csv(
            [self.row(code="", name="스마트교실 구축", project_type="스마트교실")]
        )
        first = EducationOfficeImport(fallback).run()
        second = EducationOfficeImport(fallback).run()
        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["duplicates"], 1)

    def test_school_matching_priority_and_unmatched_warning(self):
        path = self.create_csv(
            [
                self.row(school="잘못된 이름", region="다른지역"),
                self.row(code="", school="교육 미래 학교", name="공간혁신", project_type="공간혁신"),
                self.row(code="BAD", school="없는학교", name="시설 안전", project_type="안전"),
            ]
        )

        summary = EducationOfficeImport(path).run()

        self.assertEqual(summary["imported"], 3)
        self.assertEqual(summary["school_matches"], 2)
        self.assertEqual(len(ProjectService.list_for_school("OFF-S1")), 2)
        self.assertTrue(any("school not matched" in warning for warning in summary["warnings"]))

    def test_extensible_project_categories(self):
        cases = {
            "AI 교육 플랫폼": "AI Education",
            "학교 공간혁신 사업": "Space Innovation",
            "스마트교실 구축": "Smart Classroom",
            "Digital Learning Platform": "Digital Learning",
            "통학로 안전 개선": "Safety",
            "교사동 시설 보수": "Facility",
            "독서 프로그램": "Other",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(classify_project(name), expected)

    def test_school_profile_timeline_and_project_statistics(self):
        path = self.create_csv(
            [
                self.row(name="AI 교실", budget="100000000", status="Active"),
                self.row(name="시설 보수", project_type="시설", budget="50000000", status="Completed"),
            ]
        )
        EducationOfficeImport(path).run()

        profile = SchoolProfileService.get_profile("OFF-S1")

        self.assertEqual(profile["statistics"]["projects"], 2)
        self.assertEqual(profile["statistics"]["active_projects"], 1)
        self.assertEqual(profile["statistics"]["completed_projects"], 1)
        self.assertEqual(profile["statistics"]["project_budget"], 150_000_000)
        self.assertEqual(len(profile["latest_projects"]), 2)
        self.assertEqual(
            sum(event["source"] == "Education Office" for event in profile["recent_activity"]),
            2,
        )

    def test_dashboard_and_analytics_aggregation(self):
        path = self.create_csv(
            [
                self.row(name="AI 교육", budget="100000000", year="2025"),
                self.row(name="시설 보수", project_type="시설", budget="50000000", year="2026", status="Completed"),
                self.row(
                    office="부산교육청", region="부산", school="지역혁신학교",
                    code="OFF-S2", name="디지털 학습", project_type="디지털 교육",
                    budget="80000000", year="2026",
                ),
            ]
        )
        EducationOfficeImport(path).run()

        school = AnalyticsService.school_summary("OFF-S1")
        offices = AnalyticsService.education_office_analytics()

        self.assertEqual(school["project_analytics"]["total_projects"], 2)
        self.assertEqual(school["project_analytics"]["active_projects"], 1)
        self.assertEqual(school["project_analytics"]["total_budget"], 150_000_000)
        self.assertEqual(
            project_portfolio_values(school),
            (
                ("Total projects", "2건"),
                ("Active projects", "1건"),
                ("Total project budget", "150,000,000원 (1.5억원)"),
            ),
        )
        self.assertEqual(
            {row["category"] for row in school["project_analytics"]["category_distribution"]},
            {"AI Education", "Facility"},
        )
        self.assertEqual(
            {row["year"] for row in offices["budget_trends"]}, {2025, 2026}
        )
        self.assertEqual(
            {row["office"] for row in offices["office_comparison"]},
            {"서울교육청", "부산교육청"},
        )
        self.assertEqual(offices["total_budget"], 230_000_000)


if __name__ == "__main__":
    unittest.main()
