"""Career achievements for the MP Career game.

Each achievement is a small predicate over the profile dict. Earned
achievements are stored by id in ``profile["achievements"]`` and are permanent,
so predicates only need to be true at the moment they are checked.

Pure Python (no Streamlit) so it can be unit-tested directly.
"""

GOVERNMENT_RANKED = {"junior_minister", "minister_of_state", "secretary_state", "chancellor", "prime_minister"}
CABINET_RANKED = {"secretary_state", "chancellor", "prime_minister"}


def _votes(p):
    return [v for v in p.get("vote_history", []) if isinstance(v, dict)]


def _whipped(votes):
    return [v for v in votes if v.get("party_whip") in ("Aye", "No")]


def _inbox_cases_resolved(p):
    return sum(
        1
        for actions in p.get("actions_by_session", {}).values()
        for action_id in actions
        if str(action_id).startswith("inbox_")
    )


def _poll_gain(p):
    """Percentage points the player's party has gained since the career began."""
    baseline = p.get("polling_baseline") or {}
    shares = p.get("voting_intention") or {}
    party = p.get("party")
    if party not in baseline or party not in shares:
        return 0.0
    return float(shares[party]) - float(baseline[party])


ACHIEVEMENTS = [
    {"id": "first_vote", "label": "On the record", "icon": "🗳️",
     "description": "Cast your first Commons vote.",
     "check": lambda p: len(_votes(p)) >= 1},
    {"id": "rebel", "label": "Rebel with a cause", "icon": "🔥",
     "description": "Vote against your party whip.",
     "check": lambda p: any(v.get("vote") != v.get("party_whip") and v.get("vote") != "Abstain"
                            for v in _whipped(_votes(p)))},
    {"id": "loyalist", "label": "Safe pair of hands", "icon": "🤝",
     "description": "Follow the whip in eight whipped votes without a single rebellion.",
     "check": lambda p: len(_whipped(_votes(p))) >= 8 and all(v.get("followed_whip") for v in _whipped(_votes(p)))},
    {"id": "casework", "label": "Constituency champion", "icon": "🏠",
     "description": "Resolve five constituency inbox cases.",
     "check": lambda p: _inbox_cases_resolved(p) >= 5},
    {"id": "petitioner", "label": "Voice of the people", "icon": "✍️",
     "description": "Present a constituency petition.",
     "check": lambda p: len(p.get("petition_history", [])) >= 1},
    {"id": "lawmaker", "label": "Lawmaker", "icon": "📜",
     "description": "Take a Private Member's Bill all the way to Royal Assent.",
     "check": lambda p: any(b.get("stage") == "assented" for b in p.get("private_bill_history", []))},
    {"id": "promoted", "label": "First rung", "icon": "⬆️",
     "description": "Accept your first appointment.",
     "check": lambda p: len(p.get("promotion_log", [])) >= 1},
    {"id": "minister", "label": "Minister of the Crown", "icon": "💼",
     "description": "Enter government.",
     "check": lambda p: p.get("role") in GOVERNMENT_RANKED},
    {"id": "cabinet", "label": "Cabinet table", "icon": "🪑",
     "description": "Reach the Cabinet.",
     "check": lambda p: p.get("role") in CABINET_RANKED},
    {"id": "prime_minister", "label": "Number 10", "icon": "🚪",
     "description": "Become Prime Minister.",
     "check": lambda p: p.get("role") == "prime_minister"},
    {"id": "reelected", "label": "Re-elected", "icon": "✅",
     "description": "Win your seat at a general election.",
     "check": lambda p: int(p.get("seats_won", 1)) >= 2},
    {"id": "veteran", "label": "Veteran of the House", "icon": "🏛️",
     "description": "Win three general elections in a row.",
     "check": lambda p: int(p.get("seats_won", 1)) >= 4},
    {"id": "clean_hands", "label": "Clean hands", "icon": "🧼",
     "description": "Complete three years with no standards risk and integrity of 80 or more.",
     "check": lambda p: int(p.get("career_total_years", 0)) >= 3
     and int(p.get("ethics_risk", 0)) == 0
     and int(p.get("stats", {}).get("integrity", 0)) >= 80},
    {"id": "top_of_class", "label": "Top of the class", "icon": "🎓",
     "description": "Earn an A in an annual Westminster report.",
     "check": lambda p: any(r.get("grade") == "A" for r in p.get("annual_reports", []))},
    {"id": "promise_keeper", "label": "Promise keeper", "icon": "🤞",
     "description": "Keep every manifesto promise at a general election.",
     "check": lambda p: any(h.get("promises") and all(x.get("status") == "kept" for x in h["promises"])
                            for h in p.get("manifesto_history", []))},
    {"id": "rising_tide", "label": "Rising tide", "icon": "📈",
     "description": "Lift your party's fictional voting intention by 3 points or more.",
     "check": lambda p: _poll_gain(p) >= 3.0},
    {"id": "coalition", "label": "Coalition builder", "icon": "🧩",
     "description": "Win three political allies.",
     "check": lambda p: len(p.get("allies", [])) >= 3},
    {"id": "peak", "label": "Peak performance", "icon": "⭐",
     "description": "Push any career attribute to 90 or more.",
     "check": lambda p: any(int(v) >= 90 for v in p.get("stats", {}).values())},
    {"id": "against_the_odds", "label": "Against the odds", "icon": "🧗",
     "description": "Win re-election on Hard difficulty.",
     "check": lambda p: p.get("difficulty") == "hard" and int(p.get("seats_won", 1)) >= 2},
]

ACHIEVEMENT_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


def check_achievements(p):
    """Award any newly satisfied achievements; return the list of new ones."""
    earned = p.setdefault("achievements", [])
    newly = []
    for achievement in ACHIEVEMENTS:
        if achievement["id"] in earned:
            continue
        try:
            unlocked = bool(achievement["check"](p))
        except (KeyError, TypeError, ValueError, AttributeError):
            # A malformed older save must never crash the game.
            unlocked = False
        if unlocked:
            earned.append(achievement["id"])
            newly.append(achievement)
    return newly
