"""CRM Action Center dashboard and searchable workflow list."""

import customtkinter as ctk
from tkinter import messagebox, ttk

from services.action_center import (
    ACTION_PRIORITIES, ACTION_STATUSES, ACTION_TYPES, ActionCenterService,
)
from gui.ui_theme import create_empty_state, own_child_window, update_empty_state


def open_action_center(parent, action_service=ActionCenterService):
    window = ctk.CTkToplevel(parent)
    own_child_window(window, parent)
    window.title("CRM Action Center")
    window.geometry("1280x780")
    window.minsize(960, 620)

    content = ctk.CTkFrame(window, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=14, pady=14)
    ctk.CTkLabel(
        content, text="CRM Action Center", font=("맑은 고딕", 26, "bold"), anchor="w"
    ).pack(fill="x", pady=(0, 10))

    cards = ctk.CTkFrame(content, fg_color="transparent")
    cards.pack(fill="x", pady=5)
    card_labels = {}
    for column, (key, title) in enumerate((
        ("today_actions", "Today's Actions"),
        ("overdue_actions", "Overdue Actions"),
        ("completed_this_week", "Completed This Week"),
        ("upcoming_visits", "Upcoming Visits"),
    )):
        cards.grid_columnconfigure(column, weight=1, uniform="action-card")
        card = ctk.CTkFrame(cards)
        card.grid(row=0, column=column, padx=5, sticky="nsew")
        ctk.CTkLabel(card, text=title, anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        value = ctk.CTkLabel(card, text="0", font=("맑은 고딕", 25, "bold"), anchor="w")
        value.pack(fill="x", padx=14, pady=(0, 12))
        card_labels[key] = value

    filters = ctk.CTkFrame(content)
    filters.pack(fill="x", pady=10)
    status_var = ctk.StringVar(value="All")
    priority_var = ctk.StringVar(value="All")
    type_var = ctk.StringVar(value="All")
    school_var = ctk.StringVar()
    due_var = ctk.StringVar()

    def add_filter(label, widget, column):
        ctk.CTkLabel(filters, text=label).grid(row=0, column=column, padx=(10, 4), pady=10)
        widget.grid(row=0, column=column + 1, padx=(0, 8), pady=10, sticky="ew")

    add_filter("Status", ctk.CTkOptionMenu(filters, variable=status_var, values=["All", *ACTION_STATUSES]), 0)
    add_filter("Priority", ctk.CTkOptionMenu(filters, variable=priority_var, values=["All", *ACTION_PRIORITIES]), 2)
    add_filter("School", ctk.CTkEntry(filters, textvariable=school_var, width=130), 4)
    add_filter("Type", ctk.CTkOptionMenu(filters, variable=type_var, values=["All", *ACTION_TYPES]), 6)
    add_filter("Due date", ctk.CTkEntry(filters, textvariable=due_var, placeholder_text="YYYY-MM-DD", width=120), 8)

    table_frame = ctk.CTkFrame(content)
    table_frame.pack(fill="both", expand=True)
    columns = ("id", "school", "type", "title", "status", "priority", "due", "completed")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
    headings = ("ID", "School", "Type", "Title", "Status", "Priority", "Due", "Completed")
    widths = (55, 105, 105, 320, 100, 85, 105, 105)
    for key, title, width in zip(columns, headings, widths):
        tree.heading(key, text=title)
        tree.column(key, width=width, anchor="w")
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
    empty_state = create_empty_state(
        table_frame,
        "✓  표시할 CRM 액션이 없습니다.\nNo CRM actions match the current filters.",
    )

    def selected_id():
        selection = tree.selection()
        return int(tree.item(selection[0], "values")[0]) if selection else None

    def refresh():
        summary = action_service.dashboard_summary()
        for key, label in card_labels.items():
            label.configure(text=f"{summary[key]:,}")
        for item in tree.get_children():
            tree.delete(item)
        try:
            actions = action_service.search(
                status="" if status_var.get() == "All" else status_var.get(),
                priority="" if priority_var.get() == "All" else priority_var.get(),
                school=school_var.get(),
                action_type="" if type_var.get() == "All" else type_var.get(),
                due_date=due_var.get() or None,
            )
        except ValueError as error:
            messagebox.showerror("Invalid filter", str(error), parent=window)
            return
        for action in actions:
            tree.insert("", "end", values=(
                action.action_id, action.school_id, action.action_type, action.title,
                action.status, action.priority, action.due_date or "",
                action.completed_date or "",
            ))
        update_empty_state(tree, empty_state)

    def change_status(status):
        action_id = selected_id()
        if action_id is None:
            messagebox.showinfo("Select action", "Select an action first.", parent=window)
            return
        action_service.update_status(action_id, status)
        refresh()

    buttons = ctk.CTkFrame(content, fg_color="transparent")
    buttons.pack(fill="x", pady=(10, 0))
    ctk.CTkButton(buttons, text="Search", width=100, command=refresh).pack(side="left", padx=4)
    ctk.CTkButton(buttons, text="In Progress", width=120, command=lambda: change_status("In Progress")).pack(side="left", padx=4)
    ctk.CTkButton(buttons, text="Complete", width=100, command=lambda: change_status("Completed")).pack(side="left", padx=4)
    ctk.CTkButton(buttons, text="Cancel", width=100, fg_color="#6B7280", command=lambda: change_status("Cancelled")).pack(side="left", padx=4)

    refresh()
    return window
