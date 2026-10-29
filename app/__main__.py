"""Run the local TAIEX neural-network learning lab."""

import uvicorn
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(ROOT / "app"), str(ROOT / "web")],
        reload_excludes=["*.csv", "*.json", "*.md", "*.tmp"],
    )
