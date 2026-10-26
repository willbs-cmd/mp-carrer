"""Standalone Streamlit entry point for the MP Political Career game.

Deploy this file as a separate Streamlit app. The Chancellor simulator stays in app.py.
"""
import json
import streamlit as st

import career

st.set_page_config(
    page_title="Westminster · MP Career",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
      --westminster-bg: #0b1f18;
      --westminster-panel: #143629;
      --westminster-border: #2b5744;
      --westminster-gold: #c9a45c;
      --westminster-text: #eee8d8;
      --westminster-muted: #9aafa3;
    }
    .stApp { background: var(--westminster-bg); color: var(--westminster-text); }
    [data-testid="stHeader"] { background: rgba(11,31,24,.92); }
    [data-testid="stMainBlockContainer"] { max-width: 1500px; padding-top: 1.3rem; padding-bottom: 2rem; }
    .mp-hero {
      border: 1px solid var(--westminster-border);
      border-left: 7px solid var(--westminster-gold);
      border-radius: 14px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.3rem;
      background: linear-gradient(120deg, #173d2d, #0d241a 72%);
    }
    .mp-hero .kicker { color: var(--westminster-gold); text-transform: uppercase; letter-spacing: .12em; font-size: .75rem; font-weight: 750; }
    .mp-hero h1 { margin: .25rem 0 .35rem; font-family: Georgia, serif; color: var(--westminster-text); font-size: clamp(2rem, 4vw, 3.15rem); }
    .mp-hero p { margin: 0; color: #c1d0c6; font-size: 1.03rem; }
    .ch-banner {
      padding: 1rem 1.2rem; border-radius: 12px; border: 1px solid var(--westminster-border);
      border-left: 6px solid var(--westminster-gold);
      background: linear-gradient(120deg, #173d2d, #0d241a 72%); margin-bottom: 1rem;
    }
    .ch-head { display:flex; flex-wrap:wrap; gap:.8rem; justify-content:space-between; align-items:center; }
    .ch-title { color:var(--westminster-text); font-weight:800; font-size:1.6rem; font-family:Georgia,serif; }
    .ch-banner .sub { display:block; color:var(--westminster-muted); margin-top:.25rem; }
    [data-testid="stMetric"] { background:var(--westminster-panel); border:1px solid var(--westminster-border); border-top:3px solid var(--westminster-gold); padding:.75rem .9rem; border-radius:10px; }
    [data-testid="stMetricLabel"] { color:var(--westminster-muted); }
    [data-testid="stMetricValue"] { color:var(--westminster-text); font-family:Georgia,serif; }
    [data-testid="stVerticalBlock"] { gap:.8rem; }
    [data-testid="stHorizontalBlock"] { gap:.8rem; }
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
      border-radius:8px; min-height:2.65rem; white-space:normal; padding:.6rem .9rem;
    }
    [data-testid="stExpander"] { border-color:var(--westminster-border); border-radius:9px; }
    [data-testid="stRadio"] label, [data-testid="stSelectbox"] label, [data-testid="stTextInput"] label, [data-testid="stNumberInput"] label { color:var(--westminster-text); }
    .mp-source-note { font-size:.88rem; color:var(--westminster-muted); }
    @media (max-width: 760px) {
      [data-testid="stMainBlockContainer"] { padding-left:1rem; padding-right:1rem; }
      .mp-hero { padding:1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.session_state.setdefault("seed", 32458)
st.session_state.setdefault("party", "Labour")
st.session_state.setdefault("step", "setup")
st.session_state.setdefault("career_profile", None)

with st.sidebar:
    st.markdown("### 🗳️ MP Career save")
    profile = st.session_state.get("career_profile")
    if isinstance(profile, dict):
        save_data = {
            "schema_version": 1,
            "game_mode": "mp_career",
            "seed": int(st.session_state.get("seed", 32458)),
            "party": st.session_state.get("party", profile.get("party", "Labour")),
            "profile": profile,
        }
        st.download_button(
            "Download MP career save",
            data=json.dumps(save_data, ensure_ascii=False, indent=2),
            file_name=f"mp_career_{profile.get('constituency', 'westminster').lower().replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
        )
    uploaded = st.file_uploader("Load an MP career save", type=["json"], key="mp_career_save_upload")
    if uploaded is not None and st.button("Load career", use_container_width=True):
        try:
            parsed = json.loads(uploaded.getvalue().decode("utf-8"))
            candidate = parsed.get("profile", {})
            if parsed.get("game_mode") != "mp_career":
                raise ValueError("This is not an MP Career Mode save.")
            if candidate.get("role") not in career.ROLES:
                raise ValueError("The save contains an unknown political role.")
            if candidate.get("constituency") not in career.CONSTITUENCY_BY_NAME:
                raise ValueError("The save does not contain a recognised 2024 Westminster constituency.")
            if not isinstance(candidate.get("stats"), dict) or not set(career.ATTRIBUTES).issubset(candidate["stats"]):
                raise ValueError("The save is missing required career attributes.")
            st.session_state.career_profile = candidate
            st.session_state.seed = int(parsed.get("seed", 32458))
            st.session_state.party = candidate.get("party", parsed.get("party", "Labour"))
            st.session_state.step = "game"
            st.rerun()
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            st.error(f"Could not load that save: {exc}")
    st.divider()
    if profile and st.button("Start a new MP career", use_container_width=True):
        st.session_state.career_profile = None
        st.session_state.step = "setup"
        st.rerun()

profile = st.session_state.get("career_profile")
if st.session_state.get("step") == "setup" or not isinstance(profile, dict):
    st.markdown(
        """
        <div class="mp-hero">
          <div class="kicker">Westminster · Political Career Simulator</div>
          <h1>🏛️ Your Career in Parliament</h1>
          <p>Start as a backbench MP, represent a real constituency, vote in Commons divisions and build a path towards ministerial office.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## Create your MP")
    st.caption("This is a standalone game, separate from the Chancellor's Office simulator. Constituency names and codes use the official July 2024 Westminster constituency list; your character is fictional and is not asserted to be the current MP for that seat.")

    with st.form("mp_career_start_form"):
        name = st.text_input("Your MP's name", value="Alex Morgan", max_chars=70)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            party = st.selectbox("Party", career.DIVISION_DATA["party_names"], index=0)
            constituency = st.selectbox(
                "Real Westminster constituency",
                career.CONSTITUENCY_NAMES,
                index=career.CONSTITUENCY_NAMES.index("Droitwich and Evesham") if "Droitwich and Evesham" in career.CONSTITUENCY_NAMES else 0,
                format_func=lambda value: f"{value} · {career.CONSTITUENCY_BY_NAME[value]['nation']}",
                help="Search the list by typing a constituency name. The list contains all 650 constituencies in the July 2024 boundary edition.",
            )
        with c2:
            ambition = st.selectbox(
                "Career approach",
                list(career.DATA["ambitions"]),
                format_func=lambda key: career.DATA["ambitions"][key]["label"],
            )
            local_mandate = st.selectbox(
                "Your constituency campaign priority",
                list(career.MANDATES),
                format_func=lambda key: career.MANDATES[key]["label"],
                help="This is a gameplay choice, not an assumption about how everyone in the real constituency thinks.",
            )
        st.caption(career.DATA["ambitions"][ambition]["description"])
        st.caption(career.MANDATES[local_mandate]["description"])
        seed = st.number_input("Game seed", min_value=1, max_value=999999, value=int(st.session_state.get("seed", 32458)), step=1)
        start = st.form_submit_button("Enter the House of Commons", type="primary", use_container_width=True)

    st.markdown(
        '<p class="mp-source-note">Constituency source: '
        '<a href="https://www.data.gov.uk/dataset/90293fcf-9268-4a1a-be3d-d4a20d314604/westminster-parliamentary-constituencies-july-2024-names-and-codes-in-the-uk-v2" target="_blank">Office for National Statistics · July 2024 Westminster constituencies</a>.</p>',
        unsafe_allow_html=True,
    )
    if start:
        st.session_state.seed = int(seed)
        st.session_state.party = party
        st.session_state.career_profile = career.new_profile(
            name=name,
            constituency=constituency,
            ambition=ambition,
            local_mandate=local_mandate,
            party=party,
        )
        st.session_state.step = "game"
        st.rerun()
else:
    career.render()
