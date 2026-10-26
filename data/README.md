# Editable game data

The game reads these JSON files at startup. You can change game content and balance values without editing Python modules.

## Files

- `decisions.json`: policy topics, their five player-facing options, effects, ideology order, Sir Humphrey reactions, and delayed consequences.
- `crises.json`: crisis text and response options. Each response is a two-item array: `[label, effect_object]`.
- `policies.json`: tax controls, tax schemes, spending departments, spending schemes, department nudges, and baseline fiscal parameters. Tax sliders include basic/higher/additional income-tax rates, National Insurance, VAT, fuel and alcohol/tobacco duties, corporation tax, property/wealth taxes, capital gains, inheritance, council tax, land value tax, a financial transactions levy, carbon pricing and sugary-drinks duty.
- `imf_uk_baseline.json`: the external IMF World Economic Outlook vintage, source metadata and UK macroeconomic baseline values.
- `balance_thresholds.json`: required content counts and broad win/sacking-rate guardrails for regression checks.

## Editing a policy decision

Each entry in `decisions.json` has `year`, `block`, and `decision`. The game expects five option labels and five effect objects in the same order as the `ideologies` array. Effects are simplified deltas to game stats, e.g. `"approval": 2` or `"headroom": -1.5`. Use finite numbers and a `message` in each effect so the player gets feedback.

Delayed consequences are keyed by the same year/block and contain option indexes as strings (`"0"` through `"4"`). Each delayed entry uses `after`, `title`, `text`, `warn` and `fx`.

## Editing a crisis

The top-level `crises` object is keyed by a stable crisis ID. Each crisis needs `title`, `humphrey`, and an `opts` array. Each option's effect object uses the same stat keys as policy decisions. Keep at least two responses per crisis.

## Editing Budget controls

`policies.json` holds the numeric model parameters. The `base`, `per`, and `decay` fields in tax definitions are simplified game balance rules; they are not official Treasury costings. Spending and one-off schemes are similarly stylised. If you add a tax lever, preserve its stable key because saves and widget state use that key.

## Refreshing the IMF baseline

When a new IMF WEO edition is released, update `imf_uk_baseline.json`:
1. Update `vintage`, `published`, the official IMF `source_url`, and any notes.
2. Replace the values under `years` using one consistent WEO vintage.
3. Keep the series definitions clear: `deficit` is general government net lending/borrowing (% GDP); `debt` is general government gross debt (% GDP), not PSNFL and not the game's national-debt statistic.

The baseline is intentionally stored locally in the repository: the game does not silently fetch changing external numbers at runtime.

## Career Mode and parliamentary votes

The separate MP Political Career app uses the 650 official constituency names and codes from the ONS July 2024 Westminster constituency register. The player can choose any seat in setup; this is a fictional career and does not mean the player is the current MP for that constituency. Constituency codes are stable identifiers within this boundary vintage. Update the file only when official constituency boundaries change, and preserve the source metadata.

Each parliamentary session offers one featured Commons division, separate from the two career actions. The available votes and party-whip positions live in `career_divisions.json` and are fictionalised gameplay content, not current official party positions or records of historic votes. Voting with the whip can increase party trust; rebellion can build profile and integrity while risking promotion. Voting in line with the player's chosen local priority can increase constituency support when the issue matches.

## Regression check

Run `python sim.py check` after changing content. It checks content shape and non-finite effects, then runs a deterministic sample of games against broad per-party win and sacking thresholds. Use `python sim.py check 50 Hardcore` to sample more seeds. A failure means investigate the balance change; it does not automatically mean the content is wrong.
