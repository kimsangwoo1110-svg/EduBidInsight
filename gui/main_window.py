import customtkinter as ctk

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
    subtitle.pack(pady=(0, 40))

    buttons = [
        "학교 검색",
        "교육청 검색",
        "나라장터 검색",
        "AI 검색"
    ]

    for text in buttons:
        btn = ctk.CTkButton(
            app,
            text=text,
            width=320,
            height=50,
            font=("맑은 고딕", 16)
        )
        btn.pack(pady=10)

    status = ctk.CTkLabel(
        app,
        text="Status : Ready"
    )
    status.pack(side="bottom", pady=20)

    app.mainloop()