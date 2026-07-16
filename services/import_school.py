from openpyxl import load_workbook
from services.database import add_school


def import_school_data(file_path):

    wb = load_workbook(file_path, data_only=True)
    ws = wb.active

    success = 0
    fail = 0

    for row in ws.iter_rows(min_row=2, values_only=True):

        try:

            if row is None:
                continue

            school_name = "" if row[0] is None else str(row[0]).strip()

            if school_name == "":
                continue

            office = "" if len(row) < 2 or row[1] is None else str(row[1]).strip()
            region = "" if len(row) < 3 or row[2] is None else str(row[2]).strip()
            school_type = "" if len(row) < 4 or row[3] is None else str(row[3]).strip()
            address = "" if len(row) < 5 or row[4] is None else str(row[4]).strip()

            add_school(
                school_name,
                office,
                region,
                school_type,
                address
            )

            success += 1

        except Exception:

            fail += 1

    return success, fail