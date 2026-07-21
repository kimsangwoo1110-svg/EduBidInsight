from openpyxl import load_workbook
from services.database import add_school


def value(v):
    if v is None:
        return ""
    return str(v).strip()


def import_school_data(file_path):

    wb = load_workbook(file_path)
    ws = wb.active

    count = 0

    for row in ws.iter_rows(min_row=2, values_only=True):

        school_code = value(row[0]) if len(row) > 0 else ""
        school_name = value(row[1]) if len(row) > 1 else ""
        school_type = value(row[2]) if len(row) > 2 else ""
        office = value(row[3]) if len(row) > 3 else ""
        region = value(row[4]) if len(row) > 4 else ""
        address = value(row[5]) if len(row) > 5 else ""
        homepage = value(row[6]) if len(row) > 6 else ""

        add_school(
            school_code=school_code,
            name=school_name,
            office=office,
            region=region,
            school_type=school_type,
            address=address,
            homepage=homepage
        )

        count += 1

    return count