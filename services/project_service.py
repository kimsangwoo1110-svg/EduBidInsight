"""Project-domain service used by school detail and School360."""

from datetime import date, datetime

from services.database import (
    add_project,
    delete_project,
    find_projects_by_school,
    update_project,
)


PROJECT_FIELDS = (
    "id",
    "school_code",
    "project_name",
    "category",
    "status",
    "budget",
    "start_year",
    "end_year",
    "source",
    "updated_at",
    "expected_procurement_date",
    "memo",
)

ALL_FILTER = "전체"
STATUS_OPTIONS = ("진행중", "예정", "완료", "보류")


class ProjectService:
    """CRUD boundary between the GUI and project persistence."""

    STATUS_OPTIONS = STATUS_OPTIONS

    @staticmethod
    def create(
        school_code,
        project_name,
        category="",
        status="",
        budget=0,
        start_year=None,
        end_year=None,
        source="",
        expected_procurement_date="",
        memo="",
        connection=None,
        commit=True,
    ):
        if not str(school_code or "").strip():
            raise ValueError("school_code is required")
        if not str(project_name or "").strip():
            raise ValueError("project_name is required")
        procurement_date = ProjectService.normalize_date(expected_procurement_date)
        return add_project(
            school_code,
            project_name,
            category,
            status,
            budget,
            start_year,
            end_year,
            source,
            procurement_date,
            str(memo or "").strip(),
            connection=connection,
            commit=commit,
        )

    @staticmethod
    def list_for_school(
        school_code, project_name="", category=ALL_FILTER, status=ALL_FILTER, year=None
    ):
        selected_year = int(year) if str(year or "").strip() else None
        return [
            dict(zip(PROJECT_FIELDS, row))
            for row in find_projects_by_school(
                school_code,
                project_name=project_name,
                category="" if category == ALL_FILTER else category,
                status="" if status == ALL_FILTER else status,
                year=selected_year,
            )
        ]

    @staticmethod
    def update(
        project_id,
        project_name,
        category="",
        status="",
        budget=0,
        start_year=None,
        end_year=None,
        source="",
        expected_procurement_date="",
        memo="",
        connection=None,
        commit=True,
    ):
        if not str(project_name or "").strip():
            raise ValueError("project_name is required")
        procurement_date = ProjectService.normalize_date(expected_procurement_date)
        return update_project(
            project_id,
            project_name,
            category,
            status,
            budget,
            start_year,
            end_year,
            source,
            procurement_date,
            str(memo or "").strip(),
            connection=connection,
            commit=commit,
        )

    @staticmethod
    def delete(project_id):
        return delete_project(project_id)

    @staticmethod
    def sample_projects(school_code):
        """Return clearly-labelled display samples without writing synthetic data."""
        return [
            {
                "id": None,
                "school_code": school_code,
                "project_name": "AI 기반 교육환경 구축 (샘플)",
                "category": "AI 교육",
                "status": "예정",
                "budget": 150000000,
                "start_year": 2026,
                "end_year": 2027,
                "source": "샘플 데이터",
                "updated_at": "",
                "expected_procurement_date": "2026-11-01",
                "memo": "샘플 데이터입니다.",
            },
            {
                "id": None,
                "school_code": school_code,
                "project_name": "학교 공간혁신 사업 (샘플)",
                "category": "공간혁신",
                "status": "보류",
                "budget": 80000000,
                "start_year": 2026,
                "end_year": 2026,
                "source": "샘플 데이터",
                "updated_at": "",
                "expected_procurement_date": "2027-02-01",
                "memo": "샘플 데이터입니다.",
            },
        ]

    @classmethod
    def list_for_school_or_samples(cls, school_code):
        projects = cls.list_for_school(school_code)
        return projects or cls.sample_projects(school_code)

    @staticmethod
    def filter_projects(projects, project_name="", category=ALL_FILTER, status=ALL_FILTER, year=None):
        """Apply the same filters to non-persistent sample project records."""
        keyword = str(project_name or "").strip().casefold()
        selected_year = int(year) if str(year or "").strip() else None
        filtered_projects = []
        for project in projects:
            if keyword and keyword not in project["project_name"].casefold():
                continue
            if category != ALL_FILTER and project["category"] != category:
                continue
            if status != ALL_FILTER and project["status"] != status:
                continue
            if selected_year is not None:
                start_year = project["start_year"] or selected_year
                end_year = project["end_year"] or selected_year
                if not start_year <= selected_year <= end_year:
                    continue
            filtered_projects.append(project)
        return filtered_projects

    @staticmethod
    def summarize(projects):
        """Return count, budget, and standard-status totals for displayed projects."""
        status_counts = {status: 0 for status in STATUS_OPTIONS}
        total_budget = 0
        for project in projects:
            total_budget += float(project["budget"] or 0)
            if project["status"] in status_counts:
                status_counts[project["status"]] += 1
        return {
            "total_count": len(projects),
            "total_budget": total_budget,
            "status_counts": status_counts,
        }

    @staticmethod
    def format_budget(budget):
        """Format a budget with commas and Korean high-value units."""
        amount = int(float(budget or 0))
        if abs(amount) >= 100_000_000:
            value = amount / 100_000_000
            return f"{amount:,}원 ({value:,.1f}억원)"
        if abs(amount) >= 10_000:
            value = amount / 10_000
            return f"{amount:,}원 ({value:,.0f}만원)"
        return f"{amount:,}원"

    @staticmethod
    def normalize_date(value):
        if value in (None, ""):
            return ""
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        text = str(value).strip()
        for pattern in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(text, pattern).date().isoformat()
            except ValueError:
                continue
        raise ValueError("예상 조달일은 YYYY-MM-DD 형식이어야 합니다.")
