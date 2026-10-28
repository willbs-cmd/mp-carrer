"""Tests for saves, achievements, difficulty, stat history and a headless playthrough."""
import json
import re
import unittest
from unittest.mock import patch

import achievements
import career
import saves
from tests.fake_streamlit import make_fake_streamlit


def _new(**kwargs):
    kwargs.setdefault("constituency", "Droitwich and Evesham")
    return career.new_profile(name="Test MP", party="Labour", **kwargs)


class SaveTests(unittest.TestCase):
    def parse(self, raw):
        return saves.parse_save(raw, career.ROLES, career.CONSTITUENCY_BY_NAME, career.ATTRIBUTES)

    def test_round_trip_preserves_profile_and_seed(self):
        profile = _new(difficulty="hard")
        text = saves.build_save(profile, seed=777)
        loaded, seed = self.parse(text.encode("utf-8"))
        self.assertEqual(seed, 777)
        self.assertEqual(loaded["difficulty"], "hard")
        self.assertEqual(loaded["constituency"], profile["constituency"])

    def test_filename_is_a_safe_slug(self):
        self.assertEqual(saves.save_filename({"constituency": "Droitwich and Evesham"}), "mp_career_droitwich_and_evesham.json")
        self.assertEqual(saves.save_filename({"constituency": "Ynys Môn / Anglesey!"}), "mp_career_ynys_m_n_anglesey.json")
        self.assertEqual(saves.save_filename({}), "mp_career_westminster.json")

    def test_rejects_bad_files(self):
        good = json.loads(saves.build_save(_new()))
        cases = {
            "not json": "{nope",
            "wrong mode": json.dumps({**good, "game_mode": "chancellor"}),
            "future version": json.dumps({**good, "schema_version": 99}),
            "no profile": json.dumps({**good, "profile": None}),
            "unknown role": json.dumps({**good, "profile": {**good["profile"], "role": "dictator"}}),
            "unknown seat": json.dumps({**good, "profile": {**good["profile"], "constituency": "Narnia"}}),
            "missing stats": json.dumps({**good, "profile": {**good["profile"], "stats": {"integrity": 5}}}),
            "bad stat value": json.dumps({**good, "profile": {**good["profile"], "stats": {**good["profile"]["stats"], "integrity": "lots"}}}),
        }
        for name, raw in cases.items():
            with self.subTest(case=name), self.assertRaises(saves.SaveError):
                self.parse(raw)

    def test_oversized_and_non_utf8_uploads_are_rejected(self):
        with self.assertRaises(saves.SaveError):
            self.parse(b"x" * (saves.MAX_SAVE_BYTES + 1))
        with self.assertRaises(saves.SaveError):
            self.parse(b"\xff\xfe\x00")

    def test_version_1_save_is_migrated_and_stats_clamped(self):
        legacy = json.loads(saves.build_save(_new()))
        legacy["schema_version"] = 1
        for key in ("difficulty", "stat_history", "achievements"):
            legacy["profile"].pop(key)
        legacy["profile"]["stats"]["integrity"] = 400
        del legacy["profile"]["stats"]["campaign_readiness"]
        profile, _ = self.parse(json.dumps(legacy))
        self.assertEqual(profile["difficulty"], "standard")
        self.assertEqual(profile["achievements"], [])
        self.assertEqual(profile["stats"]["integrity"], 100)
        self.assertIn("campaign_readiness", profile["stats"])


class AchievementTests(unittest.TestCase):
    def test_definitions_are_well_formed(self):
        ids = [a["id"] for a in achievements.ACHIEVEMENTS]
        self.assertEqual(len(ids), len(set(ids)))
        for a in achievements.ACHIEVEMENTS:
            self.assertTrue(a["label"] and a["description"] and a["icon"], a["id"])
            self.assertTrue(callable(a["check"]), a["id"])

    def test_fresh_career_has_none_and_a_vote_unlocks_one(self):
        profile = _new()
        self.assertEqual(achievements.check_achievements(profile), [])
        profile["vote_history"] = [{"vote": "Aye", "party_whip": "Aye", "followed_whip": True}]
        unlocked = [a["id"] for a in achievements.check_achievements(profile)]
        self.assertEqual(unlocked, ["first_vote"])
        self.assertEqual(achievements.check_achievements(profile), [], "achievements are only awarded once")

    def test_rising_tide_needs_a_real_polling_gain(self):
        profile = _new()
        career._ensure_polling_state(profile)
        self.assertNotIn("rising_tide", [a["id"] for a in achievements.check_achievements(profile)])
        profile["voting_intention"]["Labour"] += 3.5
        self.assertIn("rising_tide", [a["id"] for a in achievements.check_achievements(profile)])

    def test_rebel_requires_voting_against_the_whip(self):
        profile = _new()
        profile["vote_history"] = [{"vote": "Abstain", "party_whip": "Aye", "followed_whip": False}]
        self.assertNotIn("rebel", [a["id"] for a in achievements.check_achievements(profile)])
        profile["vote_history"].append({"vote": "No", "party_whip": "Aye", "followed_whip": False})
        self.assertIn("rebel", [a["id"] for a in achievements.check_achievements(profile)])

    def test_earned_achievements_are_sticky(self):
        profile = _new()
        profile["stats"]["integrity"] = 95
        self.assertIn("peak", [a["id"] for a in achievements.check_achievements(profile)])
        profile["stats"]["integrity"] = 10
        achievements.check_achievements(profile)
        self.assertIn("peak", profile["achievements"])

    def test_government_and_election_milestones(self):
        profile = _new(difficulty="hard")
        profile.update(role="prime_minister", seats_won=2)
        got = {a["id"] for a in achievements.check_achievements(profile)}
        self.assertTrue({"minister", "cabinet", "prime_minister", "reelected", "against_the_odds"} <= got)

    def test_malformed_profile_never_crashes(self):
        profile = {"vote_history": [None, "x"], "stats": {"integrity": None}, "annual_reports": [1], "manifesto_history": [{"promises": [None]}]}
        achievements.check_achievements(profile)


class DifficultyAndHistoryTests(unittest.TestCase):
    def test_difficulty_changes_starting_stats(self):
        relaxed, standard, hard = (_new(difficulty=d) for d in ("relaxed", "standard", "hard"))
        self.assertGreater(relaxed["stats"]["constituency_support"], standard["stats"]["constituency_support"])
        self.assertLess(hard["stats"]["constituency_support"], standard["stats"]["constituency_support"])
        self.assertEqual(standard["stats"]["party_trust"], career.DEFAULT_STATS["party_trust"] + career.DATA["ambitions"][standard["ambition"]]["effects"].get("party_trust", 0))

    def test_unknown_difficulty_falls_back_to_standard(self):
        self.assertEqual(_new(difficulty="nightmare")["difficulty"], "standard")

    def test_election_threshold_and_ethics_limit_follow_difficulty(self):
        for key, spec in career.DIFFICULTIES.items():
            profile = _new(difficulty=key)
            fake = make_fake_streamlit(career_profile=profile, seed=5)
            with patch.object(career, "st", fake):
                career._hold_election(profile)
            self.assertEqual(profile["election_result"]["threshold"], spec["election_threshold"])
            self.assertEqual(career._ethics_limit(profile), spec["ethics_limit"])
        thresholds = [career.DIFFICULTIES[k]["election_threshold"] for k in ("relaxed", "standard", "hard")]
        self.assertEqual(thresholds, sorted(thresholds))

    def test_difficulty_data_is_complete(self):
        for key, spec in career.DIFFICULTIES.items():
            self.assertTrue({"label", "description", "election_threshold", "stat_bonus", "ethics_limit"} <= set(spec), key)
            self.assertTrue(set(spec["stat_bonus"]) <= set(career.ATTRIBUTES), key)
        self.assertIn(career.DEFAULT_DIFFICULTY, career.DIFFICULTIES)

    def test_new_career_starts_with_a_snapshot(self):
        profile = _new()
        self.assertEqual([s["label"] for s in profile["stat_history"]], ["Start"])
        self.assertEqual(set(profile["stat_history"][0]["stats"]), set(career.ATTRIBUTES))

    def test_snapshots_replace_same_label_and_are_capped(self):
        profile = _new()
        career._record_stat_snapshot(profile, "T1 Y1 S1")
        profile["stats"]["integrity"] = 11
        career._record_stat_snapshot(profile, "T1 Y1 S1")
        self.assertEqual(len(profile["stat_history"]), 2)
        self.assertEqual(profile["stat_history"][-1]["stats"]["integrity"], 11)
        for i in range(career.STAT_HISTORY_LIMIT + 10):
            career._record_stat_snapshot(profile, f"step {i}")
        self.assertEqual(len(profile["stat_history"]), career.STAT_HISTORY_LIMIT)

    def test_history_frame_is_long_format(self):
        profile = _new()
        career._record_stat_snapshot(profile, "next")
        frame = career._stat_history_frame(profile)
        self.assertEqual(list(frame.columns), ["Step", "Point", "Attribute", "Value"])
        self.assertEqual(len(frame), 2 * len(career.ATTRIBUTES))
        self.assertTrue(career._stat_history_frame({}).empty)

    def test_vote_summary_counts_rebellions_not_abstentions(self):
        profile = {"vote_history": [
            {"vote": "Aye", "party_whip": "Aye"}, {"vote": "No", "party_whip": "Aye"},
            {"vote": "Abstain", "party_whip": "No"}, {"vote": "Aye", "party_whip": "Free vote"},
        ]}
        self.assertEqual(career._vote_summary(profile), (3, 1, 1))


class PartyThemeTests(unittest.TestCase):
    def test_every_party_has_a_valid_theme(self):
        hex_colour = re.compile(r"^#[0-9A-F]{6}$")
        for party in career.PARTY_COLOURS:
            with self.subTest(party=party):
                for colour in career._party_theme(party):
                    self.assertRegex(colour.upper(), hex_colour)

    def test_unknown_party_falls_back_to_independent_grey(self):
        self.assertEqual(career._party_theme("Made Up Party"), career._party_theme("Independent"))

    def test_dark_is_darker_and_pale_is_lighter(self):
        accent, dark, pale = career._party_theme("Labour")
        brightness = lambda c: sum(int(c[i:i + 2], 16) for i in (1, 3, 5))
        self.assertLess(brightness(dark), brightness(accent))
        self.assertGreater(brightness(pale), brightness(accent))
        self.assertEqual(career._mix_hex("#000000", "#FFFFFF", 0.5), "#808080")


class PlaythroughTests(unittest.TestCase):
    """Play whole careers headlessly through the real game functions."""

    def autoplay(self, difficulty, party="Labour", max_sessions=45):
        profile = career.new_profile(name="Bot", constituency="Droitwich and Evesham", party=party, difficulty=difficulty)
        fake = make_fake_streamlit(career_profile=profile, seed=11, party=party)
        sessions = 0
        roles_reached = set()
        with patch.object(career, "st", fake):
            while not profile["game_over"] and sessions < max_sessions:
                career._cast_vote(profile, "Aye")
                offers = career._eligible_promotions(profile)  # accepting is free, so take it before spending actions
                if offers:
                    career._accept_promotion(profile, *offers[-1])
                    roles_reached.add(profile["role"])
                for action in career.ROLES[profile["role"]]["actions"][:career.ACTIONS_PER_SESSION]:
                    career._take_action(profile, action)
                career._advance(profile)
                career._award_achievements(profile)
                sessions += 1
        self.roles_reached = roles_reached
        return profile, sessions

    def test_full_careers_run_on_every_difficulty(self):
        for difficulty in career.DIFFICULTIES:
            with self.subTest(difficulty=difficulty):
                profile, sessions = self.autoplay(difficulty)
                self.assertGreaterEqual(sessions, career.SESSIONS_PER_YEAR * career.ELECTION_AFTER, "should reach a general election")
                self.assertIsNotNone(profile["election_result"])
                self.assertIn("first_vote", profile["achievements"])
                self.assertGreater(len(profile["stat_history"]), 5)
                for value in profile["stats"].values():
                    self.assertTrue(0 <= value <= 100)

    def test_a_career_can_reach_government(self):
        """Guards the promotion/portfolio path: the bot must climb beyond the backbenches."""
        self.autoplay("relaxed")
        self.assertTrue(self.roles_reached & career.GOVERNMENT_ROLES, f"only reached {sorted(self.roles_reached)}")

    def test_playthrough_works_for_non_whipped_parties(self):
        for party in ("Independent", "Sinn Féin", "Reform UK"):
            with self.subTest(party=party):
                profile, _ = self.autoplay("standard", party=party)
                self.assertIsNotNone(profile["election_result"])


if __name__ == "__main__":
    unittest.main()
