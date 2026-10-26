"""Playable political career mode: from backbench MP towards senior office."""
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
    "Labour": 40,
    "Conservative": 24,
    "Liberal Democrats": 13,
    "Reform UK": 8,
    "Green Party": 5,
    "SNP": 6,
    "Plaid Cymru": 4,
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
        "public_profile": 25, "policy_expertise": 30, "integrity": 78
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


def _requirements_met(p, spec):
    stats = p["stats"]
    return (
        p["career_total_years"] >= int(spec.get("min_years", 0))
        and p["career_total_years"] > int(p.get("last_promotion_total_year", 0))
        and all(float(stats.get(key, 0)) >= float(value) for key, value in spec.get("requirements", {}).items())
    )


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
        .40 * stats["constituency_support"]
        + .15 * stats["party_trust"]
        + .15 * stats["public_profile"]
        + .10 * stats["policy_expertise"]
        + .10 * stats["integrity"]
        + .10 * stats["parliamentary_influence"]
    )
    margin = round(score + rng.uniform(-8, 8), 1)
    won = margin >= 45
    result = {
        "term": int(p["career_term"]),
        "score": round(score, 1),
        "margin": margin,
        "won": won,
        "threshold": 45,
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
        p["career_total_years"] = int(p["career_total_years"]) + 1
        p["career_year"] = int(p["career_year"]) + 1
        p["career_session"] = 1
        p["stats"]["policy_expertise"] = _clip(p["stats"]["policy_expertise"] + 1)
        p["stats"]["integrity"] = _clip(p["stats"]["integrity"] + 1)
        p["last_event"] = f"Year {p['career_year']} begins. Experience has improved your policy expertise and integrity slightly."
        _record(p, f"Parliamentary year {p['career_year']}", p["last_event"])
    else:
        p["career_total_years"] = int(p["career_total_years"]) + 1
        _hold_election(p)
        if not p["game_over"]:
            # Reset the session action key naturally by changing term/year/session.
            pass
    st.session_state.career_profile = p
    st.rerun()


def render():
    """Main career-mode screen."""
    p = _profile()
    role = ROLES.get(p["role"], ROLES["mp"])
    used = _current_actions(p)
    remaining = max(0, ACTIONS_PER_SESSION - len(used))
    st.markdown(
        f"<div class='ch-banner'><div class='ch-head'><span class='ch-title'>🏛️ {p['name']}</span>"
        f"<span class='sub'>{role['label'].upper()} · PARLIAMENTARY CAREER</span></div>"
        f"<div class='sub'>{p['constituency']} · {p['constituency_nation']} · {p['constituency_code']} · "
        f"Term {p['career_term']} · Year {p['career_year']} of {ELECTION_AFTER} · Session {p['career_session']} of {SESSIONS_PER_YEAR}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"## {role['label']}")
    st.write(role["description"])
    st.caption(f"Career ambition: {DATA['ambitions'][p['ambition']]['label']}. This is a fictionalised career model; promotions depend on your stats and the path you choose.")

    stats = p["stats"]
    st.markdown("### Your political standing")
    columns = st.columns(3, gap="medium")
    for index, (key, label) in enumerate(ATTRIBUTES.items()):
        with columns[index % 3]:
            st.metric(label, f"{int(stats.get(key, 0))}/100",
                      help="A game attribute from 0 to 100. Actions and promotion bonuses change it.")
    st.progress(len(used) / ACTIONS_PER_SESSION, text=f"{len(used)}/{ACTIONS_PER_SESSION} actions used this session")

    if p.get("last_event"):
        st.info(p["last_event"])

    if p.get("game_over"):
        st.error("Career over — you lost your seat at the general election.")
        if st.button("Start a new career", type="primary"):
            st.session_state.step = "setup"
            st.session_state.game_mode = "chancellor"
            st.session_state.career_profile = None
            st.rerun()
        with st.expander("Career record", expanded=True):
            for item in reversed(p["history"][-15:]):
                st.markdown(f"**{item['title']}** · Term {item['term']}, year {item['year']}, session {item['session']}")
                st.caption(item["text"])
        return

    if p.get("election_result"):
        result = p["election_result"]
        if result["won"]:
            st.success(f"Election result: re-elected (career score {result['score']:.1f}, result {result['margin']:.1f}; threshold {result['threshold']}).")
        else:
            st.error(f"Election result: seat lost (career score {result['score']:.1f}, result {result['margin']:.1f}; threshold {result['threshold']}).")

    st.markdown("### 🗳️ Your Commons division")
    st.caption("Every session includes one vote. Voting is separate from your two career actions, just as MPs vote on multiple matters alongside their wider parliamentary work.")
    division = _division_for(p)
    session_key = _session_key(p)
    saved_vote = p.get("votes_by_session", {}).get(session_key)
    whip = division.get("whip", {}).get(p.get("party", "Labour"), "Free vote")
    with st.container(border=True):
        st.markdown(f"**{division['title']}**")
        st.write(division["description"])
        whip_label = "Free vote — decide according to your judgement." if whip == "Free vote" else f"Your party whip is **{whip}**."
        st.markdown(whip_label)
        st.caption(f"Your selected local priority: {MANDATES[p['local_mandate']]['label']}. Matching that priority can increase constituency support when the bill concerns it.")
        st.caption("The bill, party whip and simplified vote tally are fictionalised game content. Tally points use abstract game-only party weights; they are not real seat counts, a historical division or current official party positions.")
        if saved_vote:
            st.success(f"Vote recorded: **{saved_vote['vote']}** · Party whip: {saved_vote['party_whip']}.")
            result = saved_vote.get("division_result")
            if result:
                st.info(f"Simulated division result: **{result['result']}** · Ayes {result['ayes']} – Noes {result['noes']} · Majority {result['majority']} game points.")
            if saved_vote.get("effects_summary"):
                st.caption(f"Career effects: {saved_vote['effects_summary']}.")
            st.caption("You can vote on the next division when the next parliamentary session begins.")
        else:
            vote_choice = st.radio(
                "How will you vote?",
                VOTE_OPTIONS,
                index=None,
                horizontal=True,
                key=f"career_vote_choice_{session_key}",
                help="Following the whip usually builds party trust. Rebelling can boost your profile and integrity but may make future promotion harder. Abstaining can be a middle ground."
            )
            if st.button("Cast vote in the Commons", type="primary", disabled=vote_choice is None, use_container_width=True):
                if _cast_vote(p, vote_choice):
                    st.rerun()

    st.markdown("### 📬 Constituency inbox")
    st.caption("Three fictional constituent cases arrive each session. Choose one of the responses below; resolving a case uses one of your two career-action slots. A case matching your campaign priority earns a small extra local-support bonus.")
    inbox_cols = st.columns(3, gap="medium")
    for index, case in enumerate(_current_inbox_cases(p)):
        action_id = f"inbox_{case['id']}"
        with inbox_cols[index]:
            with st.container(border=True):
                st.markdown(f"**{case['title']}**")
                st.write(case["description"])
                priority_label = MANDATES.get(case["priority"], {}).get("label", case["priority"])
                st.caption(f"Area: {priority_label}")
                if action_id in used:
                    st.success("Case resolved this session")
                else:
                    for approach, label in (
                        ("investigate", "Investigate and follow up"),
                        ("parliament", "Raise it in Parliament"),
                        ("coordinate", "Bring local partners together"),
                    ):
                        if st.button(
                            label,
                            key=f"inbox_{p['career_term']}_{p['career_year']}_{p['career_session']}_{case['id']}_{approach}",
                            disabled=remaining <= 0,
                            use_container_width=True,
                        ):
                            _resolve_inbox_case(p, case, approach)

    st.markdown("### Parliamentary business")
    st.caption("Choose two career actions per session. A vote does not use one of these action slots.")
    if remaining:
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
                    if st.button("Take this action", key=f"career_act_{p['career_term']}_{p['career_year']}_{p['career_session']}_{p['role']}_{action['id']}",
                                 disabled=action["id"] in used, use_container_width=True):
                        _take_action(p, action)
    else:
        st.success("Session actions complete. You can advance to the next session.")

    if len(used) >= ACTIONS_PER_SESSION:
        if st.button("End session and continue", type="primary", use_container_width=True):
            _advance(p)

    st.markdown("### Promotion opportunities")
    offers = _eligible_promotions(p)
    if offers:
        st.success("You have earned an opportunity. Accept one appointment; you can pursue another later in your career.")
        cols = st.columns(min(2, len(offers)), gap="medium")
        for index, (role_id, spec) in enumerate(offers):
            with cols[index % len(cols)]:
                with st.container(border=True):
                    st.markdown(f"**{ROLES[role_id]['label']}**")
                    st.write(ROLES[role_id]["description"])
                    if st.button(f"Accept promotion", key=f"career_promote_{p['career_term']}_{p['career_year']}_{p['role']}_{role_id}",
                                 use_container_width=True):
                        _accept_promotion(p, role_id, spec)
    else:
        next_rules = RULES.get(p["role"], {})
        if next_rules:
            with st.expander("Promotion requirements", expanded=False):
                for role_id, spec in next_rules.items():
                    st.markdown(f"**Next step: {ROLES[role_id]['label']}**")
                    st.caption(_format_requirements(spec))
        else:
            st.caption("You have reached the top role available in this career path. Focus on retaining power at the next election.")

    with st.expander("🗳️ Voting record", expanded=False):
        votes = list(p.get("vote_history", []))
        if votes:
            for item in reversed(votes[-12:]):
                st.markdown(f"**{item['vote']}** · {item['title']}")
                st.caption(f"Term {item['term']}, year {item['year']}, session {item['session']} · party whip: {item['party_whip']} · {item.get('effects_summary', 'No stat change')}")
        else:
            st.caption("Your votes will appear here after the first Commons division.")

    with st.expander("Career record & recent decisions", expanded=False):
        for item in reversed(p["history"][-12:]):
            st.markdown(f"**{item['title']}** · Term {item['term']}, year {item['year']}, session {item['session']}")
            st.caption(item["text"])
