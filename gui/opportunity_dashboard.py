"""Global Opportunity Engine ranking dashboard."""

import customtkinter as ctk
from tkinter import ttk

from services.opportunity_engine import OpportunityEngine
from gui.ui_theme import own_child_window


def opportunity_table_values(result):
    """Map an OpportunityResult to stable dashboard values."""
    return (
        result.school_name,
        result.school_id,
        result.score,
        result.priority,
        result.confidence,
        result.recommendation,
        result.next_action,
    )


def open_opportunity_dashboard(parent):
    """Open Top 20, highest-score, and recently-increased opportunity views."""
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("Opportunity Engine Dashboard")
    window.geometry("1320x820")
    window.minsize(980, 650)

    header = ctk.CTkFrame(window)
    header.pack(fill="x", padx=16, pady=(16, 8))
    ctk.CTkLabel(
        header, text="Top 20 Opportunity Schools", font=("맑은 고딕", 24, "bold")
    ).pack(side="left", padx=14, pady=12)
    status = ctk.CTkLabel(header, text="Ready")
    status.pack(side="right", padx=12)

    content = ctk.CTkScrollableFrame(window, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=12, pady=8)

    highest_frame = ctk.CTkFrame(content)
    highest_frame.pack(fill="x", pady=6)
    ctk.CTkLabel(
        highest_frame, text="Highest Scores", font=("맑은 고딕", 17, "bold")
    ).grid(row=0, column=0, columnspan=5, padx=10, pady=(10, 4), sticky="w")
    highest_labels = []
    for index in range(5):
        highest_frame.grid_columnconfigure(index, weight=1, uniform="highest")
        label = ctk.CTkLabel(highest_frame, text="-", font=("맑은 고딕", 14, "bold"))
        label.grid(row=1, column=index, padx=5, pady=(4, 12), sticky="ew")
        highest_labels.append(label)

    columns = ("school", "code", "score", "priority", "confidence", "recommendation", "action")
    top_tree = ttk.Treeview(content, columns=columns, show="headings", height=16)
    for column, heading, width in (
        ("school", "School", 180), ("code", "Code", 100), ("score", "Score", 70),
        ("priority", "Priority", 100), ("confidence", "Confidence", 90),
        ("recommendation", "Recommendation", 300), ("action", "Next Action", 180),
    ):
        top_tree.heading(column, text=heading)
        top_tree.column(column, width=width, anchor="center")
    top_tree.pack(fill="x", pady=6)

    increased_frame = ctk.CTkFrame(content)
    increased_frame.pack(fill="x", pady=8)
    ctk.CTkLabel(
        increased_frame, text="Recently Increased Scores", font=("맑은 고딕", 17, "bold")
    ).pack(anchor="w", padx=10, pady=(10, 4))
    increased_tree = ttk.Treeview(
        increased_frame,
        columns=("school", "code", "score", "increase"),
        show="headings",
        height=6,
    )
    for column, heading, width in (
        ("school", "School", 260), ("code", "Code", 130),
        ("score", "Current Score", 120), ("increase", "Increase", 100),
    ):
        increased_tree.heading(column, text=heading)
        increased_tree.column(column, width=width, anchor="center")
    increased_tree.pack(fill="x", padx=8, pady=(2, 10))

    def refresh():
        status.configure(text="Calculating...")
        window.update_idletasks()
        dashboard = OpportunityEngine.dashboard(limit=20, persist=True)
        top_tree.delete(*top_tree.get_children())
        for index, result in enumerate(dashboard["top_opportunities"]):
            top_tree.insert("", "end", iid=f"opportunity-{index}", values=opportunity_table_values(result))
        for label, result in zip(highest_labels, dashboard["highest_scores"]):
            label.configure(text=f"{result.school_name}\n{result.score} · {result.priority}")
        for label in highest_labels[len(dashboard["highest_scores"]):]:
            label.configure(text="-")
        increased_tree.delete(*increased_tree.get_children())
        for index, item in enumerate(dashboard["recently_increased_scores"]):
            increased_tree.insert(
                "", "end", iid=f"increase-{index}",
                values=(item["school_name"], item["school_id"], item["score"], f"+{item['increase']}"),
            )
        status.configure(text=f"Updated · {len(dashboard['top_opportunities'])} schools")

    ctk.CTkButton(header, text="Refresh", width=100, command=refresh).pack(
        side="right", padx=8, pady=9
    )
    refresh()
    return window
