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



@lru_cache(maxsize=1)
def load_press_stories():
    """Return editable press-room scenarios used by the MP career game.

    The risk values are fictional game mechanics. The named podcasts are possible
    in-game outlets, not claims that real programmes received or published leaks.
    """
    return [
        {"title": "Rival minister's transport timetable collapses",
         "detail": "A private briefing suggests the department underestimated delays.",
         "boost": 5, "risk": 0.28},
        {"title": "Internal polling shows a wobble in key marginals",
         "detail": "A party memo hints that several target seats are moving.",
         "boost": 6, "risk": 0.36},
        {"title": "A policy launch was rewritten overnight",
         "detail": "Colleagues are arguing over who watered down a flagship promise.",
         "boost": 4, "risk": 0.22},
    ]
