def find_school(
    keyword="",
    region="전체",
    school_type="전체",
    office="전체"
):

    conn = get_connection()
    cursor = conn.cursor()

    region_map = {
        "서울":"서울특별시",
        "부산":"부산광역시",
        "대구":"대구광역시",
        "인천":"인천광역시",
        "광주":"광주광역시",
        "대전":"대전광역시",
        "울산":"울산광역시",
        "세종":"세종특별자치시",
        "경기":"경기도",
        "강원":"강원특별자치도",
        "충북":"충청북도",
        "충남":"충청남도",
        "전북":"전북특별자치도",
        "전남":"전라남도",
        "경북":"경상북도",
        "경남":"경상남도",
        "제주":"제주특별자치도"
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

        region = region_map.get(region, region)

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