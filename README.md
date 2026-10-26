# MP Political Career

A standalone Streamlit UK Westminster political career game. Start as a fictional backbench MP in a real 2024-era Westminster constituency in England, Scotland, Wales or Northern Ireland. Work through Commons divisions, PMQs, Select Committees, constituency casework, Westminster media, party factions, standards dilemmas and general-election campaigning while seeking ministerial office.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create an app from this repository: `willbs-cmd/mp-carrer`.
2. Set the **Main file path** to `app.py`.
3. Deploy.

This repository is independent of the UK Chancellor Simulator repository. The Chancellor game is not required to run this one.

## How to play

- Choose an MP name, UK parliamentary party, constituency, starting ambition and local campaign priority. The party list includes the main Great Britain parties, Northern Ireland parties and independents.
- The dashboard uses five clear section buttons: Commons, Constituency, Plans & bills, Press & party, and Parliament. The Parliament section shows the House of Commons and House of Lords party/group make-up plus an interactive map colouring all 650 constituencies by current MP party.
- Each parliamentary session gives you **one featured Commons vote** and **two career actions**.
- Three fictional constituent cases arrive in a session inbox. Investigating, raising an issue in Parliament, or coordinating local partners each uses one of your two career-action slots; matching your chosen local priority gives a small bonus.
- **Phase 2 — Westminster politics:** respond to a fictional political news cycle; balance the party leadership, backbench colleagues, local party and cross-party relationships; build allies or rivals; manage parliamentary standards risk; and improve campaign readiness through constituency canvassing.
- Draft a **Private Member's Bill** and try to progress it through sponsorship, second reading, committee, report stage, third reading and a simulated Royal Assent or defeat.
- Launch a **constituency petition**, organise signature drives and present it to a minister or relevant public body when it reaches the game's signature threshold.
- **Phase 3 — Government and leadership:** ministers manage a portfolio, choose a policy target, improve delivery ratings through departmental actions, and complete milestones for bonuses. Stronger delivery can be required for promotion to senior office.
- Prime Ministers can carry out Cabinet reshuffles with political consequences. Eligible senior politicians can contest the fictional party leadership; incumbents face a confidence ballot. Annual Westminster school-report cards grade your performance, and losing your seat generates a final career report.
- Career decisions and news responses use the same two-action budget per parliamentary session, so you must balance local casework, Commons work, political relationships and government delivery.
- Your general-election result now factors in campaign readiness as well as constituency support, party trust, public profile, policy expertise, integrity and parliamentary influence.
- Following the party whip usually builds party trust. Rebelling can raise your public profile and integrity while making promotion harder.
- Career actions develop constituency support, party trust, parliamentary influence, public profile, policy expertise and integrity.
- Three sessions make a career year. The game models a general election at the end of a simplified five-year parliamentary term. Win your seat to continue; lose it and that career ends.
- Promotions unlock new roles and actions, from MP through Parliamentary Private Secretary or Select Committee Chair, then ministerial ranks, Secretary of State, Chancellor and Prime Minister.

These are simplified fictional game mechanics, not a prediction of real appointments.

## Project files

- `app.py`: Streamlit app entry point, responsive Westminster portal styling, and party-colour accents.
- The interface uses party-specific accents for the selected UK party alongside a multi-colour stat-card palette. The Commons timeline, buttons and progress indicators follow the active party theme.
- `career.py`: career gameplay, fictional news events, faction relationships, ethics risk, constituency campaigning, Commons voting, ministerial portfolios, leadership contests, Cabinet reshuffles and annual/final report cards.
- `tests/test_gameplay.py`: regression smoke tests for career state, news-event effects, party tallies, portfolios, report cards, Private Members' Bills and petitions.
- `content_store.py`: loads editable JSON data.
- `data/career_content.json`: career roles, action choices, promotion rules and the campaign-readiness attribute.
- `data/constituencies_2024.json`: 650 constituency names, codes and nations from the July 2024 Westminster boundary edition.
- `data/constituencies_2024.geojson`: the 650 generalised 2024 constituency shapes used for the interactive party map.
- `data/parliament_composition_2026-10-26.json`: dated Commons and Lords party/group totals used for composition charts and the Commons division model.
- `data/career_divisions.json`: fictional divisions, simulated party-whip positions and local-priority categories.
- `data/README.md`: data structure and editing guidance.

The constituency register is based on the Office for National Statistics' *Westminster Parliamentary Constituencies (July 2024) Names and Codes in the UK (V2)*. It identifies seats but does not identify current MPs or imply that the fictional player is the sitting member. Update the data file when a new boundary review takes effect.

The Parliament tab's party composition is a dated official snapshot; constituency map colours and MP names are fetched from the UK Parliament Members API and cached for six hours. If the API is unavailable, party totals remain visible while the map shows a temporary warning. Commons division tallies use a 650-seat model, but whip positions and bills remain fictional game rules. The votes, party-whip positions, news stories, named political colleagues and faction relationships are simulation content. They are **not** records of real historical divisions, live headlines, claims about real MPs, or assertions of current official party positions. Northern Ireland parties and independent MPs default to a free vote unless a fictional game whip is explicitly set. The simulated vote tallies and general-election result are abstract game mechanics, not forecasts or official results.
