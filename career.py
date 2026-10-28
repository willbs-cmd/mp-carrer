"""Playable political career mode: from backbench MP towards senior office."""
import concurrent.futures
import html
import json
import random
import re
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

import achievements
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
PARLIAMENT_COMPOSITION = load_json("parliament_composition_2026-10-26.json")
DIVISIONS = DIVISION_DATA["divisions"]
DIVISION_BY_ID = {row["id"]: row for row in DIVISIONS}
MANDATES = DIVISION_DATA["mandates"]
DIFFICULTIES = DATA["difficulties"]
DEFAULT_DIFFICULTY = "standard"
# Starting values for every career attribute (also used to repair older saves).
DEFAULT_STATS = {
    "constituency_support": 58,
    "party_trust": 48,
    "parliamentary_influence": 24,
    "public_profile": 25,
    "policy_expertise": 30,
    "integrity": 78,
    "campaign_readiness": 30,
}
STAT_HISTORY_LIMIT = 60
# Minimum department delivery rating needed to be promoted out of each ministerial role.
DELIVERY_THRESHOLDS = {"junior_minister": 35, "minister_of_state": 42, "secretary_state": 48, "chancellor": 52}
NAV_OPTIONS = ("Desk", "Nation", "Plans", "Press", "Career", "Parliament", "Polling")
NAV_LABELS = {
    "Desk": "🗳️ Commons vote",
    "Nation": "🏠 Constituency",
    "Plans": "📜 Plans & bills",
    "Press": "📰 Press & party",
    "Career": "📈 Career",
    "Parliament": "🏛️ Parliament",
    "Polling": "📊 Voting intention",
}
VOTE_OPTIONS = ("Aye", "No", "Abstain")


# Commons divisions use full seat counts, rather than percentages or 100 game points.
# Counts are a dated snapshot of the UK Parliament's state-of-parties list.
SIMULATED_PARTY_SEATS = {
    row["party"]: int(row["seats"])
    for row in PARLIAMENT_COMPOSITION["commons"]["seats"]
}
SIMULATED_TOTAL_SEATS = sum(SIMULATED_PARTY_SEATS.values())
SIMULATED_NON_VOTING_PARTIES = {"Sinn Féin", "Speaker"}
UK_PARLIAMENT_API = "https://members-api.parliament.uk/api/Members/Search"

PARTY_COLOURS = {
    "Labour": "#E4003B",
    "Conservative": "#0087DC",
    "Liberal Democrats": "#FAA61A",
    "Liberal Democrat": "#FAA61A",
    "Reform UK": "#12B6CF",
    "Green Party": "#02A95C",
    "SNP": "#F6C900",
    "Plaid Cymru": "#005B54",
    "Democratic Unionist Party (DUP)": "#D46A4E",
    "DUP": "#D46A4E",
    "Sinn Féin": "#326760",
    "Alliance Party of Northern Ireland": "#F7BE00",
    "Alliance": "#F7BE00",
    "Social Democratic and Labour Party (SDLP)": "#2AA82D",
    "SDLP": "#2AA82D",
    "Ulster Unionist Party (UUP)": "#48A5E0",
    "UUP": "#48A5E0",
    "Your Party": "#A855F7",
    "Restore Britain": "#303846",
    "Traditional Unionist Voice (TUV)": "#3A6EA5",
    "TUV": "#3A6EA5",
    "Independent": "#667085",
    "Speaker": "#8B929B",
    "Conservative Independent": "#4D79A8",
    "Crossbench": "#AEB6C2",
    "Non-affiliated": "#8793A2",
    "Bishops": "#B89C55",
    "Lord Speaker": "#8B929B",
    "Vacant / no current MP": "#D7DDE5",
    "Party data unavailable": "#D7DDE5",
}


# Fictional vote-intention baseline weights: deliberately invented game data,
# not current polling, a forecast, or a statistically calibrated model.
POLLING_BASELINE = {
    "Labour": 25.0, "Conservative": 20.0, "Reform UK": 18.0,
    "Liberal Democrats": 13.0, "Green Party": 9.0, "Your Party": 4.0,
    "Independent": 3.0, "SNP": 3.5, "Plaid Cymru": 1.8,
    "Restore Britain": 1.2, "Democratic Unionist Party (DUP)": 0.7,
    "Sinn Féin": 0.7, "Alliance Party of Northern Ireland": 0.5,
    "Social Democratic and Labour Party (SDLP)": 0.5,
    "Ulster Unionist Party (UUP)": 0.3, "Traditional Unionist Voice (TUV)": 0.2,
}
POLLING_ACTIONS = [
    {
        "id": "poll_national_tour", "label": "Launch a national campaign tour",
        "description": "Visit several regions, give interviews and push your party's message. The in-game polling shift is fictional and not guaranteed to last.",
        "poll_shift": 1.4,
        "effects": {"public_profile": 4, "campaign_readiness": 5, "constituency_support": 1},
    },
    {
        "id": "poll_policy_launch", "label": "Launch a major policy announcement",
        "description": "Put forward a clear proposal and give journalists a focused policy story.",
        "poll_shift": 1.0,
        "effects": {"policy_expertise": 3, "public_profile": 2, "party_trust": 1},
    },
    {
        "id": "poll_voter_roundtable", "label": "Hold a national voter roundtable",
        "description": "Listen to fictional voters and adjust your campaign priorities. This gives a small game-only polling nudge.",
        "poll_shift": 0.6,
        "effects": {"integrity": 2, "policy_expertise": 1, "campaign_readiness": 3},
    },
]

MANIFESTO_PLEDGES = {
    "nhs_access": {
        "label": "Improve access to NHS appointments",
        "description": "Promise a practical plan to improve GP access and reduce avoidable delays.",
        "attribute": "policy_expertise", "threshold": 42,
    },
    "cost_of_living": {
        "label": "Help households with the cost of living",
        "description": "Commit to a credible plan on essential bills, wages and household security.",
        "attribute": "integrity", "threshold": 48,
    },
    "housing": {
        "label": "Improve housing and renters' protections",
        "description": "Promise action on housing quality, affordability and renters' concerns.",
        "attribute": "constituency_support", "threshold": 50,
    },
    "transport": {
        "label": "Strengthen local transport links",
        "description": "Commit to better local bus, rail and access-to-work connections.",
        "attribute": "campaign_readiness", "threshold": 42,
    },
    "skills": {
        "label": "Expand skills and apprenticeships",
        "description": "Promise more routes into training, apprenticeships and secure work.",
        "attribute": "policy_expertise", "threshold": 38,
    },
    "transparency": {
        "label": "Raise standards and transparency",
        "description": "Commit to clear declarations, honest reporting and accountable decisions.",
        "attribute": "integrity", "threshold": 60,
    },
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

PRIVATE_MEMBERS_BILLS = {
    "gp_access": {
        "label": "GP Access and Appointment Standards Bill",
        "description": "A fictional proposal to improve GP appointment access and publish local access standards.",
        "priority": "public_services",
        "policy_area": "Health and social care",
    },
    "renters_repair": {
        "label": "Renters' Repairs and Healthy Homes Bill",
        "description": "A fictional proposal to strengthen repair response times and reporting on serious housing hazards.",
        "priority": "cost_living",
        "policy_area": "Housing",
    },
    "bus_connectivity": {
        "label": "Local Bus Connectivity Bill",
        "description": "A fictional proposal to improve local bus information and protect links to essential services.",
        "priority": "climate_transport",
        "policy_area": "Transport",
    },
    "skills_guarantee": {
        "label": "Apprenticeships and Skills Guarantee Bill",
        "description": "A fictional proposal to expand employer-backed apprenticeships and practical training routes.",
        "priority": "jobs_growth",
        "policy_area": "Education and employment",
    },
    "contract_transparency": {
        "label": "Public Contracts Transparency Bill",
        "description": "A fictional proposal to make public contract awards and performance reporting easier to scrutinise.",
        "priority": "integrity",
        "policy_area": "Public accountability",
    },
    "flood_resilience": {
        "label": "Community Flood Resilience Bill",
        "description": "A fictional proposal to improve local flood preparation plans and public reporting on resilience work.",
        "priority": "climate_transport",
        "policy_area": "Environment and local resilience",
    },
}

PRIVATE_BILL_STAGES = {
    "drafting": "Draft and build sponsors",
    "committee": "Committee stage",
    "report": "Report stage",
    "assented": "Royal Assent — Bill becomes law",
    "defeated": "Bill did not pass",
}

PETITION_TOPICS = {
    "nhs_access": {"label": "Improve local NHS access", "priority": "public_services", "description": "Ask ministers to improve access to GP appointments and local health services."},
    "housing_repairs": {"label": "Act on poor housing conditions", "priority": "cost_living", "description": "Call for quicker action on serious disrepair and healthier rented homes."},
    "bus_routes": {"label": "Protect local bus routes", "priority": "climate_transport", "description": "Ask for a reliable transport link to colleges, work, shops and appointments."},
    "youth_opportunities": {"label": "Expand youth skills and apprenticeships", "priority": "jobs_growth", "description": "Call for more local training, apprenticeships and routes into good jobs."},
    "neighbourhood_safety": {"label": "Improve neighbourhood safety", "priority": "crime_public_safety", "description": "Call for better coordination on local safety concerns and public-space problems."},
    "public_spending": {"label": "Make public spending more transparent", "priority": "integrity", "description": "Ask public bodies to explain major spending decisions and publish clearer progress reports."},
}


def new_profile(name="Alex Morgan", constituency="Aberafan Maesteg",
                ambition="policy_specialist", local_mandate="public_services", party="Labour",
                difficulty=DEFAULT_DIFFICULTY):
    """Create an MP profile tied to a real 2024 Westminster constituency."""
    record = CONSTITUENCY_BY_NAME.get(constituency)
    if record is None:
        record = CONSTITUENCIES[0]
    constituency = record["name"]
    local_mandate = local_mandate if local_mandate in MANDATES else "public_services"
    difficulty = difficulty if difficulty in DIFFICULTIES else DEFAULT_DIFFICULTY
    stats = dict(DEFAULT_STATS)
    for key, value in DIFFICULTIES[difficulty]["stat_bonus"].items():
        stats[key] = _clip(stats.get(key, 0) + value)
    ambition_spec = DATA["ambitions"].get(ambition, DATA["ambitions"]["policy_specialist"])
    for key, value in ambition_spec["effects"].items():
        stats[key] = _clip(stats.get(key, 0) + value)
    electoral_seed = (
        73129
        + sum((index + 1) * ord(char) for index, char in enumerate(f"{constituency}|{party}|{name}"))
        + int(st.session_state.get("seed", 12345))
    )
    electoral_rng = random.Random(electoral_seed)
    if difficulty == "relaxed":
        starting_majority = round(electoral_rng.uniform(8.0, 18.0), 1)
    elif difficulty == "hard":
        starting_majority = round(electoral_rng.uniform(1.0, 8.0), 1)
    else:
        starting_majority = round(electoral_rng.uniform(3.0, 14.0), 1)

    profile = {
        "name": (name or "Alex Morgan").strip()[:70],
        "party": party if party in DIVISION_DATA["party_names"] else "Labour",
        "constituency": constituency,
        "constituency_code": record["code"],
        "constituency_nation": record["nation"],
        "local_mandate": local_mandate,
        "ambition": ambition if ambition in DATA["ambitions"] else "policy_specialist",
        "role": "mp",
        "difficulty": difficulty,
        "starting_seat_margin": starting_majority,
        "polling_baseline": None,
        "government_status": "government" if party == "Labour" else "opposition",
        "stats": stats,
        "stat_history": [],
        "achievements": [],
        "career_year": 1,
        "career_term": 1,
        "career_session": 1,
        "career_total_years": 0,
        "actions_by_session": {},
        "division_by_session": {},
        "votes_by_session": {},
        "vote_history": [],
        "voting_intention": _initial_voting_intention(
            party if party in DIVISION_DATA["party_names"] else "Labour",
            (name or "Alex Morgan").strip()[:70],
            constituency,
        ),
        "polling_history": [],
        "polling_baseline": None,
        "polling_last_change": 0.0,
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
        "private_members_bill": None,
        "private_bill_history": [],
        "petition_campaign": None,
        "petition_history": [],
        "manifesto_pledges": [],
        "manifesto_history": [],
    }
    _record_stat_snapshot(profile, "Start")
    return profile


def _ui_progress(value, text=None):
    """Render one accessible, party-coloured progress bar without nested default themes."""
    try:
        percent = max(0.0, min(100.0, float(value) * 100.0))
    except (TypeError, ValueError):
        percent = 0.0
    label = ""
    if text:
        label = f"<div class='mp-progress-label'>{html.escape(str(text))}</div>"
    st.markdown(
        f"<div class='mp-progress-wrap'>{label}<div class='mp-progress-track' role='progressbar' aria-valuenow='{int(round(percent))}' aria-valuemin='0' aria-valuemax='100' aria-label='{int(round(percent))}% complete'><div class='mp-progress-fill' style='width:{percent:.2f}%'></div></div></div>",
        unsafe_allow_html=True,
    )


def _clip(value, low=0, high=100):
    return max(low, min(high, int(round(value))))


def _profile():
    p = st.session_state.get("career_profile")
    if not isinstance(p, dict):
        p = new_profile()
        st.session_state.career_profile = p
    p.setdefault("stats", {})
    for key, value in DEFAULT_STATS.items():
        p["stats"].setdefault(key, value)
    if p.get("difficulty") not in DIFFICULTIES:
        p["difficulty"] = DEFAULT_DIFFICULTY
    p.setdefault("stat_history", [])
    p.setdefault("achievements", [])
    p.setdefault("actions_by_session", {})
    p.setdefault("division_by_session", {})
    p.setdefault("votes_by_session", {})
    p.setdefault("vote_history", [])
    p.setdefault("history", [])
    p.setdefault("manifesto_pledges", [])
    p.setdefault("manifesto_history", [])
    # Upgrade votes saved before the full House model was introduced. This
    # avoids showing the old 100-point result or missing total_seats key after
    # a player refreshes the app mid-session.
    for saved_vote in p.get("votes_by_session", {}).values():
        if not isinstance(saved_vote, dict):
            continue
        stored_result = saved_vote.get("division_result")
        if isinstance(stored_result, dict) and int(stored_result.get("total_seats", 0)) == SIMULATED_TOTAL_SEATS:
            continue
        division = DIVISION_BY_ID.get(saved_vote.get("division_id"))
        vote_choice = saved_vote.get("vote")
        if division and vote_choice in VOTE_OPTIONS:
            saved_party_profile = dict(p)
            saved_party_profile["party"] = saved_vote.get("party", p.get("party", "Labour"))
            saved_vote["division_result"] = _simulate_division_result(saved_party_profile, division, vote_choice)
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
    # Add the fictional polling series to careers saved before this feature.
    _ensure_polling_state(p)
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
    p.setdefault("private_members_bill", None)
    p.setdefault("private_bill_history", [])
    p.setdefault("petition_campaign", None)
    p.setdefault("petition_history", [])
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


def _award_achievements(p):
    """Unlock any newly earned achievements, log them and show a toast."""
    for achievement in achievements.check_achievements(p):
        _record(p, f"Achievement: {achievement['label']}", achievement["description"])
        st.toast(f"{achievement['icon']} Achievement unlocked: {achievement['label']}")


def _ethics_limit(p):
    """Standards-risk level at which a scandal triggers (depends on difficulty)."""
    return int(DIFFICULTIES.get(p.get("difficulty"), DIFFICULTIES[DEFAULT_DIFFICULTY])["ethics_limit"])


def _record_stat_snapshot(p, label):
    """Append the current stats to the history used by the Career tab chart."""
    history = p.setdefault("stat_history", [])
    entry = {
        "label": label,
        "term": int(p.get("career_term", 1)),
        "year": int(p.get("career_year", 1)),
        "session": int(p.get("career_session", 1)),
        "stats": {key: int(p["stats"].get(key, 0)) for key in ATTRIBUTES},
    }
    if history and history[-1].get("label") == label:
        history[-1] = entry
    else:
        history.append(entry)
    p["stat_history"] = history[-STAT_HISTORY_LIMIT:]


def _mix_hex(colour, other, amount):
    """Blend ``colour`` toward ``other`` (both ``#RRGGBB``) by ``amount`` (0-1)."""
    c = colour.lstrip("#")
    o = other.lstrip("#")
    mixed = [round(int(c[i:i + 2], 16) * (1 - amount) + int(o[i:i + 2], 16) * amount) for i in (0, 2, 4)]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def _party_theme(party):
    """Return ``(accent, dark, pale)`` CSS colours for a party."""
    accent = PARTY_COLOURS.get(party, PARTY_COLOURS["Independent"])
    return accent, _mix_hex(accent, "#000000", 0.32), _mix_hex(accent, "#FFFFFF", 0.88)


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
    """Simulate a Commons division with attendance, whip loyalty and a pivotal player vote."""
    seed = int(st.session_state.get("seed", 12345))
    session_mix = sum((index + 1) * ord(char) for index, char in enumerate(f"{_session_key(p)}|{division.get('id', '')}"))
    rng = random.Random(seed + session_mix)
    ayes = noes = abstentions = non_voting = 0
    player_party = p.get("party", "Labour")
    seat_counts = dict(SIMULATED_PARTY_SEATS)
    if int(seat_counts.get(player_party, 0)) <= 0:
        replacement_party = max(
            (name for name in seat_counts if name not in SIMULATED_NON_VOTING_PARTIES and name != "Speaker"),
            key=lambda name: seat_counts[name],
        )
        seat_counts[replacement_party] = max(0, int(seat_counts[replacement_party]) - 1)
        seat_counts[player_party] = 1

    strength = int(division.get("whip_strength", 1) or 1)
    loyalty = {1: 0.90, 2: 0.96, 3: 0.99}.get(strength, 0.90)
    attendance = {1: 0.94, 2: 0.96, 3: 0.97}.get(strength, 0.94)
    for party_name, seats in seat_counts.items():
        party_seats = max(0, int(seats))
        if party_name == "Speaker" or (party_name == "Sinn Féin" and player_party != "Sinn Féin"):
            non_voting += party_seats
            abstentions += party_seats
            continue
        bloc_weight = party_seats - (1 if party_name == player_party else 0)
        whip = division.get("whip", {}).get(party_name, "Free vote")
        for _ in range(max(0, bloc_weight)):
            if rng.random() > attendance:
                non_voting += 1
                abstentions += 1
                continue
            if whip in ("Aye", "No"):
                member_vote = whip if rng.random() < loyalty else ("No" if whip == "Aye" else "Aye")
            else:
                member_vote = "Aye" if rng.random() < 0.5 else "No"
            if member_vote == "Aye":
                ayes += 1
            else:
                noes += 1

    if choice == "Aye":
        ayes += 1
    elif choice == "No":
        noes += 1
    else:
        abstentions += 1

    return {
        "ayes": int(ayes), "noes": int(noes), "abstentions": int(abstentions),
        "non_voting": int(non_voting), "total_seats": int(sum(seat_counts.values())),
        "votes_cast": int(ayes + noes),
        "result": "Passed" if ayes > noes else "Rejected",
        "majority": int(abs(ayes - noes)),
        "whip_strength": strength,
        "attendance_rate": round((ayes + noes) / max(1, sum(seat_counts.values()) - non_voting) * 100, 1),
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


def _make_manifesto_pledge(p, pledge_id):
    """Add a fictional manifesto commitment; its credibility is assessed on election night."""
    spec = MANIFESTO_PLEDGES.get(pledge_id)
    if not spec:
        return
    used = _current_actions(p)
    pledges = p.setdefault("manifesto_pledges", [])
    if len(used) >= ACTIONS_PER_SESSION or pledge_id in used or len(pledges) >= 3:
        return
    if any(item.get("id") == pledge_id for item in pledges):
        return
    pledges.append({
        "id": pledge_id,
        "label": spec["label"],
        "description": spec["description"],
        "attribute": spec["attribute"],
        "threshold": int(spec["threshold"]),
        "announced_term": int(p.get("career_term", 1)),
        "announced_year": int(p.get("career_year", 1)),
        "status": "pending",
    })
    used.append(pledge_id)
    effects = {"public_profile": 2, "campaign_readiness": 3}
    _apply_effects(p, effects)
    summary = _effect_summary(effects)
    text = f"Manifesto promise announced: {spec['label']}. Voters will judge your credibility at the next general election."
    _record(p, "Manifesto: " + spec["label"], text + (f" Effects: {summary}." if summary else ""))
    p["last_event"] = text
    st.session_state.career_profile = p
    st.rerun()


def _score_manifesto_pledges(p):
    """Resolve manifesto commitments against game-stat thresholds at election time."""
    result = []
    score_effect = 0
    stats = p.get("stats", {})
    for pledge in p.get("manifesto_pledges", []):
        attribute = pledge.get("attribute", "policy_expertise")
        threshold = int(pledge.get("threshold", 50))
        kept = float(stats.get(attribute, 0)) >= threshold
        pledge["status"] = "kept" if kept else "missed"
        pledge["election_value"] = 1 if kept else -1
        score_effect += pledge["election_value"]
        result.append({
            "label": pledge.get("label", "Manifesto promise"),
            "status": pledge["status"],
            "attribute": attribute,
            "value": int(stats.get(attribute, 0)),
            "threshold": threshold,
        })
    score_effect = max(-3, min(3, score_effect))
    p["manifesto_history"].append({
        "term": int(p.get("career_term", 1)),
        "promises": result,
        "score_effect": score_effect,
    })
    p["manifesto_history"] = p["manifesto_history"][-10:]
    return score_effect, result


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
    if int(p["ethics_risk"]) >= _ethics_limit(p):
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


def _active_private_bill(p):
    bill = p.get("private_members_bill")
    if not isinstance(bill, dict) or bill.get("stage") in {"assented", "defeated"}:
        return None
    return bill


def _draft_private_members_bill(p, bill_id):
    used = _current_actions(p)
    if len(used) >= ACTIONS_PER_SESSION or "draft_private_bill" in used or _active_private_bill(p):
        return
    spec = PRIVATE_MEMBERS_BILLS.get(bill_id)
    if not spec:
        return
    p["private_members_bill"] = {
        "id": bill_id,
        "label": spec["label"],
        "description": spec["description"],
        "priority": spec["priority"],
        "policy_area": spec["policy_area"],
        "stage": "drafting",
        "sponsors": 0,
        "evidence": 0,
        "created_term": int(p["career_term"]),
        "created_year": int(p["career_year"]),
        "created_session": int(p["career_session"]),
        "last_outcome": "Bill drafted. Now seek sponsors and prepare evidence before requesting a second reading.",
    }
    p["last_event"] = f"You have drafted the fictional {spec['label']}. The next challenge is to win support and prepare the case for Parliament."
    _take_action(p, {
        "id": "draft_private_bill",
        "label": f"Draft Private Member's Bill: {spec['label']}",
        "description": f"You draft a bill on {spec['policy_area'].lower()} and set out its intended effect.",
        "effects": {"policy_expertise": 3, "parliamentary_influence": 1},
    })


def _private_bill_action(p, action_kind):
    bill = _active_private_bill(p)
    used = _current_actions(p)
    action_ids = {
        "sponsors": "bill_gather_sponsors",
        "evidence": "bill_prepare_evidence",
        "second_reading": "bill_second_reading",
        "committee_evidence": "bill_committee_evidence",
        "committee_report": "bill_committee_report",
        "report_amendment": "bill_report_amendment",
        "third_reading": "bill_third_reading",
    }
    action_id = action_ids.get(action_kind)
    if not bill or not action_id or len(used) >= ACTIONS_PER_SESSION or action_id in used:
        return
    effects = {}
    description = ""
    if action_kind == "sponsors" and bill["stage"] == "drafting":
        new_sponsors = 1 + (1 if int(p["faction_standing"].get("cross_party", 35)) >= 60 else 0)
        bill["sponsors"] = int(bill.get("sponsors", 0)) + new_sponsors
        bill["last_outcome"] = f"You secured {new_sponsors} additional fictional cross-party sponsor(s)."
        effects = {"parliamentary_influence": 2, "policy_expertise": 1}
        description = bill["last_outcome"]
    elif action_kind == "evidence" and bill["stage"] == "drafting":
        bill["evidence"] = min(100, int(bill.get("evidence", 0)) + 35)
        bill["last_outcome"] = f"Evidence prepared. Bill evidence is now {bill['evidence']}%."
        effects = {"policy_expertise": 3, "integrity": 1}
        description = bill["last_outcome"]
    elif action_kind == "second_reading" and bill["stage"] == "drafting":
        if int(bill.get("sponsors", 0)) < 2 or int(bill.get("evidence", 0)) < 35:
            return
        stats = p["stats"]
        score = (
            .32 * stats.get("parliamentary_influence", 0)
            + .27 * stats.get("policy_expertise", 0)
            + .17 * stats.get("public_profile", 0)
            + .14 * p["faction_standing"].get("cross_party", 35)
            + min(12, int(bill.get("sponsors", 0)) * 3)
            + min(8, int(bill.get("evidence", 0)) * .08)
        )
        seed = int(st.session_state.get("seed", 32458))
        event_seed = seed + int(p["career_total_years"]) * 521 + int(p["career_session"]) * 31 + sum(ord(char) for char in bill["id"])
        ballot_score = round(score + random.Random(event_seed).uniform(-7, 7), 1)
        passed = ballot_score >= 43
        bill["last_outcome"] = f"Second reading {'passed' if passed else 'was defeated'} (procedural support score {ballot_score}/100)."
        bill["last_ballot_score"] = ballot_score
        if passed:
            bill["stage"] = "committee"
            effects = {"parliamentary_influence": 2, "public_profile": 2, "party_trust": 1}
        else:
            bill["stage"] = "defeated"
            p["private_bill_history"].append(dict(bill))
            effects = {"public_profile": 1, "parliamentary_influence": -2}
        description = bill["last_outcome"]
    elif action_kind == "committee_evidence" and bill["stage"] == "committee":
        bill["evidence"] = min(100, int(bill.get("evidence", 0)) + 35)
        bill["last_outcome"] = f"Committee evidence strengthened. Evidence is now {bill['evidence']}%."
        effects = {"policy_expertise": 3, "integrity": 1, "parliamentary_influence": 1}
        description = bill["last_outcome"]
    elif action_kind == "committee_report" and bill["stage"] == "committee":
        if int(bill.get("evidence", 0)) < 65:
            return
        bill["stage"] = "report"
        bill["last_outcome"] = "Committee stage completed. The bill moves to report stage for further scrutiny and amendments."
        effects = {"policy_expertise": 1, "parliamentary_influence": 2}
        description = bill["last_outcome"]
    elif action_kind == "report_amendment" and bill["stage"] == "report":
        bill["sponsors"] = int(bill.get("sponsors", 0)) + 1
        bill["last_outcome"] = "You negotiated an amendment and won another colleague's support."
        effects = {"parliamentary_influence": 2, "party_trust": 1, "policy_expertise": 1}
        description = bill["last_outcome"]
    elif action_kind == "third_reading" and bill["stage"] == "report":
        if int(bill.get("sponsors", 0)) < 3 or int(bill.get("evidence", 0)) < 65:
            return
        stats = p["stats"]
        score = (
            .29 * stats.get("parliamentary_influence", 0)
            + .25 * stats.get("policy_expertise", 0)
            + .15 * stats.get("public_profile", 0)
            + .16 * p["faction_standing"].get("cross_party", 35)
            + min(12, int(bill.get("sponsors", 0)) * 2)
            + min(8, int(bill.get("evidence", 0)) * .08)
        )
        seed = int(st.session_state.get("seed", 32458))
        event_seed = seed + int(p["career_total_years"]) * 773 + int(p["career_session"]) * 43 + sum(ord(char) for char in bill["id"])
        ballot_score = round(score + random.Random(event_seed).uniform(-7, 7), 1)
        passed = ballot_score >= 48
        if passed:
            bill["stage"] = "assented"
            bill["last_outcome"] = f"Third reading passed and Royal Assent was granted in the fictional simulation (support score {ballot_score}/100). Your bill is now law."
            p["private_bill_history"].append(dict(bill))
            effects = {"public_profile": 5, "parliamentary_influence": 4, "policy_expertise": 3, "integrity": 2}
            if bill.get("priority") == p.get("local_mandate"):
                effects["constituency_support"] = 3
            p["faction_standing"]["cross_party"] = _clip(p["faction_standing"].get("cross_party", 35) + 8)
        else:
            bill["stage"] = "defeated"
            bill["last_outcome"] = f"The bill failed at third reading (support score {ballot_score}/100). You can return with a revised proposal in a future session."
            p["private_bill_history"].append(dict(bill))
            effects = {"public_profile": 1, "parliamentary_influence": -3, "party_trust": -1}
        description = bill["last_outcome"]
    else:
        return
    if bill.get("stage") in {"assented", "defeated"} and not any(
        item.get("id") == bill.get("id") and item.get("created_term") == bill.get("created_term")
        and item.get("created_year") == bill.get("created_year") and item.get("created_session") == bill.get("created_session")
        for item in p["private_bill_history"]
    ):
        p["private_bill_history"].append(dict(bill))
    bill["last_outcome"] = description
    _take_action(p, {
        "id": action_id,
        "label": f"Private Member's Bill: {action_kind.replace('_', ' ').title()}",
        "description": description,
        "effects": effects,
    })


def _launch_constituency_petition(p, topic_id):
    used = _current_actions(p)
    current = p.get("petition_campaign")
    if len(used) >= ACTIONS_PER_SESSION or "launch_petition" in used:
        return
    if isinstance(current, dict) and current.get("status") == "active":
        return
    topic = PETITION_TOPICS.get(topic_id)
    if not topic:
        return
    current = {
        "id": topic_id,
        "title": topic["label"],
        "description": topic["description"],
        "priority": topic["priority"],
        "status": "active",
        "signatures": 0,
        "launched_term": int(p["career_term"]),
        "launched_year": int(p["career_year"]),
        "launched_session": int(p["career_session"]),
        "last_outcome": "Petition launched. Organise a signature drive and present it when enough local people have signed.",
    }
    p["petition_campaign"] = current
    _take_action(p, {
        "id": "launch_petition",
        "label": f"Launched constituency petition: {topic['label']}",
        "description": current["last_outcome"],
        "effects": {"constituency_support": 2, "campaign_readiness": 2},
    })


def _run_petition_action(p, action_kind):
    campaign = p.get("petition_campaign")
    used = _current_actions(p)
    action_ids = {"drive": "petition_signature_drive", "present": "petition_present"}
    action_id = action_ids.get(action_kind)
    if not isinstance(campaign, dict) or campaign.get("status") != "active":
        return
    if not action_id or len(used) >= ACTIONS_PER_SESSION or action_id in used:
        return
    effects = {}
    if action_kind == "drive":
        stats = p["stats"]
        gained = 120 + int(stats.get("constituency_support", 0) * 1.2) + int(stats.get("campaign_readiness", 0) * .8)
        gained = max(100, min(300, gained))
        campaign["signatures"] = min(1000, int(campaign.get("signatures", 0)) + gained)
        campaign["last_outcome"] = f"The signature drive gathered {gained} additional supporters. Total: {campaign['signatures']:,}/1,000."
        effects = {"constituency_support": 1, "campaign_readiness": 2, "public_profile": 1}
        p["faction_standing"]["local_party"] = _clip(p["faction_standing"].get("local_party", 50) + 2)
        description = campaign["last_outcome"]
    elif action_kind == "present":
        if int(campaign.get("signatures", 0)) < 400:
            return
        campaign["status"] = "presented"
        campaign["last_outcome"] = f"You presented the petition with {int(campaign['signatures']):,} signatures to the relevant minister or public body."
        p.setdefault("petition_history", []).append(dict(campaign))
        effects = {"parliamentary_influence": 2, "public_profile": 2, "constituency_support": 3}
        if campaign.get("priority") == p.get("local_mandate"):
            effects["constituency_support"] += 2
        description = campaign["last_outcome"]
    else:
        return
    campaign["last_outcome"] = description
    _take_action(p, {
        "id": action_id,
        "label": f"Constituency petition: {action_kind.replace('_', ' ').title()}",
        "description": description,
        "effects": effects,
    })


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
    delivery_ok = (
        p.get("role") not in DELIVERY_THRESHOLDS
        or int(p.get("department_score", 0)) >= DELIVERY_THRESHOLDS[p["role"]]
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
    """Resolve a general election using constituency margin, national swing and a seat projection."""
    stats = p["stats"]
    seed = int(st.session_state.get("seed", 12345))
    rng = random.Random(seed + p["career_total_years"] * 911 + p["career_term"] * 503)
    polls = _ensure_polling_state(p)
    party = p.get("party", "Labour")
    baseline = p.get("polling_baseline")
    if not isinstance(baseline, dict) or not baseline:
        baseline = dict(polls)
        p["polling_baseline"] = dict(baseline)

    party_vote_share = float(polls.get(party, 0))
    baseline_party_share = float(baseline.get(party, party_vote_share))
    rivals = [name for name in polls if name != party]
    closest_rival = max(rivals, key=lambda name: polls.get(name, 0)) if rivals else "Other parties"
    national_swing = party_vote_share - baseline_party_share
    rival_swing = float(polls.get(closest_rival, 0)) - float(baseline.get(closest_rival, polls.get(closest_rival, 0)))
    relative_swing = national_swing - rival_swing

    starting_margin = float(p.get("starting_seat_margin", 7.0))
    local_effect = (float(stats.get("constituency_support", 50)) - 50) * 0.22
    campaign_effect = (float(stats.get("campaign_readiness", 30)) - 30) * 0.12
    reputation_effect = (float(stats.get("integrity", 50)) - 50) * 0.045
    trust_effect = (float(stats.get("party_trust", 50)) - 50) * 0.035
    polling_effect = relative_swing * 0.55
    manifesto_effect, manifesto_results = _score_manifesto_pledges(p)
    difficulty_effect = {"relaxed": 2.0, "standard": 0.0, "hard": -3.0}.get(p.get("difficulty", DEFAULT_DIFFICULTY), 0.0)
    random_swing = rng.uniform(-3.5, 3.5)
    margin = round(starting_margin + local_effect + campaign_effect + reputation_effect + trust_effect + polling_effect + manifesto_effect + difficulty_effect + random_swing, 1)
    won = margin > 0

    projected_raw = {}
    for candidate, seats in SIMULATED_PARTY_SEATS.items():
        share_change = float(polls.get(candidate, 0)) - float(baseline.get(candidate, polls.get(candidate, 0)))
        projected_raw[candidate] = max(0.0, float(seats) + share_change * 5.0)
    for candidate in polls:
        if candidate not in projected_raw:
            projected_raw[candidate] = max(0.0, float(polls[candidate]) * 0.2)
    projected_total = sum(projected_raw.values()) or 650.0
    projected_seats = {candidate: int(round(value / projected_total * 650)) for candidate, value in projected_raw.items()}
    residue = 650 - sum(projected_seats.values())
    if projected_seats and residue:
        projected_seats[max(projected_seats, key=projected_seats.get)] += residue
    projected_leader = max(projected_seats, key=projected_seats.get) if projected_seats else party
    projected_party_seats = int(projected_seats.get(party, 0))
    projected_majority = projected_party_seats >= 326
    constituency_share = round(max(20.0, min(65.0, 50.0 + margin * 1.8)), 1)

    result = {
        "term": int(p.get("career_term", 1)), "score": round(starting_margin + local_effect + campaign_effect + reputation_effect + trust_effect + polling_effect + manifesto_effect, 1),
        "margin": margin, "won": won, "threshold": 0, "starting_margin": round(starting_margin, 1),
        "local_effect": round(local_effect, 1), "campaign_effect": round(campaign_effect, 1),
        "party_vote_share": round(party_vote_share, 1), "polling_leader": max(polls, key=polls.get),
        "polling_snapshot": dict(polls), "polling_effect": round(polling_effect, 1),
        "relative_national_swing": round(relative_swing, 1), "manifesto_effect": manifesto_effect,
        "manifesto_results": manifesto_results, "constituency_vote_share": constituency_share,
        "opponent_vote_share": round(100.0 - constituency_share, 1), "projected_seats": projected_seats,
        "projected_leader": projected_leader, "projected_party_seats": projected_party_seats,
        "projected_majority": projected_majority,
    }
    p["election_result"] = result
    p.setdefault("election_history", []).append(dict(result))
    p["election_history"] = p["election_history"][-10:]

    if won:
        p["seats_won"] = int(p.get("seats_won", 0)) + 1
        p["stats"]["constituency_support"] = _clip(p["stats"]["constituency_support"] + 2)
        p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] + 1)
        text = f"Re-elected in {p['constituency']} with an estimated {constituency_share:.1f}% local vote and a simulated {margin:+.1f} point margin."
        if p.get("role") == "prime_minister":
            if projected_leader != party:
                p["role"] = "mp"
                p["government_status"] = "opposition"
                p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] - 8)
                p["stats"]["public_profile"] = _clip(p["stats"]["public_profile"] - 4)
                text += f" Nationally, {projected_leader} leads the fictional seat projection ({projected_seats.get(projected_leader, 0)} seats); your party loses office."
            elif not projected_majority:
                p["government_status"] = "minority_government"
                p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] - 3)
                text += f" Your party remains the largest projected party on {projected_party_seats} seats but falls short of a majority."
            else:
                p["government_status"] = "majority_government"
                text += f" Your party is projected to return with a majority of {projected_party_seats - 325} seats."
        p["career_term"] = int(p.get("career_term", 1)) + 1
        p["career_year"] = 1
        p["career_session"] = 1
        p["starting_seat_margin"] = round(max(1.0, min(20.0, margin)), 1)
        p["polling_baseline"] = dict(polls)
        p["last_event"] = text
        _record(p, "General election · seat retained", text)
    else:
        text = f"You lose {p['constituency']} at the general election. The simulated local margin was {margin:+.1f} points; national swing, local support and campaign readiness all mattered."
        p["government_status"] = "out_of_parliament"
        p["game_over"] = True
        p["last_event"] = text
        _record(p, "General election · seat lost", text)


def _advance(p):
    used = _current_actions(p)
    if len(used) < ACTIONS_PER_SESSION:
        return
    _advance_voting_intention(p)
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
    _record_stat_snapshot(p, f"T{p['career_term']} Y{p['career_year']} S{p['career_session']}")
    st.session_state.career_profile = p
    st.rerun()


def _normalise_poll_shares(shares):
    """Keep fictional national vote intention non-negative and summing to 100%."""
    cleaned = {str(party): max(0.01, float(value)) for party, value in shares.items()}
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("Voting-intention shares must contain a positive total.")
    result = {party: round(value / total * 100, 1) for party, value in cleaned.items()}
    residue = round(100.0 - sum(result.values()), 1)
    leader = max(result, key=result.get)
    result[leader] = round(result[leader] + residue, 1)
    return result


def _initial_voting_intention(party="Labour", name="MP", constituency="Westminster"):
    """Create a stable but varied fictional polling baseline for a new career."""
    mix = sum((index + 1) * ord(char) for index, char in enumerate(f"{name}|{constituency}|{party}"))
    rng = random.Random(84721 + mix)
    baseline = dict(POLLING_BASELINE)
    for candidate in DIVISION_DATA["party_names"]:
        baseline.setdefault(candidate, 0.25)
    shares = {}
    for candidate, base in baseline.items():
        wiggle = rng.uniform(-2.2, 2.2) if base >= 8 else rng.uniform(-0.45, 0.45)
        shares[candidate] = max(0.1, base + wiggle)
    if party not in shares:
        shares[party] = 0.5
    return _normalise_poll_shares(shares)


def _record_poll_snapshot(p, label):
    """Save a polling wave for this session, replacing its previous chart point."""
    polls = dict(p.get("voting_intention", {}))
    session_id = f"{int(p.get('career_term', 1))}:{int(p.get('career_year', 1))}:{int(p.get('career_session', 1))}"
    history = p.setdefault("polling_history", [])
    snapshot = {
        "term": int(p.get("career_term", 1)),
        "year": int(p.get("career_year", 1)),
        "session": int(p.get("career_session", 1)),
        "session_id": session_id,
        "label": str(label),
        "polls": polls,
    }
    if history and history[-1].get("session_id") == session_id:
        history[-1] = snapshot
    else:
        history.append(snapshot)
    p["polling_history"] = history[-45:]


def _ensure_polling_state(p):
    """Migrate old saves and ensure all selectable parties have a polling share."""
    current = p.get("voting_intention")
    if not isinstance(current, dict) or not current:
        current = _initial_voting_intention(
            p.get("party", "Labour"), p.get("name", "MP"), p.get("constituency", "Westminster")
        )
    else:
        current = dict(current)
        for candidate, value in POLLING_BASELINE.items():
            current.setdefault(candidate, max(0.1, value))
        for candidate in DIVISION_DATA["party_names"]:
            current.setdefault(candidate, 0.25)
    p["voting_intention"] = _normalise_poll_shares(current)
    p.setdefault("polling_history", [])
    if not isinstance(p.get("polling_baseline"), dict) or not p["polling_baseline"]:
        p["polling_baseline"] = dict(p["voting_intention"])
    if not p["polling_history"]:
        _record_poll_snapshot(p, "Starting poll")
    return p["voting_intention"]


def _shift_party_poll(p, party, delta):
    """Shift a party's invented poll share and rebalance all other parties to 100%."""
    polls = _ensure_polling_state(p)
    if party not in polls:
        polls[party] = 0.25
        polls = _normalise_poll_shares(polls)
    before = float(polls.get(party, 0))
    after = max(0.2, min(65.0, before + float(delta)))
    rest = {name: share for name, share in polls.items() if name != party}
    rest_total = sum(rest.values())
    remaining_total = max(0.0, 100.0 - after)
    if rest_total <= 0:
        rest = {name: 1.0 for name in rest}
        rest_total = sum(rest.values())
    shifted = {name: value / rest_total * remaining_total for name, value in rest.items()}
    shifted[party] = after
    p["voting_intention"] = _normalise_poll_shares(shifted)
    return round(float(p["voting_intention"].get(party, 0)) - before, 1)


def _advance_voting_intention(p):
    """Add a deliberately noisy game-only polling wave after each parliamentary session."""
    polls = _ensure_polling_state(p)
    party = p.get("party", "Labour")
    stats = p.get("stats", {})
    seed = (
        84721
        + sum((index + 1) * ord(char) for index, char in enumerate(f"{p.get('name', 'MP')}|{p.get('constituency', '')}"))
        + int(p.get("career_term", 1)) * 1901
        + int(p.get("career_year", 1)) * 419
        + int(p.get("career_session", 1)) * 103
    )
    rng = random.Random(seed)
    updated = {}
    for candidate, current in polls.items():
        volatility = 1.2 if current >= 8 else 0.35
        updated[candidate] = max(0.1, float(current) + rng.uniform(-volatility, volatility))
    player_nudge = (
        (float(stats.get("party_trust", 50)) - 50) * 0.012
        + (float(stats.get("public_profile", 50)) - 50) * 0.009
        + (float(stats.get("integrity", 50)) - 50) * 0.004
        + (float(stats.get("campaign_readiness", 30)) - 30) * 0.008
    )
    updated[party] = updated.get(party, 0.25) + max(-1.25, min(1.25, player_nudge))
    p["voting_intention"] = _normalise_poll_shares(updated)
    player_share = float(p["voting_intention"].get(party, 0))
    baseline_share = float(p.get("polling_baseline", {}).get(party, player_share))
    change = round(player_share - baseline_share, 1)
    p["polling_last_change"] = change
    label = f"Term {p.get('career_term', 1)} · Year {p.get('career_year', 1)} · Session {p.get('career_session', 1)}"
    _record_poll_snapshot(p, label)
    return change


def _take_polling_action(p, action):
    """Spend one career-action slot on a national campaign activity."""
    used = _current_actions(p)
    if len(used) >= ACTIONS_PER_SESSION or action["id"] in used:
        return
    effects = action.get("effects", {})
    _apply_effects(p, effects)
    used.append(action["id"])
    change = _shift_party_poll(p, p.get("party", "Labour"), action.get("poll_shift", 0))
    _record_poll_snapshot(p, f"{action['label']} · Term {p.get('career_term', 1)} / Year {p.get('career_year', 1)}")
    summary = _effect_summary(effects)
    narrative = f"{action['description']} Voting intention for {p.get('party', 'your party')} shifts by {change:+.1f} percentage points in the fictional poll."
    if summary:
        narrative += f" Career effects: {summary}."
    _record(p, action["label"], narrative)
    p["last_event"] = f"{action['label']}: {change:+.1f} percentage points in fictional voting intention."
    p["polling_last_change"] = change
    st.session_state.career_profile = p
    st.rerun()


def _render_polling_tab(p):
    """Display fictional national vote intention and campaign actions."""
    polls = _ensure_polling_state(p)
    party = p.get("party", "Labour")
    baseline = p.get("polling_baseline", polls)
    player_share = float(polls.get(party, 0))
    change = round(player_share - float(baseline.get(party, player_share)), 1)
    leader = max(polls, key=polls.get)
    sorted_rows = sorted(polls.items(), key=lambda item: item[1], reverse=True)
    current_df = pd.DataFrame([
        {"Party": name, "Vote intention (%)": value,
         "Change from start (pp)": round(value - float(baseline.get(name, value)), 1)}
        for name, value in sorted_rows
    ])
    st.markdown("## General-election voting intention")
    st.warning(
        "FICTIONAL GAME POLLING — the figures are invented and deliberately unreliable. "
        "They are not real polling, a real election forecast, or a statistically accurate model."
    )
    st.caption("National vote intention · shifts after parliamentary sessions and campaign actions · shares total 100%")
    metrics = st.columns(4, gap="medium")
    metrics[0].metric(f"{party} voting intention", f"{player_share:.1f}%", f"{change:+.1f} pp since start")
    metrics[1].metric("Current polling leader", leader, f"{polls[leader]:.1f}% in the game")
    metrics[2].metric("Polling waves", len(p.get("polling_history", [])))
    metrics[3].metric(
        "Sessions to election",
        max(0, (ELECTION_AFTER - int(p.get("career_year", 1))) * SESSIONS_PER_YEAR
            + SESSIONS_PER_YEAR - int(p.get("career_session", 1))),
    )

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("### Current voting intention")
        bar_frame = current_df.rename(columns={"Vote intention (%)": "Share"})
        chart = px.bar(
            bar_frame, x="Share", y="Party", color="Party", orientation="h",
            color_discrete_map=PARTY_COLOURS,
            hover_data={"Change from start (pp)": True, "Share": ":.1f"},
            text="Share",
        )
        chart.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False, marker_line_width=0)
        chart.update_layout(
            height=590, showlegend=False, margin=dict(l=8, r=35, t=8, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#263243", size=12),
            xaxis=dict(title="Vote intention (%)", range=[0, max(30, float(current_df["Vote intention (%)"].max()) * 1.25)], gridcolor="#e1e7ee"),
            yaxis=dict(title="", categoryorder="total ascending"),
        )
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False, "responsive": True})
    with right:
        st.markdown("### Polling trend")
        history = list(p.get("polling_history", []))
        if len(history) >= 2:
            trend_parties = [name for name, _ in sorted_rows[:5]]
            if party not in trend_parties:
                trend_parties.append(party)
            trend_rows = []
            for index, wave in enumerate(history):
                for trend_party in trend_parties:
                    if trend_party in wave.get("polls", {}):
                        trend_rows.append({
                            "Wave": index + 1,
                            "Poll": wave.get("label", f"Wave {index + 1}"),
                            "Party": trend_party,
                            "Vote intention (%)": wave["polls"][trend_party],
                        })
            trend_frame = pd.DataFrame(trend_rows)
            trend = px.line(
                trend_frame, x="Wave", y="Vote intention (%)", color="Party", markers=True,
                color_discrete_map=PARTY_COLOURS,
                hover_data={"Poll": True, "Wave": True, "Vote intention (%)": ":.1f"},
            )
            trend.update_traces(line=dict(width=2.5))
            trend.update_layout(
                height=460, margin=dict(l=8, r=16, t=8, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#263243", size=11),
                xaxis=dict(title="In-game polling wave", gridcolor="#e1e7ee"),
                yaxis=dict(title="Vote intention (%)", rangemode="tozero", gridcolor="#e1e7ee"),
                legend=dict(title="Party", orientation="h", yanchor="bottom", y=-0.22, xanchor="left", x=0),
            )
            st.plotly_chart(trend, use_container_width=True, config={"displayModeBar": False, "responsive": True})
        else:
            st.info("Your first polling trend appears after the next parliamentary session.")
        st.markdown("### What moves the fictional poll?")
        st.write("Campaign actions, party trust, public profile, integrity and campaign readiness gently affect your party's share. Random shocks move every party.")
        st.caption("These effects are exaggerated game rules, not polling science.")

    st.markdown("### Player campaign actions")
    st.caption("Each activity uses one career-action slot and can change fictional voting intention immediately.")
    used = _current_actions(p)
    remaining = max(0, ACTIONS_PER_SESSION - len(used))
    action_cols = st.columns(len(POLLING_ACTIONS), gap="medium")
    for col, action in zip(action_cols, POLLING_ACTIONS):
        with col:
            with st.container(border=True):
                st.markdown(f"**{action['label']}**")
                st.write(action["description"])
                st.caption(f"{_effect_summary(action['effects'])} · nominal polling nudge {action['poll_shift']:+.1f} pp before rebalancing")
                if st.button(
                    "Take this action",
                    key=f"poll_action_{p['career_term']}_{p['career_year']}_{p['career_session']}_{action['id']}",
                    type="primary" if action["id"] not in used and remaining > 0 else "secondary",
                    disabled=remaining <= 0 or action["id"] in used,
                    use_container_width=True,
                ):
                    _take_polling_action(p, action)
    st.caption("Actions share your two-slot budget with constituency work, policy work, networking and media decisions.")


def _normalise_seat_name(name):
    """Normalise constituency names for safe matching between official datasets."""
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _canonical_party_name(name):
    """Map Parliament API variants to consistent labels used by the dashboard."""
    raw = str(name or "").strip()
    text = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii").casefold()
    if "sinn fein" in text:
        return "Sinn Féin"
    if "social democratic" in text or text == "sdlp":
        return "Social Democratic and Labour Party (SDLP)"
    if "labour" in text:
        return "Labour"
    if "conservative" in text and "independent" in text:
        return "Conservative Independent"
    if "conservative" in text:
        return "Conservative"
    if "liberal democrat" in text:
        return "Liberal Democrats"
    if "reform uk" in text or text == "reform":
        return "Reform UK"
    if "green" in text:
        return "Green Party"
    if "scottish national" in text or text == "snp":
        return "SNP"
    if "plaid cymru" in text:
        return "Plaid Cymru"
    if "democratic unionist" in text or text == "dup":
        return "Democratic Unionist Party (DUP)"
    if "social democratic" in text or text == "sdlp":
        return "Social Democratic and Labour Party (SDLP)"
    if "ulster unionist" in text or text == "uup":
        return "Ulster Unionist Party (UUP)"
    if "alliance" in text:
        return "Alliance Party of Northern Ireland"
    if "your party" in text:
        return "Your Party"
    if "restore britain" in text:
        return "Restore Britain"
    if "traditional unionist" in text or text == "tuv":
        return "Traditional Unionist Voice (TUV)"
    if "speaker" in text and "lord" in text:
        return "Lord Speaker"
    if text == "speaker" or text == "spk":
        return "Speaker"
    if "crossbench" in text:
        return "Crossbench"
    if "non-affiliated" in text or "non affiliated" in text:
        return "Non-affiliated"
    if "bishop" in text or "lords spiritual" in text:
        return "Bishops"
    if "independent" in text:
        return "Independent"
    return raw or "Independent"


def _fetch_commons_page(skip):
    """Fetch one page of current Commons members from the official UK Parliament API."""
    response = requests.get(
        UK_PARLIAMENT_API,
        params={"House": 1, "IsCurrentMember": True, "skip": int(skip), "take": 20},
        headers={"Accept": "application/json", "User-Agent": "MP-Career-Simulator/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("The Parliament API returned an unexpected member-list response.")
    return payload


@st.cache_data(ttl=21600, show_spinner=False)
def _current_commons_party_map():
    """Return current constituency -> MP/party data from the official Members API."""
    first = _fetch_commons_page(0)
    total = int(first.get("totalResults", len(first.get("items", []))))
    items = list(first.get("items", []))
    offsets = list(range(20, total, 20))
    if offsets:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            pages = list(executor.map(_fetch_commons_page, offsets))
        for page in pages:
            items.extend(page.get("items", []))

    mapping = {}
    for item in items:
        member = item.get("value") or {}
        membership = member.get("latestHouseMembership") or {}
        membership_status = membership.get("membershipStatus") or {}
        if membership.get("house") not in (None, 1):
            continue
        if membership.get("membershipEndDate"):
            continue
        if membership_status and not membership_status.get("statusIsActive", True):
            continue
        constituency = str(membership.get("membershipFrom") or "").strip()
        if not constituency:
            continue
        key = _normalise_seat_name(constituency)
        party_data = member.get("latestParty") or {}
        mapping[key] = {
            "constituency": constituency,
            "mp": str(member.get("nameDisplayAs") or member.get("nameListAs") or "MP"),
            "party": _canonical_party_name(party_data.get("name")),
        }

    # A full UK map should match almost all 650 constituencies. Avoid showing
    # hundreds of grey seats if a partial API response or service error occurred.
    if len(mapping) < 600:
        raise RuntimeError(
            f"The official feed returned only {len(mapping)} constituency memberships; "
            "the map was not drawn from incomplete data."
        )
    return mapping, total


@st.cache_data(show_spinner=False)
def _load_constituency_geojson():
    """Load the static, generalised ONS 2024 Westminster constituency boundaries."""
    path = Path(__file__).resolve().parent / "data" / "constituencies_2024.geojson"
    with path.open("r", encoding="utf-8") as handle:
        geojson = json.load(handle)
    if geojson.get("type") != "FeatureCollection" or len(geojson.get("features", [])) != 650:
        raise ValueError("The bundled UK constituency geometry must contain 650 boundaries.")
    return geojson


def _bar_chart(frame, category, value, height):
    """Create a restrained horizontal chart using each party's own colour."""
    chart = px.bar(
        frame,
        x=value,
        y=category,
        color=category,
        orientation="h",
        color_discrete_map=PARTY_COLOURS,
        text=value,
        hover_data={category: True, value: True},
    )
    chart.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0)
    chart.update_layout(
        height=height,
        showlegend=False,
        margin=dict(l=8, r=32, t=8, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#263243", size=12),
        xaxis=dict(title="Members / seats", gridcolor="#e1e7ee", zeroline=False),
        yaxis=dict(title="", categoryorder="total ascending"),
    )
    return chart


def _render_parliament_tab():
    """Show the Commons and Lords composition plus a live, interactive seat map."""
    commons_rows = PARLIAMENT_COMPOSITION["commons"]["seats"]
    lords_rows = PARLIAMENT_COMPOSITION["lords"]["seats"]
    commons_total = int(PARLIAMENT_COMPOSITION["commons"]["total_seats"])
    lords_total = int(PARLIAMENT_COMPOSITION["lords"]["eligible_members"])
    commons_df = pd.DataFrame(commons_rows)
    lords_df = pd.DataFrame(lords_rows)
    commons_df = commons_df.rename(columns={"party": "Party", "seats": "Seats"})
    lords_df = lords_df.rename(columns={"party": "Party / group", "seats": "Members"})

    st.markdown("## Make-up of the UK Parliament")
    st.caption(
        f"Official party/group snapshot checked {PARLIAMENT_COMPOSITION['as_of']}. "
        "The composition charts use the dated snapshot; the constituency map requests current MP affiliations from Parliament's Members API."
    )
    st.markdown(
        "Sources: [Commons state of the parties](https://members.parliament.uk/parties/Commons) · "
        "[Lords membership](https://members.parliament.uk/parties/lords/by-peerage) · "
        "[UK Parliament Members API](https://members-api.parliament.uk/index.html)."
    )
    top = st.columns(4, gap="medium")
    top[0].metric("Commons seats", f"{commons_total:,}")
    top[1].metric("Majority threshold", f"{PARLIAMENT_COMPOSITION['commons']['majority_threshold']:,}")
    leading_party = commons_df.sort_values("Seats", ascending=False).iloc[0]
    top[2].metric("Largest Commons party", f"{leading_party['Party']} · {int(leading_party['Seats']):,}")
    top[3].metric("Eligible Lords members", f"{lords_total:,}")

    commons_col, lords_col = st.columns(2, gap="large")
    with commons_col:
        st.markdown("### House of Commons")
        st.caption("650 constituency seats, including the Speaker and non-sitting MPs as displayed in the official party list.")
        commons_chart = _bar_chart(commons_df, "Party", "Seats", 565)
        st.plotly_chart(commons_chart, use_container_width=True, config={"displayModeBar": False, "responsive": True})
        with st.expander("View Commons party totals", expanded=False):
            st.dataframe(
                commons_df.sort_values("Seats", ascending=False),
                hide_index=True,
                use_container_width=True,
            )
    with lords_col:
        st.markdown("### House of Lords")
        st.caption("Eligible members by party or group. Membership changes as appointments, retirements and other changes occur.")
        lords_chart = _bar_chart(lords_df, "Party / group", "Members", 565)
        st.plotly_chart(lords_chart, use_container_width=True, config={"displayModeBar": False, "responsive": True})
        with st.expander("View Lords group totals", expanded=False):
            st.dataframe(
                lords_df.sort_values("Members", ascending=False),
                hide_index=True,
                use_container_width=True,
            )

    st.markdown("## UK constituency map")
    st.caption(
        "Each shape is one of the 650 Westminster seats under the July 2024 boundaries. "
        "Hover over a seat to see the constituency, current MP and current parliamentary party. "
        "Use the mouse wheel to zoom and drag to move around the UK."
    )
    try:
        with st.spinner("Loading current MP and party details from UK Parliament…"):
            constituency_map, member_count = _current_commons_party_map()
        geometry = _load_constituency_geojson()
        rows = []
        matched = 0
        for feature in geometry["features"]:
            properties = feature.get("properties") or {}
            constituency = str(properties.get("PCON24NM", "Unknown constituency"))
            code = str(properties.get("PCON24CD", ""))
            current = constituency_map.get(_normalise_seat_name(constituency))
            if current:
                matched += 1
                party_name = current["party"]
                mp_name = current["mp"]
            else:
                party_name = "Vacant / no current MP"
                mp_name = "No current MP matched by constituency name"
            rows.append({
                "code": code,
                "constituency": constituency,
                "party": party_name,
                "mp": mp_name,
            })
        if matched < 600:
            st.warning(f"Only {matched} of 650 constituencies matched the live membership feed; unmapped seats are shown in grey.")
        seat_df = pd.DataFrame(rows)
        seat_options = ["— Select a constituency —"] + sorted(seat_df["constituency"].tolist())
        selected_seat = st.selectbox(
            "Find a constituency",
            seat_options,
            key="parliament_find_seat",
        )
        if selected_seat != seat_options[0]:
            chosen = seat_df.loc[seat_df["constituency"] == selected_seat].iloc[0]
            st.info(
                f"**{chosen['constituency']}** · {chosen['party']} · MP: {chosen['mp']}"
            )
        st.markdown("**Map key — current party affiliation**")
        legend_html = []
        for party_name in sorted(seat_df["party"].dropna().unique()):
            swatch = PARTY_COLOURS.get(party_name, "#D7DDE5")
            legend_html.append(
                f"<span style='display:inline-flex;align-items:center;gap:.35rem;"
                f"margin:0 .7rem .4rem 0;font-size:.82rem;white-space:nowrap;'>"
                f"<span style='display:inline-block;width:12px;height:12px;border-radius:3px;"
                f"background:{swatch};border:1px solid #9ca8b6;'></span>"
                f"{html.escape(str(party_name))}</span>"
            )
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:.1rem .25rem;padding:.35rem 0 .7rem;'>"
            + "".join(legend_html)
            + "</div>",
            unsafe_allow_html=True,
        )
        fig = px.choropleth_map(
            seat_df,
            geojson=geometry,
            locations="code",
            featureidkey="properties.PCON24CD",
            color="party",
            color_discrete_map=PARTY_COLOURS,
            hover_name="constituency",
            hover_data={
                "mp": True,
                "party": True,
                "code": True,
                "constituency": False,
            },
            map_style="open-street-map",
            center={"lat": 54.55, "lon": -3.1},
            zoom=3.25,
            opacity=0.86,
        )
        fig.update_traces(marker_line_color="#ffffff", marker_line_width=0.45)
        fig.update_layout(
            height=720,
            margin=dict(l=0, r=0, t=4, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#263243"),
            showlegend=False,
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
        )
        st.caption(
            f"Live membership response contained {member_count:,} Commons members; {matched}/650 boundary names matched. "
            "Geometry: ONS Westminster Parliamentary Constituencies, July 2024 (ultra-generalised version distributed by Open Innovations)."
        )
    except Exception as exc:
        st.warning(
            "The live constituency-party map could not be loaded right now. "
            "The official Commons and Lords composition charts above remain available. "
            "Retry by refreshing the app later."
        )
        st.caption(f"Map data source: UK Parliament Members API · {type(exc).__name__}")


def _set_active_tab(tab):
    """Switch the main navigation before Streamlit rebuilds the widgets."""
    if tab in NAV_OPTIONS:
        st.session_state["mp_active_nav"] = tab


def _render_header(p, ctx):
    """Party theme and masthead."""
    safe_name, player_party, role_label = ctx.safe_name, ctx.player_party, ctx.role_label
    party_accent, party_dark, party_pale = _party_theme(player_party)
    st.markdown(
        f"<style>:root{{--mp-red:{party_accent};--mp-red-dark:{party_dark};--mp-red-pale:{party_pale};--mp-party-accent:{party_accent};--mp-party-dark:{party_dark};--mp-party-pale:{party_pale};}}</style>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="mp-portal">
          <div class="mp-portal-brand">
            <div class="mp-crest">W</div>
            <div><div class="mp-brand-title">Westminster</div><div class="mp-brand-sub">MP Career Portal</div></div>
          </div>
          <div class="mp-portal-motto">A UK political career simulator <span>•</span> Not an official parliamentary service</div>
          <div class="mp-user-chip"><span class="mp-avatar">{safe_name[:1].upper()}</span><div><strong>{safe_name}</strong><small>{role_label}</small></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_navigation(ctx):
    """Section buttons; returns the active section name."""
    nav_options = list(NAV_OPTIONS)
    if st.session_state.get("mp_active_nav") not in nav_options:
        st.session_state["mp_active_nav"] = "Desk"
    active_tab = st.session_state.get("mp_active_nav", "Desk")
    nav_cols = st.columns(len(nav_options), gap="small")
    for nav_col, option in zip(nav_cols, nav_options):
        with nav_col:
            st.button(
                NAV_LABELS[option],
                key=f"main_nav_{option.lower()}",
                type="primary" if active_tab == option else "secondary",
                use_container_width=True,
                on_click=_set_active_tab,
                args=(option,),
            )
    return active_tab


def _render_timeline(p, ctx):
    """Term strip and parliamentary timeline."""
    safe_constituency, safe_nation, party, role_label = ctx.safe_constituency, ctx.safe_nation, ctx.party, ctx.role_label
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


def _render_metrics(p, ctx):
    """Headline stat cards and the latest-update banner."""
    stats = ctx.stats
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
        st.markdown(
            f"<div class='mp-event-banner'><strong>Latest update</strong><span>{html.escape(str(p['last_event']))}</span></div>",
            unsafe_allow_html=True,
        )


def _render_final_report(p):
    """End-of-career report after a lost seat."""
    stats_now = p.get("stats", {})
    legacy_score = round(sum(float(stats_now.get(key, 0)) for key in ATTRIBUTES) / max(1, len(ATTRIBUTES)), 1)
    legacy_grade = "A" if legacy_score >= 85 else "B" if legacy_score >= 75 else "C" if legacy_score >= 65 else "D" if legacy_score >= 55 else "E" if legacy_score >= 45 else "F"
    st.markdown("## Your final Westminster report")
    summary_cols = st.columns(4, gap="medium")
    summary_cols[0].metric("Career grade", legacy_grade)
    summary_cols[1].metric("Final standing", f"{legacy_score}/100")
    summary_cols[2].metric("Years served", int(p.get("career_total_years", 0)))
    summary_cols[3].metric("Promotions", len(p.get("promotion_log", [])))
    election_record = p.get("election_result") or {}
    if election_record:
        st.markdown(
            f"**Fictional national polling:** {html.escape(str(p.get('party', 'Your party')))} "
            f"{float(election_record.get('party_vote_share', 0)):.1f}% · "
            f"National polling leader: {html.escape(str(election_record.get('polling_leader', 'Not recorded')))}"
        )
        st.markdown(
            f"**Constituency result:** {float(election_record.get('constituency_vote_share', 0)):.1f}% estimated vote "
            f"({float(election_record.get('margin', 0)):+.1f} point margin) · "
            f"{'Seat retained' if election_record.get('won') else 'Seat lost'}"
        )
        st.caption(
            f"Starting majority: {float(election_record.get('starting_margin', 0)):+.1f} points. "
            f"National swing: {float(election_record.get('relative_national_swing', 0)):+.1f}; "
            f"local support effect: {float(election_record.get('local_effect', 0)):+.1f}; "
            f"campaign effect: {float(election_record.get('campaign_effect', 0)):+.1f}. "
            "All polling and constituency vote shares are fictional game mechanics, not an election forecast."
        )
        if election_record.get("projected_seats"):
            leader = election_record.get("projected_leader", "Not recorded")
            st.markdown(
                f"**National seat projection (fictional):** {html.escape(str(leader))} leads with "
                f"{int(election_record.get('projected_seats', {}).get(leader, 0))} of 650 seats. "
                f"Your party is projected on {int(election_record.get('projected_party_seats', 0))} seats."
            )
    if election_record.get("manifesto_results"):
        st.markdown("### Manifesto promise report")
        st.caption(f"Promise credibility changed your simulated election score by {int(election_record.get('manifesto_effect', 0)):+d} points.")
        promise_cols = st.columns(min(3, len(election_record["manifesto_results"])), gap="small")
        for idx, promise in enumerate(election_record["manifesto_results"]):
            with promise_cols[idx % len(promise_cols)]:
                if promise["status"] == "kept":
                    st.success(f"Kept: {promise['label']}")
                else:
                    st.error(f"Missed: {promise['label']}")
                st.caption(f"{promise['attribute'].replace('_', ' ').title()}: {promise['value']}/{promise['threshold']}")
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


def _render_next_steps(p, ctx):
    """Three-step checklist for the current session."""
    used, remaining, session_key = ctx.used, ctx.remaining, ctx.session_key
    vote_done = session_key in p.get("votes_by_session", {})
    active_bill = _active_private_bill(p)
    active_petition = p.get("petition_campaign")
    petition_active = isinstance(active_petition, dict) and active_petition.get("status") == "active"

    st.markdown("### Your next steps")
    st.caption("A Commons vote is free. Everything else you choose uses one of your two career-action slots.")
    guide_cols = st.columns([1.05, 1.2, 1.05], gap="medium")
    with guide_cols[0]:
        with st.container(border=True):
            st.markdown("**1 · Commons vote**")
            if vote_done:
                st.success("Vote recorded")
                vote_record = p.get("votes_by_session", {}).get(session_key, {})
                st.caption(f"You voted {vote_record.get('vote', 'this session')}.")
            else:
                st.warning("Still to cast")
                st.caption("Choose Aye, No or Abstain. This does not use a career action.")
                if st.button("Go to the vote", key=f"guide_vote_{session_key}", type="primary", use_container_width=True):
                    _set_active_tab("Desk")
                    st.rerun()

    with guide_cols[1]:
        with st.container(border=True):
            st.markdown("**2 · Career actions**")
            _ui_progress(len(used) / ACTIONS_PER_SESSION, text=f"{len(used)} of {ACTIONS_PER_SESSION} used · {remaining} remaining")
            if remaining:
                if active_bill:
                    st.write(f"Suggested next step: **{html.escape(str(active_bill.get('label', 'your bill')))}**")
                    target_tab, target_label = "Plans", "Continue your bill"
                elif petition_active:
                    signatures = int(active_petition.get("signatures", 0))
                    st.write(f"Suggested next step: **Constituency petition** · {signatures:,} signatures")
                    target_tab, target_label = "Nation", "Continue petition"
                elif not petition_active:
                    st.write("Choose local casework, policy work, press, or political networking.")
                    target_tab, target_label = "Nation", "Find an action"
                if st.button(target_label, key=f"guide_action_{session_key}", use_container_width=True):
                    _set_active_tab(target_tab)
                    st.rerun()
                st.caption("Use the navigation buttons above to choose casework, policy work, or politics and press.")
            else:
                st.success("Action slots complete")
                st.caption("Cast your Commons vote, then move on to the next session.")

    with guide_cols[2]:
        with st.container(border=True):
            st.markdown("**3 · Session progress**")
            if remaining == 0 and vote_done:
                st.success("Ready for next session")
                st.caption("Your vote and both career actions are complete.")
                if st.button("Continue session →", key=f"guide_advance_{session_key}", type="primary", use_container_width=True):
                    _advance(p)
            elif remaining == 0 and not vote_done:
                st.warning("Vote still needed")
                st.caption("Complete your Commons vote before moving on.")
                if st.button("Finish Commons vote", key=f"guide_advance_vote_{session_key}", use_container_width=True):
                    _set_active_tab("Desk")
                    st.rerun()
            else:
                st.info(f"{remaining} action{'s' if remaining != 1 else ''} left")
                st.caption("Actions are spent across all four sections, so choose the ones that fit your strategy.")


def _render_desk_tab(p, ctx):
    """Commons vote, whip mood and diary."""
    stats, used, remaining, session_key, capital, capital_dots = ctx.stats, ctx.used, ctx.remaining, ctx.session_key, ctx.capital, ctx.capital_dots
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
            st.caption(f"Local mandate: {MANDATES.get(p.get('local_mandate'), {}).get('label', p.get('local_mandate', 'Not set'))}. The result uses the full 650-seat model, but the party blocs and whip are simplified fictional gameplay—not a real Commons division.")
            if saved_vote:
                st.success(f"Vote recorded: **{saved_vote['vote']}** · Party whip: {saved_vote['party_whip']}.")
                result = saved_vote.get("division_result")
                if result:
                    st.info(f"Simulated result: **{result['result']}** · Ayes {result['ayes']:,} – Noes {result['noes']:,} · Not voting / abstaining {result['abstentions']:,} · Majority {result['majority']:,} across a {result['total_seats']}-seat House.")
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
        _ui_progress(len(used) / ACTIONS_PER_SESSION, text=f"{len(used)}/{ACTIONS_PER_SESSION} career actions used this session")
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
            _ui_progress(leadership / 100, text=f"Leadership confidence · {leadership}/100")
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


def _render_constituency_tab(p, ctx):
    """Casework, petitions and local campaigning."""
    stats, used, remaining, session_key = ctx.stats, ctx.used, ctx.remaining, ctx.session_key
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
            _ui_progress(int(stats.get("campaign_readiness", 30)) / 100)
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
        st.markdown("### 📣 Launch a constituency petition")
        st.caption("Mobilise residents around a local issue. A petition needs 400 signatures before it can be presented to a minister or relevant public body. Launching, campaigning and presenting each use a career-action slot.")
        petition = p.get("petition_campaign")
        if isinstance(petition, dict) and petition.get("status") == "active":
            with st.container(border=True):
                st.markdown(f"**{html.escape(str(petition['title']))}**")
                st.write(petition["description"])
                signatures = int(petition.get("signatures", 0))
                _ui_progress(min(1000, signatures) / 1000, text=f"{signatures:,}/1,000 signatures · {max(0, 400-signatures):,} needed to present")
                if petition.get("last_outcome"):
                    st.caption(petition["last_outcome"])
                drive_col, present_col = st.columns(2, gap="small")
                with drive_col:
                    if st.button("Run a signature drive", key=f"petition_drive_{session_key}", disabled=remaining <= 0 or "petition_signature_drive" in used, use_container_width=True):
                        _run_petition_action(p, "drive")
                with present_col:
                    ready_to_present = signatures >= 400
                    if st.button("Present petition", key=f"petition_present_{session_key}", disabled=remaining <= 0 or "petition_present" in used or not ready_to_present, type="primary", use_container_width=True):
                        _run_petition_action(p, "present")
        else:
            petition_ids = list(PETITION_TOPICS)
            chosen_topic = st.selectbox(
                "Petition issue",
                petition_ids,
                format_func=lambda key: PETITION_TOPICS[key]["label"],
                key=f"petition_topic_{p['career_term']}_{p['career_year']}_{p['career_session']}",
            )
            st.caption(PETITION_TOPICS[chosen_topic]["description"])
            if st.button("Launch petition", key=f"petition_launch_{session_key}", disabled=remaining <= 0 or "launch_petition" in used, type="primary", use_container_width=True):
                _launch_constituency_petition(p, chosen_topic)
        if p.get("petition_history"):
            with st.expander("Previously presented petitions", expanded=False):
                for old_petition in reversed(p["petition_history"][-4:]):
                    st.markdown(f"**{html.escape(str(old_petition.get('title', 'Petition')))}**")
                    st.caption(f"{int(old_petition.get('signatures', 0)):,} signatures · Presented in term {old_petition.get('launched_term')}, year {old_petition.get('launched_year')}.")

        with st.container(border=True):
            st.markdown("### Constituency casework record")
            local_records = [entry for entry in p.get("history", []) if str(entry.get("title", "")).startswith("Inbox:")][-6:]
            if local_records:
                for item in reversed(local_records):
                    st.markdown(f"**{html.escape(str(item['title']))}**")
                    st.caption(html.escape(str(item['text'])))
            else:
                st.caption("Resolved constituent issues will appear here.")


def _render_plans_tab(p, ctx):
    """Manifesto, Private Members' Bills, delivery and promotions."""
    role, used, remaining, session_key = ctx.role, ctx.used, ctx.remaining, ctx.session_key
    st.markdown("## Policy and parliamentary plans")
    st.markdown("### 🗳️ Manifesto and campaign promises")
    st.caption("Make up to three fictional manifesto promises. Each announcement uses a career-action slot. At election time, your stats determine whether voters judge each promise as kept or missed.")
    pledges = p.setdefault("manifesto_pledges", [])
    pledge_cols = st.columns(3, gap="medium")
    for idx, (pledge_id, pledge_spec) in enumerate(MANIFESTO_PLEDGES.items()):
        with pledge_cols[idx % 3]:
            with st.container(border=True):
                already = any(item.get("id") == pledge_id for item in pledges)
                st.markdown(f"**{pledge_spec['label']}**")
                st.write(pledge_spec["description"])
                stat_value = int(p.get("stats", {}).get(pledge_spec["attribute"], 0))
                st.caption(f"Election-night test: {ATTRIBUTES.get(pledge_spec['attribute'], pledge_spec['attribute'])} {pledge_spec['threshold']}+ · currently {stat_value}")
                if already:
                    st.success("Promise already in your manifesto")
                elif len(pledges) >= 3:
                    st.caption("Manifesto limit reached (3 promises).")
                elif st.button("Announce promise", key=f"manifesto_{p['career_term']}_{p['career_year']}_{p['career_session']}_{pledge_id}", disabled=remaining <= 0 or pledge_id in used, use_container_width=True):
                    _make_manifesto_pledge(p, pledge_id)
    if pledges:
        with st.container(border=True):
            st.markdown("#### Your manifesto")
            for pledge in pledges:
                st.markdown(f"**{html.escape(str(pledge.get('label', 'Promise')))}**")
                st.caption(f"Status: {pledge.get('status', 'pending').title()} · Election test: {pledge.get('attribute', 'policy_expertise')} ≥ {pledge.get('threshold', 50)}")
    if p.get("manifesto_history"):
        with st.expander("Previous election promise records", expanded=False):
            for record in reversed(p["manifesto_history"][-5:]):
                st.markdown(f"**Term {record['term']} · manifesto effect {record['score_effect']:+d} election points**")
                for item in record.get("promises", []):
                    st.caption(f"{'✓' if item['status'] == 'kept' else '✗'} {item['label']} — {item['status'].title()} ({item['value']}/{item['threshold']})")
    st.caption("Use your career actions to build expertise, work with colleagues and deliver your current responsibilities.")
    st.markdown("### 🧾 Private Members' Bill office")
    st.caption("Take an idea from a first draft through sponsorship, second reading, committee scrutiny, report stage and a final vote. This is a simplified fictional version of the parliamentary process, and each step uses one career-action slot.")
    bill = _active_private_bill(p)
    saved_bill = p.get("private_members_bill")
    if bill:
        stage_label = PRIVATE_BILL_STAGES.get(bill.get("stage"), bill.get("stage", "In progress"))
        with st.container(border=True):
            st.markdown("<div class='mp-overline'>BILL TRACKER · HOUSE OF COMMONS</div>", unsafe_allow_html=True)
            st.markdown(f"### {html.escape(str(bill['label']))}")
            st.write(bill["description"])
            status_col, sponsor_col, evidence_col = st.columns(3, gap="medium")
            status_col.metric("Current stage", stage_label)
            sponsor_col.metric("Sponsors", f"{int(bill.get('sponsors', 0))}/3")
            evidence_col.metric("Evidence prepared", f"{int(bill.get('evidence', 0))}%")
            _ui_progress(min(100, int(bill.get("evidence", 0))) / 100, text="Evidence and scrutiny preparation")
            if bill.get("last_outcome"):
                st.info(bill["last_outcome"])
            bill_cols = st.columns(2, gap="medium")
            if bill["stage"] == "drafting":
                with bill_cols[0]:
                    st.markdown("**Build cross-party sponsorship**")
                    st.caption("Seek colleagues willing to support your bill.")
                    action_id = "bill_gather_sponsors"
                    if st.button("Lobby for sponsors", key=f"bill_sponsors_{session_key}", disabled=remaining <= 0 or action_id in used, use_container_width=True):
                        _private_bill_action(p, "sponsors")
                with bill_cols[1]:
                    st.markdown("**Prepare evidence and drafting notes**")
                    st.caption("Build the policy case before asking the House to consider it.")
                    action_id = "bill_prepare_evidence"
                    if st.button("Prepare bill evidence", key=f"bill_evidence_{session_key}", disabled=remaining <= 0 or action_id in used, use_container_width=True):
                        _private_bill_action(p, "evidence")
                can_read = int(bill.get("sponsors", 0)) >= 2 and int(bill.get("evidence", 0)) >= 35
                if st.button("Seek a second reading", key=f"bill_second_reading_{session_key}", disabled=remaining <= 0 or "bill_second_reading" in used or not can_read, type="primary", use_container_width=True):
                    _private_bill_action(p, "second_reading")
                if not can_read:
                    st.caption("Requirement: at least 2 sponsors and 35% evidence prepared.")
            elif bill["stage"] == "committee":
                with bill_cols[0]:
                    st.markdown("**Take evidence and refine the bill**")
                    st.caption("Committee scrutiny can expose weaknesses and strengthen the proposal.")
                    if st.button("Prepare committee evidence", key=f"bill_committee_evidence_{session_key}", disabled=remaining <= 0 or "bill_committee_evidence" in used, use_container_width=True):
                        _private_bill_action(p, "committee_evidence")
                with bill_cols[1]:
                    st.markdown("**Complete committee stage**")
                    can_report = int(bill.get("evidence", 0)) >= 65
                    if st.button("Report the bill to the House", key=f"bill_committee_report_{session_key}", disabled=remaining <= 0 or "bill_committee_report" in used or not can_report, use_container_width=True):
                        _private_bill_action(p, "committee_report")
                    if not can_report:
                        st.caption("Requirement: 65% evidence prepared.")
            elif bill["stage"] == "report":
                with bill_cols[0]:
                    st.markdown("**Negotiate report-stage amendments**")
                    st.caption("Seek improvements and another colleague's support.")
                    if st.button("Negotiate an amendment", key=f"bill_report_amendment_{session_key}", disabled=remaining <= 0 or "bill_report_amendment" in used, use_container_width=True):
                        _private_bill_action(p, "report_amendment")
                with bill_cols[1]:
                    st.markdown("**Third reading**")
                    can_final = int(bill.get("sponsors", 0)) >= 3 and int(bill.get("evidence", 0)) >= 65
                    if st.button("Hold final reading vote", key=f"bill_third_reading_{session_key}", disabled=remaining <= 0 or "bill_third_reading" in used or not can_final, type="primary", use_container_width=True):
                        _private_bill_action(p, "third_reading")
                    if not can_final:
                        st.caption("Requirement: 3 sponsors and 65% evidence prepared.")
    else:
        if isinstance(saved_bill, dict) and saved_bill.get("stage") in {"assented", "defeated"}:
            st.success(saved_bill.get("last_outcome", "Your previous Private Member's Bill has concluded."))
        bill_ids = list(PRIVATE_MEMBERS_BILLS)
        selected_bill_id = st.selectbox(
            "Choose a proposal",
            bill_ids,
            format_func=lambda key: PRIVATE_MEMBERS_BILLS[key]["label"],
            key=f"pmb_select_{p['career_term']}_{p['career_year']}_{p['career_session']}",
        )
        selected_spec = PRIVATE_MEMBERS_BILLS[selected_bill_id]
        st.caption(f"{selected_spec['description']} Policy area: {selected_spec['policy_area']}.")
        if st.button("Draft this Private Member's Bill", key=f"pmb_draft_{p['career_term']}_{p['career_year']}_{p['career_session']}", disabled=remaining <= 0 or "draft_private_bill" in used, type="primary", use_container_width=True):
            _draft_private_members_bill(p, selected_bill_id)
    if p.get("private_bill_history"):
        with st.expander("Previous Private Members' Bills", expanded=False):
            for old_bill in reversed(p["private_bill_history"][-5:]):
                icon_label = "✅" if old_bill.get("stage") == "assented" else "❌"
                st.markdown(f"**{icon_label} {html.escape(str(old_bill.get('label', 'Bill')))}**")
                st.caption(old_bill.get("last_outcome", "Completed bill record."))

    if p.get("role") in GOVERNMENT_ROLES:
        st.markdown("### Government portfolio and delivery")
        portfolio_id = p.get("portfolio_id") if p.get("portfolio_id") in PORTFOLIOS else list(PORTFOLIOS)[0]
        portfolio = PORTFOLIOS[portfolio_id]
        portfolio_cols = st.columns(3, gap="medium")
        portfolio_cols[0].metric("Department delivery", f"{int(p.get('department_score', 40))}/100")
        portfolio_cols[1].metric("Target progress", f"{int(p.get('department_progress', 0))}%")
        portfolio_cols[2].metric("Completed targets", len(p.get("completed_targets", [])))
        _ui_progress(int(p.get("department_progress", 0)) / 100, text=f"Target: {p.get('portfolio_target') or portfolio['targets'][0]}")
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
                if p["role"] in DELIVERY_THRESHOLDS:
                    st.caption(f"Department delivery requirement for later promotions: {DELIVERY_THRESHOLDS[p['role']]}/100 or above.")
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


def _render_press_tab(p, ctx):
    """News cycle, factions, standards and leadership."""
    stats, used, remaining, session_key = ctx.stats, ctx.used, ctx.remaining, ctx.session_key
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
            _ui_progress(faction_value / 100)
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


def _render_session_footer(p, ctx):
    """Closing reminder and footer."""
    used, session_key = ctx.used, ctx.session_key
    if len(used) >= ACTIONS_PER_SESSION and not p.get("game_over"):
        st.divider()
        if session_key in p.get("votes_by_session", {}):
            st.success("All required session tasks are complete. Use “Continue session” in the checklist above.")
        else:
            st.warning("Your two career actions are complete, but your Commons vote is still outstanding. Cast it before continuing.")
    st.markdown("<div class='mp-footer-note'>Fictionalised UK parliamentary career simulator · Constituency boundaries use the July 2024 register · No live party whip or current-affairs claims</div>", unsafe_allow_html=True)


def _stat_history_frame(p):
    """Long-format DataFrame of the stat snapshots (one row per attribute per step)."""
    rows = []
    for step, snapshot in enumerate(p.get("stat_history", [])):
        for key, label in ATTRIBUTES.items():
            if key in snapshot.get("stats", {}):
                rows.append({"Step": step, "Point": snapshot.get("label", str(step)),
                             "Attribute": label, "Value": snapshot["stats"][key]})
    return pd.DataFrame(rows, columns=["Step", "Point", "Attribute", "Value"])


def _vote_summary(p):
    """Return ``(whipped_votes, rebellions, abstentions)`` from the voting record."""
    whipped = [v for v in p.get("vote_history", []) if v.get("party_whip") in ("Aye", "No")]
    rebellions = sum(1 for v in whipped if v.get("vote") not in (v.get("party_whip"), "Abstain"))
    abstentions = sum(1 for v in whipped if v.get("vote") == "Abstain")
    return len(whipped), rebellions, abstentions


def _render_stat_trends(p):
    frame = _stat_history_frame(p)
    if frame["Step"].nunique() < 2:
        st.caption("Your attribute trends appear after your first completed session.")
        return
    chart = px.line(
        frame, x="Step", y="Value", color="Attribute", markers=True,
        hover_data={"Point": True, "Step": False, "Value": True},
    )
    chart.update_traces(line=dict(width=2.3))
    chart.update_layout(
        height=360, margin=dict(l=8, r=16, t=8, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#263243", size=11),
        xaxis=dict(title="Parliamentary sessions", gridcolor="#e1e7ee", dtick=1),
        yaxis=dict(title="Attribute (0-100)", range=[0, 100], gridcolor="#e1e7ee"),
        legend=dict(title="", orientation="h", yanchor="bottom", y=-0.35, xanchor="left", x=0),
    )
    st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def _render_achievements(p):
    earned = set(p.get("achievements", []))
    columns = st.columns(3, gap="small")
    for index, achievement in enumerate(achievements.ACHIEVEMENTS):
        with columns[index % 3]:
            with st.container(border=True):
                if achievement["id"] in earned:
                    st.markdown(f"{achievement['icon']} **{achievement['label']}**")
                else:
                    st.markdown(f"🔒 **{achievement['label']}**")
                st.caption(achievement["description"])


def _render_career_tab(p, ctx):
    """Attribute trends, achievements, annual report cards and the full record."""
    st.markdown("## Your career")
    st.caption("How your attributes have moved, what you have achieved and the record you are building.")
    whipped, rebellions, abstentions = _vote_summary(p)
    summary = st.columns(4, gap="small")
    summary[0].metric("Difficulty", DIFFICULTIES.get(p.get("difficulty"), DIFFICULTIES[DEFAULT_DIFFICULTY])["label"])
    summary[1].metric("Years served", int(p.get("career_total_years", 0)))
    summary[2].metric("Rebellions", f"{rebellions} of {whipped}", help=f"Votes against your whip. {abstentions} abstention(s) on whipped votes.")
    summary[3].metric("Achievements", f"{len(p.get('achievements', []))}/{len(achievements.ACHIEVEMENTS)}")
    st.markdown("### Attribute trends")
    _render_stat_trends(p)
    st.markdown("### Achievements")
    _render_achievements(p)
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


def _render_help(p):
    """Short 'how a session works' panel, open during the very first session."""
    first_session = int(p.get("career_total_years", 0)) == 0 and int(p.get("career_session", 1)) == 1 and int(p.get("career_term", 1)) == 1
    with st.expander("How a session works", expanded=first_session):
        st.markdown(
            "- **Vote** in the Commons division (free, once per session).\n"
            f"- Spend your **{ACTIONS_PER_SESSION} career actions** on casework, policy, press or politics.\n"
            "- Press **Continue session** when both are done. "
            f"Every {SESSIONS_PER_YEAR} sessions is a year; after {ELECTION_AFTER} years you face a general election.\n"
            "- Build your attributes, keep standards risk low and watch the fictional polls to win your seat and climb the ladder."
        )


def _build_context(p):
    """Collect the per-run values the section renderers share."""
    role = ROLES.get(p.get("role"), ROLES["mp"])
    stats = p["stats"]
    used = _current_actions(p)
    player_party = str(p.get("party", "Independent"))
    capital = max(0, min(10, int(round(int(stats.get("parliamentary_influence", 0)) / 10))))
    capital_dots = "".join(
        f"<span class='mp-capital-dot {'filled' if n < capital else ''}'></span>" for n in range(10)
    )
    return SimpleNamespace(
        role=role,
        stats=stats,
        used=used,
        remaining=max(0, ACTIONS_PER_SESSION - len(used)),
        session_key=_session_key(p),
        safe_name=html.escape(str(p.get("name", "MP"))),
        safe_constituency=html.escape(str(p.get("constituency", "Westminster"))),
        safe_nation=html.escape(str(p.get("constituency_nation", "United Kingdom"))),
        player_party=player_party,
        party=html.escape(player_party),
        role_label=html.escape(str(role.get("label", "MP"))),
        capital=capital,
        capital_dots=capital_dots,
    )


TAB_RENDERERS = {
    "Desk": _render_desk_tab,
    "Nation": _render_constituency_tab,
    "Plans": _render_plans_tab,
    "Press": _render_press_tab,
    "Career": _render_career_tab,
}


def render():
    """Westminster career dashboard, styled after an official political portal."""
    p = _profile()
    _award_achievements(p)
    ctx = _build_context(p)
    st.session_state.setdefault("mp_active_nav", "Desk")
    _render_header(p, ctx)
    active_tab = _render_navigation(ctx)
    _render_timeline(p, ctx)
    _render_metrics(p, ctx)
    if p.get("game_over"):
        _render_final_report(p)
        return
    _render_help(p)
    _render_next_steps(p, ctx)
    if active_tab == "Parliament":
        _render_parliament_tab()
    elif active_tab == "Polling":
        _render_polling_tab(p)
    else:
        TAB_RENDERERS[active_tab](p, ctx)
    _render_session_footer(p, ctx)
