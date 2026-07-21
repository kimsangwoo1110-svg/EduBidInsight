"""Default Today Dashboard home screen."""

import customtkinter as ctk
from tkinter import messagebox, ttk

from services.dashboard_service import DashboardService


AUTO_REFRESH_MS = 5 * 60 * 1000


def build_today_dashboard(
    parent, dashboard_service=DashboardService, refresh_interval_ms=AUTO_REFRESH_MS
):
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.pack(fill="both", expand=True)

    header = ctk.CTkFrame(container)
    header.pack(fill="x", padx=12, pady=(12, 6))
    ctk.CTkLabel(
        header, text="Today Dashboard", font=("맑은 고딕", 26, "bold"), anchor="w"
    ).pack(side="left", padx=14, pady=12)
    status = ctk.CTkLabel(header, text="Ready", anchor="e")
    status.pack(side="right", padx=12)

    content = ctk.CTkScrollableFrame(container, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=8, pady=(2, 10))
    for column in range(2):
        content.grid_columnconfigure(column, weight=1, uniform="today-column")

    kpi_frame = ctk.CTkFrame(content, fg_color="transparent")
    kpi_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=4)
    kpi_keys = (
        ("opportunity_count", "Opportunity Count"),
        ("completed_this_week", "Completed This Week"),
        ("upcoming_visits", "Upcoming Visits"),
        ("average_opportunity_score", "Average Opportunity Score"),
        ("open_actions", "Open Actions"),
    )
    kpi_labels = {}
    for column, (key, title) in enumerate(kpi_keys):
        kpi_frame.grid_columnconfigure(column, weight=1, uniform="today-kpi")
        card = ctk.CTkFrame(kpi_frame)
        card.grid(row=0, column=column, padx=4, sticky="nsew")
        ctk.CTkLabel(card, text=title, text_color="gray", anchor="w").pack(
            fill="x", padx=12, pady=(11, 2)
        )
        label = ctk.CTkLabel(card, text="0", font=("맑은 고딕", 23, "bold"), anchor="w")
        label.pack(fill="x", padx=12, pady=(0, 11))
        kpi_labels[key] = label

    def table_panel(row, column, title, columns, height=7):
        panel = ctk.CTkFrame(content)
        panel.grid(row=row, column=column, padx=4, pady=5, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            panel, text=title, font=("맑은 고딕", 16, "bold"), anchor="w"
        ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")
        tree = ttk.Treeview(
            panel, columns=[item[0] for item in columns], show="headings", height=height
        )
        for key, heading, width in columns:
            tree.heading(key, text=heading)
            tree.column(key, width=width, anchor="w")
        tree.grid(row=1, column=0, padx=8, pady=(2, 9), sticky="nsew")
        return panel, tree

    _, priority_tree = table_panel(1, 0, "Priority Schools — Top 10", (
        ("school", "School", 150), ("score", "Score", 55),
        ("priority", "Priority", 85), ("recommendation", "Recommendation", 250),
    ))
    today_panel, today_tree = table_panel(1, 1, "Today's Actions", (
        ("school", "School", 115), ("action", "Action", 230),
        ("due", "Due Time", 90), ("status", "Status", 90),
    ))
    _, visits_tree = table_panel(2, 0, "Upcoming Visits", (
        ("school", "School", 130), ("visit", "Visit", 250), ("due", "Due", 95),
    ), height=5)
    _, overdue_tree = table_panel(2, 1, "Overdue Actions", (
        ("school", "School", 130), ("action", "Action", 245), ("due", "Due", 95),
    ), height=5)
    _, completed_tree = table_panel(3, 0, "Recently Completed", (
        ("school", "School", 130), ("action", "Action", 235),
        ("completed", "Completed", 105),
    ), height=5)
    _, activity_tree = table_panel(3, 1, "Recent Activity", (
        ("time", "Time", 130), ("type", "Type", 100),
        ("school", "School", 90), ("detail", "Detail", 190),
    ), height=5)
    _, alert_tree = table_panel(4, 0, "Alerts", (
        ("severity", "Severity", 75), ("type", "Type", 120),
        ("school", "School", 120), ("message", "Message", 220),
    ), height=6)
    opportunity_panel, opportunity_tree = table_panel(4, 1, "Opportunity Summary", (
        ("band", "Band", 160), ("count", "Schools", 90),
    ), height=6)

    ctk.CTkLabel(
        kpi_frame, text="Weekly KPI", font=("맑은 고딕", 14, "bold"), anchor="w"
    ).grid(row=1, column=0, columnspan=5, padx=5, pady=(7, 0), sticky="w")

    def school_name(snapshot, school_id):
        return snapshot.get("school_names", {}).get(school_id, school_id)

    def reset_tree(tree):
        tree.delete(*tree.get_children())

    def populate(snapshot):
        for key, label in kpi_labels.items():
            value = snapshot["weekly_kpi"][key]
            label.configure(text=f"{value:.1f}" if isinstance(value, float) else f"{value:,}")

        for tree in (
            priority_tree, today_tree, visits_tree, overdue_tree, completed_tree,
            activity_tree, alert_tree, opportunity_tree,
        ):
            reset_tree(tree)
        for item in snapshot["priority_schools"]:
            priority_tree.insert("", "end", values=(
                item.school_name, item.score, item.priority, item.recommendation,
            ))
        for action in snapshot["today_actions"]:
            today_tree.insert("", "end", iid=f"action-{action.action_id}", values=(
                school_name(snapshot, action.school_id), action.title,
                action.due_date or "All day", action.status,
            ))
        for action in snapshot["upcoming_visits"]:
            visits_tree.insert("", "end", values=(
                school_name(snapshot, action.school_id), action.title, action.due_date or "-",
            ))
        for action in snapshot["overdue_actions"]:
            overdue_tree.insert("", "end", values=(
                school_name(snapshot, action.school_id), action.title, action.due_date or "-",
            ))
        for action in snapshot["recently_completed"]:
            completed_tree.insert("", "end", values=(
                school_name(snapshot, action.school_id), action.title,
                action.completed_date or "-",
            ))
        for event in snapshot["recent_activity"]:
            activity_tree.insert("", "end", values=(
                str(event.get("timestamp") or "")[:16], event.get("activity_type", ""),
                school_name(snapshot, event.get("school_id", "")),
                event.get("description") or event.get("title", ""),
            ))
        for alert in snapshot["alerts"]:
            alert_tree.insert("", "end", values=(
                alert["severity"], alert["type"], alert["school_name"], alert["message"],
            ))
        summary = snapshot["opportunity_summary"]
        for label, key in (
            ("High Priority (70+)", "high_priority"),
            ("Qualified (50–69)", "qualified"),
            ("Monitor (<50)", "monitor"),
            ("Average Score", "average_score"),
            ("All Opportunities", "total"),
        ):
            opportunity_tree.insert("", "end", values=(label, summary[key]))
        status.configure(
            text=f"Updated {snapshot['generated_at'][11:19]} • {snapshot['elapsed_ms']:.0f} ms"
        )

    def refresh(force=False):
        status.configure(text="Refreshing…")
        container.update_idletasks()
        try:
            snapshot = (
                dashboard_service.refresh() if force
                else dashboard_service.get_dashboard()
            )
            populate(snapshot)
        except Exception as error:
            status.configure(text="Refresh failed")
            messagebox.showerror("Today Dashboard", str(error), parent=container.winfo_toplevel())

    def complete_selected():
        selection = today_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Complete action", "Select today's action first.",
                parent=container.winfo_toplevel(),
            )
            return
        action_id = int(selection[0].split("-", 1)[1])
        snapshot = dashboard_service.complete_action(action_id)
        populate(snapshot)

    ctk.CTkButton(
        today_panel, text="Complete Selected", width=140, command=complete_selected
    ).grid(row=2, column=0, padx=8, pady=(0, 9), sticky="e")
    ctk.CTkButton(
        header, text="Refresh", width=100, command=lambda: refresh(True)
    ).pack(side="right", padx=6, pady=9)

    def auto_refresh():
        if container.winfo_exists():
            refresh(False)
            container.after(refresh_interval_ms, auto_refresh)

    refresh(False)
    container.after(refresh_interval_ms, auto_refresh)
    return container


def open_today_dashboard(parent):
    window = ctk.CTkToplevel(parent)
    window.title("Today Dashboard")
    window.geometry("1400x900")
    window.minsize(1050, 700)
    window.transient(parent)
    build_today_dashboard(window)
    return window
