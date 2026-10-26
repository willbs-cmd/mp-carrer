"""Standalone Streamlit entry point for the MP Political Career game.

Deploy this file as a separate Streamlit app. The Chancellor simulator stays in app.py.
"""
import json
import streamlit as st

import career

st.set_page_config(
    page_title="Westminster · UK MP Career",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
:root {
  --mp-bg: #edf0f3;
  --mp-paper: #ffffff;
  --mp-paper-soft: #f7f8fa;
  --mp-border: #d9e0e8;
  --mp-text: #171b22;
  --mp-muted: #626e7d;
  --mp-red: #bd1730;
  --mp-red-dark: #941128;
  --mp-red-pale: #fff0f2;
  --mp-gold: #c9a34f;
  --mp-gold-pale: #f6e8ba;
  --mp-shadow: 0 2px 5px rgba(19, 30, 45, .055);
}
html { scroll-behavior: smooth; }
.stApp {
  background: var(--mp-bg);
  color: var(--mp-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
[data-testid="stHeader"] { background: rgba(237,240,243,.94); }
[data-testid="stMainBlockContainer"] {
  max-width: 1800px;
  padding: 1.1rem clamp(1rem, 2vw, 2.1rem) 2.4rem;
}
h1, h2, h3, h4 { color: var(--mp-text); letter-spacing: -.025em; }
h2, h3 { font-weight: 760; }
p, label, [data-testid="stMarkdownContainer"] { color: var(--mp-text); }
small, [data-testid="stCaptionContainer"] { color: var(--mp-muted); }
[data-testid="stVerticalBlock"] { gap: .72rem; }
[data-testid="stHorizontalBlock"] { gap: .7rem; }

/* Official-portal inspired masthead */
.mp-portal {
  display: grid;
  grid-template-columns: minmax(250px, 1.1fr) minmax(220px, 1fr) auto;
  align-items: center;
  gap: 1.25rem;
  min-height: 88px;
  padding: .75rem 0 1rem;
  border-bottom: 4px solid var(--mp-red);
  margin-bottom: .45rem;
  animation: mpFadeDown .45s ease-out both;
}
.mp-portal-brand { display:flex; align-items:center; gap:.8rem; min-width:0; }
.mp-crest {
  width:48px; height:48px; border-radius:50%;
  display:grid; place-items:center; flex:0 0 auto;
  background:linear-gradient(145deg,#fff,#f1e3b7);
  color:#7e1825; font-family:Georgia,serif; font-size:1.65rem; font-weight:800;
  border:2px solid #bca15d; box-shadow:inset 0 0 0 3px #fff,0 2px 5px #00000012;
}
.mp-brand-title { font-size:1.5rem; line-height:1.05; font-weight:850; letter-spacing:-.045em; color:#141920; }
.mp-brand-sub { margin-top:.22rem; font-size:.88rem; font-weight:650; color:#687382; }
.mp-portal-motto { color:#596574; font-size:.83rem; line-height:1.5; }
.mp-portal-motto span { color:var(--mp-red); padding:0 .25rem; }
.mp-user-chip {
  display:flex; align-items:center; gap:.65rem; padding:.4rem .7rem;
  border:1px solid var(--mp-border); background:#fff; border-radius:999px;
  box-shadow:var(--mp-shadow); max-width:260px;
}
.mp-user-chip strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.mp-user-chip small { display:block; color:var(--mp-muted); margin-top:.08rem; }
.mp-avatar {
  display:grid; place-items:center; flex:0 0 auto;
  width:36px; height:36px; border-radius:50%; background:#171b22; color:#fff;
  border:2px solid var(--mp-red); font-weight:800;
}

/* Streamlit radio navigation styled as portal tabs */
[data-testid="stRadio"] { margin:.1rem 0 .5rem; }
[data-testid="stRadio"] > label { display:none; }
[data-testid="stRadio"] div[role="radiogroup"] {
  display:flex; align-items:center; gap:clamp(.65rem,2.4vw,2.3rem);
  border-bottom:1px solid var(--mp-border); padding:0 .15rem; flex-wrap:wrap;
}
[data-testid="stRadio"] div[role="radiogroup"] > label {
  margin:0; padding:.8rem .25rem .75rem; border-radius:0;
  background:transparent; border-bottom:3px solid transparent;
  color:#343c47; font-size:1rem; font-weight:760;
  transition:color .18s ease,border-color .18s ease,transform .18s ease;
}
[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
  color:var(--mp-red); transform:translateY(-1px);
}
[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
  color:#111820; border-bottom-color:var(--mp-red);
}
[data-testid="stRadio"] div[role="radiogroup"] input { accent-color:var(--mp-red); }

/* Term and parliamentary timeline */
.mp-season-strip {
  display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding:.72rem 0 .8rem; flex-wrap:wrap;
}
.mp-season-left,.mp-season-right { display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; }
.mp-season-left strong { font-size:1.05rem; }
.mp-season-detail,.mp-season-right { color:var(--mp-muted); font-size:.92rem; }
.mp-season-right { text-align:right; }
.mp-season-right span { color:var(--mp-red); }
.mp-live-tag {
  display:inline-flex; align-items:center; justify-content:center;
  color:var(--mp-red); background:#fbe7eb; border:1px solid #f2d0d7;
  border-radius:5px; padding:.24rem .55rem; font-size:.73rem;
  font-weight:850; letter-spacing:.07em;
}
.mp-overview-panel {
  background:var(--mp-paper); border:1px solid var(--mp-border); border-radius:12px;
  padding:.9rem 1rem 1rem; margin-bottom:1rem; box-shadow:var(--mp-shadow);
  animation:mpFadeUp .45s .08s both;
}
.mp-overview-heading { display:flex; align-items:baseline; gap:.7rem; flex-wrap:wrap; margin-bottom:.8rem; }
.mp-overview-heading strong { font-size:1.02rem; }
.mp-overview-heading span { font-size:.89rem; color:var(--mp-muted); }
.mp-timeline-track {
  display:grid; grid-template-columns:repeat(15,minmax(0,1fr)) minmax(58px,.9fr);
  gap:.35rem; align-items:stretch;
}
.mp-timeline-tile,.mp-timeline-poll {
  min-width:0; min-height:54px; padding:.45rem .45rem .35rem;
  display:flex; flex-direction:column; justify-content:space-between;
  background:#f5f7f9; border:1px solid #d6dee7; border-radius:8px;
  border-top:3px solid transparent;
  transition:transform .2s ease,background .2s ease,border-color .2s ease,box-shadow .2s ease;
}
.mp-timeline-tile small,.mp-timeline-poll small { font-size:.65rem; font-weight:850; color:#738090; letter-spacing:.02em; }
.mp-timeline-tile strong { font-size:.75rem; color:#485362; }
.mp-timeline-tile.complete { border-top-color:#c5ccd5; background:#f1f3f6; }
.mp-timeline-tile.current {
  border-color:var(--mp-red); border-top-color:var(--mp-red); background:#fff7f8;
  box-shadow:0 0 0 2px #bd173018; animation:mpCurrentPulse 2.6s ease-in-out infinite;
}
.mp-timeline-tile.current small,.mp-timeline-tile.current strong { color:var(--mp-red); }
.mp-timeline-tile:hover { transform:translateY(-2px); box-shadow:var(--mp-shadow); }
.mp-timeline-poll {
  border-color:#e8a3af; color:var(--mp-red);
  background:repeating-linear-gradient(135deg,#fff 0,#fff 7px,#fff0f2 7px,#fff0f2 14px);
}
.mp-timeline-poll strong { color:var(--mp-red); font-size:1rem; }

/* Headline stats cards */
[data-testid="stMetric"] {
  background:var(--mp-paper); border:1px solid var(--mp-border);
  border-radius:12px; padding:.7rem .75rem .72rem; min-height:94px;
  box-shadow:var(--mp-shadow); animation:mpFadeUp .5s ease both;
  transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;
}
[data-testid="stMetric"]:hover {
  transform:translateY(-3px); border-color:#c7a0a7;
  box-shadow:0 7px 17px rgba(21,32,48,.08);
}
[data-testid="stMetricLabel"] { color:#5d6876 !important; font-size:.8rem !important; font-weight:700 !important; }
[data-testid="stMetricValue"] { color:#111820 !important; font-size:clamp(1.2rem,1.45vw,1.8rem) !important; font-weight:850 !important; letter-spacing:-.045em; }
[data-testid="stMetricDelta"] { font-size:.75rem; }

/* White paper / card surfaces */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--mp-paper); border:1px solid var(--mp-border);
  border-radius:12px; overflow:hidden; box-shadow:var(--mp-shadow);
  animation:mpFadeUp .42s ease both;
  transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"] > div { background:transparent; }
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color:#c8d0da; box-shadow:0 5px 16px rgba(22,33,47,.06);
}
[data-testid="stAlert"] { border-radius:9px; border:1px solid var(--mp-border); }
[data-testid="stAlert"] p { color:var(--mp-text); }
[data-testid="stExpander"] { border:1px solid var(--mp-border); border-radius:10px; background:#fff; }
[data-testid="stExpander"] details summary { transition:background .18s ease,color .18s ease; }
[data-testid="stExpander"] details summary:hover { background:#fff6f7; color:var(--mp-red); }
.mp-overline {
  color:var(--mp-red); font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.74rem; letter-spacing:.15em; font-weight:850; margin-bottom:.5rem;
}
.mp-capital-meter { display:flex; align-items:center; gap:.35rem; margin:.7rem 0; }
.mp-capital-dot {
  width:20px; height:20px; border:2px solid #bfccd8; border-radius:50%;
  background:#f8fafb; display:inline-block; flex:0 0 auto;
  transition:background .35s ease,border-color .35s ease,transform .2s ease;
}
.mp-capital-dot.filled {
  background:radial-gradient(circle at 30% 25%,#f7e8ad,#c09a43 68%,#967629);
  border-color:#ab8838; box-shadow:inset 0 1px 1px #ffffffaa;
}
.mp-capital-dot.filled:hover { transform:scale(1.12); }
.mp-capital-meter strong { margin-left:auto; font-size:2rem; letter-spacing:-.04em; }
.mp-diary-entry { display:grid; grid-template-columns:12px 1fr; gap:.7rem; padding:.55rem 0; }
.mp-diary-marker { width:9px; height:9px; border-radius:50%; background:var(--mp-red); margin-top:.45rem; box-shadow:0 0 0 4px #bd173013; }
.mp-diary-entry strong { display:block; font-size:.9rem; }
.mp-diary-entry p { margin:.16rem 0 .25rem; color:#4f5c6a; font-size:.85rem; line-height:1.45; }
.mp-diary-entry small { color:#7b8795; font-size:.74rem; }
.mp-person-pill {
  display:inline-block; padding:.35rem .65rem; margin:.15rem;
  border:1px solid #b6ddc5; color:#24643b; background:#effaf2; border-radius:999px; font-size:.86rem;
}
.mp-person-pill.rival { border-color:#efc2c8; color:#9a2031; background:#fff1f3; }
.mp-footer-note { padding:1rem 0 0; margin-top:1.4rem; border-top:1px solid var(--mp-border); color:#76818e; font-size:.78rem; letter-spacing:.02em; }
.mp-setup-card { background:#fff; border:1px solid var(--mp-border); border-radius:14px; padding:1.3rem; box-shadow:var(--mp-shadow); }
[data-testid="stProgress"] { margin:.35rem 0 .65rem; }
[data-testid="stProgress"] > div { background:#e8edf2; border-radius:99px; overflow:hidden; }
[data-testid="stProgress"] > div > div { background:var(--mp-red); border-radius:99px; transition:width .55s cubic-bezier(.2,.7,.2,1); }

/* Buttons */
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button {
  min-height:2.55rem; padding:.55rem .9rem; border-radius:8px;
  background:#fff; color:#2a323c; border:1px solid #cfd7e0;
  font-weight:740; white-space:normal;
  transition:background .18s ease,color .18s ease,border-color .18s ease,transform .18s ease,box-shadow .18s ease;
}
[data-testid="stButton"] button:hover,[data-testid="stDownloadButton"] button:hover,[data-testid="stFormSubmitButton"] button:hover {
  background:#fff0f2; color:var(--mp-red); border-color:#dba5ae;
  transform:translateY(-1px); box-shadow:0 4px 10px #bd173014;
}
[data-testid="stButton"] button:active,[data-testid="stDownloadButton"] button:active { transform:translateY(0) scale(.99); }
[data-testid="stButton"] button:disabled { background:#f3f5f7; color:#8993a0; border-color:#dce2e8; opacity:1; cursor:not-allowed; box-shadow:none; transform:none; }
[data-testid="stButton"] button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background:var(--mp-red) !important; color:#fff !important; border-color:var(--mp-red) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
  background:var(--mp-red-dark) !important; color:#fff !important; border-color:var(--mp-red-dark) !important;
}
[data-testid="stSelectbox"] label,[data-testid="stTextInput"] label,[data-testid="stNumberInput"] label,[data-testid="stRadio"] label { color:#35404c; font-weight:650; }
[data-testid="stSelectbox"] > div > div { background:#fff; border-color:#cfd7e0; }
.mp-source-note { font-size:.85rem; color:var(--mp-muted); }
.mp-source-note a { color:var(--mp-red); text-decoration:underline; text-underline-offset:2px; }

/* Motion: subtle, reduced automatically for people who request less animation */
@keyframes mpFadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
@keyframes mpFadeDown { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }
@keyframes mpCurrentPulse { 0%,100% { box-shadow:0 0 0 2px #bd173012; } 50% { box-shadow:0 0 0 4px #bd173021; } }

@media (max-width: 1150px) {
  .mp-portal { grid-template-columns:1fr auto; }
  .mp-portal-motto { grid-column:1 / -1; grid-row:2; }
  .mp-timeline-track { grid-template-columns:repeat(5,minmax(0,1fr)); }
  .mp-timeline-poll { min-height:48px; }
  [data-testid="stMetric"] { min-height:84px; }
}
@media (max-width: 720px) {
  [data-testid="stMainBlockContainer"] { padding: .7rem .75rem 1.5rem; }
  .mp-portal { grid-template-columns:1fr; gap:.7rem; padding:.5rem 0 .8rem; }
  .mp-user-chip { justify-self:start; }
  .mp-season-strip { align-items:flex-start; }
  .mp-season-right { text-align:left; }
  .mp-timeline-track { grid-template-columns:repeat(4,minmax(0,1fr)); }
  .mp-timeline-tile,.mp-timeline-poll { min-height:48px; }
  [data-testid="stMetricValue"] { font-size:1.2rem !important; }
  [data-testid="stMetric"] { padding:.55rem .55rem; }
  [data-testid="stRadio"] div[role="radiogroup"] { gap:.45rem; }
  [data-testid="stRadio"] div[role="radiogroup"] > label { font-size:.88rem; padding:.65rem .2rem; }
}
@media (prefers-reduced-motion: reduce) {
  *,*::before,*::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; transition-duration:.01ms !important; }
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
            required_stats = set(career.ATTRIBUTES) - {"campaign_readiness"}
            if not isinstance(candidate.get("stats"), dict) or not required_stats.issubset(candidate["stats"]):
                raise ValueError("The save is missing required career attributes.")
            candidate["stats"].setdefault("campaign_readiness", 30)
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
          <h1>🏛️ Your Westminster Career</h1>
          <p>Start as a backbench MP in England, Scotland, Wales or Northern Ireland. Navigate Commons votes, PMQs, Select Committees, party factions, the Westminster press and the next general election.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## Create your MP")
    st.caption("This is a UK Westminster political simulation, separate from the Chancellor's Office simulator. Constituency names and codes use the July 2024 Westminster boundary list. Your MP and all Phase 2 headlines, colleagues, divisions and whip positions are fictional game content, not live political news or claims about current MPs.")

    with st.form("mp_career_start_form"):
        name = st.text_input("Your MP's name", value="Alex Morgan", max_chars=70)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            party = st.selectbox("UK parliamentary party", career.DIVISION_DATA["party_names"], index=0, help="Includes parties from across the UK and independent MPs. Northern Ireland parties and independents default to free votes in this simplified fictional model.")
            constituency = st.selectbox(
                "Real Westminster constituency",
                career.CONSTITUENCY_NAMES,
                index=career.CONSTITUENCY_NAMES.index("Droitwich and Evesham") if "Droitwich and Evesham" in career.CONSTITUENCY_NAMES else 0,
                format_func=lambda value: f"{value} · {career.CONSTITUENCY_BY_NAME[value]['nation']}",
                help="Search the list by typing a constituency name. The list contains all 650 constituencies in the July 2024 boundary edition, covering England, Scotland, Wales and Northern Ireland.",
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
