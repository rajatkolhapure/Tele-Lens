import sys
import os

# Ensure the bundle directory (or receiver source directory) is first in sys.path
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from telelens.ui.app import main

if __name__ == "__main__":
    main()
