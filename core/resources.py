"""Runtime resource lookup and Windows application identity helpers."""

import ctypes
import os
import shutil
import sys
from pathlib import Path


APP_USER_MODEL_ID = "KimSangwoo.EduBidInsight.Personal.1.0"
TCL_RUNTIME_VERSION = "8.6.15"


def resource_path(relative_path):
    """Resolve a bundled PyInstaller resource or a source-tree asset."""
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return bundle_root / relative_path


def configure_windows_identity():
    """Set the taskbar identity used by packaged Windows builds."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass


def configure_packaged_tk():
    """Use a stable Tcl/Tk cache for PyInstaller one-file Windows builds."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    bundle_root = Path(getattr(sys, "_MEIPASS", ""))
    tcl_source = bundle_root / "_tcl_data"
    tk_source = bundle_root / "_tk_data"
    if not tcl_source.is_dir() or not tk_source.is_dir():
        return
    local_root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    runtime_root = local_root / "EduBidInsight" / "runtime" / f"tcltk-{TCL_RUNTIME_VERSION}"
    marker = runtime_root / ".complete"
    if not marker.is_file():
        runtime_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(tcl_source, runtime_root / "tcl8.6", dirs_exist_ok=True)
        shutil.copytree(tk_source, runtime_root / "tk8.6", dirs_exist_ok=True)
        marker.write_text(TCL_RUNTIME_VERSION, encoding="ascii")
    os.environ["TCL_LIBRARY"] = str(runtime_root / "tcl8.6")
    os.environ["TK_LIBRARY"] = str(runtime_root / "tk8.6")


def apply_window_icon(window):
    """Apply the shared application icon after CustomTkinter initializes."""
    icon_path = resource_path("assets/edubid.ico")
    if not icon_path.is_file():
        return

    def apply():
        if window.winfo_exists():
            try:
                window.iconbitmap(str(icon_path))
            except Exception:
                pass

    apply()
    window.after(250, apply)
