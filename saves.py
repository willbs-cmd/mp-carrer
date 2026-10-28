"""Save-file helpers for the MP Career game.

Pure Python (no Streamlit) so the format can be unit-tested. A save is a JSON
document wrapping the profile dict; ``parse_save`` validates it and upgrades
older saves so they keep working as the game grows.
"""
import json
import re

SAVE_SCHEMA_VERSION = 2
GAME_MODE = "mp_career"
DEFAULT_SEED = 32458
MAX_SAVE_BYTES = 2_000_000


class SaveError(ValueError):
    """Raised when an uploaded save cannot be used."""


def build_save(profile, seed=DEFAULT_SEED, party=None):
    """Return the JSON text for a downloadable save file."""
    payload = {
        "schema_version": SAVE_SCHEMA_VERSION,
        "game_mode": GAME_MODE,
        "seed": int(seed),
        "party": party or profile.get("party", "Labour"),
        "profile": profile,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_filename(profile):
    """A safe download name such as ``mp_career_droitwich_and_evesham.json``."""
    seat = str(profile.get("constituency", "westminster")).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", seat).strip("_") or "westminster"
    return f"mp_career_{slug}.json"


def parse_save(raw, roles, constituencies, attributes):
    """Validate raw upload bytes/text and return ``(profile, seed)``.

    ``roles``, ``constituencies`` and ``attributes`` come from the game data so
    this module has no dependency on ``career.py``.
    """
    if isinstance(raw, bytes):
        if len(raw) > MAX_SAVE_BYTES:
            raise SaveError("That file is too large to be an MP Career save.")
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SaveError("The file is not valid UTF-8 text.") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SaveError(f"The file is not valid JSON ({exc.msg}).") from exc
    if not isinstance(parsed, dict) or parsed.get("game_mode") != GAME_MODE:
        raise SaveError("This is not an MP Career Mode save.")
    version = parsed.get("schema_version", 1)
    if not isinstance(version, int) or version > SAVE_SCHEMA_VERSION:
        raise SaveError("This save was made by a newer version of the game.")
    profile = parsed.get("profile")
    if not isinstance(profile, dict):
        raise SaveError("The save has no career profile.")
    if profile.get("role") not in roles:
        raise SaveError("The save contains an unknown political role.")
    if profile.get("constituency") not in constituencies:
        raise SaveError("The save does not contain a recognised 2024 Westminster constituency.")
    required = set(attributes) - {"campaign_readiness"}
    stats = profile.get("stats")
    if not isinstance(stats, dict) or not required.issubset(stats):
        raise SaveError("The save is missing required career attributes.")
    for key in attributes:
        try:
            stats[key] = max(0, min(100, int(stats.get(key, 30))))
        except (TypeError, ValueError) as exc:
            raise SaveError(f"The save has an invalid value for {key}.") from exc
    profile = migrate_profile(profile, version)
    try:
        seed = int(parsed.get("seed", DEFAULT_SEED))
    except (TypeError, ValueError):
        seed = DEFAULT_SEED
    return profile, seed


def migrate_profile(profile, from_version):
    """Upgrade an older profile in place to the current schema."""
    if from_version < 2:
        profile.setdefault("difficulty", "standard")
        profile.setdefault("stat_history", [])
        profile.setdefault("achievements", [])
    return profile
