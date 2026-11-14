"""Render analysis 11's note from its outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", "out/fig"
CATS = ["SC", "ST", "OBC", "General"]


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def main() -> None:
    path = TAB / "summary.json"
    if not path.exists():
        print("skipped: analysis 11 not built")
        return
    s = json.loads(path.read_text())
    h_raw, h_rj = s["headline"]["raw"], s["headline"]["rajasthan"]
    tk = s["tokens"]
    rk = s["ranking"]
    ok = s["outkast"]
    tokens = pd.read_csv(TAB / "tokens.csv")
    top = pd.read_csv(TAB / "commonest_tokens.csv")
    compare = pd.read_csv(TAB / "outkast_compare.csv")
    split = pd.read_csv(TAB / "by_category.csv")

    raw_share = s["category_share_raw"]
    contest_share = s["contest_category_share_raw"]
    by_source = s["by_source"]

    top_rows = "\n".join(
        f"| `{r.token}` | {r.n:,} | {_pct(r.share_of_candidates)} | "
        f"{_pct(r.share_SC)} | {_pct(r.share_ST)} | {_pct(r.share_OBC)} | "
        f"{_pct(r.share_General)} | {r.tier} |"
        for r in top.itertuples()
    )
    det = tokens[tokens["tier"] == "deterministic"]
    det_examples = ", ".join(
        f"`{r.token}` ({r.majority}, {_pct(r.purity)})"
        for r in det[det["is_jati_name"]]
        .sort_values("n", ascending=False)
        .head(8)
        .itertuples()
    )
    scores = pd.read_csv(TAB / "scores.csv").set_index(
        ["sample", "cue", "fold", "weighting"]
    )

    def sex(sample, cue):
        return scores.loc[(sample, cue, "district", "raw"), "mistakes_per_100"]

    neither = ", ".join(f"`{t}`" for t in tk["deterministic_neither"])
    verma = tokens.set_index("token").loc["verma"]
    kanwar = tokens.set_index("token").loc["kanwar"]
    kaur = tokens.set_index("token").loc["kaur"]
    abstain_names = ", ".join(f"`{t}`" for t in tk["abstain_given_names"][4:12])

    split_rows = "\n".join(
        f"| {c} | {_pct(g.loc[g.category == c, 'share'].item())} | "
        f"{g.loc[g.category == c, 'blind_wrong_per_100'].item():.0f} | "
        f"**{g.loc[g.category == c, 'wrong_per_100'].item():.0f}** |"
        for g in [split[split["weighting"] == "rajasthan"]]
        for c in ["OBC", "General", "ST", "SC"]
    )

    disagree = compare[compare["token"].isin(ok["disagree_by_more_than_20_points"])]
    disagree_rows = "\n".join(
        f"| `{r.token}` | {r.n:,} | {r.secc_n:,} | {_pct(r.election_share_SC)} | "
        f"{_pct(r.secc_share_SC)} |"
        for r in disagree.sort_values("secc_n", ascending=False).itertuples()
    )

    md = f"""# What a surname reveals about caste category in Rajasthan

Every other analysis here that sorts people into census categories can tell a
Dalit or an Adivasi from everyone else, and nothing more, because SECC records
nothing finer. In Rajasthan "everyone else" is about seven people in ten, and
the line that matters inside it, between Other Backward Classes and General,
is one the census never drew. Panchayat elections draw it. Every candidate for
a village council seat declares a category to stand, and the State Election
Commission publishes it beside the name.

Pick a Rajasthani at random, know only the last word of their name, and guess
their category. Knowing nothing, you are wrong **{h_rj['blind']:.0f} times in
100**, because you guess OBC for everyone. With the name you are wrong
**{h_rj['surname']:.0f}**. That closes {s['gap_closed_share']['rajasthan']:.0f}%
of the gap, about what analysis 08 found for four categories in Karnataka,
and it is measured on districts the guesser has never seen.

## Scope, before the numbers

Three things about the source shape everything below.

**The category is self-declared.** It is what the candidate wrote on a
nomination form to stand for a seat, checked to the extent a returning officer
checks it. For a reserved seat a certificate is required; for a general seat
nothing is.

**The sample is shaped by reservation.** A seat reserved for Scheduled Tribes
takes only ST candidates, and Rajasthan reserves seats in proportion to local
population, so the tribal south sends whole slates of ST candidates. Among the
2020-22 sarpanch contestants ST is {_pct(contest_share['ST'])} of the file
against 13.5% of the state; across all {s['rows']:,} records it is
{_pct(raw_share['ST'])}. The raw base rate is a fact about the quota, not about
Rajasthan. So every score is given twice: on the sample as it comes, and with
each record re-weighted so the four categories sit at the state's own shares.
Those shares are 17.8% SC and 13.5% ST from Census 2011, and the remaining
68.7% split OBC:General as 50:19, which is the ratio the state commission and
the Mandal-era estimates put it at. **No census records that split; it is an
assumption**, and moving it moves the re-weighted blind guess directly.

**A third of the names are one word.** {_pct(s['single_token_name_share'])} of
candidates are recorded as `SUNITA` or `KAMLA` or `BABULAL`, and for them the
"surname" a last-token rule reads is the given name. This is the same failure
analyses 04, 08 and 10 found in Maharashtra, Karnataka and Kerala, in a fourth
form: not the wrong token, not an initial, but a name that has only one token.

The records are {by_source['sarpanch_2020']:,} sarpanch contestants from
2020-22, {by_source['ward_2020']:,} ward panch winners from the same
elections, and {by_source['sarpanch_2005'] + by_source['sarpanch_2010'] + by_source['sarpanch_2015']:,}
sarpanch winners from 2005, 2010 and 2015, across {s['districts']} districts.
Only the first file names a father or husband. {s['dropped']['no_surname']}
records had no readable name and {sum(s['dropped']['unmappable_category'].values())}
had a category outside the four; both were dropped. {_pct(s['devanagari_name_share'])}
of names are in Devanagari; the commonest Devanagari tokens are mapped to
their Latin spelling by hand, and {_pct(s['devanagari_surname_left_share'])}
of records keep a Devanagari token that forms its own cell.

## The headline, and what a relative's surname adds

| cue | sample as it comes | re-weighted to Rajasthan |
|---|---|---|
| knowing nothing | {h_raw['blind']:.1f} | {h_rj['blind']:.1f} |
| last token of the name | **{h_raw['surname']:.1f}** | **{h_rj['surname']:.1f}** |
| last token, names of two or more words | {h_raw['surname_named']:.1f} | {h_rj['surname_named']:.1f} |
| *2020-22 sarpanch contestants with a recorded relative's surname:* | | |
| knowing nothing | {h_raw['blind_contest']:.1f} | {h_rj['blind_contest']:.1f} |
| own surname | {h_raw['surname_contest']:.1f} | {h_rj['surname_contest']:.1f} |
| father's or husband's surname | {h_raw['father_contest']:.1f} | {h_rj['father_contest']:.1f} |
| both | **{h_raw['both_contest']:.1f}** | **{h_rj['both_contest']:.1f}** |

Mistakes per 100, from `out/tab/scores.csv`. Every figure is
leave-one-district-out: the table used to score a district is built from the
other {s['districts'] - 1}. That is stricter than the leave-one-person-out the
other analyses use, and deliberately so, because a jati that lives in one
district would otherwise score itself. Leave-one-person-out gives
{h_raw['surname_self_loo']:.1f} instead of {h_raw['surname']:.1f}, so about two
of the mistakes are geography the name carries and a stranger would not have.

![Mistakes per hundred by cue]({FIG}/by_cue.png)

Only the 2020-22 sarpanch contestant records also give a father's or husband's
name. Among the {int(scores.loc[('sarpanch_2020', 'surname', 'district', 'raw'), 'people']):,}
candidates with a usable relative's surname, using the candidate's own surname
gives **{h_rj['surname_contest']:.1f} incorrect caste-category guesses per 100
candidates**; using both surnames gives **{h_rj['both_contest']:.1f} mistakes
per 100**. Adding the relative's surname therefore saves about
**{h_rj['surname_contest'] - h_rj['both_contest']:.0f} mistakes per 100 candidates**
when guessing SC, ST, OBC or General. Both figures use the same candidates,
category weights and held-out districts. The pooled surname error of
{h_rj['surname']:.1f} per 100 above uses the larger sample that also includes
election winners, so the gain from the extra surname is measured against the
{h_rj['surname_contest']:.1f} baseline for contestants with a relative's surname.

Using only the father's or husband's surname gives
{h_rj['father_contest']:.1f} mistakes per 100 candidates, close to the
{h_rj['surname_contest']:.1f} from the candidate's own surname. The pair cell resolves
{scores.loc[('sarpanch_2020', 'both', 'district', 'raw'), 'share_resolved_by_pair']:.0f}%
of contestants and the surname alone the rest. One might expect the gain to
come from women, whose own `Devi` says nothing and whose husband's `Meena`
says everything; it does not. Fitted and scored within each sex, the surname
leaves {sex('sarpanch_2020_men', 'surname'):.0f} for men and
{sex('sarpanch_2020_women', 'surname'):.0f} for women, and both cues together
{sex('sarpanch_2020_men', 'both'):.0f} and {sex('sarpanch_2020_women', 'both'):.0f}.
A woman's recorded name is as often `Sunita Meena` as `Sunita Devi`.

Restricting to names with two or more words, where there is a surname to read,
takes the error from {h_rj['surname']:.0f} to {h_rj['surname_named']:.0f}. The
difference is what the one-word names cost.

## It discriminates better than it decides

The ranking measure from analysis 01: take one person from the category and
one from outside it, rank the pair by what their surnames say, and count how
often the one in the category ranks higher. Half is no information.

| contrast | ranks the member higher |
|---|---|
| Scheduled Caste against the rest | **{rk['SC vs rest | surname']:.2f}** |
| Scheduled Tribe against the rest | **{rk['ST vs rest | surname']:.2f}** |
| OBC against General | **{rk['OBC vs General | surname']:.2f}** |

From `out/tab/ranking.csv`. The OBC/General line, which nothing in SECC can
draw, is drawn about as well by the surname as the SC line is. The national
SECC figures in analysis 01 are 0.80 for Dalit and 0.91 for Adivasi, on a
different population with a different last-token rule, so read the gap as a
direction and not a distance.

## Who the guess fails

| category | share of Rajasthan | wrong knowing nothing | wrong with the surname |
|---|---|---|---|
{split_rows}

Re-weighted, from `out/tab/by_category.csv`. The blind guess says OBC, so it is
right about every OBC and wrong about everyone else; the surname fixes most of
the ST errors and few of the SC ones. Analysis 05 found the same direction
nationally and analysis 08 in Karnataka: the guess is wrong most often about
the people the categories exist for. Here it is wrong about
{split.query("weighting == 'rajasthan' and category == 'SC'")['wrong_per_100'].item():.0f}
of every 100 Dalits.

## Which surnames settle it

{tk['count']} tokens are carried by {tk['min_n']} or more candidates, covering
{_pct(tk['people_covered_share'])} of records. Each is placed by how one-sided
its category is:

- **deterministic**, at least 90% one category: {tk['tiers']['deterministic']}
  tokens, {_pct(tk['tier_people_share']['deterministic'])} of records;
- **informative**, the rest that move the guess: {tk['tiers']['informative']}
  tokens, {_pct(tk['tier_people_share']['informative'])};
- **abstain**, a majority within five points of that category's base rate:
  {tk['tiers']['abstain']} tokens, {_pct(tk['tier_people_share']['abstain'])}.

![Purity against frequency, every token with 40 or more bearers]({FIG}/tokens.png)

The settled names are mostly the name of the caste itself. Of the
{tk['deterministic']} deterministic tokens, **{tk['deterministic_jati_names']}
are literally a jati name** ({_pct(tk['deterministic_jati_names'] / tk['deterministic'])})
by a hand list in `pipeline.py`, and {tk['deterministic_clan_names']} more are
the clan of one: Shekhawat and Ranawat among Rajputs, Godara among Jats, Katara
and Ninama among Bhils. The commonest are {det_examples}. That leaves
{len(tk['deterministic_neither'])}: {neither}. A surname in Rajasthan pins the
category when it *is* the category, and Yadav, Meena and Bairwa are not a
signal that has to be learned; they are the answer written on the form.

Two of the leftovers are findings. **`verma` is {_pct(verma['share_SC'])}
Scheduled Caste** here, on {int(verma['n'])} candidates, a surname several
communities carry elsewhere in north India and one Dalit communities have
taken in Rajasthan. **`kanwar` is {_pct(kanwar['share_General'])} General**
on {int(kanwar['n']):,}, because it is what Rajput women are called, the female
counterpart of `singh`; a sex-marking name that carries caste, which `devi`
does not. And `kaur`, {int(kaur['n'])} Sikh women, splits
{_pct(kaur['share_OBC'])} OBC to {_pct(kaur['share_SC'])} SC.

The abstain tier is almost entirely given names. After `bai`, `kumar`,
`kumari` and `chand` it reads {abstain_names}: people recorded by one name,
whose last token is their first.

## Where the ambiguous mass is

| token | n | share of records | SC | ST | OBC | General | tier |
|---|---|---|---|---|---|---|---|
{top_rows}

From `out/tab/commonest_tokens.csv`. The first three names cover a quarter of
the records and none of them settles anything. `devi` is every category at
roughly the state's rate. `singh` is half General and two fifths OBC, so it
moves the guess and remains wrong about half its bearers. `ram` and `lal` are
the Dalit end of the same problem, a third SC each, still short of a majority.
Analysis 01's finding that the commonest names tell you least holds here with
four categories as it did with three.

## Against SECC

outkast's Rajasthan extract holds {ok['secc_tokens']} surnames that cleared a
100-record floor, and {ok['tokens_in_both']} of them are among the election
tokens above. For those, the election data's SC share correlates with SECC's
at **{ok['corr_SC_reweighted']:.3f}** and its ST share at
**{ok['corr_ST_reweighted']:.3f}** (re-weighted; {ok['corr_SC_raw']:.3f} and
{ok['corr_ST_raw']:.3f} raw). Two sources, one a census of heads of household
and the other a list of people who stood for office a decade later, agree on
what a name means. SECC cannot see OBC against General, so the comparison stops
there.

The disagreements are small cells and point one way:

| token | election n | SECC n | SC share, election | SC share, SECC |
|---|---|---|---|---|
{disagree_rows}

From `out/tab/outkast_compare.csv`. `suman` is a woman's given name in the
election file and a surname in SECC, so it is not the same token. Solanki,
Bhati, Tanwar and Panwar are Rajput clan names that Dalit communities in
Rajasthan also carry, and a file of candidates for reserved seats holds more
of the latter than a census does. `garg` and `bharti` are cells of sixty.

## How the numbers are computed

The surname is the last token of the candidate's own name after cutting at a
slash or `S/O` and dropping single letters. The guess for a token is its
commonest category among candidates in *other* districts; a token no other
district has seen falls back to the blind guess. Re-weighting multiplies each
record by the ratio of its category's assumed state share to its sample share,
and both the table and the score use the weights. `both` uses the
(surname, father's surname) pair where another district has seen it, else the
surname. The token tiers are in-sample and unweighted, being a description of
the tokens rather than a score.

---

*Sarpanch and ward panch records from the Rajasthan State Election Commission,
collected in
[local_elections_rajasthan](https://github.com/in-rolls/local_elections_rajasthan).*
"""
    out = HERE / "note.md"
    out.write_text(md)
    print(f"wrote {out} ({len(md.splitlines())} lines)")


if __name__ == "__main__":
    main()
