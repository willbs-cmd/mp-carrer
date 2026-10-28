"""Render every dashboard section in several game states without a Streamlit server."""
import unittest
from unittest.mock import MagicMock, patch

import career
from tests.fake_streamlit import make_fake_streamlit

TABS = ("Desk", "Nation", "Plans", "Press", "Career", "Parliament", "Polling")


def _profile(**overrides):
    profile = career.new_profile(name="Test MP", constituency="Droitwich and Evesham", party="Labour")
    profile.update(overrides)
    return profile


def _mid_career():
    profile = _profile()
    for session in range(1, 4):
        profile["career_session"] = session
        career._record_stat_snapshot(profile, f"T1 Y1 S{session}")
    key = career._session_key(profile)
    division = career.DIVISIONS[0]
    profile["votes_by_session"][key] = {
        "vote": "Aye", "party_whip": "Aye", "division_result": career._simulate_division_result(profile, division, "Aye"),
        "effects_summary": "+1 integrity",
    }
    profile["vote_history"] = [{"term": 1, "year": 1, "session": 1, "title": "Test", "vote": "No", "party_whip": "Aye",
                                "followed_whip": False, "effects_summary": ""}]
    profile["annual_reports"] = [{"term": 1, "year": 1, "score": 70.0, "grade": "C", "strongest": "Integrity",
                                  "focus": "Party trust", "actions_taken": 6, "votes_cast": 3, "whips_followed": 2}]
    return profile


def _profiles():
    minister = _profile(role="junior_minister")
    pm = _profile(role="prime_minister")
    bill = _mid_career()
    career._draft_private_members_bill = career._draft_private_members_bill  # keep reference stable
    bill["private_members_bill"] = {
        "id": next(iter(career.PRIVATE_MEMBERS_BILLS)), "label": "Test Bill", "description": "d",
        "policy_area": "x", "stage": "drafting", "sponsors": 1, "evidence": 10, "last_outcome": "",
    }
    bill["petition_campaign"] = {"title": "Petition", "description": "d", "signatures": 120, "status": "active",
                                 "topic": next(iter(career.PETITION_TOPICS))}
    over = _mid_career()
    over.update(game_over=True, election_result={"party_vote_share": 24.0, "polling_leader": "Labour", "polling_effect": 1.0})
    legacy = _profile()
    for key in ("difficulty", "stat_history", "achievements"):
        legacy.pop(key, None)
    return {"new": _profile(), "mid": _mid_career(), "minister": minister, "pm": pm,
            "bill_and_petition": bill, "game_over": over, "legacy_save": legacy}


class RenderSmokeTests(unittest.TestCase):
    def _render(self, profile, tab):
        fake = make_fake_streamlit(career_profile=profile, seed=1, mp_active_nav=tab, step="game")
        with patch.object(career, "st", fake), patch.object(career, "px", MagicMock()), \
                patch.object(career, "_current_commons_party_map", side_effect=RuntimeError("offline")):
            career.render()
        return fake

    def test_every_tab_renders_in_every_game_state(self):
        for name, profile in _profiles().items():
            for tab in TABS:
                with self.subTest(state=name, tab=tab):
                    self._render(profile, tab)

    def test_legacy_save_is_upgraded_on_render(self):
        legacy = _profiles()["legacy_save"]
        self._render(legacy, "Desk")
        self.assertEqual(legacy["difficulty"], career.DEFAULT_DIFFICULTY)
        self.assertIsInstance(legacy["stat_history"], list)
        self.assertIsInstance(legacy["achievements"], list)

    def test_rendering_awards_achievements_once(self):
        profile = _mid_career()
        self._render(profile, "Career")
        self.assertIn("first_vote", profile["achievements"])
        count = len(profile["achievements"])
        self._render(profile, "Career")
        self.assertEqual(len(profile["achievements"]), count)

    def test_navigation_options_all_have_labels_and_renderers(self):
        self.assertEqual(set(career.NAV_OPTIONS), set(career.NAV_LABELS))
        for tab in career.NAV_OPTIONS:
            self.assertTrue(tab in career.TAB_RENDERERS or tab in {"Parliament", "Polling"}, tab)


if __name__ == "__main__":
    unittest.main()
