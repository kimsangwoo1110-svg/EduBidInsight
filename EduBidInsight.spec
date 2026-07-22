# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files


ROOT = Path(SPECPATH)
datas = collect_data_files("customtkinter")
tkdnd_datas, tkdnd_binaries, tkdnd_hiddenimports = collect_all("tkinterdnd2")
datas += tkdnd_datas
datas += [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "packaging" / "default_config" / "app_settings.json"), "config"),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "RELEASE.md"), "."),
    (str(ROOT / "CHANGELOG.md"), "."),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "requirements.txt"), "."),
]

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=tkdnd_binaries,
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "openpyxl",
        "requests",
        "sqlite3",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
        *tkdnd_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pdfplumber", "pypdf", "reportlab"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EduBidInsight",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ROOT / "assets" / "edubid.ico")],
    version=str(ROOT / "packaging" / "version_info.txt"),
    uac_admin=False,
)
