"""Entry point for the Threads Worker desktop app."""

import sys

# Ensure the repo root is on sys.path when running standalone
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from worker_app.gui import WorkerApp


def main():
    app = WorkerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
