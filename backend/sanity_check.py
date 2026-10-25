import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.analysis import run_sanity_check

if __name__ == "__main__":
    run_sanity_check()
