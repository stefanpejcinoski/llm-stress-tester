"""Entry point for the PyInstaller frozen bundle.

Launches the Streamlit app via subprocess so Streamlit's own CLI
bootstrapping (click, file-watcher threads, asset resolution) runs
correctly inside the frozen binary.

Can also be run directly in dev mode:
    python launcher.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _app_path() -> Path:
    """Resolve the path to app.py in both frozen and dev contexts."""
    if getattr(sys, "frozen", False):
        # PyInstaller extracts the bundle to sys._MEIPASS at runtime.
        # app.py is bundled under llm_stress_tester/app.py inside that dir.
        return Path(sys._MEIPASS) / "llm_stress_tester" / "app.py"  # noqa: SLF001
    # Dev mode: resolve relative to this launcher file.
    return Path(__file__).parent / "src" / "llm_stress_tester" / "app.py"


def main() -> None:
    """Launch Streamlit with the bundled app."""
    app = _app_path()
    if not app.exists():
        print(f"ERROR: app.py not found at {app}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app),
            "--server.headless",
            "true",
        ],
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
