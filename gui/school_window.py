import customtkinter as ctk
from tkinter import ttk

from services.database import find_school
from services.excel_service import export_school_excel
from services.region_data import OFFICES


# ==========================================================
# 학교 상세창
# ==========================================================
def open_school_detail(parent, row):

    detail = ctk.CTkToplevel(parent)
    detail.title(row[1])
    detail.geometry("700x620")

    ctk.CTkLabel(
        detail,
        text=row[1],
        font=("맑은 고딕", 26, "bold")
    ).pack(pady=20)

    frame = ctk.CTkFrame(detail)
    frame.pack(fill="both", expand=True, padx=20, pady=10)

    infos = [

        ("학교코드", row[0]),
        ("학교명", row[1]),
        ("학교급", row[2]),
        ("교육청", row[3]),
        ("지역", row[4]),
        ("주소", row[5]),
        ("홈페이지", row[6]),
        ("학생수", f"{row[11]:,}"),
        ("학급수", f"{row[12]:,}")

    ]

    for title, value in infos:

        line = ctk.CTkFrame(frame)
        line.pack(fill="x", pady=3)

        ctk.CTkLabel(
            line,
            text=title,
            width=120,
            anchor="w",
            font=("맑은 고딕",13,"bold")
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            line,
            text=value,
            anchor="w"
        ).pack(side="left")

    ctk.CTkButton(
        detail,
        text="닫기",
        width=150,
        command=detail.destroy
    ).pack(pady=20)


# ==========================================================
# 학교 검색창
# ==========================================================
def open_school_window(parent):

    popup = ctk.CTkToplevel(parent)
    popup.title("학교 검색")
    popup.geometry("1400x850")

    current_rows = []

    title = ctk.CTkLabel(
        popup,
        text="학교 검색",
        font=("맑은 고딕",32,"bold")
    )
    title.pack(pady=20)

    search_frame = ctk.CTkFrame(popup)
    search_frame.pack(fill="x", padx=20)
        # ==============================
    # 학교명
    # ==============================
    ctk.CTkLabel(search_frame, text="학교명").grid(row=0, column=0, padx=10)

    keyword = ctk.CTkEntry(
        search_frame,
        width=220,
        placeholder_text="학교명을 입력하세요"
    )
    keyword.grid(row=1, column=0, padx=10, pady=(0, 15))

    # ==============================
    # 지역
    # ==============================
    ctk.CTkLabel(search_frame, text="지역").grid(row=0, column=1)

    region = ctk.CTkComboBox(
        search_frame,
        width=180,
        values=list(OFFICES.keys())
    )
    region.set("전체")
    region.grid(row=1, column=1, padx=10)

    # ==============================
    # 학교급
    # ==============================
    ctk.CTkLabel(search_frame, text="학교급").grid(row=0, column=2)

    school_type = ctk.CTkComboBox(
        search_frame,
        width=180,
        values=[
            "전체",
            "유치원",
            "초등학교",
            "중학교",
            "고등학교",
            "특수학교"
        ]
    )
    school_type.set("전체")
    school_type.grid(row=1, column=2, padx=10)

    # ==============================
    # 교육청
    # ==============================
    ctk.CTkLabel(search_frame, text="교육청").grid(row=0, column=3)

    office = ctk.CTkComboBox(
        search_frame,
        width=220,
        values=OFFICES["전체"]
    )
    office.set("전체")
    office.grid(row=1, column=3, padx=10)

    def change_region(choice):

        office.configure(values=OFFICES[choice])
        office.set(OFFICES[choice][0])

    region.configure(command=change_region)

    # ==============================
    # 사업 체크
    # ==============================
    option_frame = ctk.CTkFrame(popup)
    option_frame.pack(fill="x", padx=20, pady=10)

    ai_var = ctk.BooleanVar()
    digital_var = ctk.BooleanVar()
    space_var = ctk.BooleanVar()
    green_var = ctk.BooleanVar()

    ctk.CTkCheckBox(
        option_frame,
        text="AI중점학교",
        variable=ai_var
    ).pack(side="left", padx=15)

    ctk.CTkCheckBox(
        option_frame,
        text="디지털선도학교",
        variable=digital_var
    ).pack(side="left", padx=15)

    ctk.CTkCheckBox(
        option_frame,
        text="공간혁신학교",
        variable=space_var
    ).pack(side="left", padx=15)

    ctk.CTkCheckBox(
        option_frame,
        text="그린스마트학교",
        variable=green_var
    ).pack(side="left", padx=15)

    result_count = ctk.CTkLabel(
        popup,
        text="검색 결과 : 0건",
        font=("맑은 고딕", 14, "bold")
    )
    result_count.pack(anchor="w", padx=20)

    columns = (
        "학교명",
        "학교급",
        "교육청",
        "지역",
        "학생수",
        "학급수"
    )

    tree = ttk.Treeview(
        popup,
        columns=columns,
        show="headings",
        height=20
    )

    widths = [340, 120, 240, 150, 120, 120]

    for col, width in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor="center")

    tree.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=10
    )    
    def search():

        nonlocal current_rows

        tree.delete(*tree.get_children())

        rows = find_school(
            keyword.get(),
            region.get(),
            school_type.get(),
            office.get()
        )

        current_rows = []

        for row in rows:

            if ai_var.get() and row[7] == 0:
                continue

            if digital_var.get() and row[8] == 0:
                continue

            if space_var.get() and row[9] == 0:
                continue

            if green_var.get() and row[10] == 0:
                continue

            current_rows.append(row)

            tree.insert(
                "",
                "end",
                values=(
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    f"{row[11]:,}",
                    f"{row[12]:,}"
                )
            )

        result_count.configure(
            text=f"검색 결과 : {len(current_rows):,}건"
        )


    def reset():

        keyword.delete(0, "end")

        region.set("전체")

        school_type.set("전체")

        office.configure(values=OFFICES["전체"])
        office.set("전체")

        ai_var.set(False)
        digital_var.set(False)
        space_var.set(False)
        green_var.set(False)

        search()


    def open_detail(event):

        item = tree.focus()

        if not item:
            return

        idx = tree.index(item)

        if idx >= len(current_rows):
            return

        open_school_detail(
            popup,
            current_rows[idx]
        )


    tree.bind("<Double-1>", open_detail)


    button_frame = ctk.CTkFrame(
        popup,
        fg_color="transparent"
    )
    button_frame.pack(pady=10)


    ctk.CTkButton(
        button_frame,
        text="검색",
        width=150,
        command=search
    ).pack(side="left", padx=5)


    ctk.CTkButton(
        button_frame,
        text="초기화",
        width=150,
        command=reset
    ).pack(side="left", padx=5)


    ctk.CTkButton(
        button_frame,
        text="Excel 다운로드",
        width=180,
        command=lambda: export_school_excel(current_rows)
    ).pack(side="left", padx=5)


    search()