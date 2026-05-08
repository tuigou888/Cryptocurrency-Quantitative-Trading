import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

for d in [DATA_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)
