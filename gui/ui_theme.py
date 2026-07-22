"""Shared presentation tokens and widget styling for EduBid Insight."""

from tkinter import ttk

import customtkinter as ctk


FONT_FAMILY = "Segoe UI"

# CustomTkinter accepts (light, dark) color tuples.  The palette intentionally
# stays close to Windows 11 neutrals with low-saturation semantic accents.
COLORS = {
    "window": ("#F5F7FA", "#111827"),
    "sidebar": ("#EEF2F7", "#172033"),
    "surface": ("#FFFFFF", "#1F2937"),
    "surface_alt": ("#F8FAFC", "#253247"),
    "border": ("#DDE3EA", "#344258"),
    "text": ("#182230", "#F3F6FA"),
    "muted": ("#667085", "#AAB5C5"),
    "blue": ("#4F78A6", "#6F9ACA"),
    "blue_hover": ("#426A95", "#82A8D2"),
    "blue_tint": ("#EAF1F8", "#243A54"),
    "green": ("#5E8F78", "#78AE94"),
    "green_tint": ("#EDF5F1", "#263E35"),
    "orange": ("#B08355", "#CEA373"),
    "orange_tint": ("#F8F1E9", "#483829"),
    "red": ("#A96B6B", "#C88989"),
    "red_tint": ("#F8EEEE", "#472F34"),
    "gray_tint": ("#F0F2F5", "#303A49"),
}

FONTS = {
    "display": (FONT_FAMILY, 30, "bold"),
    "title": (FONT_FAMILY, 24, "bold"),
    "section": (FONT_FAMILY, 18, "bold"),
    "body": (FONT_FAMILY, 14),
    "body_bold": (FONT_FAMILY, 14, "bold"),
    "caption": (FONT_FAMILY, 12),
    "kpi": (FONT_FAMILY, 32, "bold"),
}


def card(parent, **kwargs):
    """Create a standard commercial-style surface card."""
    options = {
        "fg_color": COLORS["surface"],
        "border_color": COLORS["border"],
        "border_width": 1,
        "corner_radius": 10,
    }
    options.update(kwargs)
    return ctk.CTkFrame(parent, **options)


def primary_button(parent, **kwargs):
    options = {
        "height": 36,
        "corner_radius": 7,
        "fg_color": COLORS["blue"],
        "hover_color": COLORS["blue_hover"],
        "font": FONTS["body_bold"],
    }
    options.update(kwargs)
    return ctk.CTkButton(parent, **options)


def secondary_button(parent, **kwargs):
    options = {
        "height": 36,
        "corner_radius": 7,
        "fg_color": COLORS["surface_alt"],
        "hover_color": COLORS["blue_tint"],
        "border_color": COLORS["border"],
        "border_width": 1,
        "text_color": COLORS["text"],
        "font": FONTS["body_bold"],
    }
    options.update(kwargs)
    return ctk.CTkButton(parent, **options)


def own_child_window(window, parent):
    """Give a Toplevel proper ownership and reliably foreground it on Windows."""
    window.transient(parent)

    def bring_forward():
        if not window.winfo_exists():
            return
        window.lift()
        window.focus_force()
        # A short topmost pulse handles Windows focus timing without leaving a
        # tool window permanently above unrelated applications.
        try:
            window.attributes("-topmost", True)
            window.after(120, lambda: window.winfo_exists() and window.attributes("-topmost", False))
        except Exception:
            pass

    window.after_idle(bring_forward)
    return window


def create_empty_state(parent, message):
    """Create a reusable bilingual empty-state label for a table panel."""
    return ctk.CTkLabel(
        parent,
        text=message,
        font=FONTS["body"],
        text_color=COLORS["muted"],
        justify="center",
    )


def update_empty_state(tree, label):
    """Show an empty-state overlay only while a Treeview has no records."""
    if tree.get_children(""):
        label.place_forget()
    else:
        label.place(in_=tree, relx=0.5, rely=0.5, anchor="center")
        label.lift()


def configure_ttk_styles(root):
    """Apply readable Windows table styling application-wide."""
    dark = ctk.get_appearance_mode().lower() == "dark"
    surface = "#1F2937" if dark else "#FFFFFF"
    alternate = "#253247" if dark else "#F7F9FC"
    text = "#F3F6FA" if dark else "#253142"
    header = "#303E52" if dark else "#E9EEF4"
    header_active = "#3B4C63" if dark else "#DDE5EE"
    selected = "#355777" if dark else "#D7E7F6"
    selected_text = "#FFFFFF" if dark else "#18324C"
    border = "#344258" if dark else "#D8E0E8"

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Treeview",
        background=surface,
        fieldbackground=surface,
        foreground=text,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        rowheight=34,
        relief="flat",
        font=(FONT_FAMILY, 11),
    )
    style.configure(
        "Treeview.Heading",
        background=header,
        foreground=text,
        bordercolor=border,
        relief="flat",
        padding=(9, 8),
        font=(FONT_FAMILY, 11, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", selected)],
        foreground=[("selected", selected_text)],
    )
    style.map("Treeview.Heading", background=[("active", header_active)])
    style.configure("Vertical.TScrollbar", arrowsize=14)
    root.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, 10))
    # Feature windows create their tables lazily. Styling at map-time keeps all
    # existing screens consistent without coupling presentation to services.
    def finish_treeview(event):
        try:
            prepare_treeview(event.widget)
            stripe_treeview(event.widget)
        except Exception:
            # A widget may be destroyed while a queued map event is delivered.
            return

    root.bind_class("Treeview", "<Map>", finish_treeview, add="+")
    return {"surface": surface, "alternate": alternate}


def prepare_treeview(tree):
    """Make a Treeview responsive and configure zebra-row tags."""
    dark = ctk.get_appearance_mode().lower() == "dark"
    tree.tag_configure("evenrow", background="#FFFFFF" if not dark else "#1F2937")
    tree.tag_configure("oddrow", background="#F7F9FC" if not dark else "#253247")
    for column in tree["columns"]:
        configured = tree.column(column)
        width = max(int(configured.get("width", 80)), 70)
        tree.column(column, minwidth=min(width, 110))
    return tree


def stripe_treeview(tree):
    """Apply alternating backgrounds without changing displayed data."""
    for index, item in enumerate(tree.get_children("")):
        existing = tuple(tag for tag in tree.item(item, "tags") if tag not in {"evenrow", "oddrow"})
        tree.item(item, tags=existing + (("evenrow" if index % 2 == 0 else "oddrow"),))
