"""Start only Project HQ, on loopback, with the current Python environment."""
import os
from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    raise SystemExit(subprocess.call([
        sys.executable, "-B", "-m", "streamlit", "run", str(folder / "app.py"),
        "--server.address=127.0.0.1", "--server.port=8510",
        "--server.headless=true", "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false", "--server.enableStaticServing=false",
    ], cwd=folder, env=env))
