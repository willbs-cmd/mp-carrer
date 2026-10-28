"""Validate the editable JSON content so a bad edit fails CI with a clear message."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
VOTES = {"Aye", "No", "Free vote"}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class DataFileTests(unittest.TestCase):
    def test_every_json_file_parses(self):
        files = list(DATA.glob("*.json")) + [DATA / "constituencies_2024.geojson"]
        self.assertGreaterEqual(len(files), 5)
        for path in files:
            with self.subTest(file=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_constituency_register_and_map_have_650_seats(self):
        seats = load("constituencies_2024.json")["constituencies"]
        self.assertEqual(len(seats), 650)
        self.assertEqual(len({s["code"] for s in seats}), 650, "constituency codes must be unique")
        self.assertEqual(len({s["name"] for s in seats}), 650, "constituency names must be unique")
        self.assertEqual(len(load("constituencies_2024.geojson")["features"]), 650)

    def test_parliament_composition_totals(self):
        comp = load("parliament_composition_2026-10-26.json")
        self.assertEqual(sum(x["seats"] for x in comp["commons"]["seats"]), 650)
        self.assertEqual(sum(x["seats"] for x in comp["lords"]["seats"]), 797)


class CareerContentTests(unittest.TestCase):
    def setUp(self):
        self.content = load("career_content.json")
        self.attributes = set(self.content["attributes"])
        self.roles = self.content["roles"]

    def test_roles_link_to_real_roles_and_actions_use_real_attributes(self):
        for role_id, role in self.roles.items():
            with self.subTest(role=role_id):
                for nxt in role.get("next", []):
                    self.assertIn(nxt, self.roles)
                ids = [a["id"] for a in role["actions"]]
                self.assertEqual(len(ids), len(set(ids)), "action ids must be unique within a role")
                for action in role["actions"]:
                    self.assertTrue(set(action["effects"]) <= self.attributes, action["id"])

    def test_promotion_rules_reference_real_roles_and_attributes(self):
        for from_role, targets in self.content["promotion_rules"].items():
            self.assertIn(from_role, self.roles)
            for to_role, spec in targets.items():
                with self.subTest(rule=f"{from_role}->{to_role}"):
                    self.assertIn(to_role, self.roles)
                    self.assertTrue(set(spec["requirements"]) <= self.attributes)
                    self.assertTrue(set(spec.get("bonus", {})) <= self.attributes)

    def test_ambitions_and_difficulties_use_real_attributes(self):
        for key, ambition in self.content["ambitions"].items():
            self.assertTrue(set(ambition["effects"]) <= self.attributes, key)
        for key, spec in self.content["difficulties"].items():
            self.assertTrue(set(spec["stat_bonus"]) <= self.attributes, key)
        self.assertIn("standard", self.content["difficulties"])

    def test_session_policy_is_sane(self):
        policy = self.content["session_policy"]
        for key in ("sessions_per_year", "actions_per_session", "election_after_years"):
            self.assertGreaterEqual(int(policy[key]), 1, key)


class DivisionTests(unittest.TestCase):
    def setUp(self):
        self.data = load("career_divisions.json")

    def test_divisions_are_complete(self):
        divisions = self.data["divisions"]
        self.assertGreaterEqual(len(divisions), 15)
        ids = [d["id"] for d in divisions]
        self.assertEqual(len(ids), len(set(ids)), "division ids must be unique")
        for division in divisions:
            with self.subTest(division=division["id"]):
                if division["priority"] is None:
                    # Conscience votes have no local-priority link, but must then be a free vote.
                    self.assertEqual(division["local_preference"], "Free vote")
                else:
                    self.assertIn(division["priority"], self.data["mandates"])
                self.assertIn(division["local_preference"], VOTES)
                self.assertTrue(division["title"] and division["description"])
                self.assertTrue(set(division["whip"].values()) <= VOTES)

    def test_whips_only_name_known_parties(self):
        parties = set(self.data["party_names"])
        for division in self.data["divisions"]:
            unknown = set(division["whip"]) - parties
            self.assertFalse(unknown, f"{division['id']} whips unknown parties: {sorted(unknown)}")


if __name__ == "__main__":
    unittest.main()
