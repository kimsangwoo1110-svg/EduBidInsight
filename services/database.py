import os
import sqlite3
from datetime import datetime

DB_NAME = "data/edubid.db"


# -------------------------------------------------
# DB 연결
# -------------------------------------------------
def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_NAME)


# -------------------------------------------------
# DB 생성
# -------------------------------------------------
def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schools(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        school_code TEXT UNIQUE,

        school_name TEXT NOT NULL,

        office TEXT,
        region TEXT,
        school_type TEXT,

        address TEXT,
        homepage TEXT,

        ai_school INTEGER DEFAULT 0,
        digital_school INTEGER DEFAULT 0,
        space_innovation INTEGER DEFAULT 0,
        green_smart INTEGER DEFAULT 0,

        student_count INTEGER DEFAULT 0,
        class_count INTEGER DEFAULT 0,

        updated_at TEXT

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_school_name
    ON schools(school_name)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_region
    ON schools(region)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_office
    ON schools(office)
    """)

    conn.commit()
    conn.close()

    print("Database Ready")


# -------------------------------------------------
# 기존 데이터 삭제
# -------------------------------------------------
def clear_school_data():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM schools")

    conn.commit()
    conn.close()


# -------------------------------------------------
# 학교 저장
# -------------------------------------------------
def add_school(
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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO schools(

            school_code,
            school_name,

            office,
            region,
            school_type,

            address,
            homepage,

            ai_school,
            digital_school,
            space_innovation,
            green_smart,

            student_count,
            class_count,

            updated_at

        )

        VALUES(
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?
        )
        """,
        (

            school_code,
            name,

            office,
            region,
            school_type,

            address,
            homepage,

            ai_school,
            digital_school,
            space_innovation,
            green_smart,

            student_count,
            class_count,

            datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        )
    )

    conn.commit()
    conn.close()


# -------------------------------------------------
# 학교 검색
# -------------------------------------------------
def find_school(
    keyword="",
    region="전체",
    school_type="전체",
    office="전체"
):

    conn = get_connection()
    cursor = conn.cursor()

    region_map = {

        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "세종": "세종특별자치시",
        "경기": "경기도",
        "강원": "강원특별자치도",
        "충북": "충청북도",
        "충남": "충청남도",
        "전북": "전북특별자치도",
        "전남": "전라남도",
        "경북": "경상북도",
        "경남": "경상남도",
        "제주": "제주특별자치도"

    }

    sql = """
    SELECT

        school_code,
        school_name,
        school_type,
        office,
        region,
        address,
        homepage,

        ai_school,
        digital_school,
        space_innovation,
        green_smart,

        student_count,
        class_count

    FROM schools

    WHERE 1=1
    """

    params = []

    if keyword:

        sql += " AND school_name LIKE ?"
        params.append(f"%{keyword}%")

    if region != "전체":

        sql += " AND region=?"
        params.append(region_map.get(region, region))

    if school_type != "전체":

        sql += " AND school_type=?"
        params.append(school_type)

    if office != "전체":

        sql += " AND office=?"
        params.append(office)

    sql += " ORDER BY school_name"

    cursor.execute(sql, params)

    rows = cursor.fetchall()

    conn.close()

    return rows