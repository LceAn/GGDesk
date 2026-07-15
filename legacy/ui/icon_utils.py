import os
import re
import ctypes

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QFileIconProvider, QStyle

try:
    import win32com.client
    import win32gui
except Exception:  # pragma: no cover - pywin32 is Windows-only.
    win32com = None
    win32gui = None


_PROVIDER = QFileIconProvider()
_CACHE = {}


def is_shell_app_id(value):
    if not value:
        return False
    clean = value.strip()
    if not clean or os.path.exists(clean) or "://" in clean:
        return False
    if re.match(r"^[a-zA-Z]:[\\/]", clean) or clean.startswith("\\\\"):
        return False
    return ":" not in clean


def shortcut_icon(exe_path="", lnk_path="", source_type="", fallback=None):
    key = (exe_path or "", lnk_path or "", source_type or "")
    if key in _CACHE:
        return _CACHE[key]

    icon = QIcon()
    if source_type == "uwp" and is_shell_app_id(exe_path):
        icon = _icon_from_shell_app_id(exe_path)
    if icon.isNull() and lnk_path and os.path.exists(lnk_path):
        icon = _icon_from_shortcut(lnk_path)
    if icon.isNull() and exe_path and os.path.exists(exe_path):
        icon = _icon_from_file(exe_path)
    if icon.isNull() and exe_path and os.path.exists(exe_path):
        icon = _PROVIDER.icon(QFileInfo(exe_path))
    if icon.isNull() and lnk_path and os.path.exists(lnk_path):
        icon = _PROVIDER.icon(QFileInfo(lnk_path))
    if icon.isNull():
        icon = fallback or QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)

    _CACHE[key] = icon
    return icon


def _icon_from_shortcut(path):
    if not win32com:
        return QIcon()
    try:
        shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortCut(path)
        icon_path, icon_index = _parse_icon_location(shortcut.IconLocation)
        if icon_path and os.path.exists(icon_path):
            icon = _icon_from_file(icon_path, icon_index)
            if not icon.isNull():
                return icon
        target = shortcut.TargetPath
        if target and os.path.exists(target):
            return _icon_from_file(target)
    except Exception:
        pass
    return QIcon()


def _parse_icon_location(value):
    if not value:
        return "", 0
    raw = value.strip().strip('"')
    match = re.match(r"^(.*?),(-?\d+)$", raw)
    if match:
        return match.group(1).strip().strip('"'), int(match.group(2))
    return raw, 0


def _icon_from_file(path, index=0):
    if not win32gui or not path or not os.path.exists(path):
        return QIcon()
    try:
        large, small = win32gui.ExtractIconEx(path, index)
        handles = large or small
        if not handles:
            return QIcon()
        hicon = handles[0]
        image = QImage.fromHICON(hicon)
        icon = QIcon(QPixmap.fromImage(image)) if not image.isNull() else QIcon()
        for handle in large + small:
            win32gui.DestroyIcon(handle)
        return icon
    except Exception:
        return QIcon()


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


def _make_guid(text):
    import uuid

    value = uuid.UUID(text)
    data4 = (ctypes.c_ubyte * 8).from_buffer_copy(value.bytes[8:])
    return _GUID(value.time_low, value.time_mid, value.time_hi_version, data4)


def _icon_from_shell_app_id(app_id, size=96):
    try:
        ole32 = ctypes.OleDLL("ole32")
        shell32 = ctypes.OleDLL("shell32")
        gdi32 = ctypes.WinDLL("gdi32")
        ole32.CoInitialize(None)

        iid = _make_guid("bcc18b79-ba16-442f-80c4-8a59c30c463b")
        factory = ctypes.c_void_p()
        parsing_name = f"shell:AppsFolder\\{app_id}"
        hr = shell32.SHCreateItemFromParsingName(
            ctypes.c_wchar_p(parsing_name),
            None,
            ctypes.byref(iid),
            ctypes.byref(factory)
        )
        if hr != 0 or not factory.value:
            return QIcon()

        vtbl = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        get_image = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            _SIZE,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p)
        )(vtbl[3])
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])

        hbitmap = ctypes.c_void_p()
        # SIIGBF_BIGGERSIZEOK | SIIGBF_ICONONLY
        hr = get_image(factory, _SIZE(size, size), 0x1 | 0x4, ctypes.byref(hbitmap))
        release(factory)
        if hr != 0 or not hbitmap.value:
            return QIcon()

        image = QImage.fromHBITMAP(hbitmap.value)
        gdi32.DeleteObject(hbitmap)
        if image.isNull():
            return QIcon()
        return QIcon(QPixmap.fromImage(image))
    except Exception:
        return QIcon()
