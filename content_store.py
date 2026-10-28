"""Load editable JSON game content from the repository's data/ directory."""
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def load_json(filename):
    """Load one version-controlled content file and fail clearly if it is invalid."""
    path = DATA_DIR / filename
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Required game data file is missing: {path}. "
            "Restore the file from the repository's data/ directory."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
