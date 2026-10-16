"""logbot: a small production-log analyst (Apache + Java logs). Shared by the notebooks and the FastAPI app."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
LOGS = DATA / 'logs'
KB = DATA / 'kb'
INDEX = ROOT / 'index'
