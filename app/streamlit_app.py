"""Guess the caste: a quiz that is also the repo's headline measurement.

Run locally with `streamlit run app/streamlit_app.py`. Rounds append to a local
CSV unless a Google Sheet is configured in secrets, in which case they go there.
"""

from __future__ import annotations

import uuid

import numpy as np
import quiz
import streamlit as st

st.set_page_config(page_title="Guess the caste", page_icon="?", layout="centered")


@st.cache_data
def names():
    return quiz.load_names()


@st.cache_data
def data_score() -> float:
    return quiz.baseline(names())


def log(row: dict) -> None:
    """Append a round. A configured sheet wins; otherwise a local CSV."""
    try:
        connection = st.connection("gsheets", type="gsheets")
    except Exception:
        quiz.append_local(row)
        return
    try:
        existing = connection.read(worksheet="rounds", ttl=0).dropna(how="all")
        import pandas as pd

        connection.update(
            worksheet="rounds",
            data=pd.concat([existing, pd.DataFrame([row])], ignore_index=True),
        )
    except Exception:
        # A misconfigured sheet must not cost the player their round.
        quiz.append_local(row)


def start() -> None:
    st.session_state.session = uuid.uuid4().hex[:12]
    st.session_state.rng = np.random.default_rng()
    st.session_state.asked = 0
    st.session_state.right = 0
    st.session_state.pair = quiz.draw(names(), st.session_state.rng)
    st.session_state.verdict = None


if "session" not in st.session_state:
    start()

table = names()
target = data_score()

st.title("One of these two people is Dalit")
st.caption(
    "Which one? Guessing from the surname alone, exactly as a stranger reading "
    "a form would have to."
)

if st.session_state.asked == 0:
    st.info(
        "Each round records the two surnames shown, which you picked and "
        "whether it was right. Nothing about you is recorded: no name, no "
        "account, no address, only a random id for the session."
    )

pair = st.session_state.pair
left, right = st.columns(2)


def answer(side: str) -> None:
    correct = side == pair.dalit_side
    st.session_state.asked += 1
    st.session_state.right += int(correct)
    st.session_state.verdict = (side, correct)
    log(quiz.log_row(pair, side, st.session_state.session, st.session_state.asked))


with left:
    st.button(
        pair.left,
        use_container_width=True,
        disabled=st.session_state.verdict is not None,
        on_click=answer,
        args=("left",),
    )
with right:
    st.button(
        pair.right,
        use_container_width=True,
        disabled=st.session_state.verdict is not None,
        on_click=answer,
        args=("right",),
    )

if st.session_state.verdict is not None:
    _, correct = st.session_state.verdict
    st.success("Right.") if correct else st.error(f"No. It was {pair.dalit}.")
    if st.button("Next", type="primary"):
        st.session_state.pair = quiz.draw(table, st.session_state.rng)
        st.session_state.verdict = None
        st.rerun()

if st.session_state.asked:
    you = 100 * st.session_state.right / st.session_state.asked
    st.divider()
    st.subheader(f"{st.session_state.right} of {st.session_state.asked}")
    st.progress(min(you / 100, 1.0))
    st.markdown(f"""
| | out of 100 |
|---|---|
| a coin | 50 |
| **you, so far** | **{you:.0f}** |
| the surname data | {100 * target:.0f} |
""")
    st.caption(
        "The bottom row is not a different measurement from your score. It is "
        "the same game played by something that knows every surname's caste "
        "composition, over the 1,000 commonest surnames in India, which is "
        "93% of the names people carry."
    )

st.divider()
st.caption(
    "Caste composition from the 2011 Socio-Economic and Caste Census via "
    "[outkast](https://github.com/appeler/outkast); how common a name is from "
    "the 2017 electoral rolls via "
    "[instate](https://github.com/appeler/instate). The workings are in "
    "[last-name-basis](https://github.com/in-rolls/caste-name-information)."
)
