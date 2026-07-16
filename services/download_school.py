import requests

from config.settings import NEIS_API_KEY
from services.database import add_school


URL = "https://open.neis.go.kr/hub/schoolInfo"


def download_school_data():

    page = 1
    total = 0

    while True:

        print("=" * 80)
        print(f"PAGE : {page}")

        params = {
            "KEY": NEIS_API_KEY,
            "Type": "json",
            "pIndex": page,
            "pSize": 1000
        }

        response = requests.get(URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if "schoolInfo" not in data:
            print("다운로드 완료")
            break

        rows = data["schoolInfo"][1]["row"]

        if not rows:
            break

        for school in rows:

            try:

                add_school(
                    school_code=school.get("SD_SCHUL_CODE", ""),
                    name=school.get("SCHUL_NM", ""),
                    office=school.get("ATPT_OFCDC_SC_NM", ""),
                    region=school.get("LCTN_SC_NM", ""),
                    school_type=school.get("SCHUL_KND_SC_NM", ""),
                    address=school.get("ORG_RDNMA", ""),
                    homepage=school.get("HMPG_ADRES", ""),
                    ai_school=0,
                    digital_school=0,
                    space_innovation=0,
                    green_smart=0,
                    student_count=0,
                    class_count=0
                )

                total += 1

            except Exception as e:
                print(e)

        print(f"저장 완료 : {total:,}개")

        page += 1

    print("=" * 80)
    print(f"최종 저장 : {total:,}개")

    return total