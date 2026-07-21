"""
EduBid Insight

Module : School Service
Version : 0.2.0

학교 데이터 관리 서비스
"""

from services.database import (
    add_school,
    find_school,
    clear_school_data,
    find_school_by_name,
    find_school_by_code,
)


SCHOOL_FIELDS = (
    "school_code", "school_name", "school_type", "office", "region", "address",
    "homepage", "ai_school", "digital_school", "space_innovation", "green_smart",
    "student_count", "class_count",
)


class SchoolService:
    """학교 데이터 서비스"""

    @staticmethod
    def save(
        school_code,
        name,
        office,
        region,
        school_type,
        address,
        homepage="",
        ai_school=0,
        digital_school=0,
        space_innovation=0,
        green_smart=0,
        student_count=0,
        class_count=0
    ):
        """학교 저장"""

        add_school(
            school_code=school_code,
            name=name,
            office=office,
            region=region,
            school_type=school_type,
            address=address,
            homepage=homepage,
            ai_school=ai_school,
            digital_school=digital_school,
            space_innovation=space_innovation,
            green_smart=green_smart,
            student_count=student_count,
            class_count=class_count
        )

    @staticmethod
    def search(
        keyword="",
        region="전체",
        school_type="전체",
        office="전체"
    ):
        """학교 검색"""

        return find_school(
            keyword=keyword,
            region=region,
            school_type=school_type,
            office=office
        )

    @staticmethod
    def all():
        """Return every school as dictionaries for batch aggregation."""
        return [dict(zip(SCHOOL_FIELDS, row)) for row in find_school()]

    @staticmethod
    def clear():
        """학교 데이터 전체 삭제"""

        clear_school_data()

    @staticmethod
    def match_name(school_name, connection=None):
        """Return an exact normalized school match or ``None``."""
        return find_school_by_name(school_name, connection=connection)

    @staticmethod
    def get_by_code(school_code, connection=None):
        """Return one school dictionary without a broad name search."""
        row = find_school_by_code(school_code, connection=connection)
        return dict(zip(SCHOOL_FIELDS, row)) if row else None

    @classmethod
    def match_import(cls, school_code="", school_name="", region="", connection=None):
        """Match imports by code, then normalized name constrained by region."""
        if str(school_code or "").strip():
            match = cls.get_by_code(school_code, connection=connection)
            if match:
                return match
        match = cls.match_name(school_name, connection=connection)
        if not match:
            return None
        if str(region or "").strip():
            complete = cls.get_by_code(match["school_code"], connection=connection)
            normalized_expected = "".join(str(region).split()).casefold()
            normalized_actual = "".join(str(complete.get("region", "")).split()).casefold()
            if normalized_expected != normalized_actual:
                return None
            return complete
        return match
