"""Read-only School360 view model assembled from connector mock records."""

from __future__ import annotations

from connectors.base_connector import ConnectorMetadata, MockConnector
from connectors.education_connector import EducationConnector
from connectors.g2b_connector import G2BConnector
from connectors.s2b_connector import S2BConnector
from connectors.school_info_connector import SchoolInfoConnector


SCHOOL_FIELDS = (
    "school_code", "school_name", "school_type", "office", "region", "address",
    "homepage", "ai_school", "digital_school", "space_innovation", "green_smart",
    "student_count", "class_count",
)


class _CRMViewConnector(MockConnector):
    metadata = ConnectorMetadata(
        "school360_crm", "CRM Mock", "crm", "School360 CRM presentation mock"
    )


class _AttachmentViewConnector(MockConnector):
    metadata = ConnectorMetadata(
        "school360_attachments", "Attachment Mock", "crm",
        "School360 attachment presentation mock",
    )


def normalize_school_selection(school):
    """Normalize a School Search tuple or dictionary for presentation use."""
    if isinstance(school, dict):
        result = {field: school.get(field, "") for field in SCHOOL_FIELDS}
    else:
        values = tuple(school or ())
        result = {
            field: values[index] if index < len(values) else ""
            for index, field in enumerate(SCHOOL_FIELDS)
        }
    result["school_code"] = str(result.get("school_code") or "").strip()
    result["school_name"] = str(result.get("school_name") or "").strip()
    if not result["school_code"]:
        raise ValueError("school_code is required")
    if not result["school_name"]:
        raise ValueError("school_name is required")
    for field in ("student_count", "class_count"):
        try:
            result[field] = max(0, int(result.get(field) or 0))
        except (TypeError, ValueError):
            result[field] = 0
    return result


class School360MockProvider:
    """Build one deterministic School360 snapshot through mock connectors only."""

    @classmethod
    def dashboard(cls, school):
        school = normalize_school_selection(school)
        name = school["school_name"]
        school_code = school["school_code"]

        basic = cls._fetch(SchoolInfoConnector([school]))[0]
        projects = cls._fetch(EducationConnector([
            {"name": "AI 기반 미래교실 구축", "category": "디지털 교육", "period": "2026.09 – 2027.02", "budget": 120_000_000, "status": "예정"},
            {"name": "학교 공간혁신 사업", "category": "시설", "period": "2027.01 – 2027.08", "budget": 85_000_000, "status": "검토"},
            {"name": "교내 무선망 고도화", "category": "네트워크", "period": "2026.11 – 2027.03", "budget": 64_000_000, "status": "예정"},
        ]))
        procurement = cls._fetch(S2BConnector([
            {"source": "S2B", "date": "2026-07-15", "item": "교육용 태블릿", "vendor": "미래교육상사", "amount": 18_500_000},
            {"source": "S2B", "date": "2026-06-28", "item": "교실용 디스플레이", "vendor": "에듀테크솔루션", "amount": 12_800_000},
        ])) + cls._fetch(G2BConnector([
            {"source": "G2B", "date": "2026-05-10", "item": "무선 네트워크 장비", "vendor": "코리아네트웍스", "amount": 32_000_000},
        ]))
        crm = cls._fetch(_CRMViewConnector([
            {"date": "2026-07-22", "type": "미팅", "contact": "정보부장", "summary": "미래교실 구축 일정 협의", "status": "Qualified"},
            {"date": "2026-07-18", "type": "전화", "contact": "행정실", "summary": "조달 일정 및 예산 확인", "status": "Lead"},
            {"date": "2026-07-10", "type": "견적", "contact": "담당교사", "summary": "태블릿 30대 견적 전달", "status": "Proposal"},
        ]))
        attachments = cls._fetch(_AttachmentViewConnector([
            {"name": f"{name}_학교현황.pdf", "type": "PDF", "updated": "2026-07-21", "size": "1.2 MB"},
            {"name": f"{school_code}_미래교실_제안서.pptx", "type": "PowerPoint", "updated": "2026-07-19", "size": "4.8 MB"},
            {"name": "현장미팅_회의록.docx", "type": "Word", "updated": "2026-07-18", "size": "620 KB"},
        ]))

        procurement_total = sum(int(item.get("amount") or 0) for item in procurement)
        statistics = {
            "students": basic["student_count"],
            "classes": basic["class_count"],
            "planned_projects": len(projects),
            "planned_budget": sum(int(item.get("budget") or 0) for item in projects),
            "procurement_count": len(procurement),
            "procurement_total": procurement_total,
            "crm_activities": len(crm),
            "attachments": len(attachments),
        }
        return {
            "school": basic,
            "statistics": statistics,
            "planned_projects": projects,
            "procurement": sorted(procurement, key=lambda item: item["date"], reverse=True),
            "crm": crm,
            "attachments": attachments,
            "mock": True,
            "connector_sources": (
                "School Info OpenAPI", "Education Office", "School Market (S2B)",
                "NaraJangteo (G2B)", "CRM Mock", "Attachment Mock",
            ),
        }

    @staticmethod
    def _fetch(connector):
        try:
            connector.connect()
            if connector.validate() is not True:
                raise ValueError(f"mock connector validation failed: {connector.metadata.key}")
            return list(connector.fetch())
        finally:
            connector.disconnect()
