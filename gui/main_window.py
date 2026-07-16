import customtkinter as ctk
from tkinter import filedialog, messagebox

from gui.school_window import open_school_window
from services.import_school import import_school_data

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def run():

    app = ctk.CTk()
    app.title("EduBid Insight")
    app.geometry("1000x700")

    title = ctk.CTkLabel(
        app,
        text="EduBid Insight",
        font=("맑은 고딕", 32, "bold")
    )
    title.pack(pady=(40, 10))

    subtitle = ctk.CTkLabel(
        app,
        text="학교 예정사업 통합 검색 플랫폼",
        font=("맑은 고딕", 15)
    )
    subtitle.pack(pady=(0, 30))

    status = ctk.CTkLabel(
        app,
        text="학교 데이터를 가져오세요."
    )
    status.pack(pady=10)

    def import_excel():

        file_path = filedialog.askopenfilename(
            title="학교 데이터 선택",
            filetypes=[("Excel 파일", "*.xlsx")]
        )

        if not file_path:
            return

        try:

            success, fail = import_school_data(file_path)

            status.configure(
                text=f"등록 완료 : {success:,}개 (실패 {fail}개)"
            )

            messagebox.showinfo(
                "가져오기 완료",
                f"""성공 : {success:,}개

실패 : {fail:,}개"""
            )

        except Exception as e:

            messagebox.showerror(
                "오류",
                str(e)
            )

    import_btn = ctk.CTkButton(
        app,
        text="학교 데이터 가져오기",
        width=320,
        height=45,
        command=import_excel
    )
    import_btn.pack(pady=10)

    school_btn = ctk.CTkButton(
        app,
        text="학교 검색",
        width=320,
        height=45,
        command=lambda: open_school_window(app)
    )
    school_btn.pack(pady=10)

    office_btn = ctk.CTkButton(
        app,
        text="교육청 검색",
        width=320,
        height=45,
        command=lambda: print("교육청 검색")
    )
    office_btn.pack(pady=10)

    g2b_btn = ctk.CTkButton(
        app,
        text="나라장터 검색",
        width=320,
        height=45,
        command=lambda: print("나라장터 검색")
    )
    g2b_btn.pack(pady=10)

    ai_btn = ctk.CTkButton(
        app,
        text="AI 검색",
        width=320,
        height=45,
        command=lambda: print("AI 검색")
    )
    ai_btn.pack(pady=10)

    footer = ctk.CTkLabel(
        app,
        text="EduBid Insight v0.1    |    Developer : 김상우",
        font=("맑은 고딕", 11),
        text_color="gray"
    )
    footer.pack(side="bottom", pady=10)

    app.mainloop()