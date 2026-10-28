"""Streamlit entry point for the MP Political Career game.

Run with ``streamlit run app.py``. Styling lives in ``assets/style.css``, save
handling in ``saves.py`` and gameplay in ``career.py``.
"""
from pathlib import Path

import streamlit as st

import career
import saves

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_SEED = saves.DEFAULT_SEED

st.set_page_config(
    page_title="Westminster · UK MP Career",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def _stylesheet():
    return (ASSETS_DIR / "style.css").read_text(encoding="utf-8")


st.markdown(f"<style>{_stylesheet()}</style>", unsafe_allow_html=True)

st.session_state.setdefault("seed", DEFAULT_SEED)
st.session_state.setdefault("party", "Labour")
st.session_state.setdefault("step", "setup")
st.session_state.setdefault("career_profile", None)


def _render_sidebar():
    """Save / load controls and the 'new career' button."""
    with st.sidebar:
        st.markdown("### 🗳️ MP Career save")
        profile = st.session_state.get("career_profile")
        if isinstance(profile, dict):
            st.download_button(
                "Download MP career save",
                data=saves.build_save(profile, st.session_state.get("seed", DEFAULT_SEED), st.session_state.get("party")),
                file_name=saves.save_filename(profile),
                mime="application/json",
                use_container_width=True,
            )
        uploaded = st.file_uploader("Load an MP career save", type=["json"], key="mp_career_save_upload")
        if uploaded is not None and st.button("Load career", use_container_width=True):
            try:
                candidate, seed = saves.parse_save(
                    uploaded.getvalue(), career.ROLES, career.CONSTITUENCY_BY_NAME, career.ATTRIBUTES
                )
            except saves.SaveError as exc:
                st.error(f"Could not load that save: {exc}")
            else:
                st.session_state.career_profile = candidate
                st.session_state.seed = seed
                st.session_state.party = candidate.get("party", "Labour")
                st.session_state.step = "game"
                st.rerun()
        st.divider()
        if profile and st.button("Start a new MP career", use_container_width=True):
            st.session_state.career_profile = None
            st.session_state.step = "setup"
            st.rerun()


def _render_setup():
    """Character creation screen."""
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
    st.caption(
        "Constituency names and codes use the July 2024 Westminster boundary list. Your MP and all headlines, "
        "colleagues, divisions and whip positions are fictional game content, not live political news or claims about current MPs."
    )
    default_seat = "Droitwich and Evesham"
    seats = career.CONSTITUENCY_NAMES
    with st.form("mp_career_start_form"):
        name = st.text_input("Your MP's name", value="Alex Morgan", max_chars=70)
        left, right = st.columns(2, gap="medium")
        with left:
            party = st.selectbox(
                "UK parliamentary party",
                career.DIVISION_DATA["party_names"],
                index=0,
                help="Northern Ireland parties and independents default to free votes in this simplified model.",
            )
            constituency = st.selectbox(
                "Real Westminster constituency",
                seats,
                index=seats.index(default_seat) if default_seat in seats else 0,
                format_func=lambda value: f"{value} · {career.CONSTITUENCY_BY_NAME[value]['nation']}",
                help="Type to search all 650 constituencies.",
            )
        with right:
            ambition = st.selectbox(
                "Career approach",
                list(career.DATA["ambitions"]),
                format_func=lambda key: career.DATA["ambitions"][key]["label"],
            )
            local_mandate = st.selectbox(
                "Your constituency campaign priority",
                list(career.MANDATES),
                format_func=lambda key: career.MANDATES[key]["label"],
                help="A gameplay choice, not an assumption about how everyone in the real constituency thinks.",
            )
        difficulty = st.select_slider(
            "Difficulty",
            options=list(career.DIFFICULTIES),
            value="standard",
            format_func=lambda key: career.DIFFICULTIES[key]["label"],
        )
        st.caption(career.DATA["ambitions"][ambition]["description"])
        st.caption(career.MANDATES[local_mandate]["description"])
        st.caption(career.DIFFICULTIES[difficulty]["description"])
        seed = st.number_input("Game seed", min_value=1, max_value=999999, value=int(st.session_state.get("seed", DEFAULT_SEED)), step=1)
        start = st.form_submit_button("Enter the House of Commons", type="primary", use_container_width=True)

    st.markdown(
        '<p class="mp-source-note">Constituency source: '
        '<a href="https://www.data.gov.uk/dataset/90293fcf-9268-4a1a-be3d-d4a20d314604/westminster-parliamentary-constituencies-july-2024-names-and-codes-in-the-uk-v2" target="_blank">'
        "Office for National Statistics · July 2024 Westminster constituencies</a>.</p>",
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
            difficulty=difficulty,
        )
        st.session_state.step = "game"
        st.rerun()


_render_sidebar()
_profile = st.session_state.get("career_profile")
if st.session_state.get("step") == "setup" or not isinstance(_profile, dict):
    _render_setup()
else:
    career.render()
