import sqlite3
import os

DB_NAME = "data/edubid.db"


def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_NAME)


def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schools(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        school_name TEXT,
        office TEXT,
        region TEXT,
        school_type TEXT,
        address TEXT,

        ai_school INTEGER DEFAULT 0,
        digital_school INTEGER DEFAULT 0,
        space_innovation INTEGER DEFAULT 0,
        green_smart INTEGER DEFAULT 0,
        student_count INTEGER DEFAULT 0,
        class_count INTEGER DEFAULT 0

    )
    """)

    conn.commit()
    conn.close()

    print("✅ Database Ready")


def add_school(
    name,
    office,
    region,
    school_type,
    address,
    ai_school=0,
    digital_school=0,
    space_innovation=0,
    green_smart=0,
    student_count=0,
    class_count=0
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO schools(

        school_name,
        office,
        region,
        school_type,
        address,

        ai_school,
        digital_school,
        space_innovation,
        green_smart,
        student_count,
        class_count

    )

    VALUES(?,?,?,?,?,?,?,?,?,?,?)

    """, (

        name,
        office,
        region,
        school_type,
        address,

        ai_school,
        digital_school,
        space_innovation,
        green_smart,
        student_count,
        class_count

    ))

    conn.commit()
    conn.close()


def find_school(
    keyword="",
    region="전체",
    school_type="전체",
    office="전체"
):

    conn = get_connection()
    cursor = conn.cursor()

    sql = """

    SELECT

        school_name,
        school_type,
        office,
        region,
        address,
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
        params.append(region)

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