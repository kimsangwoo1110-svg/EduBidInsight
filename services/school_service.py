"""
EduBid Insight

Module : School Service
Version : 0.2.0

학교 데이터 관리 서비스
"""

from services.database import (
    add_school,
    find_school,
    clear_school_data
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
    def clear():
        """학교 데이터 전체 삭제"""

        clear_school_data()