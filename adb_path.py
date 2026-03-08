"""
Utility module to resolve the path to bundled ADB and images.
Works both when running from source and from a PyInstaller bundle.
"""
import sys
import os


def get_base_path():
    """Get the base path for bundled resources (images, minitouch, adb)."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        return sys._MEIPASS
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))


def get_adb_path():
    """Return the full path to the bundled adb.exe."""
    base = get_base_path()
    adb_exe = os.path.join(base, "adb", "adb.exe")
    if os.path.exists(adb_exe):
        return adb_exe
    # Fallback to system adb
    return "adb"


def get_images_dir():
    """Return the full path to the bundled images directory."""
    return os.path.join(get_base_path(), "images")


def get_minitouch_path():
    """Return the full path to the bundled minitouch binary."""
    return os.path.join(get_base_path(), "minitouch")


# Subprocess creation flag to hide console windows on Windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0
