# MP Political Career

A standalone Streamlit political career game. Start as a backbench MP in a real Westminster constituency, vote in simulated Commons divisions, represent local priorities, build your parliamentary reputation and pursue promotions into ministerial office.

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

- Choose an MP name, party, constituency, starting ambition and local campaign priority.
- Each parliamentary session gives you **one featured Commons vote** and **two career actions**.
- Three fictional constituent cases arrive in a session inbox. Investigating, raising an issue in Parliament, or coordinating local partners each uses one of your two career-action slots; matching your chosen local priority gives a small bonus.
- Following the party whip usually builds party trust. Rebelling can raise your public profile and integrity while making promotion harder.
- Career actions develop constituency support, party trust, parliamentary influence, public profile, policy expertise and integrity.
- Three sessions make a career year. A general election takes place after five years. Win your seat to continue; lose it and that career ends.
- Promotions unlock new roles and actions, from MP through Parliamentary Private Secretary or Select Committee Chair, then ministerial ranks, Secretary of State, Chancellor and Prime Minister.

These are simplified fictional game mechanics, not a prediction of real appointments.

## Project files

- `app.py`: Streamlit app entry point.
- `career.py`: career gameplay, constituency selection, Commons voting and progression.
- `content_store.py`: loads editable JSON data.
- `data/career_content.json`: career roles, action choices and promotion rules.
- `data/constituencies_2024.json`: 650 constituency names, codes and nations from the July 2024 Westminster boundary edition.
- `data/career_divisions.json`: fictional divisions, simulated party-whip positions and local-priority categories.
- `data/README.md`: data structure and editing guidance.

The constituency register is based on the Office for National Statistics' *Westminster Parliamentary Constituencies (July 2024) Names and Codes in the UK (V2)*. It identifies seats but does not identify current MPs or imply that the fictional player is the sitting member. Update the data file when a new boundary review takes effect.

The votes and party-whip positions are simulation content. They are **not** records of real historical divisions or assertions of current official party positions.
