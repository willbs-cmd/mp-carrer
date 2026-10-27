"""Smoke tests for the standalone MP Career gameplay systems."""
import json
import unittest
from pathlib import Path

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

    def test_navigation_uses_clear_named_sections(self):
        from unittest.mock import patch

        with patch.object(career.st, "session_state", {}):
            career._set_active_tab("Nation")
            self.assertEqual(career.st.session_state["mp_active_nav"], "Nation")
            career._set_active_tab("Press")
            self.assertEqual(career.st.session_state["mp_active_nav"], "Press")
            career._set_active_tab("Not a real section")
            self.assertEqual(career.st.session_state["mp_active_nav"], "Press")

    def test_fictional_voting_intention_is_normalised_and_moves(self):
        self.assertGreaterEqual(len(career.POLLING_BASELINE), 10)
        self.assertGreaterEqual(len(career.POLLING_ACTIONS), 3)
        self.assertTrue(set(career.POLLING_BASELINE).issuperset({"Labour", "Conservative", "Reform UK"}))
        shares = self.profile["voting_intention"]
        self.assertAlmostEqual(sum(shares.values()), 100.0, places=1)
        career._ensure_polling_state(self.profile)
        self.assertTrue(self.profile["polling_history"])
        self.assertIn("polling_baseline", self.profile)
        before = dict(self.profile["voting_intention"])
        shifted = career._shift_party_poll(self.profile, "Labour", 1.4)
        self.assertGreater(shifted, 0)
        self.assertAlmostEqual(sum(self.profile["voting_intention"].values()), 100.0, places=1)
        self.assertGreater(self.profile["voting_intention"]["Labour"], before["Labour"])
        career._advance_voting_intention(self.profile)
        self.assertAlmostEqual(sum(self.profile["voting_intention"].values()), 100.0, places=1)
        self.assertLessEqual(len(self.profile["polling_history"]), 45)

    def test_polling_actions_use_valid_career_attributes(self):
        for action in career.POLLING_ACTIONS:
            self.assertIn("poll_shift", action)
            self.assertTrue(set(action.get("effects", {})).issubset(career.ATTRIBUTES), action["id"])

    def test_manifesto_promises_affect_election_score(self):
        self.assertGreaterEqual(len(career.MANIFESTO_PLEDGES), 6)
        self.assertEqual(self.profile["manifesto_pledges"], [])
        self.profile["manifesto_pledges"] = [
            {
                "id": "nhs_access",
                "label": career.MANIFESTO_PLEDGES["nhs_access"]["label"],
                "attribute": "policy_expertise",
                "threshold": 20,
                "status": "pending",
            },
            {
                "id": "transparency",
                "label": career.MANIFESTO_PLEDGES["transparency"]["label"],
                "attribute": "integrity",
                "threshold": 99,
                "status": "pending",
            },
        ]
        effect, results = career._score_manifesto_pledges(self.profile)
        self.assertEqual(effect, 0)
        self.assertEqual([row["status"] for row in results], ["kept", "missed"])
        self.assertEqual(len(self.profile["manifesto_history"]), 1)

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

    def test_private_members_bill_and_petition_content_exists(self):
        self.assertGreaterEqual(len(career.PRIVATE_MEMBERS_BILLS), 6)
        self.assertGreaterEqual(len(career.PETITION_TOPICS), 6)
        for bill in career.PRIVATE_MEMBERS_BILLS.values():
            self.assertIn(bill["priority"], career.MANDATES)
            self.assertTrue(bill["label"])
            self.assertTrue(bill["description"])
        for topic in career.PETITION_TOPICS.values():
            self.assertIn(topic["priority"], career.MANDATES)
            self.assertTrue(topic["label"])
            self.assertTrue(topic["description"])
        self.assertIsNone(self.profile["private_members_bill"])
        self.assertEqual(self.profile["private_bill_history"], [])
        self.assertIsNone(self.profile["petition_campaign"])
        self.assertEqual(self.profile["petition_history"], [])

    def test_private_bill_stage_rules_and_effects_are_consistent(self):
        valid_stages = {"drafting", "committee", "report", "assented", "defeated"}
        self.assertEqual(set(career.PRIVATE_BILL_STAGES), valid_stages)
        self.assertIsNotNone(career._active_private_bill({
            "private_members_bill": {"stage": "drafting"}
        }))
        for bill in career.PRIVATE_MEMBERS_BILLS.values():
            self.assertIn(bill["priority"], career.MANDATES)

    def test_commons_vote_uses_all_650_seats(self):
        self.assertEqual(sum(career.SIMULATED_PARTY_SEATS.values()), 650)
        self.assertEqual(career.SIMULATED_TOTAL_SEATS, 650)
        self.assertEqual(career.SIMULATED_PARTY_SEATS["Labour"], 404)
        result = career._simulate_division_result(self.profile, career.DIVISIONS[0], "Aye")
        self.assertIn(result["result"], {"Passed", "Rejected"})
        self.assertEqual(result["total_seats"], 650)
        self.assertEqual(result["ayes"] + result["noes"] + result["abstentions"], 650)
        self.assertGreater(result["votes_cast"], 600)
        self.assertEqual(result["non_voting"], 8)

    def test_player_in_a_party_with_no_current_seats_does_not_create_a_651st_seat(self):
        self.profile["party"] = "Fictional Unity Party"
        result = career._simulate_division_result(self.profile, career.DIVISIONS[0], "No")
        self.assertEqual(result["total_seats"], 650)
        self.assertEqual(result["ayes"] + result["noes"] + result["abstentions"], 650)

    def test_parliament_composition_and_map_have_all_uk_seats(self):
        composition = career.PARLIAMENT_COMPOSITION
        self.assertEqual(sum(row["seats"] for row in composition["commons"]["seats"]), 650)
        self.assertEqual(sum(row["seats"] for row in composition["lords"]["seats"]), 797)
        geo_path = Path(__file__).resolve().parents[1] / "data" / "constituencies_2024.geojson"
        geojson = json.loads(geo_path.read_text(encoding="utf-8"))
        self.assertEqual(len(geojson["features"]), 650)
        codes = [feature["properties"]["PCON24CD"] for feature in geojson["features"]]
        self.assertEqual(len(set(codes)), 650)

    def test_party_name_normalisation_for_map_legend(self):
        self.assertEqual(career._canonical_party_name("Conservative"), "Conservative")
        self.assertEqual(career._canonical_party_name("Scottish National Party"), "SNP")
        self.assertEqual(career._canonical_party_name("Liberal Democrat"), "Liberal Democrats")
        self.assertEqual(career._canonical_party_name("Alliance"), "Alliance Party of Northern Ireland")

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
