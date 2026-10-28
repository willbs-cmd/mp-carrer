"""Load editable JSON game content from the repository's data/ directory."""
import json
from functools import lru_cache
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
DATA_DIR = REPO_DIR / "data"


def _content_path(filename):
    """Resolve content from the repository root or the optional data/ folder."""
    root_path = REPO_DIR / filename
    data_path = DATA_DIR / filename
    if root_path.is_file():
        return root_path
    if data_path.is_file():
        return data_path
    return root_path


@lru_cache(maxsize=None)
def load_json(filename):
    """Load one version-controlled content file and fail clearly if it is invalid."""
    path = _content_path(filename)
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
