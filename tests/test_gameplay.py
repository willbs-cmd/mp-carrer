"""Smoke tests for the standalone MP Career gameplay systems."""
import unittest

import career


class CareerGameplayTests(unittest.TestCase):
    def setUp(self):
        self.profile = career.new_profile(
            name="Test MP",
            constituency="Droitwich and Evesham",
            ambition="policy_specialist",
            local_mandate="public_services",
            party="Labour",
        )

    def test_new_profile_has_phase_two_and_three_state(self):
        self.assertIn("campaign_readiness", self.profile["stats"])
        self.assertEqual(self.profile["stats"]["campaign_readiness"], 30)
        self.assertIn("faction_standing", self.profile)
        self.assertIn("annual_reports", self.profile)
        self.assertIn("portfolio_id", self.profile)
        self.assertEqual(self.profile["role"], "mp")

    def test_every_news_event_has_two_decisions_with_valid_effects(self):
        self.assertGreaterEqual(len(career.PHASE2_NEWS), 6)
        for event in career.PHASE2_NEWS:
            self.assertGreaterEqual(len(event["choices"]), 2)
            for choice in event["choices"]:
                self.assertTrue(set(choice.get("effects", {})).issubset(career.ATTRIBUTES))

    def test_department_and_network_effects_use_known_attributes(self):
        for action in career.DEPARTMENT_ACTIONS + career.PHASE2_NETWORK_ACTIONS:
            self.assertTrue(set(action.get("effects", {})).issubset(career.ATTRIBUTES), action["id"])
        for strategy in career.LEADERSHIP_STRATEGIES.values():
            self.assertTrue(set(strategy.get("effects", {})).issubset(career.ATTRIBUTES))
        for option in career.CABINET_RESHUFFLE_OPTIONS.values():
            self.assertTrue(set(option.get("effects", {})).issubset(career.ATTRIBUTES))
        self.assertGreaterEqual(len(career.PORTFOLIOS), 10)
        for portfolio in career.PORTFOLIOS.values():
            self.assertGreaterEqual(len(portfolio["targets"]), 2)

    def test_uk_party_tally_weights_are_complete_and_balanced(self):
        self.assertEqual(set(career.SIMULATED_PARTY_WEIGHTS), set(career.DIVISION_DATA["party_names"]))
        self.assertEqual(sum(career.SIMULATED_PARTY_WEIGHTS.values()), 100)
        result = career._simulate_division_result(self.profile, career.DIVISIONS[0], "Aye")
        self.assertIn(result["result"], {"Passed", "Rejected"})
        self.assertEqual(result["ayes"] + result["noes"], 100)
        self.assertEqual(result["abstentions"], 0)

    def test_annual_report_is_created_once_per_year(self):
        self.profile["actions_by_session"] = {"1:1:1": ["question"], "1:1:2": ["casework", "media"]}
        self.profile["vote_history"] = [
            {"term": 1, "year": 1, "session": 1, "followed_whip": True},
            {"term": 1, "year": 1, "session": 2, "followed_whip": False},
        ]
        career._record_annual_report(self.profile)
        career._record_annual_report(self.profile)
        self.assertEqual(len(self.profile["annual_reports"]), 1)
        report = self.profile["annual_reports"][0]
        self.assertIn(report["grade"], {"A", "B", "C", "D", "E", "F"})
        self.assertEqual(report["actions_taken"], 3)
        self.assertEqual(report["votes_cast"], 2)
        self.assertEqual(report["whips_followed"], 1)

    def test_leadership_contest_has_a_sensible_eligibility_gate(self):
        self.assertFalse(career._leadership_eligible(self.profile))
        self.profile["role"] = "secretary_state"
        self.assertTrue(career._leadership_eligible(self.profile))
        self.profile["leadership_cooldown_year"] = 2
        self.assertFalse(career._leadership_eligible(self.profile))


if __name__ == "__main__":
    unittest.main()
