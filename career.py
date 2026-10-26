"""Playable political career mode: from backbench MP towards senior office."""
import html
import random
import streamlit as st

from content_store import load_json

DATA = load_json("career_content.json")
ROLES = DATA["roles"]
RULES = DATA["promotion_rules"]
ATTRIBUTES = DATA["attributes"]
ACTIONS_PER_SESSION = int(DATA["session_policy"]["actions_per_session"])
SESSIONS_PER_YEAR = int(DATA["session_policy"]["sessions_per_year"])
ELECTION_AFTER = int(DATA["session_policy"]["election_after_years"])
CONSTITUENCY_DATA = load_json("constituencies_2024.json")
CONSTITUENCIES = CONSTITUENCY_DATA["constituencies"]
CONSTITUENCY_BY_NAME = {row["name"]: row for row in CONSTITUENCIES}
CONSTITUENCY_NAMES = [row["name"] for row in CONSTITUENCIES]
DIVISION_DATA = load_json("career_divisions.json")
DIVISIONS = DIVISION_DATA["divisions"]
DIVISION_BY_ID = {row["id"]: row for row in DIVISIONS}
MANDATES = DIVISION_DATA["mandates"]
VOTE_OPTIONS = ("Aye", "No", "Abstain")


# Abstract game-only party bloc weights (not current Commons seat counts).
SIMULATED_PARTY_WEIGHTS = {
    "Labour": 36,
    "Conservative": 22,
    "Liberal Democrats": 12,
    "Reform UK": 8,
    "Green Party": 5,
    "SNP": 5,
    "Plaid Cymru": 3,
    "Democratic Unionist Party (DUP)": 2,
    "Sinn Féin": 2,
    "Alliance Party of Northern Ireland": 1,
    "Social Democratic and Labour Party (SDLP)": 1,
    "Ulster Unionist Party (UUP)": 1,
    "Independent": 2,
}


INBOX_CASES = [
    {
        "id": "gp_access", "priority": "public_services",
        "title": "Residents report long waits for GP appointments",
        "description": "A group of constituents say they are struggling to get timely appointments and want you to press for a practical response.",
    },
    {
        "id": "school_places", "priority": "public_services",
        "title": "Families are worried about school-place pressures",
        "description": "Parents have raised concerns about overcrowding and support for pupils with additional needs.",
    },
    {
        "id": "rent_repairs", "priority": "cost_living",
        "title": "Private renters report unresolved repair problems",
        "description": "Residents say damp, mould and slow repairs are affecting their homes and household budgets.",
    },
    {
        "id": "energy_bills", "priority": "cost_living",
        "title": "Local households are anxious about energy bills",
        "description": "Advice groups are seeing residents who are finding it difficult to manage essential household costs.",
    },
    {
        "id": "bus_service", "priority": "climate_transport",
        "title": "A bus route may be cut or reduced",
        "description": "Residents who rely on public transport worry that fewer services will make work, college and appointments harder to reach.",
    },
    {
        "id": "flood_defences", "priority": "climate_transport",
        "title": "Residents want answers on local flood protection",
        "description": "People in a flood-risk area want clearer plans for maintenance, preparedness and future resilience.",
    },
    {
        "id": "high_street", "priority": "jobs_growth",
        "title": "Shopkeepers are concerned about empty high-street premises",
        "description": "Local businesses want action on footfall, skills and the barriers to bringing vacant units back into use.",
    },
    {
        "id": "apprenticeships", "priority": "jobs_growth",
        "title": "Young residents are asking for more training routes",
        "description": "Residents and employers want clearer routes into apprenticeships, work experience and skilled jobs.",
    },
    {
        "id": "neighbourhood_safety", "priority": "crime_public_safety",
        "title": "Residents want action on a neighbourhood safety concern",
        "description": "Constituents want agencies to work together and provide a clear response to a local safety issue.",
    },
    {
        "id": "spending_transparency", "priority": "integrity",
        "title": "A community group is asking for clearer public spending information",
        "description": "Residents want decisions and the use of public funds explained in a way they can scrutinise.",
    },
]


# Fictional Phase 2 Westminster news stories. These are game scenarios, not real headlines.
PHASE2_NEWS = [
    {
        "id": "pmqs_clip", "headline": "A PMQs exchange dominates the lunchtime bulletins",
        "brief": "A short clip from Prime Minister's Questions is spreading online. Colleagues want you to help shape the story before the evening news.",
        "choices": [
            {"id": "factcheck", "label": "Publish a sourced factsheet", "description": "Answer the criticism with evidence and a clear explanation.",
             "effects": {"policy_expertise": 2, "parliamentary_influence": 2, "integrity": 2, "public_profile": 1}, "factions": {"party_leadership": 2}},
            {"id": "counterattack", "label": "Launch a sharp counterattack", "description": "Make a punchy intervention that attracts attention, but risks looking evasive.",
             "effects": {"public_profile": 5, "party_trust": -2, "integrity": -1}, "factions": {"backbenchers": 2, "party_leadership": -2}}
        ]
    },
    {
        "id": "whips_call", "headline": "The Whips' Office wants a word after a difficult division",
        "brief": "The Chief Whip is worried about parliamentary arithmetic and wants to know whether you can be relied upon on the next vote.",
        "choices": [
            {"id": "private_meeting", "label": "Meet the Whips privately", "description": "Explain your concerns and negotiate a workable way forward.",
             "effects": {"party_trust": 4, "parliamentary_influence": 2}, "factions": {"party_leadership": 5, "backbenchers": -1}},
            {"id": "public_stand", "label": "Defend your position publicly", "description": "Show your independence, even if the leadership is annoyed.",
             "effects": {"public_profile": 4, "integrity": 1, "party_trust": -3}, "factions": {"party_leadership": -4, "backbenchers": 3}}
        ]
    },
    {
        "id": "expenses_question", "headline": "A local paper asks for details about parliamentary expenses",
        "brief": "A reporter has asked for an explanation of a claim. The paperwork is available, but a rushed response could turn a small query into a story.",
        "choices": [
            {"id": "publish_receipts", "label": "Publish the documents and explain the claim", "description": "Be transparent and let readers inspect the evidence.",
             "effects": {"integrity": 5, "constituency_support": 2, "public_profile": 1}, "factions": {"local_party": 1}, "risk_delta": -1},
            {"id": "dismiss_question", "label": "Dismiss the question as a Westminster row", "description": "Move on quickly, but risk making the story look worse.",
             "effects": {"public_profile": 2, "integrity": -4, "constituency_support": -2}, "risk_delta": 1}
        ]
    },
    {
        "id": "donor_meeting", "headline": "A donor offers a private briefing ahead of a policy announcement",
        "brief": "The offer raises questions about transparency and access. Your handling of the meeting could come back to the Standards Commissioner or the press.",
        "choices": [
            {"id": "declare_meeting", "label": "Declare the meeting and seek advice", "description": "Record the relevant interest and follow the proper parliamentary process.",
             "effects": {"integrity": 5, "policy_expertise": 1, "party_trust": 1}, "risk_delta": -2},
            {"id": "keep_quiet", "label": "Keep the meeting off the record", "description": "You may gain short-term access, but the lack of transparency creates a serious standards risk.",
             "effects": {"public_profile": 1, "integrity": -6, "party_trust": 1}, "risk_delta": 2}
        ]
    },
    {
        "id": "committee_leak", "headline": "A Select Committee draft appears in the newspapers",
        "brief": "A confidential draft has been quoted before colleagues have agreed their report. The committee needs someone to restore confidence in its work.",
        "choices": [
            {"id": "protect_process", "label": "Refer the leak through the proper committee process", "description": "Protect evidence-gathering and avoid prejudging the inquiry.",
             "effects": {"integrity": 4, "policy_expertise": 2, "parliamentary_influence": 1}, "factions": {"backbenchers": 1}},
            {"id": "feed_story", "label": "Brief journalists to get your side heard", "description": "Your version may dominate the news, but colleagues may see it as self-serving.",
             "effects": {"public_profile": 4, "parliamentary_influence": 1, "integrity": -3}, "factions": {"backbenchers": -3}, "risk_delta": 1}
        ]
    },
    {
        "id": "local_campaign", "headline": "Local campaigners challenge the Government's latest announcement",
        "brief": "A constituency group says the policy misses local needs. The local party wants a response before canvassing this weekend.",
        "choices": [
            {"id": "meet_campaigners", "label": "Meet campaigners and take their evidence to Westminster", "description": "Link local concerns to a concrete parliamentary question or amendment.",
             "effects": {"constituency_support": 4, "policy_expertise": 2, "parliamentary_influence": 1, "campaign_readiness": 2}, "factions": {"local_party": 3}},
            {"id": "defend_line", "label": "Defend the party line on local radio", "description": "Show loyalty, but accept the risk of sounding out of touch with local concerns.",
             "effects": {"party_trust": 3, "public_profile": 2, "constituency_support": -2}, "factions": {"party_leadership": 2, "local_party": -2}}
        ]
    },
    {
        "id": "leadership_briefing", "headline": "An anonymous briefing fuels Westminster leadership speculation",
        "brief": "Political journalists are reporting tensions in the party and asking MPs for comment. The story is fictional and can affect your relationships.",
        "choices": [
            {"id": "cool_tensions", "label": "Call for calm and discuss policy privately", "description": "Avoid adding fuel to the story and work on the disagreements behind it.",
             "effects": {"party_trust": 2, "integrity": 2, "parliamentary_influence": 1}, "factions": {"party_leadership": 2, "backbenchers": 2}},
            {"id": "join_briefing", "label": "Use the moment to criticise the leadership", "description": "You may attract attention from discontented colleagues, but it risks your route to promotion.",
             "effects": {"public_profile": 5, "party_trust": -4, "parliamentary_influence": 1}, "factions": {"party_leadership": -5, "backbenchers": 3}}
        ]
    }
]

PHASE2_FACTIONS = {
    "party_leadership": "Party leadership",
    "backbenchers": "Backbench colleagues",
    "local_party": "Local constituency party",
    "cross_party": "Cross-party relationships",
}

# Named characters below are fictional game characters, not real MPs.
PHASE2_NETWORK_ACTIONS = [
    {
        "id": "chief_whip", "label": "Meet the Chief Whip",
        "description": "Explain your priorities and negotiate with the Whips' Office before a difficult Commons vote.",
        "effects": {"party_trust": 3, "parliamentary_influence": 2},
        "factions": {"party_leadership": 6, "backbenchers": -1}
    },
    {
        "id": "backbench_amendment", "label": "Back a colleague's amendment",
        "description": "Work with Priya Shah, a fictional backbench MP, to build support for a practical amendment.",
        "effects": {"parliamentary_influence": 3, "policy_expertise": 2, "party_trust": -1},
        "factions": {"backbenchers": 5, "cross_party": 2}, "ally": "Priya Shah"
    },
    {
        "id": "cross_party", "label": "Build a cross-party coalition",
        "description": "Work with Alex Morgan, a fictional opposition MP, on an issue where several parties may agree.",
        "effects": {"parliamentary_influence": 4, "policy_expertise": 2, "party_trust": -1},
        "factions": {"cross_party": 7}, "ally": "Alex Morgan"
    },
    {
        "id": "doorstep_campaign", "label": "Canvass with local party activists",
        "description": "Join a doorstep session, listen to residents and help the constituency campaign prepare for the next general election.",
        "effects": {"constituency_support": 3, "campaign_readiness": 10, "public_profile": 1},
        "factions": {"local_party": 6}, "ally": "Ellie Watkins"
    },
    {
        "id": "challenge_rival", "label": "Challenge a rival's public briefing",
        "description": "Challenge Morgan Reed, a fictional political rival, over a claim you believe is misleading.",
        "effects": {"public_profile": 4, "parliamentary_influence": 2, "party_trust": -2},
        "factions": {"party_leadership": -1, "backbenchers": 2}, "rival": "Morgan Reed"
    }
]


GOVERNMENT_ROLES = {"junior_minister", "minister_of_state", "secretary_state", "chancellor", "prime_minister"}

PORTFOLIOS = {
    "health": {"label": "Health and Social Care", "targets": ["Improve NHS waiting times", "Strengthen GP access", "Improve mental health support"]},
    "education": {"label": "Education", "targets": ["Raise school standards", "Improve attendance and inclusion", "Expand technical education and apprenticeships"]},
    "treasury": {"label": "HM Treasury", "targets": ["Support sustainable growth", "Maintain fiscal credibility", "Improve productivity and investment"]},
    "housing": {"label": "Housing, Communities and Local Government", "targets": ["Increase affordable housing delivery", "Improve local-authority capacity", "Support high streets and town centres"]},
    "transport": {"label": "Transport", "targets": ["Improve rail and bus reliability", "Deliver safer local roads", "Improve regional transport links"]},
    "energy": {"label": "Energy Security and Net Zero", "targets": ["Accelerate grid connections", "Improve home energy efficiency", "Support reliable low-carbon power"]},
    "home_office": {"label": "Home Office", "targets": ["Improve neighbourhood safety", "Reduce casework backlogs", "Strengthen public-service accountability"]},
    "justice": {"label": "Justice", "targets": ["Reduce court backlogs", "Improve access to legal support", "Strengthen victim support"]},
    "defence": {"label": "Defence", "targets": ["Improve service readiness", "Support service personnel and families", "Strengthen procurement accountability"]},
    "work_pensions": {"label": "Work and Pensions", "targets": ["Improve routes into work", "Strengthen disability employment support", "Improve pensioner security"]},
    "foreign_office": {"label": "Foreign, Commonwealth and Development Office", "targets": ["Build diplomatic partnerships", "Improve aid effectiveness", "Support British nationals overseas"]},
    "cabinet_office": {"label": "Cabinet Office and Government Coordination", "targets": ["Improve cross-government delivery", "Strengthen crisis preparedness", "Improve public-service standards"]},
}

DEPARTMENT_ACTIONS = [
    {"id": "delivery_plan", "label": "Drive a departmental delivery plan", "description": "Set milestones, assign responsibility and publish a delivery timetable.", "effects": {"policy_expertise": 3, "parliamentary_influence": 2, "party_trust": 1}, "score": 8, "progress": 25},
    {"id": "frontline_visit", "label": "Visit frontline services", "description": "Hear directly from staff and the public before changing how the service works.", "effects": {"constituency_support": 2, "integrity": 2, "policy_expertise": 2}, "score": 7, "progress": 20},
    {"id": "committee_accountability", "label": "Defend results before a Select Committee", "description": "Explain what has improved, admit what has not, and set out how you will fix it.", "effects": {"public_profile": 2, "parliamentary_influence": 3, "integrity": 1}, "score": 5, "progress": 15},
    {"id": "budget_settlement", "label": "Negotiate funding with the Treasury", "description": "Make a case for resources and explain the trade-offs or savings needed to pay for them.", "effects": {"party_trust": 2, "policy_expertise": 2, "parliamentary_influence": 2}, "score": 6, "progress": 18},
]

LEADERSHIP_STRATEGIES = {
    "quiet": {"label": "Quietly build endorsements", "description": "Talk to MPs privately, negotiate policy commitments and avoid public confrontation.", "bonus": 3, "effects": {"party_trust": 2, "parliamentary_influence": 2}},
    "backbench": {"label": "Mobilise backbench support", "description": "Build a coalition of colleagues who want a change in direction.", "bonus": 5, "effects": {"public_profile": 2, "party_trust": -1}},
    "public": {"label": "Launch a public campaign", "description": "Make a direct public case for your leadership, risking a backlash from senior colleagues.", "bonus": 2, "effects": {"public_profile": 5, "party_trust": -3}},
}

CABINET_RESHUFFLE_OPTIONS = {
    "reward_delivery": {"label": "Reward departments that deliver", "description": "Promote a delivery-first approach and signal that results matter.", "effects": {"party_trust": 3, "parliamentary_influence": 2}, "factions": {"party_leadership": 4, "backbenchers": 2}},
    "balance_factions": {"label": "Rebalance the Cabinet", "description": "Offer different wings of the party a clearer role in government.", "effects": {"party_trust": 1, "public_profile": 1}, "factions": {"party_leadership": 2, "backbenchers": 4, "local_party": 2}},
    "remove_rival": {"label": "Move a rival out of the inner circle", "description": "Tighten control of the Cabinet, but risk resentment among colleagues.", "effects": {"party_trust": -2, "parliamentary_influence": 3, "public_profile": 2}, "factions": {"party_leadership": 4, "backbenchers": -5}},
}


def new_profile(name="Alex Morgan", constituency="Aberafan Maesteg",
                ambition="policy_specialist", local_mandate="public_services", party="Labour"):
    """Create an MP profile tied to a real 2024 Westminster constituency."""
    record = CONSTITUENCY_BY_NAME.get(constituency)
    if record is None:
        record = CONSTITUENCIES[0]
    constituency = record["name"]
    local_mandate = local_mandate if local_mandate in MANDATES else "public_services"
    stats = {
        "constituency_support": 58,
        "party_trust": 48,
        "parliamentary_influence": 24,
        "public_profile": 25,
        "policy_expertise": 30,
        "integrity": 78,
        "campaign_readiness": 30,
    }
    ambition_spec = DATA["ambitions"].get(ambition, DATA["ambitions"]["policy_specialist"])
    for key, value in ambition_spec["effects"].items():
        stats[key] = _clip(stats.get(key, 0) + value)
    return {
        "name": (name or "Alex Morgan").strip()[:70],
        "party": party if party in DIVISION_DATA["party_names"] else "Labour",
        "constituency": constituency,
        "constituency_code": record["code"],
        "constituency_nation": record["nation"],
        "local_mandate": local_mandate,
        "ambition": ambition if ambition in DATA["ambitions"] else "policy_specialist",
        "role": "mp",
        "stats": stats,
        "career_year": 1,
        "career_term": 1,
        "career_session": 1,
        "career_total_years": 0,
        "actions_by_session": {},
        "division_by_session": {},
        "votes_by_session": {},
        "vote_history": [],
        "history": [{
            "year": 1,
            "term": 1,
            "session": 1,
            "title": "Elected to Parliament",
            "text": f"{name or 'Alex Morgan'} begins a career as a backbench MP for {constituency}, {record['nation']}.",
        }],
        "last_event": "Welcome to Westminster. Each session has one Commons division plus two career actions. Your vote affects party trust, influence and constituency support.",
        "last_promotion_total_year": 0,
        "game_over": False,
        "election_result": None,
        "seats_won": 1,
        "promotion_log": [],
        "faction_standing": {"party_leadership": 50, "backbenchers": 50, "local_party": 50, "cross_party": 35},
        "allies": [],
        "rivals": [],
        "ethics_risk": 0,
        "news_responses_by_session": {},
        "portfolio_id": None,
        "portfolio_target": None,
        "department_score": 0,
        "department_progress": 0,
        "annual_reports": [],
        "leadership_contests": [],
        "leadership_cooldown_year": 0,
        "reshuffle_log": [],
        "completed_targets": [],
        "cabinet_exclusions": [],
    }


def _clip(value, low=0, high=100):
    return max(low, min(high, int(round(value))))


def _profile():
    p = st.session_state.get("career_profile")
    if not isinstance(p, dict):
        p = new_profile()
        st.session_state.career_profile = p
    p.setdefault("stats", {})
    for key, value in {
        "constituency_support": 58, "party_trust": 48, "parliamentary_influence": 24,
        "public_profile": 25, "policy_expertise": 30, "integrity": 78, "campaign_readiness": 30
    }.items():
        p["stats"].setdefault(key, value)
    p.setdefault("actions_by_session", {})
    p.setdefault("division_by_session", {})
    p.setdefault("votes_by_session", {})
    p.setdefault("vote_history", [])
    p.setdefault("history", [])
    current_seat = CONSTITUENCY_BY_NAME.get(p.get("constituency"))
    if current_seat is None:
        current_seat = CONSTITUENCIES[0]
        p["constituency"] = current_seat["name"]
        p["last_event"] = f"Your old save used a fictional constituency name; your career has been moved to the real 2024 seat {current_seat['name']}."
    p["constituency_code"] = current_seat["code"]
    p["constituency_nation"] = current_seat["nation"]
    if p.get("local_mandate") not in MANDATES:
        p["local_mandate"] = "public_services"
    if p.get("party") not in DIVISION_DATA["party_names"]:
        p["party"] = st.session_state.get("party", "Labour")
    p.setdefault("promotion_log", [])
    p.setdefault("career_total_years", 0)
    p.setdefault("faction_standing", {"party_leadership": 50, "backbenchers": 50, "local_party": 50, "cross_party": 35})
    for faction in PHASE2_FACTIONS:
        p["faction_standing"].setdefault(faction, 50 if faction != "cross_party" else 35)
    p.setdefault("allies", [])
    p.setdefault("rivals", [])
    p.setdefault("ethics_risk", 0)
    p.setdefault("news_responses_by_session", {})
    p.setdefault("portfolio_id", None)
    p.setdefault("portfolio_target", None)
    p.setdefault("department_score", 0)
    p.setdefault("department_progress", 0)
    p.setdefault("annual_reports", [])
    p.setdefault("leadership_contests", [])
    p.setdefault("leadership_cooldown_year", 0)
    p.setdefault("reshuffle_log", [])
    p.setdefault("completed_targets", [])
    p.setdefault("cabinet_exclusions", [])
    if p.get("role") in GOVERNMENT_ROLES:
        if p.get("portfolio_id") not in PORTFOLIOS:
            stable_mix = sum((i + 1) * ord(ch) for i, ch in enumerate(p.get("name", "MP")))
            portfolio_ids = list(PORTFOLIOS)
            p["portfolio_id"] = portfolio_ids[(stable_mix + int(p.get("career_total_years", 0))) % len(portfolio_ids)]
            p["portfolio_target"] = PORTFOLIOS[p["portfolio_id"]]["targets"][0]
            p["department_score"] = max(40, int(p.get("department_score", 0)))
        if p.get("portfolio_target") not in PORTFOLIOS[p["portfolio_id"]]["targets"]:
            p["portfolio_target"] = PORTFOLIOS[p["portfolio_id"]]["targets"][0]
    return p


def _session_key(p):
    return f"{p['career_term']}:{p['career_year']}:{p['career_session']}"


def _current_actions(p):
    return p["actions_by_session"].setdefault(_session_key(p), [])


def _record(p, title, text):
    p["history"].append({
        "year": int(p["career_year"]),
        "term": int(p["career_term"]),
        "session": int(p["career_session"]),
        "role": p["role"],
        "title": title,
        "text": text,
    })
    p["history"] = p["history"][-60:]


def _apply_effects(p, effects):
    changed = []
    for key, value in effects.items():
        if key not in ATTRIBUTES:
            continue
        before = int(p["stats"].get(key, 0))
        after = _clip(before + value)
        p["stats"][key] = after
        if after != before:
            changed.append((ATTRIBUTES[key], after - before))
    return changed


def _effect_summary(effects):
    pieces = []
    for key, value in effects.items():
        if key in ATTRIBUTES and value:
            pieces.append(f"{value:+g} {ATTRIBUTES[key].lower()}")
    return " · ".join(pieces)


def _division_for(p):
    """Return one deterministic, persisted division for the current parliamentary session."""
    key = _session_key(p)
    p.setdefault("division_by_session", {})
    division_id = p["division_by_session"].get(key)
    if division_id not in DIVISION_BY_ID:
        seed = int(st.session_state.get("seed", 12345))
        seat_mix = sum((index + 1) * ord(char) for index, char in enumerate(p.get("constituency", "")))
        term = int(p.get("career_term", 1))
        year = int(p.get("career_year", 1))
        session = int(p.get("career_session", 1))
        index = (seed + seat_mix + term * 37 + year * 113 + session * 271) % len(DIVISIONS)
        division_id = DIVISIONS[index]["id"]
        p["division_by_session"][key] = division_id
        st.session_state.career_profile = p
    return DIVISION_BY_ID[division_id]


def _simulate_division_result(p, division, choice):
    """Estimate a fictional vote tally using game-only party weights."""
    ayes = 0
    noes = 0
    abstentions = 0
    player_party = p.get("party", "Labour")
    for party, weight in SIMULATED_PARTY_WEIGHTS.items():
        whip = division.get("whip", {}).get(party, "Free vote")
        bloc_weight = max(0, int(weight) - (1 if party == player_party else 0))
        if whip == "Aye":
            ayes += bloc_weight
        elif whip == "No":
            noes += bloc_weight
        else:
            # A free-vote bloc is split approximately evenly in the simplified model.
            ayes += bloc_weight // 2
            noes += bloc_weight - (bloc_weight // 2)
    if choice == "Aye":
        ayes += 1
    elif choice == "No":
        noes += 1
    else:
        abstentions += 1
    result = "Passed" if ayes > noes else "Rejected"
    return {
        "ayes": int(ayes),
        "noes": int(noes),
        "abstentions": int(abstentions),
        "result": result,
        "majority": int(abs(ayes - noes)),
    }


def _cast_vote(p, choice):
    """Record a Commons vote once per session, independently from career action slots."""
    if choice not in VOTE_OPTIONS:
        return False
    key = _session_key(p)
    p.setdefault("votes_by_session", {})
    if key in p["votes_by_session"]:
        return False

    division = _division_for(p)
    whip = division.get("whip", {}).get(p.get("party", "Labour"), "Free vote")
    division_result = _simulate_division_result(p, division, choice)
    effects = {}
    def add(stat, amount):
        effects[stat] = effects.get(stat, 0) + amount

    if whip == "Free vote":
        add("integrity", 1)
        if choice != "Abstain":
            add("public_profile", 1)
            add("parliamentary_influence", 1)
    elif choice == whip:
        add("party_trust", 3)
        add("parliamentary_influence", 1)
    elif choice == "Abstain":
        add("party_trust", -1)
        add("integrity", 1)
        add("public_profile", 1)
    else:
        add("party_trust", -5)
        add("integrity", 2)
        add("public_profile", 3)
        add("parliamentary_influence", 2)

    mandate_match = division.get("priority") == p.get("local_mandate")
    local_preference = division.get("local_preference", "Free vote")
    if mandate_match and local_preference in ("Aye", "No"):
        if choice == local_preference:
            add("constituency_support", 4)
            add("public_profile", 1)
        elif choice == "Abstain":
            add("constituency_support", -1)
        else:
            add("constituency_support", -3)

    _apply_effects(p, effects)
    record = {
        "term": int(p["career_term"]),
        "year": int(p["career_year"]),
        "session": int(p["career_session"]),
        "division_id": division["id"],
        "title": division["title"],
        "vote": choice,
        "party": p.get("party", "Labour"),
        "party_whip": whip,
        "followed_whip": (whip == "Free vote" or choice == whip),
        "division_result": division_result,
        "local_priority": p.get("local_mandate"),
        "constituency_effect": "Aligned with local priority" if mandate_match and choice == local_preference else ("Conflicted with local priority" if mandate_match and choice in ("Aye", "No") else "No direct local-priority effect"),
        "effects": effects,
        "effects_summary": _effect_summary(effects),
    }
    p["votes_by_session"][key] = record
    p.setdefault("vote_history", [])
    p["vote_history"] = (p["vote_history"] + [record])[-40:]
    p["last_vote"] = record
    summary = _effect_summary(effects)
    narrative = f"You voted {choice} on '{division['title']}'. Party whip: {whip}."
    if summary:
        narrative += f" Effects: {summary}."
    _record(p, f"Commons division · {choice}", narrative)
    p["last_event"] = narrative
    st.session_state.career_profile = p
    return True


def _current_inbox_cases(p):
    """Return three repeatable fictional constituent cases for this parliamentary session."""
    session_key = _session_key(p)
    seed = int(st.session_state.get("seed", 12345))
    seat_mix = sum((index + 1) * ord(char) for index, char in enumerate(p.get("constituency", "")))
    session_mix = sum((index + 3) * ord(char) for index, char in enumerate(session_key))
    rng = random.Random(seed + seat_mix + session_mix)
    return rng.sample(INBOX_CASES, k=min(3, len(INBOX_CASES)))


def _resolve_inbox_case(p, case, approach):
    """Resolve one inbox case; handling it consumes one ordinary career-action slot."""
    used = _current_actions(p)
    action_id = f"inbox_{case['id']}"
    if len(used) >= ACTIONS_PER_SESSION or action_id in used:
        return
    approaches = {
        "investigate": {
            "label": "Investigate and follow up",
            "effects": {"constituency_support": 4, "integrity": 2, "policy_expertise": 1},
            "description": "You gather details from the constituent and follow the issue through the relevant service.",
        },
        "parliament": {
            "label": "Raise it in Parliament",
            "effects": {"public_profile": 3, "parliamentary_influence": 3, "party_trust": -1},
            "description": "You use parliamentary scrutiny to press for answers and make the issue more visible.",
        },
        "coordinate": {
            "label": "Bring local partners together",
            "effects": {"constituency_support": 2, "party_trust": 1, "integrity": 1, "policy_expertise": 1},
            "description": "You seek a practical response by getting the relevant local organisations around the table.",
        },
    }
    chosen = approaches[approach]
    effects = dict(chosen["effects"])
    if case["priority"] == p.get("local_mandate"):
        effects["constituency_support"] = effects.get("constituency_support", 0) + 2
        effects["public_profile"] = effects.get("public_profile", 0) + 1
    action = {
        "id": action_id,
        "label": f"Inbox: {case['title']} — {chosen['label']}",
        "description": chosen["description"],
        "effects": effects,
    }
    _take_action(p, action)


def _take_action(p, action):
    used = _current_actions(p)
    if len(used) >= ACTIONS_PER_SESSION:
        return
    changes = _apply_effects(p, action["effects"])
    used.append(action["id"])
    summary = _effect_summary(action["effects"])
    narrative = action["description"]
    if summary:
        narrative += " Effects: " + summary + "."
    _record(p, action["label"], narrative)
    p["last_event"] = f"{action['label']}: {summary or 'No lasting career-stat change.'}"
    st.session_state.career_profile = p
    st.rerun()


def _current_phase2_news(p):
    """Return one repeatable fictional UK Westminster headline for the current session."""
    key = _session_key(p)
    seed = int(st.session_state.get("seed", 12345))
    seat_mix = sum((index + 1) * ord(char) for index, char in enumerate(p.get("constituency", "")))
    session_mix = sum((index + 3) * ord(char) for index, char in enumerate(key))
    index = (seed + seat_mix + session_mix * 7) % len(PHASE2_NEWS)
    return PHASE2_NEWS[index]


def _resolve_phase2_decision(p, action_id, label, description, effects,
                             faction_effects=None, risk_delta=0, ally=None, rival=None,
                             response_key=None, response_label=None):
    """Apply one Phase 2 choice as an ordinary career action."""
    used = _current_actions(p)
    if len(used) >= ACTIONS_PER_SESSION or action_id in used:
        return
    _apply_effects(p, effects)
    used.append(action_id)
    for faction, delta in (faction_effects or {}).items():
        if faction in PHASE2_FACTIONS:
            p["faction_standing"][faction] = _clip(p["faction_standing"].get(faction, 50) + delta)
    if ally and ally not in p["allies"]:
        p["allies"].append(ally)
        p["allies"] = p["allies"][-8:]
    if rival and rival not in p["rivals"]:
        p["rivals"].append(rival)
        p["rivals"] = p["rivals"][-8:]
    p["ethics_risk"] = max(0, min(5, int(p.get("ethics_risk", 0)) + int(risk_delta)))
    narrative = description
    summary = _effect_summary(effects)
    if summary:
        narrative += " Effects: " + summary + "."
    if response_key:
        p.setdefault("news_responses_by_session", {})[_session_key(p)] = {
            "event_id": response_key,
            "choice": response_label or label,
            "effects_summary": summary,
        }
    if int(p["ethics_risk"]) >= 3:
        scrutiny_effects = {"integrity": -8, "party_trust": -4, "public_profile": 4}
        _apply_effects(p, scrutiny_effects)
        p["ethics_risk"] = 1
        narrative += " A transparency lapse has triggered a fictional Westminster standards row; the Parliamentary Commissioner for Standards is asking questions."
    _record(p, label, narrative)
    p["last_event"] = f"{label}: {summary or 'The decision has affected your political relationships.'}"
    if int(p.get("ethics_risk", 0)) > 0:
        p["last_event"] += f" Standards risk: {p['ethics_risk']}/5."
    st.session_state.career_profile = p
    st.rerun()


def _resolve_news_choice(p, event, choice):
    _resolve_phase2_decision(
        p,
        action_id=f"news_{event['id']}",
        label=f"Westminster news: {choice['label']}",
        description=choice["description"],
        effects=choice.get("effects", {}),
        faction_effects=choice.get("factions", {}),
        risk_delta=choice.get("risk_delta", 0),
        ally=choice.get("ally"),
        rival=choice.get("rival"),
        response_key=event["id"],
        response_label=choice["label"],
    )


def _resolve_network_action(p, action):
    _resolve_phase2_decision(
        p,
        action_id=f"network_{action['id']}",
        label=action["label"],
        description=action["description"],
        effects=action.get("effects", {}),
        faction_effects=action.get("factions", {}),
        ally=action.get("ally"),
        rival=action.get("rival"),
    )


def _set_portfolio_and_target(p, portfolio_id, target):
    """Change a minister's portfolio priorities as a career action."""
    used = _current_actions(p)
    action_id = "portfolio_target"
    if len(used) >= ACTIONS_PER_SESSION or action_id in used or portfolio_id not in PORTFOLIOS:
        return
    spec = PORTFOLIOS[portfolio_id]
    if target not in spec["targets"]:
        target = spec["targets"][0]
    changed_portfolio = p.get("portfolio_id") != portfolio_id
    p["portfolio_id"] = portfolio_id
    p["portfolio_target"] = target
    if changed_portfolio:
        p["department_score"] = max(35, int(p.get("department_score", 0)))
        p["department_progress"] = 0
    used.append(action_id)
    narrative = f"You set {spec['label']} priorities around: {target}."
    _record(p, "Set ministerial portfolio and target", narrative)
    p["last_event"] = narrative
    st.session_state.career_profile = p
    st.rerun()


def _run_department_action(p, action):
    """Apply a portfolio delivery action; it shares the same two action slots."""
    used = _current_actions(p)
    action_id = f"department_{action['id']}"
    if len(used) >= ACTIONS_PER_SESSION or action_id in used:
        return
    if p.get("portfolio_id") not in PORTFOLIOS:
        return
    _apply_effects(p, action["effects"])
    used.append(action_id)
    p["department_score"] = _clip(int(p.get("department_score", 40)) + int(action["score"]))
    previous_progress = int(p.get("department_progress", 0))
    new_progress = min(100, previous_progress + int(action["progress"]))
    portfolio = PORTFOLIOS[p["portfolio_id"]]
    target_name = p.get("portfolio_target") or portfolio["targets"][0]
    target_key = f"{p['portfolio_id']}:{target_name}"
    narrative = f"{action['description']} "
    if new_progress >= 100 and previous_progress < 100:
        if target_key not in p["completed_targets"]:
            p["completed_targets"].append(target_key)
            p["completed_targets"] = p["completed_targets"][-30:]
        completion_bonus = {"policy_expertise": 2, "party_trust": 2, "integrity": 1}
        _apply_effects(p, completion_bonus)
        p["department_score"] = _clip(p["department_score"] + 4)
        target_index = portfolio["targets"].index(target_name) if target_name in portfolio["targets"] else -1
        p["portfolio_target"] = portfolio["targets"][(target_index + 1) % len(portfolio["targets"])]
        p["department_progress"] = 0
        narrative += f"Milestone achieved: {target_name}. Ministers and officials can now focus on the next target: {p['portfolio_target']}. "
        narrative += f"Completion bonus: {_effect_summary(completion_bonus)}. "
    else:
        p["department_progress"] = new_progress
    narrative += f"Delivery rating is now {p['department_score']}/100 and target progress is {p['department_progress']}%."
    summary = _effect_summary(action["effects"])
    if summary:
        narrative += " Career effects: " + summary + "."
    _record(p, f"{portfolio['label']}: {action['label']}", narrative)
    p["last_event"] = f"{action['label']}: delivery rating {p['department_score']}/100."
    st.session_state.career_profile = p
    st.rerun()


def _record_annual_report(p):
    """Create a school-report-style annual review from the previous parliamentary year."""
    year = int(p.get("career_year", 1))
    term = int(p.get("career_term", 1))
    if any(int(r.get("term", -1)) == term and int(r.get("year", -1)) == year for r in p.get("annual_reports", [])):
        return
    stats = p.get("stats", {})
    score = (
        .20 * stats.get("constituency_support", 0)
        + .16 * stats.get("party_trust", 0)
        + .15 * stats.get("parliamentary_influence", 0)
        + .13 * stats.get("public_profile", 0)
        + .13 * stats.get("policy_expertise", 0)
        + .13 * stats.get("integrity", 0)
        + .10 * stats.get("campaign_readiness", 30)
    )
    score = round(score, 1)
    grade = "A" if score >= 85 else "B" if score >= 75 else "C" if score >= 65 else "D" if score >= 55 else "E" if score >= 45 else "F"
    labels = {key: value for key, value in ATTRIBUTES.items()}
    ranked = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    strongest = labels.get(ranked[0][0], ranked[0][0].replace("_", " ").title()) if ranked else "No data"
    weakest = labels.get(ranked[-1][0], ranked[-1][0].replace("_", " ").title()) if ranked else "No data"
    year_prefix = f"{term}:{year}:"
    year_actions = sum(len(actions) for key, actions in p.get("actions_by_session", {}).items() if key.startswith(year_prefix))
    year_votes = [v for v in p.get("vote_history", []) if int(v.get("term", -1)) == term and int(v.get("year", -1)) == year]
    followed = sum(1 for vote in year_votes if vote.get("followed_whip"))
    report = {
        "term": term, "year": year, "score": score, "grade": grade,
        "strongest": strongest, "focus": weakest,
        "actions_taken": year_actions, "votes_cast": len(year_votes), "whips_followed": followed,
        "department_score": int(p.get("department_score", 0)) if p.get("role") in GOVERNMENT_ROLES else None,
        "portfolio": PORTFOLIOS.get(p.get("portfolio_id"), {}).get("label") if p.get("role") in GOVERNMENT_ROLES else None,
        "ethics_risk": int(p.get("ethics_risk", 0)),
    }
    p.setdefault("annual_reports", []).append(report)
    p["annual_reports"] = p["annual_reports"][-15:]
    label = f"Westminster school report: Grade {grade} ({score}/100)"
    report_text = f"Year {year} review complete. Strongest subject: {strongest}. Next year's focus: {weakest}. You used {year_actions} career-action slots and cast {len(year_votes)} Commons vote(s)."
    if report["department_score"] is not None:
        report_text += f" Department delivery rating: {report['department_score']}/100."
    if report["ethics_risk"] >= 2:
        report_text += " Parliamentary standards risk remains a concern."
    _record(p, label, report_text)
    p["last_annual_report"] = report
    p["last_event"] = report_text


def _leadership_eligible(p):
    if int(p.get("leadership_cooldown_year", 0)) > int(p.get("career_total_years", 0)):
        return False
    if p.get("role") in {"secretary_state", "chancellor", "prime_minister"}:
        return True
    return (
        int(p.get("career_total_years", 0)) >= 4
        and int(p.get("stats", {}).get("party_trust", 0)) >= 70
        and int(p.get("stats", {}).get("parliamentary_influence", 0)) >= 60
        and int(p.get("stats", {}).get("public_profile", 0)) >= 55
    )


def _run_leadership_contest(p, strategy_key):
    """Run a fictional party leadership contest or an incumbent confidence ballot."""
    used = _current_actions(p)
    action_id = "leadership_contest"
    if len(used) >= ACTIONS_PER_SESSION or action_id in used or not _leadership_eligible(p):
        return
    strategy = LEADERSHIP_STRATEGIES[strategy_key]
    _apply_effects(p, strategy["effects"])
    stats = p["stats"]
    factions = p["faction_standing"]
    score = (
        .30 * stats.get("party_trust", 0)
        + .22 * stats.get("parliamentary_influence", 0)
        + .17 * stats.get("public_profile", 0)
        + .13 * factions.get("party_leadership", 50)
        + .13 * factions.get("backbenchers", 50)
        + .05 * factions.get("cross_party", 35)
        + strategy["bonus"]
    )
    seed = int(st.session_state.get("seed", 32458))
    mix = int(p.get("career_total_years", 0)) * 701 + int(p.get("career_term", 1)) * 101 + int(p.get("career_session", 1)) * 37
    outcome_score = round(score + random.Random(seed + mix).uniform(-7, 7), 1)
    won = outcome_score >= 62
    was_pm = p.get("role") == "prime_minister"
    record = {
        "term": int(p["career_term"]), "year": int(p["career_year"]),
        "strategy": strategy["label"], "score": outcome_score, "won": won,
        "was_pm": was_pm,
    }
    p.setdefault("leadership_contests", []).append(record)
    p["leadership_cooldown_year"] = int(p.get("career_total_years", 0)) + 2
    used.append(action_id)
    if won and not was_pm:
        old_role = p.get("role", "mp")
        p["role"] = "prime_minister"
        p["last_promotion_total_year"] = int(p.get("career_total_years", 0))
        p["stats"]["party_trust"] = _clip(p["stats"].get("party_trust", 0) + 3)
        p["stats"]["parliamentary_influence"] = _clip(p["stats"].get("parliamentary_influence", 0) + 2)
        p["stats"]["public_profile"] = _clip(p["stats"].get("public_profile", 0) + 3)
        p["promotion_log"].append({"from": ROLES.get(old_role, {}).get("label", old_role), "to": ROLES["prime_minister"]["label"], "total_year": int(p.get("career_total_years", 0)), "term": int(p["career_term"]), "year": int(p["career_year"]), "via": "party leadership contest"})
        stable_mix = sum((i + 1) * ord(ch) for i, ch in enumerate(p.get("name", "MP")))
        p["portfolio_id"] = list(PORTFOLIOS)[stable_mix % len(PORTFOLIOS)]
        p["portfolio_target"] = PORTFOLIOS[p["portfolio_id"]]["targets"][0]
        p["department_score"] = max(45, int(p.get("department_score", 0)))
        p["department_progress"] = 0
        narrative = f"You win the fictional party leadership contest with a contest score of {outcome_score}. You become Prime Minister."
    elif won:
        p["stats"]["party_trust"] = _clip(p["stats"].get("party_trust", 0) + 4)
        p["faction_standing"]["party_leadership"] = _clip(factions.get("party_leadership", 50) + 6)
        narrative = f"You survive the fictional party confidence ballot with a score of {outcome_score}. The Cabinet remains under your leadership."
    else:
        p["stats"]["party_trust"] = _clip(p["stats"].get("party_trust", 0) - (10 if was_pm else 5))
        p["faction_standing"]["party_leadership"] = _clip(factions.get("party_leadership", 50) - 5)
        p["faction_standing"]["backbenchers"] = _clip(factions.get("backbenchers", 50) + 3)
        if was_pm:
            p["role"] = "mp"
            p["portfolio_id"] = None
            p["department_score"] = 0
            p["department_progress"] = 0
            narrative = f"You lose the fictional party confidence ballot (score {outcome_score}) and leave the premiership, returning to the backbenches."
        else:
            narrative = f"Your leadership bid falls short (contest score {outcome_score}). Party trust takes a hit, so you must rebuild support."
    p["last_event"] = narrative
    _record(p, "Party leadership contest", narrative)
    st.session_state.career_profile = p
    st.rerun()


def _run_cabinet_reshuffle(p, option_key):
    """Apply a fictional prime-ministerial reshuffle decision."""
    used = _current_actions(p)
    action_id = "cabinet_reshuffle"
    if len(used) >= ACTIONS_PER_SESSION or action_id in used or p.get("role") != "prime_minister":
        return
    option = CABINET_RESHUFFLE_OPTIONS[option_key]
    _apply_effects(p, option["effects"])
    for faction, delta in option.get("factions", {}).items():
        p["faction_standing"][faction] = _clip(p["faction_standing"].get(faction, 50) + delta)
    used.append(action_id)
    displaced = None
    if option_key == "remove_rival" and p.get("rivals"):
        displaced = p["rivals"][0]
        p["cabinet_exclusions"].append(displaced)
        p["cabinet_exclusions"] = p["cabinet_exclusions"][-10:]
    record = {"term": int(p["career_term"]), "year": int(p["career_year"]), "choice": option["label"], "displaced": displaced}
    p.setdefault("reshuffle_log", []).append(record)
    narrative = f"Cabinet reshuffle: {option['label']}. {option['description']}"
    if displaced:
        narrative += f" You move fictional rival {displaced} out of your inner Cabinet circle."
    elif option_key == "remove_rival":
        narrative += " You use the reshuffle to tighten Cabinet discipline; no personal rival was recorded as part of the reshuffle."
    _record(p, "Cabinet reshuffle", narrative)
    p["last_event"] = narrative
    st.session_state.career_profile = p
    st.rerun()


def _requirements_met(p, spec):
    stats = p["stats"]
    requirements_ok = (
        p["career_total_years"] >= int(spec.get("min_years", 0))
        and p["career_total_years"] > int(p.get("last_promotion_total_year", 0))
        and all(float(stats.get(key, 0)) >= float(value) for key, value in spec.get("requirements", {}).items())
    )
    delivery_threshold = {"junior_minister": 35, "minister_of_state": 42, "secretary_state": 48, "chancellor": 52}
    delivery_ok = (
        p.get("role") not in delivery_threshold
        or int(p.get("department_score", 0)) >= delivery_threshold[p["role"]]
    )
    return requirements_ok and delivery_ok


def _eligible_promotions(p):
    rules = RULES.get(p["role"], {})
    return [(role_id, spec) for role_id, spec in rules.items()
            if role_id in ROLES and _requirements_met(p, spec)]


def _format_requirements(spec):
    bits = []
    for key, threshold in spec.get("requirements", {}).items():
        label = ATTRIBUTES.get(key, key.replace("_", " ").title())
        current = int(_profile()["stats"].get(key, 0))
        bits.append(f"{label} {current}/{threshold}")
    if int(_profile().get("career_total_years", 0)) < int(spec.get("min_years", 0)):
        bits.insert(0, f"Experience {int(_profile().get('career_total_years', 0))}/{spec['min_years']} completed year(s)")
    return " · ".join(bits)


def _accept_promotion(p, role_id, spec):
    old_label = ROLES[p["role"]]["label"]
    new_label = ROLES[role_id]["label"]
    bonus = spec.get("bonus", {})
    bonus_summary = _effect_summary(bonus)
    _apply_effects(p, bonus)
    p["role"] = role_id
    p["last_promotion_total_year"] = int(p["career_total_years"])
    if role_id in GOVERNMENT_ROLES:
        stable_mix = sum((i + 1) * ord(ch) for i, ch in enumerate(p.get("name", "MP")))
        portfolio_ids = list(PORTFOLIOS)
        p["portfolio_id"] = portfolio_ids[(stable_mix + int(p.get("career_total_years", 0)) + ROLES[role_id]["rank"]) % len(portfolio_ids)]
        p["portfolio_target"] = PORTFOLIOS[p["portfolio_id"]]["targets"][0]
        p["department_score"] = max(45, int(p.get("department_score", 0)))
        p["department_progress"] = 0
    entry = {
        "from": old_label,
        "to": new_label,
        "total_year": int(p["career_total_years"]),
        "term": int(p["career_term"]),
        "year": int(p["career_year"]),
    }
    p["promotion_log"].append(entry)
    p["last_event"] = f"Promotion accepted: {new_label}. Your new responsibilities unlock a different set of actions."
    if bonus_summary:
        p["last_event"] += f" Appointment bonus: {bonus_summary}."
    _record(p, f"Appointed {new_label}", p["last_event"])
    st.session_state.career_profile = p
    st.rerun()


def _hold_election(p):
    stats = p["stats"]
    seed = int(st.session_state.get("seed", 12345))
    rng = random.Random(seed + p["career_total_years"] * 911 + p["career_term"] * 503)
    score = (
        .35 * stats["constituency_support"]
        + .15 * stats["party_trust"]
        + .12 * stats["public_profile"]
        + .10 * stats["policy_expertise"]
        + .10 * stats["integrity"]
        + .08 * stats["parliamentary_influence"]
        + .10 * stats.get("campaign_readiness", 30)
    )
    margin = round(score + rng.uniform(-8, 8), 1)
    won = margin >= 45
    result = {
        "term": int(p["career_term"]),
        "score": round(score, 1),
        "margin": margin,
        "won": won,
        "threshold": 45,
        "campaign_readiness": int(stats.get("campaign_readiness", 30)),
    }
    p["election_result"] = result
    if won:
        p["seats_won"] = int(p.get("seats_won", 0)) + 1
        p["stats"]["constituency_support"] = _clip(p["stats"]["constituency_support"] + 2)
        p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] + 1)
        text = f"Re-elected in {p['constituency']}. Your career continues into a new Parliament."
        if p["role"] == "prime_minister":
            government_score = .55 * stats["party_trust"] + .45 * stats["public_profile"] + rng.uniform(-12, 12)
            if government_score < 50:
                p["role"] = "mp"
                p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] - 8)
                p["stats"]["public_profile"] = _clip(p["stats"]["public_profile"] - 4)
                text += " Your party has lost power nationally; you return to the backbenches and must rebuild your influence."
        p["career_term"] = int(p["career_term"]) + 1
        p["career_year"] = 1
        p["career_session"] = 1
        p["last_event"] = text
        _record(p, "General election · re-elected", text)
    else:
        text = f"You lose {p['constituency']} at the general election. Your parliamentary career ends here."
        p["game_over"] = True
        p["last_event"] = text
        _record(p, "General election · seat lost", text)


def _advance(p):
    used = _current_actions(p)
    if len(used) < ACTIONS_PER_SESSION:
        return
    if int(p["career_session"]) < SESSIONS_PER_YEAR:
        p["career_session"] = int(p["career_session"]) + 1
        p["last_event"] = f"Session {p['career_session']} begins. Choose two actions to advance your career."
        _record(p, f"Parliamentary session {p['career_session']}", p["last_event"])
    elif int(p["career_year"]) < ELECTION_AFTER:
        _record_annual_report(p)
        p["career_total_years"] = int(p["career_total_years"]) + 1
        p["career_year"] = int(p["career_year"]) + 1
        p["career_session"] = 1
        p["stats"]["policy_expertise"] = _clip(p["stats"]["policy_expertise"] + 1)
        p["stats"]["integrity"] = _clip(p["stats"]["integrity"] + 1)
        p["last_event"] = f"Year {p['career_year']} begins. Experience has improved your policy expertise and integrity slightly."
        _record(p, f"Parliamentary year {p['career_year']}", p["last_event"])
    else:
        _record_annual_report(p)
        p["career_total_years"] = int(p["career_total_years"]) + 1
        _hold_election(p)
        if not p["game_over"]:
            # Reset the session action key naturally by changing term/year/session.
            pass
    st.session_state.career_profile = p
    st.rerun()


def render():
    """Modern UK Westminster career dashboard, styled after an official political portal."""
    p = _profile()
    role = ROLES.get(p.get("role"), ROLES["mp"])
    stats = p["stats"]
    used = _current_actions(p)
    remaining = max(0, ACTIONS_PER_SESSION - len(used))
    session_key = _session_key(p)
    nav_options = ["Desk", "Nation", "Plans", "Press"]
    st.session_state.setdefault("mp_active_nav", "Desk")

    safe_name = html.escape(str(p.get("name", "MP")))
    safe_constituency = html.escape(str(p.get("constituency", "Westminster")))
    safe_nation = html.escape(str(p.get("constituency_nation", "United Kingdom")))
    party = html.escape(str(p.get("party", "Independent")))
    role_label = html.escape(str(role.get("label", "MP")))

    st.markdown(
        f"""
        <div class="mp-portal">
          <div class="mp-portal-brand">
            <div class="mp-crest">£</div>
            <div><div class="mp-brand-title">Westminster</div><div class="mp-brand-sub">MP Career Portal</div></div>
          </div>
          <div class="mp-portal-motto">A UK political career simulator <span>•</span> Not an official parliamentary service</div>
          <div class="mp-user-chip"><span class="mp-avatar">{safe_name[:1].upper()}</span><div><strong>{safe_name}</strong><small>{role_label}</small></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.radio(
        "Game section",
        nav_options,
        horizontal=True,
        label_visibility="collapsed",
        key="mp_active_nav",
    )
    active_tab = st.session_state.get("mp_active_nav", "Desk")
    calendar_year = 2027 + (int(p.get("career_term", 1)) - 1) * ELECTION_AFTER + int(p.get("career_year", 1)) - 1
    season_names = ("SPR", "SUM", "BUD")
    current_step = (int(p.get("career_year", 1)) - 1) * SESSIONS_PER_YEAR + int(p.get("career_session", 1)) - 1
    timeline_tiles = []
    for year_offset in range(ELECTION_AFTER):
        display_year = calendar_year - (int(p.get("career_year", 1)) - 1) + year_offset
        for session_idx, season in enumerate(season_names):
            tile_index = year_offset * SESSIONS_PER_YEAR + session_idx
            classes = ["mp-timeline-tile"]
            if tile_index < current_step:
                classes.append("complete")
            elif tile_index == current_step and not p.get("game_over"):
                classes.append("current")
            tile_label = season
            if season == "BUD":
                tile_label += " £"
            timeline_tiles.append(
                f"<div class='{' '.join(classes)}'><small>{tile_label}</small><strong>{display_year}</strong></div>"
            )
    timeline_tiles.append(
        "<div class='mp-timeline-poll'><small>POLL</small><strong>✕</strong></div>"
    )
    term_label = "General election" if p.get("game_over") else f"Term {int(p.get('career_term', 1))} · Year {int(p.get('career_year', 1))} of {ELECTION_AFTER}"
    capital = max(0, min(10, int(round(int(stats.get("parliamentary_influence", 0)) / 10))))
    capital_dots = "".join(
        f"<span class='mp-capital-dot {'filled' if n < capital else ''}'></span>" for n in range(10)
    )
    st.markdown(
        f"""
        <div class="mp-season-strip">
          <div class="mp-season-left"><span class="mp-live-tag">CAREER</span><strong>{term_label}</strong><span class="mp-season-detail">{safe_constituency} · {safe_nation} · {html.escape(str(p.get('constituency_code', '')))}</span></div>
          <div class="mp-season-right">{party} <span>·</span> {role_label}</div>
        </div>
        <div class="mp-overview-panel">
          <div class="mp-overview-heading"><strong>Your Parliament</strong><span>{(ELECTION_AFTER - int(p.get('career_year', 1))) * SESSIONS_PER_YEAR + (SESSIONS_PER_YEAR - int(p.get('career_session', 1)) + 1)} sessions until the next general election · {len(p.get('promotion_log', []))} appointments to date</span></div>
          <div class="mp-timeline-track">{''.join(timeline_tiles)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = [
        ("Constituency", f"{int(stats.get('constituency_support', 0))}%", "Local support"),
        ("Party trust", f"{int(stats.get('party_trust', 0))}", "Whips and colleagues"),
        ("Influence", f"{int(stats.get('parliamentary_influence', 0))}", "Parliamentary capital"),
        ("Public profile", f"{int(stats.get('public_profile', 0))}", "Media recognition"),
        ("Policy expertise", f"{int(stats.get('policy_expertise', 0))}", "Subject knowledge"),
        ("Integrity", f"{int(stats.get('integrity', 0))}", "Standards and trust"),
        ("Campaign", f"{int(stats.get('campaign_readiness', 30))}%", "Election readiness"),
        ("Standards risk", f"{int(p.get('ethics_risk', 0))}/5", "Lower is safer"),
    ]
    metric_cols = st.columns(8, gap="small")
    for col, (label, value, help_text) in zip(metric_cols, metrics):
        with col:
            st.metric(label, value, help=help_text)

    if p.get("last_event"):
        st.info(p["last_event"])

    if p.get("game_over"):
        stats_now = p.get("stats", {})
        legacy_score = round(sum(float(stats_now.get(key, 0)) for key in ATTRIBUTES) / max(1, len(ATTRIBUTES)), 1)
        legacy_grade = "A" if legacy_score >= 85 else "B" if legacy_score >= 75 else "C" if legacy_score >= 65 else "D" if legacy_score >= 55 else "E" if legacy_score >= 45 else "F"
        st.markdown("## Your final Westminster report")
        summary_cols = st.columns(4, gap="medium")
        summary_cols[0].metric("Career grade", legacy_grade)
        summary_cols[1].metric("Final standing", f"{legacy_score}/100")
        summary_cols[2].metric("Years served", int(p.get("career_total_years", 0)))
        summary_cols[3].metric("Promotions", len(p.get("promotion_log", [])))
        st.caption(f"General elections won: {max(0, int(p.get('seats_won', 1)) - 1)} · Allies: {len(p.get('allies', []))} · Rivals: {len(p.get('rivals', []))} · Final standards risk: {int(p.get('ethics_risk', 0))}/5")
        with st.expander("Career record", expanded=True):
            for item in reversed(p.get("history", [])[-20:]):
                st.markdown(f"**{item['title']}** · Term {item['term']}, year {item['year']}, session {item['session']}")
                st.caption(item["text"])
        if st.button("Start a new Westminster career", type="primary", use_container_width=True):
            st.session_state.step = "setup"
            st.session_state.career_profile = None
            st.session_state.mp_active_nav = "Desk"
            st.rerun()
        return

    if active_tab == "Desk":
        left, right = st.columns([2.15, 0.95], gap="large")
        with left:
            st.markdown("## The Commons desk")
            st.caption("Your daily political work: vote, influence the party and use your two career-action slots wisely.")
            division = _division_for(p)
            saved_vote = p.get("votes_by_session", {}).get(session_key)
            whip = division.get("whip", {}).get(p.get("party", "Labour"), "Free vote")
            with st.container(border=True):
                st.markdown("<div class='mp-overline'>COMMONS DIVISION · WHIP CHECK</div>", unsafe_allow_html=True)
                st.markdown(f"### {division['title']}")
                st.write(division["description"])
                whip_label = "Free vote — decide according to your judgement." if whip == "Free vote" else f"Your party whip is **{whip}**."
                st.markdown(whip_label)
                st.caption(f"Local mandate: {MANDATES.get(p.get('local_mandate'), {}).get('label', p.get('local_mandate', 'Not set'))}. The bill, whip and tally are fictionalised game content, not current party positions.")
                if saved_vote:
                    st.success(f"Vote recorded: **{saved_vote['vote']}** · Party whip: {saved_vote['party_whip']}.")
                    result = saved_vote.get("division_result")
                    if result:
                        st.info(f"Simulated result: **{result['result']}** · Ayes {result['ayes']} – Noes {result['noes']} · Majority {result['majority']} game points.")
                    if saved_vote.get("effects_summary"):
                        st.caption(f"Career effects: {saved_vote['effects_summary']}.")
                else:
                    vote_choice = st.radio(
                        "How will you vote?",
                        VOTE_OPTIONS,
                        index=None,
                        horizontal=True,
                        key=f"career_vote_choice_{session_key}",
                        help="Following the whip tends to build party trust. Rebelling can raise your profile but may make promotion harder.",
                    )
                    if st.button("Cast vote in the Commons", type="primary", disabled=vote_choice is None, use_container_width=True):
                        if _cast_vote(p, vote_choice):
                            st.rerun()

            st.markdown("### Political standing")
            st.progress(len(used) / ACTIONS_PER_SESSION, text=f"{len(used)}/{ACTIONS_PER_SESSION} career actions used this session")
            st.markdown("### Parliamentary record")
            if p.get("history"):
                for item in reversed(p["history"][-4:]):
                    st.markdown(
                        f"<div class='mp-diary-entry'><div class='mp-diary-marker'></div><div><strong>{html.escape(str(item['title']))}</strong><p>{html.escape(str(item['text']))}</p><small>Term {item['term']} · Year {item['year']} · Session {item['session']}</small></div></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Your Westminster diary will appear here as you make decisions.")
        with right:
            with st.container(border=True):
                st.markdown("### Political capital")
                st.markdown(f"<div class='mp-capital-meter'>{capital_dots}<strong>{capital}</strong></div>", unsafe_allow_html=True)
                st.write("Your parliamentary influence fuels this meter. Use your career actions to build relationships, shape decisions and strengthen your standing.")
                st.caption(f"{remaining} of {ACTIONS_PER_SESSION} career actions remain this session. Commons votes do not consume an action slot.")
            with st.container(border=True):
                st.markdown("### The whip's mood")
                faction = p.get("faction_standing", {})
                leadership = int(faction.get("party_leadership", 50))
                if leadership >= 70:
                    mood = "The leadership trusts you with important assignments."
                elif leadership >= 45:
                    mood = "The Whips are watching, but doors remain open."
                else:
                    mood = "You are on the leadership's watchlist. Promotion may be harder."
                st.write(mood)
                st.progress(leadership / 100, text=f"Leadership confidence · {leadership}/100")
                st.caption(f"Party trust: {int(stats.get('party_trust', 0))}/100")
            with st.container(border=True):
                st.markdown("### Your diary")
                recent = list(reversed(p.get("history", [])[-3:]))
                if recent:
                    for entry in recent:
                        st.markdown(f"**{html.escape(str(entry['title']))}**")
                        st.caption(html.escape(str(entry['text'])))
                else:
                    st.caption("No entries yet.")

    elif active_tab == "Nation":
        st.markdown("## Your constituency office")
        st.caption("Local casework, campaign priorities and the next general election. Each response uses one career-action slot.")
        top_a, top_b = st.columns([1.25, 1], gap="medium")
        with top_a:
            st.markdown("### Constituency priorities")
            for key, mandate in MANDATES.items():
                selected = key == p.get("local_mandate")
                with st.container(border=True):
                    st.markdown(f"**{'✓ ' if selected else ''}{mandate['label']}**")
                    st.caption(mandate["description"])
                    if selected:
                        st.caption("Your current campaign priority")
            st.markdown("### Constituency inbox")
            st.caption("Three fictional cases arrive each parliamentary session. Choose a response to resolve the case.")
            for case in _current_inbox_cases(p):
                action_id = f"inbox_{case['id']}"
                with st.container(border=True):
                    st.markdown(f"**{case['title']}**")
                    st.write(case["description"])
                    st.caption(f"Area: {MANDATES.get(case['priority'], {}).get('label', case['priority'])}")
                    if action_id in used:
                        st.success("Case resolved this session")
                    elif remaining > 0:
                        responses = [
                            ("investigate", "Investigate and follow up"),
                            ("parliament", "Raise the issue in Parliament"),
                            ("coordinate", "Bring local partners together"),
                        ]
                        options = {key: label for key, label in responses}
                        response = st.selectbox(
                            "Response",
                            list(options),
                            format_func=lambda key: options[key],
                            key=f"inbox_response_{p['career_term']}_{p['career_year']}_{p['career_session']}_{case['id']}",
                        )
                        if st.button("Resolve case", key=f"inbox_{p['career_term']}_{p['career_year']}_{p['career_session']}_{case['id']}", use_container_width=True):
                            _resolve_inbox_case(p, case, response)
                    else:
                        st.caption("No action slots left. Advance the parliamentary session to continue.")
        with top_b:
            with st.container(border=True):
                st.markdown("### Election readiness")
                st.metric("Campaign readiness", f"{int(stats.get('campaign_readiness', 30))}/100")
                st.progress(int(stats.get("campaign_readiness", 30)) / 100)
                st.write("Canvassing, local events and showing voters you understand their priorities improve your chances at the next simulated general election.")
                if len(used) >= ACTIONS_PER_SESSION:
                    st.warning("Both action slots are used.")
            with st.container(border=True):
                st.markdown("### Local campaign actions")
                for action in PHASE2_NETWORK_ACTIONS:
                    if action["id"] not in {"doorstep_campaign", "cross_party"}:
                        continue
                    action_id = f"network_{action['id']}"
                    if action_id in used:
                        st.caption(f"Completed: {action['label']}")
                        continue
                    st.markdown(f"**{action['label']}**")
                    st.caption(action["description"])
                    if st.button("Run campaign action", key=f"local_action_{p['career_term']}_{p['career_year']}_{p['career_session']}_{action['id']}", disabled=remaining <= 0, use_container_width=True):
                        _resolve_network_action(p, action)
            with st.container(border=True):
                st.markdown("### Constituency casework record")
                local_records = [entry for entry in p.get("history", []) if str(entry.get("title", "")).startswith("Inbox:")][-6:]
                if local_records:
                    for item in reversed(local_records):
                        st.markdown(f"**{html.escape(str(item['title']))}**")
                        st.caption(html.escape(str(item['text'])))
                else:
                    st.caption("Resolved constituent issues will appear here.")

    elif active_tab == "Plans":
        st.markdown("## Policy and parliamentary plans")
        st.caption("Use your career actions to build expertise, work with colleagues and deliver your current responsibilities.")
        if p.get("role") in GOVERNMENT_ROLES:
            st.markdown("### Government portfolio and delivery")
            portfolio_id = p.get("portfolio_id") if p.get("portfolio_id") in PORTFOLIOS else list(PORTFOLIOS)[0]
            portfolio = PORTFOLIOS[portfolio_id]
            portfolio_cols = st.columns(3, gap="medium")
            portfolio_cols[0].metric("Department delivery", f"{int(p.get('department_score', 40))}/100")
            portfolio_cols[1].metric("Target progress", f"{int(p.get('department_progress', 0))}%")
            portfolio_cols[2].metric("Completed targets", len(p.get("completed_targets", [])))
            st.progress(int(p.get("department_progress", 0)) / 100, text=f"Target: {p.get('portfolio_target') or portfolio['targets'][0]}")
            with st.container(border=True):
                st.markdown("#### Set a departmental portfolio and target")
                portfolio_id_select = st.selectbox(
                    "Portfolio",
                    list(PORTFOLIOS),
                    index=list(PORTFOLIOS).index(portfolio_id),
                    format_func=lambda key: PORTFOLIOS[key]["label"],
                    key=f"portfolio_select_{p['career_term']}_{p['career_year']}_{p['career_session']}",
                )
                targets = PORTFOLIOS[portfolio_id_select]["targets"]
                current_target = p.get("portfolio_target")
                target_select = st.selectbox(
                    "Policy target",
                    targets,
                    index=targets.index(current_target) if current_target in targets else 0,
                    key=f"portfolio_target_select_{p['career_term']}_{p['career_year']}_{p['career_session']}",
                )
                if st.button("Set portfolio and target (1 action)", disabled=remaining <= 0 or "portfolio_target" in used, type="primary", use_container_width=True):
                    _set_portfolio_and_target(p, portfolio_id_select, target_select)
            delivery_cols = st.columns(2, gap="medium")
            for idx, action in enumerate(DEPARTMENT_ACTIONS):
                with delivery_cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{action['label']}**")
                        st.write(action["description"])
                        st.caption(f"{_effect_summary(action['effects'])} · +{action['score']} delivery rating · +{action['progress']}% target progress")
                        action_id = f"department_{action['id']}"
                        if st.button("Take delivery action", key=f"delivery_{p['career_term']}_{p['career_year']}_{p['career_session']}_{action['id']}", disabled=remaining <= 0 or action_id in used, use_container_width=True):
                            _run_department_action(p, action)
        else:
            st.info(f"You are currently a {role['label']}. Ministerial portfolio management unlocks once you enter government.")
        st.markdown("### Your available political actions")
        if remaining > 0:
            actions = role.get("actions", [])
            cols = st.columns(2, gap="medium")
            for index, action in enumerate(actions):
                with cols[index % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{action['label']}**")
                        st.write(action["description"])
                        summary = _effect_summary(action["effects"])
                        if summary:
                            st.caption(summary)
                        action_used = action["id"] in used
                        if st.button("Take this action", key=f"career_act_{p['career_term']}_{p['career_year']}_{p['career_session']}_{p['role']}_{action['id']}", disabled=action_used, use_container_width=True):
                            _take_action(p, action)
        else:
            st.success("Both career actions are complete. End the session to continue.")
        st.markdown("### Promotion opportunities")
        offers = _eligible_promotions(p)
        if offers:
            for role_id, spec in offers:
                with st.container(border=True):
                    st.markdown(f"**Appointment opportunity: {ROLES[role_id]['label']}**")
                    st.write(ROLES[role_id]["description"])
                    if role_id in {"junior_minister", "minister_of_state", "secretary_state", "chancellor"}:
                        threshold = {"junior_minister": 35, "minister_of_state": 42, "secretary_state": 48, "chancellor": 52}.get(p["role"], 0)
                        st.caption(f"Department delivery requirement for later promotions: {threshold}/100 or above.")
                    st.caption(_format_requirements(spec))
                    if st.button(f"Accept appointment as {ROLES[role_id]['label']}", key=f"career_promote_{p['career_term']}_{p['career_year']}_{p['role']}_{role_id}", use_container_width=True):
                        _accept_promotion(p, role_id, spec)
        else:
            next_rules = RULES.get(p["role"], {})
            if next_rules:
                with st.expander("Promotion requirements", expanded=False):
                    for role_id, spec in next_rules.items():
                        st.markdown(f"**Next step: {ROLES[role_id]['label']}**")
                        st.caption(_format_requirements(spec))
            else:
                st.caption("You have reached the top role available in this career path.")

    elif active_tab == "Press":
        st.markdown("## Politics, press and party management")
        st.caption("Westminster's news cycle is fictional gameplay. Your choices affect public profile, party trust, standards risk and political relationships.")
        news_event = _current_phase2_news(p)
        news_response = p.get("news_responses_by_session", {}).get(session_key)
        with st.container(border=True):
            st.markdown("<div class='mp-overline'>WESTMINSTER NEWS DESK · FICTIONAL EVENT</div>", unsafe_allow_html=True)
            st.markdown(f"### {news_event['headline']}")
            st.write(news_event["brief"])
            if news_response and news_response.get("event_id") == news_event["id"]:
                st.success(f"Response recorded: **{news_response['choice']}**.")
                if news_response.get("effects_summary"):
                    st.caption(f"Effects: {news_response['effects_summary']}.")
            elif remaining > 0:
                cols = st.columns(len(news_event["choices"]), gap="medium")
                for idx, choice in enumerate(news_event["choices"]):
                    with cols[idx]:
                        with st.container(border=True):
                            st.markdown(f"**{choice['label']}**")
                            st.write(choice["description"])
                            preview = _effect_summary(choice.get("effects", {}))
                            if preview:
                                st.caption(preview)
                            if st.button("Choose this response", key=f"phase2_news_{p['career_term']}_{p['career_year']}_{p['career_session']}_{news_event['id']}_{choice['id']}", use_container_width=True):
                                _resolve_news_choice(p, news_event, choice)
            else:
                st.caption("Both action slots are used. You can leave this story unanswered.")
        st.markdown("### Party factions, allies and rivals")
        faction_cols = st.columns(4, gap="small")
        for idx, (faction_key, faction_label) in enumerate(PHASE2_FACTIONS.items()):
            with faction_cols[idx]:
                faction_value = int(p.get("faction_standing", {}).get(faction_key, 50))
                st.metric(faction_label, f"{faction_value}/100")
                st.progress(faction_value / 100)
        people_cols = st.columns(2, gap="medium")
        with people_cols[0]:
            with st.container(border=True):
                st.markdown("#### Allies")
                if p.get("allies"):
                    for ally in p["allies"]:
                        st.markdown(f"<div class='mp-person-pill'>✓ {html.escape(str(ally))}</div>", unsafe_allow_html=True)
                else:
                    st.caption("No established allies yet.")
        with people_cols[1]:
            with st.container(border=True):
                st.markdown("#### Rivals")
                if p.get("rivals"):
                    for rival in p["rivals"]:
                        st.markdown(f"<div class='mp-person-pill rival'>! {html.escape(str(rival))}</div>", unsafe_allow_html=True)
                else:
                    st.caption("No declared rivals yet.")
        if remaining > 0:
            st.markdown("### Political networking")
            network_cols = st.columns(2, gap="medium")
            for idx, action in enumerate(PHASE2_NETWORK_ACTIONS):
                with network_cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{action['label']}**")
                        st.write(action["description"])
                        summary = _effect_summary(action.get("effects", {}))
                        if summary:
                            st.caption(summary)
                        action_id = f"network_{action['id']}"
                        if st.button("Take political action", key=f"phase2_network_{p['career_term']}_{p['career_year']}_{p['career_session']}_{action['id']}", disabled=action_id in used, use_container_width=True):
                            _resolve_network_action(p, action)
        st.markdown("### Parliamentary standards")
        if int(p.get("ethics_risk", 0)) >= 3:
            st.error(f"High standards risk: {p['ethics_risk']}/5. Another transparency lapse could trigger severe political consequences.")
        elif int(p.get("ethics_risk", 0)) >= 1:
            st.warning(f"Standards risk: {p['ethics_risk']}/5. Declaration, transparency and proper process protect your reputation.")
        else:
            st.success("Standards risk is low. Continue declaring interests and explaining decisions transparently.")
        if _leadership_eligible(p):
            st.markdown("### Party leadership")
            st.caption("A fictional internal party leadership contest. The outcome reflects your stats, faction support and chosen approach.")
            strategy_key = st.selectbox("Leadership strategy", list(LEADERSHIP_STRATEGIES), format_func=lambda key: LEADERSHIP_STRATEGIES[key]["label"], key=f"leadership_strategy_{p['career_term']}_{p['career_year']}_{p['career_session']}")
            st.caption(LEADERSHIP_STRATEGIES[strategy_key]["description"])
            label = "Test your mandate in a confidence ballot" if p.get("role") == "prime_minister" else "Contest the party leadership"
            if st.button(label, key=f"leadership_contest_{p['career_term']}_{p['career_year']}_{p['career_session']}", disabled=remaining <= 0 or "leadership_contest" in used, type="primary", use_container_width=True):
                _run_leadership_contest(p, strategy_key)
        elif int(p.get("career_total_years", 0)) < 4 or int(stats.get("party_trust", 0)) < 70:
            st.caption("Leadership contests unlock for senior politicians with enough parliamentary experience, trust and influence.")
        if p.get("role") == "prime_minister":
            st.markdown("### Prime Minister's Cabinet")
            reshuffle_cols = st.columns(3, gap="medium")
            for idx, (option_key, option) in enumerate(CABINET_RESHUFFLE_OPTIONS.items()):
                with reshuffle_cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"**{option['label']}**")
                        st.write(option["description"])
                        st.caption(_effect_summary(option["effects"]))
                        if st.button("Carry out reshuffle", key=f"reshuffle_{p['career_term']}_{p['career_year']}_{p['career_session']}_{option_key}", disabled=remaining <= 0 or "cabinet_reshuffle" in used, use_container_width=True):
                            _run_cabinet_reshuffle(p, option_key)
        st.markdown("### Annual Westminster report cards")
        reports = list(p.get("annual_reports", []))
        if reports:
            for report in reversed(reports[-5:]):
                with st.container(border=True):
                    st.markdown(f"**Term {report['term']} · Year {report['year']} — Grade {report['grade']} ({report['score']}/100)**")
                    st.caption(f"Strongest subject: {report['strongest']} · Focus for improvement: {report['focus']}")
                    st.caption(f"Actions: {report['actions_taken']} · Commons votes: {report['votes_cast']} · Followed whip: {report['whips_followed']}")
                    if report.get("portfolio"):
                        st.caption(f"{report['portfolio']} delivery rating: {report['department_score']}/100")
        else:
            st.caption("Your first annual report card appears after the end of your first parliamentary year.")
        with st.expander("Voting record", expanded=False):
            votes = list(p.get("vote_history", []))
            if votes:
                for item in reversed(votes[-12:]):
                    st.markdown(f"**{item['vote']}** · {item['title']}")
                    st.caption(f"Term {item['term']}, year {item['year']}, session {item['session']} · whip: {item['party_whip']} · {item.get('effects_summary', 'No stat change')}")
            else:
                st.caption("Votes will appear after your first Commons division.")
        with st.expander("Full career record", expanded=False):
            for item in reversed(p.get("history", [])[-20:]):
                st.markdown(f"**{item['title']}** · Term {item['term']}, year {item['year']}, session {item['session']}")
                st.caption(item["text"])

    if len(used) >= ACTIONS_PER_SESSION:
        st.divider()
        st.warning("Your two career-action slots are used. You can still cast the current Commons vote, then continue to the next session.")
    if len(used) >= ACTIONS_PER_SESSION and not p.get("game_over"):
        if st.button(
            "End parliamentary session and continue",
            key=f"advance_session_{p['career_term']}_{p['career_year']}_{p['career_session']}",
            type="primary",
            use_container_width=True,
        ):
            _advance(p)
    st.markdown("<div class='mp-footer-note'>Fictionalised UK parliamentary career simulator · Constituency boundaries use the July 2024 register · No live party whip or current-affairs claims</div>", unsafe_allow_html=True)
