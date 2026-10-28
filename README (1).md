# Editable game data

Content and balance values live in JSON so they can be changed without touching Python. `tests/test_data.py` validates every file, so a bad edit fails CI with a clear message.

## Files

| File | Contents |
| --- | --- |
| `career_content.json` | Career attributes, starting approaches (`ambitions`), `difficulties`, roles and their actions, promotion rules and the session policy (sessions per year, actions per session, years per Parliament). |
| `career_divisions.json` | The fictional Commons divisions, party-whip positions, the constituency-priority `mandates` and the list of selectable parties. |
| `constituencies_2024.json` | The 650 constituency names, codes and nations (ONS, July 2024 boundary edition). |
| `constituencies_2024.geojson` | Generalised shapes for the 650 constituencies, used by the Parliament map. |
| `parliament_composition_2026-10-26.json` | Dated Commons and Lords party/group totals (650 Commons seats, 797 Lords). |

## Editing content

**Attributes.** The seven attribute keys in `career_content.json` (`constituency_support`, `party_trust`, `parliamentary_influence`, `public_profile`, `policy_expertise`, `integrity`, `campaign_readiness`) are referenced by effects throughout the game. Keep the keys stable; change only labels.

**Roles and actions.** Each role has `rank`, `next` (roles it can be promoted to) and a list of `actions`. An action needs a unique `id`, a `label`, a `description` and an `effects` object of attribute deltas.

**Promotion rules.** `promotion_rules[from_role][to_role]` sets `min_years`, `requirements` (minimum attribute values) and an optional `bonus`. Ministerial roles also need a minimum department delivery rating, set in `DELIVERY_THRESHOLDS` in `career.py`.

**Difficulties.** Each entry in `difficulties` sets:
- `election_threshold`: the score needed to hold your seat (Standard is 45)
- `stat_bonus`: attribute changes applied at the start of a career
- `ethics_limit`: the standards-risk level that triggers a scandal

**Divisions.** Each division has an `id`, `title`, `description`, a `priority` (a key from `mandates`, or `null` for a conscience vote that must also have `local_preference: "Free vote"`) and a `whip` object mapping party names to `Aye`, `No` or `Free vote`. Parties missing from `whip` default to a free vote. These positions are fictional game content, not records of real votes or current party positions.

## Source data

- Constituencies: [ONS Westminster Parliamentary Constituencies (July 2024) Names and Codes in the UK](https://www.data.gov.uk/dataset/90293fcf-9268-4a1a-be3d-d4a20d314604/westminster-parliamentary-constituencies-july-2024-names-and-codes-in-the-uk-v2). Update only when boundaries change, and keep the source metadata. Choosing a seat does not mean the player is its real MP.
- Map shapes: [Open Innovations constituency boundary GeoJSON](https://github.com/open-innovations/constituencies/blob/8e37a221cdfecdde9de0896a58bec9f57278f522/src/_data/geojson/Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BUC.geojson).
- Party totals: refresh `parliament_composition_*.json` from the official state-of-the-parties pages ([Commons](https://members.parliament.uk/parties/Commons), [Lords](https://members.parliament.uk/parties/lords/by-peerage)). If you rename the file, update `PARLIAMENT_COMPOSITION` in `career.py` and the README.
- The Parliament tab also fetches current MP/party labels from the [UK Parliament Members API](https://members-api.parliament.uk/index.html) (cached for six hours). It is informational and is not the fictional player-seat assignment.

## What is fictional

Commons tallies use the 650-seat snapshot as starting arithmetic (the Speaker and non-sitting Sinn Féin MPs do not vote), but whips, bills, news stories, named colleagues, factions, voting intention and election results are invented game mechanics. Voting intention (`POLLING_BASELINE` in `career.py`) is deliberately unreliable and must not be presented as real polling or a forecast.

## Checking changes

```bash
python -m unittest discover -s tests -v
```
