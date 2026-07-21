"""Education Office project import for the Smart Import Framework."""

import hashlib
import os
import threading

from services import database
from services.base_import import BaseImport
from services.connectors.schoolmarket_import import SchoolMarketImport
from services.contract_service import ContractService
from services.project_service import ProjectService
from services.school_service import SchoolService


EDUCATION_OFFICE_COLUMNS = (
    "office",
    "region",
    "school_name",
    "school_code",
    "project_name",
    "project_type",
    "budget",
    "fiscal_year",
    "status",
    "start_date",
    "end_date",
)
EDUCATION_OFFICE_REQUIRED_FIELDS = (
    "project_name",
    "budget",
    "fiscal_year",
)
EDUCATION_OFFICE_FIELD_LABELS = {
    "office": "교육청",
    "region": "지역",
    "school_name": "학교명",
    "school_code": "학교코드",
    "project_name": "사업명",
    "project_type": "사업유형",
    "budget": "예산",
    "fiscal_year": "회계연도",
    "status": "상태",
    "start_date": "시작일",
    "end_date": "종료일",
}
EDUCATION_OFFICE_COLUMN_ALIASES = {
    "office": ("교육청", "교육지원청", "주관교육청", "office", "educationoffice"),
    "region": ("지역", "시도", "권역", "region", "area"),
    "school_name": ("학교명", "학교", "기관명", "schoolname", "school name"),
    "school_code": ("학교코드", "표준학교코드", "기관코드", "schoolcode", "school code"),
    "project_name": ("사업명", "프로젝트명", "과제명", "projectname", "project name"),
    "project_type": ("사업유형", "사업구분", "프로젝트유형", "projecttype", "project type"),
    "budget": ("예산", "사업비", "총사업비", "배정예산", "budget", "projectbudget"),
    "fiscal_year": ("회계연도", "사업연도", "연도", "fiscalyear", "fiscal year", "year"),
    "status": ("상태", "진행상태", "사업상태", "status", "projectstatus"),
    "start_date": ("시작일", "사업시작일", "착수일", "startdate", "start date"),
    "end_date": ("종료일", "사업종료일", "완료일", "enddate", "end date"),
}

PROJECT_CATEGORY_RULES = (
    ("AI Education", ("ai education", "artificial intelligence", "ai교육", "ai 교육", "인공지능", "ai 교실")),
    ("Space Innovation", ("space innovation", "공간혁신", "공간 개선", "학교공간")),
    ("Smart Classroom", ("smart classroom", "스마트교실", "스마트 교실", "미래교실")),
    ("Digital Learning", ("digital learning", "디지털학습", "디지털 교육", "에듀테크", "온라인학습")),
    ("Safety", ("safety", "안전", "방재", "소방", "내진")),
    ("Facility", ("facility", "시설", "보수", "리모델링", "환경개선")),
)
STATUS_ALIASES = {
    "active": "진행중",
    "inprogress": "진행중",
    "진행": "진행중",
    "진행중": "진행중",
    "planned": "예정",
    "planning": "예정",
    "예정": "예정",
    "completed": "완료",
    "complete": "완료",
    "finished": "완료",
    "완료": "완료",
    "hold": "보류",
    "onhold": "보류",
    "보류": "보류",
}


def classify_project(project_name, project_type=""):
    """Classify an office project using ordered, extensible keyword rules."""
    normalized = " ".join(f"{project_type or ''} {project_name or ''}".casefold().split())
    for category, terms in PROJECT_CATEGORY_RULES:
        if any(term in normalized for term in terms):
            return category
    return "Other"


class EducationOfficeImport(SchoolMarketImport):
    """Import Education Office projects through the shared atomic lifecycle."""

    source = "Education Office"

    def __init__(
        self,
        filename,
        sheet_name=None,
        mapping=None,
        history_service=None,
        cancel_event=None,
    ):
        BaseImport.__init__(self, self.source, filename, history_service)
        self.extension = os.path.splitext(self.filename)[1].lower()
        if self.extension not in {".xlsx", ".csv"}:
            raise ValueError("only .xlsx and .csv Education Office files are supported")
        if not os.path.isfile(self.filename):
            raise ValueError("Education Office file does not exist")
        sheets = self.sheet_names(self.filename)
        self.sheet_name = sheet_name or sheets[0]
        headers = self.headers(self.filename, self.sheet_name)
        self.mapping = mapping or self.auto_map(headers)
        self.validate_mapping(self.mapping, headers)
        self.cancel_event = cancel_event or threading.Event()
        self._loaded = None

    def _transform(self, source_row):
        values = {
            field: source_row.get(header, "") if header else ""
            for field, header in self.mapping.items()
        }
        fiscal_year = self._year(values.get("fiscal_year"))
        start_date = self._date(values.get("start_date"))
        end_date = self._date(values.get("end_date"))
        project_name = str(values.get("project_name") or "").strip()
        project_type = str(values.get("project_type") or "").strip()
        project = {
            "office": str(values.get("office") or "").strip(),
            "region": str(values.get("region") or "").strip(),
            "school_name": str(values.get("school_name") or "").strip(),
            "source_school_code": str(values.get("school_code") or "").strip(),
            "project_name": project_name,
            "project_type": project_type,
            "budget": ContractService.normalize_amount(values.get("budget")),
            "fiscal_year": fiscal_year,
            "status": self._status(values.get("status")),
            "start_date": start_date,
            "end_date": end_date,
            "category": classify_project(project_name, project_type),
            # Generic preview aliases.
            "contract_date": start_date or f"{fiscal_year:04d}-01-01",
            "product": project_name,
            "vendor": str(values.get("office") or "").strip(),
            "quantity": 0,
            "amount": ContractService.normalize_amount(values.get("budget")),
        }
        if not project["source_school_code"] and not project["school_name"]:
            raise ValueError("school_code or school_name is required")
        return project

    def _raw_contract(self, source_row):
        values = {
            field: source_row.get(header, "") if header else ""
            for field, header in self.mapping.items()
        }
        project_name = str(values.get("project_name") or "").strip()
        return {
            "school_name": str(values.get("school_name") or "").strip(),
            "contract_date": values.get("start_date") or values.get("fiscal_year", ""),
            "product": project_name,
            "vendor": values.get("office", ""),
            "quantity": 0,
            "amount": values.get("budget", ""),
            "category": classify_project(project_name, values.get("project_type")),
        }

    def _save_purchase(self, row, result, connection):
        project = row["purchase"]
        result["school_rows"] += 1
        match = SchoolService.match_import(
            project["source_school_code"],
            project["school_name"],
            project["region"],
            connection=connection,
        )
        if match:
            result["school_matches"] += 1
            school_code = match["school_code"]
        else:
            identity = project["source_school_code"] or project["school_name"]
            school_code = self._unmatched_school_code(identity)
            result["warnings"].append(
                f"Row {row['row_number']}: school not matched: {identity}"
            )
        record_key = self._record_key(project, school_code)
        if database.education_office_key_exists(record_key, connection=connection):
            result["duplicates"] += 1
            return
        start_year = (
            int(project["start_date"][:4]) if project["start_date"] else project["fiscal_year"]
        )
        end_year = int(project["end_date"][:4]) if project["end_date"] else project["fiscal_year"]
        project_id = ProjectService.create(
            school_code,
            project["project_name"],
            project["category"],
            project["status"],
            project["budget"],
            start_year,
            end_year,
            self.source,
            connection=connection,
            commit=False,
        )
        database.add_education_office_key(
            {
                "record_key": record_key,
                "office": project["office"],
                "region": project["region"],
                "fiscal_year": project["fiscal_year"],
                "start_date": project["start_date"],
                "end_date": project["end_date"],
            },
            project_id,
            connection,
        )
        result["imported"] += 1
        result["category_summary"][project["category"]] += 1

    @staticmethod
    def _record_key(project, matched_school_code):
        name = "".join(project["project_name"].split()).casefold()
        if project["source_school_code"]:
            code = "".join(project["source_school_code"].split()).casefold()
            return f"primary:{code}|{name}|{project['fiscal_year']}"
        composite = "|".join(
            str(value or "").strip().casefold()
            for value in (
                matched_school_code,
                project["school_name"],
                project["region"],
                project["office"],
                project["project_name"],
                project["project_type"],
                project["fiscal_year"],
                project["budget"],
            )
        )
        return "composite:" + hashlib.sha256(composite.encode("utf-8")).hexdigest()

    @classmethod
    def auto_map(cls, headers):
        normalized = {cls._normalize(header): header for header in headers}
        return {
            field: next(
                (
                    normalized[cls._normalize(alias)]
                    for alias in EDUCATION_OFFICE_COLUMN_ALIASES[field]
                    if cls._normalize(alias) in normalized
                ),
                "",
            )
            for field in EDUCATION_OFFICE_COLUMNS
        }

    @staticmethod
    def validate_mapping(mapping, headers):
        missing = [field for field in EDUCATION_OFFICE_REQUIRED_FIELDS if not mapping.get(field)]
        if not mapping.get("school_code") and not mapping.get("school_name"):
            missing.append("school_code/school_name")
        if missing:
            raise ValueError(f"required column mappings are missing: {', '.join(missing)}")
        invalid = [value for value in mapping.values() if value and value not in set(headers)]
        if invalid:
            raise ValueError(f"mapped columns do not exist: {', '.join(invalid)}")
        selected = [value for value in mapping.values() if value]
        if len(selected) != len(set(selected)):
            raise ValueError("one source column cannot be mapped more than once")
        return True

    @staticmethod
    def _year(value):
        try:
            year = int(float(str(value or "").replace("년", "").strip()))
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid fiscal year: {value}") from error
        if year < 1900 or year > 2200:
            raise ValueError(f"invalid fiscal year: {value}")
        return year

    @staticmethod
    def _date(value):
        if value in (None, ""):
            return ""
        return ContractService.normalize_date(value)

    @staticmethod
    def _status(value):
        text = str(value or "").strip()
        normalized = "".join(character for character in text.casefold() if character.isalnum())
        return STATUS_ALIASES.get(normalized, text or "예정")


EDUCATION_OFFICE_PROJECT_FIELDS = (
    "id", "school_code", "project_name", "category", "status", "budget",
    "start_year", "end_year", "source", "updated_at", "office", "region",
    "fiscal_year", "start_date", "end_date",
)


class EducationOfficeService:
    """Read-only project metadata and aggregation service."""

    @staticmethod
    def projects(school_code=""):
        return [
            dict(zip(EDUCATION_OFFICE_PROJECT_FIELDS, row))
            for row in database.find_education_office_projects(school_code)
        ]


EducationOfficeImportConnector = EducationOfficeImport
