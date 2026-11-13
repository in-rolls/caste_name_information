# Guess the caste

A quiz that is also the repo's headline measurement.

It draws one Dalit and one non-Dalit at random, shows you their two surnames,
and asks which is which. That is not an illustration of the ranking statistic in
analysis 01; it is the same experiment. That statistic is *defined* as the share
of exactly these pairs in which the Dalit's surname ranks higher, so your score
and the data's score are the same quantity measured the same way.

    a coin              50 out of 100
    you                 ?? out of 100
    the surname data    83 out of 100

## Run it

```
make app-data     # regenerate app/data/names.csv from analysis 01
make app          # streamlit run app/streamlit_app.py
```

## What it draws from

`data/names.csv` holds the 1,000 commonest surnames with how many Dalit and
non-Dalit bearers each has. Two kinds are then dropped before play:

**Religion-marked surnames.** They are near-perfect "not Dalit" tells, together
4.8% of non-Dalit draws against 0.1% of Dalit ones. A player who recognizes them
wins those rounds without knowing anything about caste.

**One surname spelled two ways.** `sing` against `singh` asks about
transliteration. The commoner spelling is kept.

Removing both costs about a point of the score the data achieves. 873 names
remain.

A round never shows the same surname on both sides, which would be
unanswerable, and the baseline is computed over the same restriction, so the
figure quoted is one a player could actually reach. Counting those rounds as the
coin flips they are would put the target a point below anything achievable.

## Logging

One row per round: a timestamp, a random session id, the two surnames, which was
the Dalit, what was picked, and whether it was right. No name, no account, no
address, nothing that identifies a player.

Rounds append to `data/rounds.csv` locally. In deployment, configure a Google
Sheet in Streamlit secrets and they go there instead:

```toml
# .streamlit/secrets.toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/..."
type = "service_account"
project_id = "..."
private_key = "..."
client_email = "..."
```

The sheet needs a worksheet named `rounds`. A misconfigured sheet falls back to
the local file rather than costing the player their round.
