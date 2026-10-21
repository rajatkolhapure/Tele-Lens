import sys
import os
import traceback

# Ensure the bundle directory (or receiver source directory) is first in sys.path
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

def _log_crash_and_notify(exc: Exception):
    err_msg = traceback.format_exc()
    log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TeleLens")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "startup_crash.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n--- Startup Crash ---\n{err_msg}\n")
    except Exception:
        pass

    # Output to stderr if available
    try:
        if sys.stderr:
            sys.stderr.write(f"\n[TeleLens Startup Error] {exc}\n{err_msg}\n")
    except Exception:
        pass

    # Show native Windows modal dialog for packaged frozen executable (.exe)
    if sys.platform == "win32" and getattr(sys, 'frozen', False) and not os.environ.get("CI"):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"TeleLens encountered an error during startup:\n\n{exc}\n\nFull crash log saved to:\n{log_file}",
                "TeleLens Startup Error",
                0x10  # MB_ICONERROR
            )
        except Exception:
            pass

if __name__ == "__main__":
    try:
        from telelens.ui.app import main
        main()
    except Exception as e:
        _log_crash_and_notify(e)
        sys.exit(1)
